import pandas as pd
import gc

chunk_size = 5000
year_counts = {}

print("Scanning o2c.csv for years...")
try:
    for chunk in pd.read_csv(
        "o2c.csv", sep=";", dtype=str, encoding="latin1", chunksize=chunk_size
    ):
        if "DT_NUM_NF" in chunk.columns:
            # Parse date in this chunk
            dates = pd.to_datetime(chunk["DT_NUM_NF"], dayfirst=True, errors="coerce", format="mixed")
            years = dates.dt.year.dropna().astype(int)

            for year, count in years.value_counts().items():
                year_counts[year] = year_counts.get(year, 0) + count

        # Free memory
        del chunk
        gc.collect()

    print("Years found in o2c.csv:")
    for year in sorted(year_counts.keys()):
        print(f"{year}: {year_counts[year]}")

except Exception as e:
    print(f"Error reading o2c.csv: {e}")
