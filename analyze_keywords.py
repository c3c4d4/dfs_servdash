import pandas as pd

INPUT_FILE = "o2c.csv"
CHUNK_SIZE = 10000
TARGET_YEAR = 2024


def analyze_keywords():
    counts = {
        "BOMBA_MEDIDORA": 0,
        "W7_START": 0,
        "W7_AND_BOMBA": 0,
        "LINHA_1_2": 0,
        "DOMESTIC_EXPORT": 0,
    }

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

            df["QUANTIDADE"] = (
                df["QUANTIDADE"]
                .astype(str)
                .str.replace(",", ".")
                .astype(float)
                .fillna(0)
            )

            # Check combinations
            mask_bomba = (
                df["DESCRICAO"]
                .astype(str)
                .str.upper()
                .str.contains("BOMBA MEDIDORA", na=False)
            )
            mask_w7 = df["ITEM"].astype(str).str.upper().str.startswith("W7")
            mask_linha = df["LINHA"].isin(["1", "2"])
            mask_tipo = (
                df["TIPO"]
                .astype(str)
                .str.upper()
                .isin(["WBP EQUIPAMENTO DOMESTICO", "WBP EQUIPAMENTO EXPORTACAO"])
            )

            counts["BOMBA_MEDIDORA"] += df[mask_bomba]["QUANTIDADE"].sum()
            counts["W7_START"] += df[mask_w7]["QUANTIDADE"].sum()
            counts["W7_AND_BOMBA"] += df[mask_bomba & mask_w7]["QUANTIDADE"].sum()
            counts["LINHA_1_2"] += df[mask_linha]["QUANTIDADE"].sum()
            counts["DOMESTIC_EXPORT"] += df[mask_tipo]["QUANTIDADE"].sum()

            # Debug: What if we remove "W7" constraint from "W7_AND_BOMBA"?
            # We already have BOMBA_MEDIDORA count (12420).

            # What if we use TIPO + BOMBA MEDIDORA?
            counts["TIPO_AND_BOMBA"] = (
                counts.get("TIPO_AND_BOMBA", 0)
                + df[mask_tipo & mask_bomba]["QUANTIDADE"].sum()
            )

    except Exception as e:
        print(f"Error: {e}")

    for k, v in counts.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    analyze_keywords()
