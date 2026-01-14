import pandas as pd

INPUT_FILE = "o2c.csv"
CHUNK_SIZE = 10000
TARGET_YEAR = 2024


def analyze_dispenser_filter():
    counts = {"NF": 0}

    try:
        reader = pd.read_csv(
            INPUT_FILE, sep=";", dtype=str, encoding="latin1", chunksize=CHUNK_SIZE
        )

        for chunk in reader:
            chunk.columns = [c.strip().replace("\ufeff", "") for c in chunk.columns]

            # Filter for Chassis (W7 + DISPENSER)
            # Or just DISPENSER in description?
            # Or LINHA contains DISPENSER? (LINHA was numeric codes 1,2...)
            # "SEGMENTO" is usually "DISPENSERS"

            if "SEGMENTO" in chunk.columns:
                mask_segment = (
                    chunk["SEGMENTO"]
                    .astype(str)
                    .str.upper()
                    .str.contains("DISPENSER", na=False)
                )
                # And Item starts with W7
                mask_item = chunk["ITEM"].astype(str).str.upper().str.startswith("W7")

                df_chassis = chunk[mask_segment & mask_item].copy()

                if len(df_chassis) > 0:
                    df_chassis["QUANTIDADE"] = (
                        df_chassis["QUANTIDADE"]
                        .astype(str)
                        .str.replace(",", ".")
                        .astype(float)
                        .fillna(0)
                    )

                    if "DT_NUM_NF" in df_chassis.columns:
                        dates = pd.to_datetime(
                            df_chassis["DT_NUM_NF"], dayfirst=True, errors="coerce"
                        )
                        mask_2024 = dates.dt.year == TARGET_YEAR
                        counts["NF"] += df_chassis[mask_2024]["QUANTIDADE"].sum()

    except Exception as e:
        print(f"Error: {e}")

    print(f"Counts by SEGMENTO='DISPENSERS' + W7 + 2024 Invoice: {counts['NF']}")


if __name__ == "__main__":
    analyze_dispenser_filter()
