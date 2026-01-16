import pandas as pd
import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import init, Fore, Style
import re
import time
import threading
import csv
import shutil
import os

init(autoreset=True)

# Thread lock for cache operations
cache_lock = threading.Lock()

INPUT_CSV = "o2c_unpacked.csv"
CACHE_FILE = "rtm_cache.csv"  # Cache de ITEM -> RTM para evitar rechecagem
BOM_URL = (
    "https://production.wayne.com/asp/BomLookup.asp?Function=BOM&PartNumber={}&Org=6705"
)
MAX_WORKERS = 40
BLOCK_STATUS_CODES = {429, 403, 503}
BLOCK_PAUSE = 60
MAX_RETRIES = 3
TARGET_YEAR = 2023  # Ano alvo para verificação

print(Fore.CYAN + f"Lendo {INPUT_CSV}...")
df = None
for enc in ["utf-8-sig", "latin1", "cp1252"]:
    try:
        df = pd.read_csv(INPUT_CSV, sep=";", dtype=str, encoding=enc)
        print(Fore.GREEN + f"Successfully read {INPUT_CSV} with encoding: {enc}")
        break
    except Exception as e:
        print(Fore.YELLOW + f"Failed to read {INPUT_CSV} with encoding {enc}: {e}")
        continue

if df is None:
    print(Fore.RED + f"Erro ao ler {INPUT_CSV} com codificações conhecidas.")
    exit(1)

# Clean column names
df.columns = [c.strip().replace("\ufeff", "") for c in df.columns]

if "RTM" not in df.columns:
    df["RTM"] = ""

# Função para extrair ano da coluna DT_NUM_NF
DATE_COL = "DT_NUM_NF"


def get_year(date_str):
    if pd.isna(date_str):
        return None
    match = re.search(r"(\d{4})", date_str)
    if match:
        return int(match.group(1))
    return None


# Carregar cache existente de ITEM -> RTM
rtm_cache = {}
if os.path.exists(CACHE_FILE):
    print(Fore.CYAN + f"Carregando cache de RTM de {CACHE_FILE}...")
    try:
        cache_df = pd.read_csv(CACHE_FILE, sep=";", dtype=str, encoding="utf-8-sig")
        for _, row in cache_df.iterrows():
            if pd.notna(row.get("ITEM")) and pd.notna(row.get("RTM")):
                rtm_cache[row["ITEM"]] = row["RTM"]
        print(Fore.GREEN + f"Cache carregado com {len(rtm_cache)} ITEMs.")
    except Exception as e:
        print(Fore.YELLOW + f"Erro ao carregar cache: {e}. Continuando sem cache.")

# 1. Preencher todos pre-2025 com 'NAO' de uma vez (focando apenas em 2025)
print(
    Fore.CYAN + f"Marcando RTM = NAO para todos os anos anteriores a {TARGET_YEAR}..."
)
pre_target_mask = (df["RTM"].isna() | df["RTM"].eq("")) & df[DATE_COL].apply(
    lambda x: (get_year(x) or 0) < TARGET_YEAR
)
df.loc[pre_target_mask, "RTM"] = "NAO"
df.to_csv(INPUT_CSV, sep=";", index=False, encoding="utf-8-sig")
print(
    Fore.GREEN
    + f"{pre_target_mask.sum()} linhas marcadas como NAO (pré-{TARGET_YEAR})."
)


# Função para verificar Bluetooth por ITEM (part_number)
def check_bluetooth_item(part_number):
    """Verifica se um ITEM (modelo) tem Bluetooth. Retorna 'SIM', 'NAO' ou None (falha)."""
    # Verificar cache primeiro
    if part_number in rtm_cache:
        return rtm_cache[part_number], None

    url = BOM_URL.format(part_number)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code in BLOCK_STATUS_CODES:
                print(
                    Fore.RED
                    + Style.BRIGHT
                    + f"\nBloqueado pelo servidor (HTTP {resp.status_code}) para {part_number}. Pausando por {BLOCK_PAUSE} segundos..."
                )
                time.sleep(BLOCK_PAUSE)
                continue
            resp.raise_for_status()
            if "BLUETOOTH" in resp.text.upper():
                return "SIM", None
            elif "BLUETOOH" in resp.text.upper():
                print(
                    Fore.YELLOW
                    + f"Possível erro de digitação em {part_number}: 'BLUETOOH' encontrado."
                )
                return "SIM", None
            else:
                return "NAO", None
        except requests.exceptions.Timeout:
            print(
                Fore.YELLOW
                + f"Timeout ao buscar BOM para {part_number} (tentativa {attempt}/{MAX_RETRIES})"
            )
            time.sleep(2)
        except Exception as e:
            print(
                Fore.RED
                + f"Erro ao buscar BOM para {part_number} (tentativa {attempt}/{MAX_RETRIES}): {e}"
            )
            time.sleep(2)
    print(
        Fore.MAGENTA
        + Style.BRIGHT
        + f"Falha ao buscar BOM para {part_number} após {MAX_RETRIES} tentativas. URL: {url}"
    )
    return None, url


# Filtrar linhas que precisam de verificação (ano >= TARGET_YEAR e sem RTM)
print(Fore.CYAN + f"Identificando linhas para verificar (ano >= {TARGET_YEAR})...")
rows_to_check = df[
    (df["RTM"].isna() | (df["RTM"] == ""))
    & (df[DATE_COL].apply(lambda x: (get_year(x) or 0) >= TARGET_YEAR))
].copy()

print(Fore.CYAN + f"Total de linhas a verificar: {len(rows_to_check)}")

# Obter ITEMs únicos que precisam de verificação
unique_items_to_check = rows_to_check["ITEM"].dropna().unique().tolist()

# Remover ITEMs já no cache
items_already_cached = [item for item in unique_items_to_check if item in rtm_cache]
items_to_fetch = [item for item in unique_items_to_check if item not in rtm_cache]

print(Fore.GREEN + f"ITEMs únicos a verificar: {len(unique_items_to_check)}")
print(Fore.GREEN + f"ITEMs já em cache: {len(items_already_cached)}")
print(Fore.CYAN + f"ITEMs a buscar na API: {len(items_to_fetch)}")

failed_urls = []
BATCH_SIZE = 100


def safe_save_dataframe(df_to_save, filename):
    """Salva DataFrame de forma segura, primeiro em arquivo temporário"""
    temp_file = filename + ".tmp"
    try:
        df_to_save.to_csv(temp_file, sep=";", index=False, encoding="utf-8-sig")
        shutil.move(temp_file, filename)
        return True
    except Exception as e:
        print(Fore.RED + f"Erro ao salvar {filename}: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return False


def save_cache():
    """Salva o cache de ITEM -> RTM em arquivo"""
    cache_df = pd.DataFrame(list(rtm_cache.items()), columns=["ITEM", "RTM"])
    cache_df.to_csv(CACHE_FILE, sep=";", index=False, encoding="utf-8-sig")


# Função para processar um ITEM único
def process_item(item):
    rtm, fail_url = check_bluetooth_item(item)
    return item, rtm, fail_url


# Processar ITEMs únicos
if items_to_fetch:
    print(Fore.CYAN + f"\nBuscando RTM para {len(items_to_fetch)} ITEMs únicos...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_item, item): item for item in items_to_fetch}

        processed_count = 0
        for future in tqdm(
            as_completed(futures), total=len(futures), desc="Verificando ITEMs"
        ):
            try:
                item, rtm, fail_url = future.result()
                with cache_lock:
                    if rtm:
                        rtm_cache[item] = rtm
                    if fail_url:
                        failed_urls.append((item, fail_url))

                    processed_count += 1

                    # Salvar cache a cada BATCH_SIZE ITEMs
                    if processed_count % BATCH_SIZE == 0:
                        save_cache()
                        print(
                            Fore.YELLOW + f"\nCache salvo com {len(rtm_cache)} ITEMs..."
                        )

            except Exception as e:
                print(Fore.RED + f"Erro inesperado na thread: {e}")

        # Salvar cache final
        save_cache()
        print(Fore.GREEN + f"Cache final salvo com {len(rtm_cache)} ITEMs.")

# Aplicar resultados do cache a todas as linhas
print(Fore.CYAN + "\nAplicando resultados às linhas do DataFrame...")
rows_updated = 0
for idx, row in tqdm(
    rows_to_check.iterrows(), total=len(rows_to_check), desc="Aplicando RTM"
):
    item = row["ITEM"]
    if pd.notna(item) and item in rtm_cache:
        df.at[idx, "RTM"] = rtm_cache[item]
        rows_updated += 1

print(Fore.GREEN + f"{rows_updated} linhas atualizadas com RTM.")

# Salvar DataFrame final
if safe_save_dataframe(df, INPUT_CSV):
    print(Fore.GREEN + "Arquivo final salvo com sucesso!")
else:
    print(Fore.RED + "ERRO: Falha ao salvar arquivo final!")

print(Fore.GREEN + "\nProcessamento finalizado!")
print(Fore.CYAN + f"Resumo:")
print(Fore.CYAN + f"  - Linhas verificadas: {len(rows_to_check)}")
print(Fore.CYAN + f"  - ITEMs únicos checados: {len(unique_items_to_check)}")
print(Fore.CYAN + f"  - Chamadas API realizadas: {len(items_to_fetch)}")
print(
    Fore.CYAN
    + f"  - Redução de chamadas: {len(rows_to_check) - len(items_to_fetch)} ({100 * (1 - len(items_to_fetch) / max(len(rows_to_check), 1)):.1f}%)"
)

if failed_urls:
    print(Fore.RED + Style.BRIGHT + "\nURLs que falharam após todas as tentativas:")
    for part, url in failed_urls:
        print(Fore.YELLOW + f"PartNumber: {part}  URL: {url}")
    print(Fore.CYAN + "\nVocê pode testar manualmente essas URLs no navegador.")
else:
    print(Fore.GREEN + "Todos os ITEMs processados com sucesso!")
