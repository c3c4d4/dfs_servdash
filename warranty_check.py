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

INPUT_CSV = 'o2c_unpacked.csv'
TEMP_CSV = 'o2c_unpacked_temp.csv'
BACKUP_CSV = 'o2c_unpacked_backup.csv'
BOM_URL = 'https://production.wayne.com/asp/BomLookup.asp?Function=BOM&PartNumber={}&Org=6705'
MAX_WORKERS = 5
BLOCK_STATUS_CODES = {429, 403, 503}
BLOCK_PAUSE = 60
MAX_RETRIES = 3
BATCH_SIZE = 100

print(Fore.CYAN + f'Lendo {INPUT_CSV}...')
try:
    df = pd.read_csv(INPUT_CSV, sep=';', dtype=str, encoding='latin1')
except Exception as e:
    print(Fore.RED + f'Erro ao ler {INPUT_CSV}: {e}')
    exit(1)

# Criar backup antes de começar
if os.path.exists(INPUT_CSV):
    shutil.copy2(INPUT_CSV, BACKUP_CSV)
    print(Fore.GREEN + f'Backup criado: {BACKUP_CSV}')

if 'GARANTIA' not in df.columns:
    df['GARANTIA'] = ''

# Lock para escrita concorrente
write_lock = threading.Lock()

def safe_save_dataframe(df_to_save, filename):
    """Salva DataFrame de forma segura, primeiro em arquivo temporário"""
    temp_file = filename + '.tmp'
    try:
        # Salva primeiro no arquivo temporário
        df_to_save.to_csv(temp_file, sep=';', index=False, encoding='utf-8')
        # Se salvou com sucesso, move para o arquivo final
        shutil.move(temp_file, filename)
        return True
    except Exception as e:
        print(Fore.RED + f'Erro ao salvar {filename}: {e}')
        # Remove arquivo temporário se existir
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return False

def extract_garantia_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    for td in soup.find_all('td'):
        txt = td.get_text(separator=' ', strip=True).replace('\n', ' ').replace('\r', ' ')
        if txt.upper().startswith('GARANTIA'):
            return txt.strip()
        elif txt.upper().startswith('WARRANTY - '):
            return txt.strip()
    return ''

def check_garantia(row):
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
                return garantia, None
            else:
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

# Função para processar uma linha (usada no ThreadPool)
def process_row(idx_row):
    idx, row = idx_row
    garantia, fail_url = check_garantia(row)
    return idx, garantia, fail_url

results = []
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    batch = []
    for i, result in enumerate(tqdm(executor.map(process_row, rows_to_check.iterrows()), total=len(rows_to_check), desc='Processando')):
        batch.append(result)
        if (i + 1) % BATCH_SIZE == 0:
            # Atualiza o DataFrame e salva de forma segura
            for idx, garantia, fail_url in batch:
                if garantia:
                    df.at[idx, 'GARANTIA'] = garantia
                if fail_url:
                    failed_urls.append((df.at[idx, 'ITEM'], fail_url))
            
            if safe_save_dataframe(df, INPUT_CSV):
                print(Fore.YELLOW + f'Salvo progresso em {i+1} linhas...')
            else:
                print(Fore.RED + 'ERRO: Falha ao salvar arquivo!')
                break
            batch = []
    
    # Processa o restante do último batch
    for idx, garantia, fail_url in batch:
        if garantia:
            df.at[idx, 'GARANTIA'] = garantia
        if fail_url:
            failed_urls.append((df.at[idx, 'ITEM'], fail_url))
    
    # Salva final de forma segura
    if safe_save_dataframe(df, INPUT_CSV):
        print(Fore.GREEN + 'Arquivo salvo com sucesso!')
    else:
        print(Fore.RED + 'ERRO: Falha ao salvar arquivo final!')

print(Fore.GREEN + 'Processamento finalizado!')

if failed_urls:
    print(Fore.RED + Style.BRIGHT + '\nURLs que falharam após todas as tentativas:')
    for part, url in failed_urls:
        print(Fore.YELLOW + f'PartNumber: {part}  URL: {url}')
    print(Fore.CYAN + '\nVocê pode testar manualmente essas URLs no navegador.')
else:
    print(Fore.GREEN + 'Todas as linhas processadas com sucesso!')

print(Fore.CYAN + f'\nBackup disponível em: {BACKUP_CSV}') 