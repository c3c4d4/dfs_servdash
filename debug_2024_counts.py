import pandas as pd

INPUT_FILE = "o2c.csv"
CHUNK_SIZE = 10000
TARGET_YEAR = 2024


def analyze_2024_data():
    item_counts = {}

    try:
        reader = pd.read_csv(
            INPUT_FILE, sep=";", dtype=str, encoding="latin1", chunksize=CHUNK_SIZE
        )

        for chunk in reader:
            chunk.columns = [c.strip().replace("\ufeff", "") for c in chunk.columns]

            if "DT_NUM_NF" not in chunk.columns:
                continue

            chunk["DT_NUM_NF"] = pd.to_datetime(
                chunk["DT_NUM_NF"], dayfirst=True, errors="coerce"
            )
            mask_2024 = chunk["DT_NUM_NF"].dt.year == TARGET_YEAR
            df_2024 = chunk[mask_2024].copy()

            if len(df_2024) == 0:
                continue

            # Filter for "BOMBA" to see what we were counting
            if "DESCRICAO" in df_2024.columns:
                mask_bomba = (
                    df_2024["DESCRICAO"]
                    .astype(str)
                    .str.upper()
                    .str.contains("BOMBA", na=False)
                )
                df_bomba = df_2024[mask_bomba].copy()

                df_bomba["QUANTIDADE"] = (
                    df_bomba["QUANTIDADE"]
                    .astype(str)
                    .str.replace(",", ".")
                    .astype(float)
                    .fillna(0)
                )

                for _, row in df_bomba.iterrows():
                    key = (
                        row.get("LINHA", "N/A"),
                        row.get("ITEM", "N/A"),
                        row.get("DESCRICAO", "N/A"),
                    )
                    item_counts[key] = item_counts.get(key, 0) + row["QUANTIDADE"]

    except Exception as e:
        print(f"Error: {e}")

    # Convert to DF for sorting
    results = []
    for (linha, item, desc), qty in item_counts.items():
        results.append({"LINHA": linha, "ITEM": item, "DESCRICAO": desc, "QTY": qty})

    df_res = pd.DataFrame(results)
    if not df_res.empty:
        df_res = df_res.sort_values("QTY", ascending=False)
        print(f"Top 20 items counted as 'BOMBA' in 2024:")
        print(df_res.head(20).to_string())
        print(f"\nTotal Quantity: {df_res['QTY'].sum()}")
    else:
        print("No items found.")


if __name__ == "__main__":
    analyze_2024_data()
