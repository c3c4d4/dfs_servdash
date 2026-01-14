import pandas as pd
from datetime import datetime, timedelta

INPUT_FILE = "o2c.csv"
CHUNK_SIZE = 5000
TARGET_YEAR = 2023
TODAY = datetime(2026, 1, 13)
GARANTIA_ELETRONICA_DAYS = 365


def normalize_garantia_to_days(garantia_text):
    return 365  # Default to 1 year if parsing fails


def calc_2023():
    counts = {
        "RTM": {"total": 0, "elec_active": 0, "norm_active": 0},
        "NON_RTM": {"total": 0, "elec_active": 0, "norm_active": 0},
    }

    rtm_map = {}
    garantia_map = {}

    try:
        df = pd.read_csv("rtm_cache.csv", sep=";", dtype=str, encoding="utf-8-sig")
        for _, row in df.iterrows():
            rtm_map[row["ITEM"]] = str(row["RTM"]).upper().strip()
    except:
        pass

    try:
        df = pd.read_csv("garantia_cache.csv", sep=";", dtype=str, encoding="utf-8-sig")
        for _, row in df.iterrows():
            try:
                days = int(row["GARANTIA"])
            except:
                days = 0
            garantia_map[row["ITEM"]] = days
    except:
        pass

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

            if "SEGMENTO" in chunk.columns and "ITEM" in chunk.columns:
                mask_segment = (
                    chunk["SEGMENTO"]
                    .astype(str)
                    .str.upper()
                    .str.contains("DISPENSER", na=False)
                )
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
                        mask_year = dates.dt.year == TARGET_YEAR
                        df_final = df_chassis[mask_year].copy()

                        if len(df_final) > 0:
                            for _, row in df_final.iterrows():
                                item = row["ITEM"]
                                qty = row["QUANTIDADE"]

                                is_rtm = "SIM" in rtm_map.get(item, "NAO")
                                w_days = garantia_map.get(item, 0)

                                date_nf = pd.to_datetime(
                                    row["DT_NUM_NF"], dayfirst=True, errors="coerce"
                                )
                                if pd.isna(date_nf):
                                    continue

                                elec_active = (
                                    date_nf + timedelta(days=GARANTIA_ELETRONICA_DAYS)
                                ) >= TODAY
                                norm_active = (
                                    date_nf + timedelta(days=w_days)
                                ) >= TODAY

                                cat = "RTM" if is_rtm else "NON_RTM"
                                counts[cat]["total"] += qty
                                if elec_active:
                                    counts[cat]["elec_active"] += qty
                                if norm_active:
                                    counts[cat]["norm_active"] += qty

    except Exception as e:
        print(f"Error: {e}")

    print(f"RESULTS FOR {TARGET_YEAR} (SEGMENTO=DISPENSER + W7):")
    for cat in ["RTM", "NON_RTM"]:
        data = counts[cat]
        total = data["total"]
        print(f"\nCategory: {cat}")
        print(f"Total: {int(total)}")
        if total > 0:
            print(
                f"Electronics Warranty Active: {int(data['elec_active'])} ({data['elec_active'] / total * 100:.2f}%)"
            )
            print(
                f"Normal Warranty Active: {int(data['norm_active'])} ({data['norm_active'] / total * 100:.2f}%)"
            )


if __name__ == "__main__":
    calc_2023()
