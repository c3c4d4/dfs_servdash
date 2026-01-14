import pandas as pd

INPUT_FILE = "o2c.csv"
CHUNK_SIZE = 5000
TARGET_YEAR = 2024


def count_w7_bomba():
    count_rtm = 0
    count_non_rtm = 0
    rtm_map = {}

    # Load RTM Cache
    try:
        df = pd.read_csv("rtm_cache.csv", sep=";", dtype=str, encoding="utf-8-sig")
        for _, row in df.iterrows():
            rtm_map[row["ITEM"]] = str(row["RTM"]).upper().strip()
    except:
        pass

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

            if "DESCRICAO" in df.columns and "ITEM" in df.columns:
                # Filter for "BOMBA MEDIDORA" AND ITEM starts with "W7"
                mask_desc = (
                    df["DESCRICAO"]
                    .astype(str)
                    .str.upper()
                    .str.contains("BOMBA MEDIDORA", na=False)
                )
                mask_item = df["ITEM"].astype(str).str.upper().str.startswith("W7")

                df_chassis = df[mask_desc & mask_item].copy()

                if len(df_chassis) > 0:
                    df_chassis["QUANTIDADE"] = (
                        df_chassis["QUANTIDADE"]
                        .astype(str)
                        .str.replace(",", ".")
                        .astype(float)
                        .fillna(0)
                    )

                    for _, row in df_chassis.iterrows():
                        qty = row["QUANTIDADE"]
                        item = row["ITEM"]

                        rtm_status = rtm_map.get(item, "NAO")
                        if "SIM" in rtm_status:
                            count_rtm += qty
                        else:
                            count_non_rtm += qty

    except Exception as e:
        print(f"Error: {e}")

    print(f"Total BOMBA MEDIDORA (starting with W7) in 2024:")
    print(f"RTM: {count_rtm}")
    print(f"Non-RTM: {count_non_rtm}")
    print(f"Total: {count_rtm + count_non_rtm}")


if __name__ == "__main__":
    count_w7_bomba()
