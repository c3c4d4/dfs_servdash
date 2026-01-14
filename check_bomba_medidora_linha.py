import pandas as pd

INPUT_FILE = "o2c.csv"
CHUNK_SIZE = 10000
TARGET_YEAR = 2024


def check_bomba_medidora_linha():
    linha_counts = {}

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

            if "DESCRICAO" in df.columns:
                mask_chassis = (
                    df["DESCRICAO"]
                    .astype(str)
                    .str.upper()
                    .str.contains("BOMBA MEDIDORA", na=False)
                )
                df_chassis = df[mask_chassis].copy()

                df_chassis["QUANTIDADE"] = (
                    df_chassis["QUANTIDADE"]
                    .astype(str)
                    .str.replace(",", ".")
                    .astype(float)
                    .fillna(0)
                )

                for _, row in df_chassis.iterrows():
                    linha = row.get("LINHA", "N/A")
                    linha_counts[linha] = linha_counts.get(linha, 0) + row["QUANTIDADE"]

    except Exception as e:
        print(f"Error: {e}")

    print(f"BOMBA MEDIDORA Quantity by LINHA in 2024:")
    for linha, qty in sorted(linha_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"LINHA {linha}: {qty}")


if __name__ == "__main__":
    check_bomba_medidora_linha()
