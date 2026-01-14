import pandas as pd
from datetime import datetime, timedelta

INPUT_FILE = "o2c.csv"
CHUNK_SIZE = 5000
YEARS = [2025]
TODAY = datetime(2026, 1, 13)


def check_missing_rtm_2025():
    # If the user says 130 RTMs in 2025, but we see 79, maybe some "BOMBA" don't start with "W7"?
    # Or maybe the "BOMBA MEDIDORA" description is too restrictive?

    rtm_map = {}
    try:
        df = pd.read_csv("rtm_cache.csv", sep=";", dtype=str, encoding="utf-8-sig")
        for _, row in df.iterrows():
            rtm_map[row["ITEM"]] = str(row["RTM"]).upper().strip()
    except:
        pass

    found_rtm = 0
    rtm_items = []

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

            # Broader filter: Just "DISPENSER" in Segment? Or Just "BOMBA" in Desc?
            # Let's try "SEGMENTO=DISPENSER" AND Date=2025 AND RTM=SIM

            if "DT_NUM_NF" in chunk.columns:
                chunk["DT_NUM_NF"] = pd.to_datetime(
                    chunk["DT_NUM_NF"], dayfirst=True, errors="coerce"
                )
                mask_2025 = chunk["DT_NUM_NF"].dt.year == 2025
                df_2025 = chunk[mask_2025].copy()

                if len(df_2025) > 0:
                    df_2025["QUANTIDADE"] = (
                        df_2025["QUANTIDADE"]
                        .astype(str)
                        .str.replace(",", ".")
                        .astype(float)
                        .fillna(0)
                    )

                    for _, row in df_2025.iterrows():
                        item = row.get("ITEM", "")
                        # Check if RTM
                        is_rtm = "SIM" in rtm_map.get(item, "NAO")

                        if is_rtm:
                            # We found an RTM item in 2025.
                            # Is it a chassis?
                            # Let's log it to see if we missed it with our "W7 + BOMBA" filter
                            desc = str(row.get("DESCRICAO", "")).upper()
                            qty = row["QUANTIDADE"]

                            is_w7 = str(item).upper().startswith("W7")
                            has_bomba = "BOMBA MEDIDORA" in desc
                            has_segment = (
                                "DISPENSER" in str(row.get("SEGMENTO", "")).upper()
                            )

                            rtm_items.append(
                                {
                                    "ITEM": item,
                                    "DESC": desc,
                                    "QTY": qty,
                                    "IS_W7": is_w7,
                                    "HAS_BOMBA": has_bomba,
                                    "HAS_SEGMENT": has_segment,
                                }
                            )

                            found_rtm += qty

    except Exception as e:
        print(f"Error: {e}")

    print(f"Total Raw RTM Items in 2025 (No Chassis Filter): {found_rtm}")

    df_res = pd.DataFrame(rtm_items)
    if not df_res.empty:
        # Check what we missed
        missed = df_res[~((df_res["IS_W7"]) & (df_res["HAS_BOMBA"]))]
        print("\nRTM Items excluded by W7+BOMBA filter:")
        print(
            missed.groupby(["ITEM", "DESC"])
            .sum("QTY")
            .sort_values("QTY", ascending=False)
            .head(20)
            .to_string()
        )


if __name__ == "__main__":
    check_missing_rtm_2025()
