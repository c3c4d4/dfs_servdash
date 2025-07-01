import pandas as pd
import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import init, Fore, Style
import re
import time
import threading
import csv

init(autoreset=True)

INPUT_CSV = 'o2c_unpacked.csv'
BOM_URL = 'https://production.wayne.com/asp/BomLookup.asp?Function=BOM&PartNumber={}&Org=6705'
MAX_WORKERS = 5
BLOCK_STATUS_CODES = {429, 403, 503}
BLOCK_PAUSE = 60
MAX_RETRIES = 3

print(Fore.CYAN + f'Lendo {INPUT_CSV}...')
try:
    df = pd.read_csv(INPUT_CSV, sep=';', dtype=str, encoding='latin1')
except Exception as e:
    print(Fore.RED + f'Erro ao ler {INPUT_CSV}: {e}')
    exit(1)

if 'RTM' not in df.columns:
    df['RTM'] = ''

# Função para extrair ano da coluna DT_NUM_NF
DATE_COL = 'DT_NUM_NF'
def get_year(date_str):
    if pd.isna(date_str):
        return None
    match = re.search(r'(\d{4})', date_str)
    if match:
        return int(match.group(1))
    return None

# 1. Preencher todos pre-2023 com 'NAO' de uma vez
print(Fore.CYAN + 'Marcando RTM = NAO para todos os anos anteriores a 2023...')
pre2023_mask = df['RTM'].eq('') & df[DATE_COL].apply(lambda x: (get_year(x) or 0) < 2023)
df.loc[pre2023_mask, 'RTM'] = 'NAO'
df.to_csv(INPUT_CSV, sep=';', index=False, encoding='latin1')
print(Fore.GREEN + f'{pre2023_mask.sum()} linhas marcadas como NAO (pré-2023).')

# Lock para escrita concorrente
write_lock = threading.Lock()

# Função para atualizar RTM em tempo real
def update_rtm_in_csv(idx, rtm):
    with write_lock:
        # Lê o arquivo, atualiza a linha, e reescreve só aquela linha
        with open(INPUT_CSV, 'r', encoding='latin1', newline='') as f:
            reader = list(csv.reader(f, delimiter=';'))
        header = reader[0]
        rtm_col = header.index('RTM')
        # idx+1 porque header é linha 0
        reader[idx+1][rtm_col] = rtm
        with open(INPUT_CSV, 'w', encoding='latin1', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerows(reader)

def check_bluetooth(row, idx):
    part_number = row['ITEM']
    year = get_year(row[DATE_COL])
    if year is None or year < 2023:
        return 'NAO', None
    url = BOM_URL.format(part_number)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code in BLOCK_STATUS_CODES:
                print(Fore.RED + Style.BRIGHT + f"\nBloqueado pelo servidor (HTTP {resp.status_code}) para {part_number}. Pausando por {BLOCK_PAUSE} segundos...")
                time.sleep(BLOCK_PAUSE)
                continue
            resp.raise_for_status()
            if 'BLUETOOTH' in resp.text.upper():
                update_rtm_in_csv(idx, 'SIM')
                return 'SIM', None
            elif 'BLUETOOH' in resp.text.upper():
                print(Fore.YELLOW + f"Possível erro de digitação em {part_number}: 'BLUETOOH' encontrado.")
                update_rtm_in_csv(idx, 'SIM')
                return 'SIM', None
            else:
                update_rtm_in_csv(idx, 'NAO')
                return 'NAO', None
        except requests.exceptions.Timeout:
            print(Fore.YELLOW + f"Timeout ao buscar BOM para {part_number} (tentativa {attempt}/{MAX_RETRIES})")
            time.sleep(2)
        except Exception as e:
            print(Fore.RED + f"Erro ao buscar BOM para {part_number} (tentativa {attempt}/{MAX_RETRIES}): {e}")
            time.sleep(2)
    print(Fore.MAGENTA + Style.BRIGHT + f"Falha ao buscar BOM para {part_number} após {MAX_RETRIES} tentativas. URL: {url}")
    return None, url

print(Fore.CYAN + 'Verificando RTM para cada linha >= 2023...')
rows_to_check = df[(df['RTM'] == '') & (df[DATE_COL].apply(lambda x: (get_year(x) or 0) >= 2023))].copy()
failed_urls = []

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    future_to_idx = {executor.submit(check_bluetooth, row, idx): idx for idx, row in rows_to_check.iterrows()}
    for future in tqdm(as_completed(future_to_idx), total=len(future_to_idx), desc='Processando'):
        idx = future_to_idx[future]
        try:
            rtm, fail_url = future.result()
        except Exception as e:
            print(Fore.RED + f'Erro inesperado: {e}')
            rtm, fail_url = None, None
        if fail_url:
            failed_urls.append((df.at[idx, 'ITEM'], fail_url))

print(Fore.GREEN + 'Processamento finalizado!')

if failed_urls:
    print(Fore.RED + Style.BRIGHT + '\nURLs que falharam após todas as tentativas:')
    for part, url in failed_urls:
        print(Fore.YELLOW + f'PartNumber: {part}  URL: {url}')
    print(Fore.CYAN + '\nVocê pode testar manualmente essas URLs no navegador.')
else:
    print(Fore.GREEN + 'Todas as linhas processadas com sucesso!') 