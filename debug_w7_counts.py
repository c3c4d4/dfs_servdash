import pandas as pd

INPUT_FILE = "o2c.csv"
CHUNK_SIZE = 10000
TARGET_YEAR = 2024


def analyze_w7_items():
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

            # Filter for ITEM starts with 'W7'
            if "ITEM" in df_2024.columns:
                mask_w7 = df_2024["ITEM"].astype(str).str.upper().str.startswith("W7")
                df_w7 = df_2024[mask_w7].copy()

                df_w7["QUANTIDADE"] = (
                    df_w7["QUANTIDADE"]
                    .astype(str)
                    .str.replace(",", ".")
                    .astype(float)
                    .fillna(0)
                )

                for _, row in df_w7.iterrows():
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
        print(f"Top 20 items starting with 'W7' in 2024:")
        print(df_res.head(20).to_string())
        print(f"\nTotal Quantity (W7 items): {df_res['QTY'].sum()}")

        # Check for service items
        mask_service = df_res["DESCRICAO"].str.contains(
            "SERVICO|MANUTENCAO", case=False, na=False
        )
        service_qty = df_res[mask_service]["QTY"].sum()
        print(
            f"Total Quantity (Service items excluded): {df_res['QTY'].sum() - service_qty}"
        )

    else:
        print("No W7 items found.")


if __name__ == "__main__":
    analyze_w7_items()
