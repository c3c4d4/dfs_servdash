import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from tqdm import tqdm
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import init, Fore, Style

init(autoreset=True)

INPUT_CSV = 'o2c.csv'
OUTPUT_CSV = 'o2c_unpacked.csv'
SERIAL_LOOKUP_URL = 'https://production.wayne.com/asp/SerialLookup.asp?SerialNumber=&WorkOrder=&PartNumber={}'
MAX_WORKERS = 5  # Number of parallel threads
BLOCK_STATUS_CODES = {429, 403, 503}
BLOCK_PAUSE = 60  # seconds to pause if blocked

OUTPUT_COLUMNS = None

def normalize_key(row):
    return tuple(str(row.get(col, '')).strip() for col in OUTPUT_COLUMNS)

def fetch_serials(row):
    part_number = row['ITEM']
    url = SERIAL_LOOKUP_URL.format(part_number)
    try:
        resp = requests.get(url, timeout=20)
        if resp.status_code in BLOCK_STATUS_CODES:
            print(Fore.RED + Style.BRIGHT + f"\nBlocked by server (HTTP {resp.status_code}). Pausing for {BLOCK_PAUSE} seconds...")
            time.sleep(BLOCK_PAUSE)
            return row, []
        resp.raise_for_status()
    except Exception as e:
        print(Fore.RED + f"Error fetching serials for part {part_number}: {e}")
        return row, []
    soup = BeautifulSoup(resp.text, 'html.parser')
    serials = []
    table = soup.find('table', {'border': '1'})
    if table:
        for tr in table.find_all('tr')[1:]:
            tds = tr.find_all('td')
            if tds:
                serial = tds[0].get_text(strip=True)
                if serial:
                    serials.append(serial)
    if not serials:
        serials = ['']
    return row, serials

print(Fore.CYAN + f'Reading {INPUT_CSV}...')
try:
    df = pd.read_csv(INPUT_CSV, sep=';', dtype=str, encoding='latin1')
except Exception as e:
    print(Fore.RED + f'Error reading {INPUT_CSV}: {e}')
    exit(1)

if os.path.exists(OUTPUT_CSV):
    print(Fore.CYAN + f'Found existing {OUTPUT_CSV}, loading...')
    out_df = pd.read_csv(OUTPUT_CSV, sep=';', dtype=str, encoding='latin1')
    output_columns = list(out_df.columns)
    key_columns = [col for col in output_columns if col != 'Serial']
    processed_keys = set(tuple(str(out_row.get(col, '')).strip() for col in key_columns) for _, out_row in out_df.iterrows())
else:
    output_columns = list(df.columns) + ['Serial']
    key_columns = list(df.columns)
    processed_keys = set()

rows_to_process = []
for idx, row in df.iterrows():
    key = tuple(str(row.get(col, '')).strip() for col in key_columns)
    if key not in processed_keys:
        rows_to_process.append((idx, row))

print(Fore.CYAN + f'Total rows in input: {len(df)}')
print(Fore.CYAN + f'Rows to process (not yet unpacked): {len(rows_to_process)}')
if rows_to_process:
    print(Fore.CYAN + 'Sample rows to process:')
    for i, (idx, row) in enumerate(rows_to_process[:5]):
        print(Fore.CYAN + f'  idx={idx}, ITEM={row["ITEM"]}')

rows_appended = 0

with open(OUTPUT_CSV, 'a', encoding='latin1', newline='') as f:
    if os.stat(OUTPUT_CSV).st_size == 0:
        f.write(';'.join(output_columns) + '\n')
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_serials, row): (idx, row) for idx, row in rows_to_process}
        for future in tqdm(as_completed(futures), total=len(futures), desc='Processing'):
            idx, row = futures[future]
            row, serials = future.result()
            for serial in serials:
                out_row = row.copy()
                out_row['Serial'] = serial
                f.write(';'.join(str(out_row.get(col, '')) for col in output_columns) + '\n')
                rows_appended += 1

print(Fore.GREEN + f'Processing complete. {rows_appended} new rows written/appended to {OUTPUT_CSV}.') 