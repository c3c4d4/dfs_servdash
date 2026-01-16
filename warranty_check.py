import pandas as pd
import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import init, Fore, Style
import re
import time
import threading
import csv
from bs4 import BeautifulSoup
import shutil
import os

init(autoreset=True)

# Thread lock for cache operations
cache_lock = threading.Lock()

INPUT_CSV = "o2c_unpacked.csv"
CACHE_FILE = "garantia_cache.csv"  # Cache de ITEM -> GARANTIA para evitar rechecagem
BACKUP_CSV = "o2c_unpacked_backup.csv"
BOM_URL = (
    "https://production.wayne.com/asp/BomLookup.asp?Function=BOM&PartNumber={}&Org=6705"
)
MAX_WORKERS = 40
BLOCK_STATUS_CODES = {429, 403, 503}
BLOCK_PAUSE = 60
MAX_RETRIES = 3
BATCH_SIZE = 100
TARGET_YEAR = 2023  # Ano alvo para verificacao

# Mapeamento de texto de garantia para dias numericos
GARANTIA_TEXT_TO_DAYS = {
    "6 MESES": 183,
    "6 MONTHS": 183,
    "12 MESES": 365,
    "12 MONTHS": 365,
    "1 ANO": 365,
    "1 YEAR": 365,
    "18 MESES": 548,
    "18 MONTHS": 548,
    "24 MESES": 730,
    "24 MONTHS": 730,
    "2 ANOS": 730,
    "2 YEARS": 730,
    "36 MESES": 1095,
    "36 MONTHS": 1095,
    "3 ANOS": 1095,
    "3 YEARS": 1095,
}

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
    print(Fore.RED + f"Erro ao ler {INPUT_CSV} com codificacoes conhecidas.")
    exit(1)

# Clean column names
df.columns = [c.strip().replace("\ufeff", "") for c in df.columns]

# Criar backup antes de comecar
if os.path.exists(INPUT_CSV):
    shutil.copy2(INPUT_CSV, BACKUP_CSV)
    print(Fore.GREEN + f"Backup criado: {BACKUP_CSV}")

if "GARANTIA" not in df.columns:
    df["GARANTIA"] = ""

# Funcao para extrair ano da coluna DT_NUM_NF
DATE_COL = "DT_NUM_NF"


def get_year(date_str):
    if pd.isna(date_str):
        return None
    match = re.search(r"(\d{4})", str(date_str))
    if match:
        return int(match.group(1))
    return None


def normalize_garantia_to_days(garantia_text):
    """Converte texto de garantia para numero de dias."""
    if (
        pd.isna(garantia_text)
        or garantia_text == ""
        or garantia_text == "NAO ENCONTRADO"
    ):
        return ""

    garantia_upper = str(garantia_text).upper().strip()

    # Remove prefixos comuns
    for prefix in ["GARANTIA", "WARRANTY", "-", ":"]:
        garantia_upper = garantia_upper.replace(prefix, "").strip()

    # Tenta match direto
    for pattern, days in GARANTIA_TEXT_TO_DAYS.items():
        if pattern in garantia_upper:
            return str(days)

    # Tenta extrair numero de meses
    match = re.search(r"(\d+)\s*(MES|MONTH|M)", garantia_upper)
    if match:
        meses = int(match.group(1))
        dias = int(meses * 30.44)  # Media de dias por mes
        # Arredonda para valores conhecidos
        if dias <= 183:
            return "183"
        elif dias <= 365:
            return "365"
        elif dias <= 548:
            return "548"
        elif dias <= 730:
            return "730"
        else:
            return "1095"

    # Tenta extrair numero de anos
    match = re.search(r"(\d+)\s*(ANO|YEAR|Y)", garantia_upper)
    if match:
        anos = int(match.group(1))
        if anos == 1:
            return "365"
        elif anos == 2:
            return "730"
        elif anos == 3:
            return "1095"

    # Retorna o valor original se nao conseguir normalizar
    return garantia_text


# Carregar cache existente de ITEM -> GARANTIA
garantia_cache = {}
if os.path.exists(CACHE_FILE):
    print(Fore.CYAN + f"Carregando cache de GARANTIA de {CACHE_FILE}...")
    try:
        cache_df = pd.read_csv(CACHE_FILE, sep=";", dtype=str, encoding="utf-8-sig")
        for _, row in cache_df.iterrows():
            if pd.notna(row.get("ITEM")) and pd.notna(row.get("GARANTIA")):
                garantia_cache[row["ITEM"]] = row["GARANTIA"]
        print(Fore.GREEN + f"Cache carregado com {len(garantia_cache)} ITEMs.")
    except Exception as e:
        print(Fore.YELLOW + f"Erro ao carregar cache: {e}. Continuando sem cache.")

# 1. Preencher todos pre-TARGET_YEAR com valor vazio (nao verificar)
print(Fore.CYAN + f"Identificando linhas para verificar (ano >= {TARGET_YEAR})...")


def extract_garantia_from_html(html):
    """Extrai informacao de garantia do HTML da BOM."""
    soup = BeautifulSoup(html, "html.parser")
    for td in soup.find_all("td"):
        txt = (
            td.get_text(separator=" ", strip=True).replace("\n", " ").replace("\r", " ")
        )
        if txt.upper().startswith("GARANTIA"):
            return txt.strip()
        elif txt.upper().startswith("WARRANTY"):
            return txt.strip()
    return ""


def check_garantia_item(part_number):
    """Verifica garantia de um ITEM (part_number). Retorna garantia em dias ou texto."""
    # Verificar cache primeiro
    if part_number in garantia_cache:
        return garantia_cache[part_number], None

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
            garantia_text = extract_garantia_from_html(resp.text)
            if garantia_text:
                # Normaliza para dias
                garantia_days = normalize_garantia_to_days(garantia_text)
                return garantia_days if garantia_days else garantia_text, None
            else:
                return "NAO ENCONTRADO", None
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
        + f"Falha ao buscar BOM para {part_number} apos {MAX_RETRIES} tentativas. URL: {url}"
    )
    return None, url


# Filtrar linhas que precisam de verificacao (ano >= TARGET_YEAR e sem GARANTIA)
rows_to_check = df[
    (df["GARANTIA"].isna() | (df["GARANTIA"] == ""))
    & (df[DATE_COL].apply(lambda x: (get_year(x) or 0) >= TARGET_YEAR))
].copy()

print(Fore.CYAN + f"Total de linhas a verificar: {len(rows_to_check)}")

# Obter ITEMs unicos que precisam de verificacao
unique_items_to_check = rows_to_check["ITEM"].dropna().unique().tolist()

# Remover ITEMs ja no cache
items_already_cached = [
    item for item in unique_items_to_check if item in garantia_cache
]
items_to_fetch = [item for item in unique_items_to_check if item not in garantia_cache]

print(Fore.GREEN + f"ITEMs unicos a verificar: {len(unique_items_to_check)}")
print(Fore.GREEN + f"ITEMs ja em cache: {len(items_already_cached)}")
print(Fore.CYAN + f"ITEMs a buscar na API: {len(items_to_fetch)}")

failed_urls = []


def safe_save_dataframe(df_to_save, filename):
    """Salva DataFrame de forma segura, primeiro em arquivo temporario"""
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
    """Salva o cache de ITEM -> GARANTIA em arquivo"""
    cache_df = pd.DataFrame(list(garantia_cache.items()), columns=["ITEM", "GARANTIA"])
    cache_df.to_csv(CACHE_FILE, sep=";", index=False, encoding="utf-8-sig")


# Funcao para processar um ITEM unico
def process_item(item):
    garantia, fail_url = check_garantia_item(item)
    return item, garantia, fail_url


# Processar ITEMs unicos
if items_to_fetch:
    print(Fore.CYAN + f"\nBuscando GARANTIA para {len(items_to_fetch)} ITEMs unicos...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_item, item): item for item in items_to_fetch}

        processed_count = 0
        for future in tqdm(
            as_completed(futures), total=len(futures), desc="Verificando ITEMs"
        ):
            try:
                item, garantia, fail_url = future.result()
                with cache_lock:
                    if garantia:
                        garantia_cache[item] = garantia
                    if fail_url:
                        failed_urls.append((item, fail_url))

                    processed_count += 1

                    # Salvar cache a cada BATCH_SIZE ITEMs
                    if processed_count % BATCH_SIZE == 0:
                        save_cache()
                        print(
                            Fore.YELLOW
                            + f"\nCache salvo com {len(garantia_cache)} ITEMs..."
                        )

            except Exception as e:
                print(Fore.RED + f"Erro inesperado na thread: {e}")

        # Salvar cache final
        save_cache()
        print(Fore.GREEN + f"Cache final salvo com {len(garantia_cache)} ITEMs.")

# Aplicar resultados do cache a todas as linhas
print(Fore.CYAN + "\nAplicando resultados as linhas do DataFrame...")
rows_updated = 0
for idx, row in tqdm(
    rows_to_check.iterrows(), total=len(rows_to_check), desc="Aplicando GARANTIA"
):
    item = row["ITEM"]
    if pd.notna(item) and item in garantia_cache:
        df.at[idx, "GARANTIA"] = garantia_cache[item]
        rows_updated += 1

print(Fore.GREEN + f"{rows_updated} linhas atualizadas com GARANTIA.")

# Salvar DataFrame final
if safe_save_dataframe(df, INPUT_CSV):
    print(Fore.GREEN + "Arquivo final salvo com sucesso!")
else:
    print(Fore.RED + "ERRO: Falha ao salvar arquivo final!")

print(Fore.GREEN + "\nProcessamento finalizado!")
print(Fore.CYAN + f"Resumo:")
print(Fore.CYAN + f"  - Linhas verificadas: {len(rows_to_check)}")
print(Fore.CYAN + f"  - ITEMs unicos checados: {len(unique_items_to_check)}")
print(Fore.CYAN + f"  - Chamadas API realizadas: {len(items_to_fetch)}")
print(
    Fore.CYAN
    + f"  - Reducao de chamadas: {len(rows_to_check) - len(items_to_fetch)} ({100 * (1 - len(items_to_fetch) / max(len(rows_to_check), 1)):.1f}%)"
)

if failed_urls:
    print(Fore.RED + Style.BRIGHT + "\nURLs que falharam apos todas as tentativas:")
    for part, url in failed_urls:
        print(Fore.YELLOW + f"PartNumber: {part}  URL: {url}")
    print(Fore.CYAN + "\nVoce pode testar manualmente essas URLs no navegador.")
else:
    print(Fore.GREEN + "Todos os ITEMs processados com sucesso!")

print(Fore.CYAN + f"\nBackup disponivel em: {BACKUP_CSV}")
