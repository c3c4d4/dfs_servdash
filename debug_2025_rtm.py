import pandas as pd
from datetime import datetime, timedelta

INPUT_FILE = "o2c.csv"
CHUNK_SIZE = 5000
YEARS = [2025]
TODAY = datetime(2026, 1, 13)


def debug_2025_rtm():
    rtm_map = {}

    # Load RTM Cache
    try:
        df = pd.read_csv("rtm_cache.csv", sep=";", dtype=str, encoding="utf-8-sig")
        for _, row in df.iterrows():
            rtm_map[row["ITEM"]] = str(row["RTM"]).upper().strip()
    except:
        pass

    rtm_counts = {}
    total_rtm = 0

    try:
        reader = pd.read_csv(
            INPUT_FILE,
            sep=";",
            dtype=str,
            encoding="latin1",
            chunksize=CHUNK_SIZE,
            on_bad_lines="skip",
        )

        for chunk in reader:
            chunk.columns = [c.strip().replace("\ufeff", "") for c in chunk.columns]

            if (
                "SEGMENTO" in chunk.columns
                and "ITEM" in chunk.columns
                and "DT_NUM_NF" in chunk.columns
            ):
                mask_segment = (
                    chunk["SEGMENTO"]
                    .astype(str)
                    .str.upper()
                    .str.contains("DISPENSER", na=False)
                )
                mask_item = chunk["ITEM"].astype(str).str.upper().str.startswith("W7")

                df_filtered = chunk[mask_segment & mask_item].copy()

                if len(df_filtered) > 0:
                    df_filtered["QUANTIDADE"] = (
                        df_filtered["QUANTIDADE"]
                        .astype(str)
                        .str.replace(",", ".")
                        .astype(float)
                        .fillna(0)
                    )
                    df_filtered["DT_NUM_NF"] = pd.to_datetime(
                        df_filtered["DT_NUM_NF"], dayfirst=True, errors="coerce"
                    )

                    mask_2025 = df_filtered["DT_NUM_NF"].dt.year == 2025
                    df_2025 = df_filtered[mask_2025]

                    if len(df_2025) > 0:
                        for _, row in df_2025.iterrows():
                            item = row["ITEM"]
                            qty = row["QUANTIDADE"]

                            is_rtm = "SIM" in rtm_map.get(item, "NAO")

                            if is_rtm:
                                rtm_counts[item] = rtm_counts.get(item, 0) + qty
                                total_rtm += qty

    except Exception as e:
        print(f"Error: {e}")

    print(f"Total RTM in 2025: {total_rtm}")
    print("\nTop RTM Items in 2025:")
    sorted_items = sorted(rtm_counts.items(), key=lambda x: x[1], reverse=True)
    for item, qty in sorted_items:
        print(f"{item}: {qty}")


if __name__ == "__main__":
    debug_2025_rtm()
