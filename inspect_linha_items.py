import pandas as pd

INPUT_FILE = "o2c.csv"
CHUNK_SIZE = 10000
TARGET_YEAR = 2024


def inspect_linha_items():
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
            df = chunk[mask_2024].copy()

            if len(df) == 0:
                continue

            # Filter for LINHA 1 and 2, and BOMBA MEDIDORA
            if "DESCRICAO" in df.columns and "LINHA" in df.columns:
                mask_bomba = (
                    df["DESCRICAO"]
                    .astype(str)
                    .str.upper()
                    .str.contains("BOMBA MEDIDORA", na=False)
                )
                mask_linha = df["LINHA"].isin(["1", "2"])
                df_target = df[mask_bomba & mask_linha].copy()

                df_target["QUANTIDADE"] = (
                    df_target["QUANTIDADE"]
                    .astype(str)
                    .str.replace(",", ".")
                    .astype(float)
                    .fillna(0)
                )

                for _, row in df_target.iterrows():
                    key = (
                        row.get("LINHA", "N/A"),
                        row.get("ITEM", "N/A"),
                        row.get("DESCRICAO", "N/A"),
                    )
                    item_counts[key] = item_counts.get(key, 0) + row["QUANTIDADE"]

    except Exception as e:
        print(f"Error: {e}")

    results = []
    for (linha, item, desc), qty in item_counts.items():
        results.append({"LINHA": linha, "ITEM": item, "DESCRICAO": desc, "QTY": qty})

    df_res = pd.DataFrame(results)
    if not df_res.empty:
        df_res = df_res.sort_values("QTY", ascending=False)
        print(f"Top 20 BOMBA MEDIDORA items in LINHA 1 and 2 (2024):")
        print(df_res.head(20).to_string())


if __name__ == "__main__":
    inspect_linha_items()
