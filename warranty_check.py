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

if 'GARANTIA' not in df.columns:
    df['GARANTIA'] = ''

# Lock para escrita concorrente
write_lock = threading.Lock()

def update_garantia_in_csv(idx, garantia):
    with write_lock:
        with open(INPUT_CSV, 'r', encoding='latin1', newline='') as f:
            reader = list(csv.reader(f, delimiter=';'))
        header = reader[0]
        garantia_col = header.index('GARANTIA')
        reader[idx+1][garantia_col] = garantia
        with open(INPUT_CSV, 'w', encoding='latin1', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerows(reader)

def extract_garantia_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tr in soup.find_all('tr'):
        tds = tr.find_all('td')
        for td in tds:
            if td and 'GARANTIA' in td.text.upper():
                return td.text.strip()
    return ''

def check_garantia(row, idx):
    part_number = row['ITEM']
    url = BOM_URL.format(part_number)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code in BLOCK_STATUS_CODES:
                print(Fore.RED + Style.BRIGHT + f"\nBloqueado pelo servidor (HTTP {resp.status_code}) para {part_number}. Pausando por {BLOCK_PAUSE} segundos...")
                time.sleep(BLOCK_PAUSE)
                continue
            resp.raise_for_status()
            garantia = extract_garantia_from_html(resp.text)
            if garantia:
                update_garantia_in_csv(idx, garantia)
                return garantia, None
            else:
                update_garantia_in_csv(idx, 'NAO ENCONTRADO')
                return 'NAO ENCONTRADO', None
        except requests.exceptions.Timeout:
            print(Fore.YELLOW + f"Timeout ao buscar BOM para {part_number} (tentativa {attempt}/{MAX_RETRIES})")
            time.sleep(2)
        except Exception as e:
            print(Fore.RED + f"Erro ao buscar BOM para {part_number} (tentativa {attempt}/{MAX_RETRIES}): {e}")
            time.sleep(2)
    print(Fore.MAGENTA + Style.BRIGHT + f"Falha ao buscar BOM para {part_number} após {MAX_RETRIES} tentativas. URL: {url}")
    return None, url

print(Fore.CYAN + 'Verificando GARANTIA para cada linha sem valor...')
rows_to_check = df[df['GARANTIA'].isna() | (df['GARANTIA'] == '')].copy()
failed_urls = []

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    future_to_idx = {executor.submit(check_garantia, row, idx): idx for idx, row in rows_to_check.iterrows()}
    for future in tqdm(as_completed(future_to_idx), total=len(future_to_idx), desc='Processando'):
        idx = future_to_idx[future]
        try:
            garantia, fail_url = future.result()
        except Exception as e:
            print(Fore.RED + f'Erro inesperado: {e}')
            garantia, fail_url = None, None
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