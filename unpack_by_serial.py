import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from tqdm import tqdm
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import init, Fore, Style

init(autoreset=True)

INPUT_CSV = "o2c.csv"
OUTPUT_CSV = "o2c_unpacked.csv"
SERIAL_LOOKUP_URL = "https://production.wayne.com/asp/SerialLookup.asp?SerialNumber=&WorkOrder=&PartNumber={}"
MAX_WORKERS = 20  # Number of parallel threads
BLOCK_STATUS_CODES = {429, 403, 503}
BLOCK_PAUSE = 60  # seconds to pause if blocked

OUTPUT_COLUMNS = []


def normalize_key(row):
    return tuple(str(row.get(col, "")).strip() for col in OUTPUT_COLUMNS)


def fetch_serials(row):
    part_number = row["ITEM"]
    url = SERIAL_LOOKUP_URL.format(part_number)
    try:
        resp = requests.get(url, timeout=20)
        if resp.status_code in BLOCK_STATUS_CODES:
            print(
                Fore.RED
                + Style.BRIGHT
                + f"\nBlocked by server (HTTP {resp.status_code}). Pausing for {BLOCK_PAUSE} seconds..."
            )
            time.sleep(BLOCK_PAUSE)
            return row, []
        resp.raise_for_status()
    except Exception as e:
        print(Fore.RED + f"Error fetching serials for part {part_number}: {e}")
        return row, []
    soup = BeautifulSoup(resp.text, "html.parser")
    serials = []
    table = soup.find("table", {"border": "1"})
    if table:
        for tr in table.find_all("tr")[1:]:
            tds = tr.find_all("td")
            if tds:
                serial = tds[0].get_text(strip=True)
                if serial:
                    serials.append(serial)
    if not serials:
        serials = [""]
    return row, serials


print(Fore.CYAN + f"Reading {INPUT_CSV}...")
df = None
# Try reading with different encodings
for enc in ["utf-8-sig", "latin1", "cp1252"]:
    try:
        df = pd.read_csv(INPUT_CSV, sep=";", dtype=str, encoding=enc)
        print(Fore.GREEN + f"Successfully read {INPUT_CSV} with encoding: {enc}")
        break
    except UnicodeDecodeError:
        continue
    except Exception as e:
        print(Fore.RED + f"Error reading {INPUT_CSV} with {enc}: {e}")

if df is None:
    print(Fore.RED + f"Failed to read {INPUT_CSV} with any compatible encoding.")
    exit(1)

# Clean column names (remove BOM artifacts if any remain, and whitespace)
df.columns = [c.strip().replace("\ufeff", "") for c in df.columns]

# Filter to only 2025+ data (DT_NUM_NF format: DD/MM/YYYY)
DATE_COL = "DT_NUM_NF"
if DATE_COL in df.columns:
    original_count = len(df)

    # Extract year from date string and filter
    try:
        # Try to convert to datetime, handling multiple formats automatically
        df["_year"] = pd.to_datetime(df[DATE_COL], errors="coerce").dt.year
        # Fill NaNs with 0 or handle them (here we drop them effectively by the filter)
        df = df[df["_year"] >= 2023].drop(columns=["_year"])
        print(
            Fore.YELLOW + f"Filtered to 2023+ data: {original_count} -> {len(df)} rows"
        )
    except Exception as e:
        print(Fore.RED + f"Error filtering by date: {e}")

else:
    print(Fore.RED + f"Warning: Date column {DATE_COL} not found, processing all rows")

if os.path.exists(OUTPUT_CSV):
    print(Fore.CYAN + f"Found existing {OUTPUT_CSV}, loading...")
    try:
        # Also try to read output with robust encoding
        out_df = None
        for enc in ["utf-8-sig", "latin1", "cp1252"]:
            try:
                out_df = pd.read_csv(OUTPUT_CSV, sep=";", dtype=str, encoding=enc)
                break
            except:
                continue

        if out_df is None:
            out_df = pd.read_csv(OUTPUT_CSV, sep=";", dtype=str, encoding="latin1")

        # Clean output columns
        out_df.columns = [c.strip().replace("\ufeff", "") for c in out_df.columns]

        # Use only common columns that exist in BOTH files for key matching
        # This handles schema evolution (new columns added to input)
        input_cols = set(df.columns)
        output_cols = set(out_df.columns)
        common_cols = input_cols & output_cols

        # Prefer specific key columns if they exist for reliable matching
        preferred_keys = ["PEDIDO", "LINHA", "ITEM"]
        key_columns = [k for k in preferred_keys if k in common_cols]

        # Fallback: use all common columns except Serial if no preferred keys found
        if not key_columns:
            key_columns = [col for col in common_cols if col != "Serial"]

        print(Fore.YELLOW + f"Using key columns for matching: {key_columns}")

        # Robust key generation from output
        processed_keys = set()
        for _, out_row in out_df.iterrows():
            key = tuple(str(out_row.get(col, "")).strip() for col in key_columns)
            processed_keys.add(key)

        print(
            Fore.YELLOW + f"Loaded {len(processed_keys)} existing keys from output file"
        )

        # Output columns should match the input plus Serial
        output_columns = list(df.columns) + ["Serial"]

    except Exception as e:
        print(
            Fore.RED
            + f"Warning: Could not read existing output file correctly ({e}). Starting fresh."
        )
        processed_keys = set()
        output_columns = list(df.columns) + ["Serial"]
        key_columns = (
            ["PEDIDO", "LINHA", "ITEM"]
            if all(k in df.columns for k in ["PEDIDO", "LINHA", "ITEM"])
            else list(df.columns)
        )
else:
    output_columns = list(df.columns) + ["Serial"]
    key_columns = (
        ["PEDIDO", "LINHA", "ITEM"]
        if all(k in df.columns for k in ["PEDIDO", "LINHA", "ITEM"])
        else list(df.columns)
    )
    processed_keys = set()

rows_to_process = []
for idx, row in df.iterrows():
    key = tuple(str(row.get(col, "")).strip() for col in key_columns)
    if key not in processed_keys:
        rows_to_process.append((idx, row))

print(Fore.CYAN + f"Total rows in input: {len(df)}")
print(Fore.CYAN + f"Rows to process (not yet unpacked): {len(rows_to_process)}")
if rows_to_process:
    print(Fore.CYAN + "Sample rows to process:")
    for i, (idx, row) in enumerate(rows_to_process[:5]):
        print(Fore.CYAN + f"  idx={idx}, ITEM={row['ITEM']}")

rows_appended = 0

with open(OUTPUT_CSV, "a", encoding="utf-8-sig", newline="") as f:
    if os.stat(OUTPUT_CSV).st_size == 0:
        f.write(";".join(output_columns) + "\n")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(fetch_serials, row): (idx, row)
            for idx, row in rows_to_process
        }
        for future in tqdm(
            as_completed(futures), total=len(futures), desc="Processing"
        ):
            idx, row = futures[future]
            row, serials = future.result()
            for serial in serials:
                out_row = row.copy()
                out_row["Serial"] = serial
                f.write(
                    ";".join(str(out_row.get(col, "")) for col in output_columns) + "\n"
                )
                rows_appended += 1

print(
    Fore.GREEN
    + f"Processing complete. {rows_appended} new rows written/appended to {OUTPUT_CSV}."
)
