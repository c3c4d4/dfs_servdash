import pandas as pd
from datetime import datetime, timedelta
import re

INPUT_FILE = "o2c.csv"
CHUNK_SIZE = 2000
TARGET_YEAR = 2024
TODAY = datetime(2026, 1, 13)
GARANTIA_ELETRONICA_DAYS = 365

# Text to Days mapping
GARANTIA_TEXT_TO_DAYS = {
    "6 MESES": 183,
    "6 MONTHS": 183,
    "12 MESES": 365,
    "12 MONTHS": 365,
    "1 ANO": 365,
    "1 YEAR": 365,
    "18 MESES": 548,
    "18 MONTHS": 548,
    "24 MESES": 730,
    "24 MONTHS": 730,
    "2 ANOS": 730,
    "2 YEARS": 730,
    "36 MESES": 1095,
    "36 MONTHS": 1095,
    "3 ANOS": 1095,
    "3 YEARS": 1095,
}


def normalize_garantia_to_days(garantia_text):
    if (
        pd.isna(garantia_text)
        or garantia_text == ""
        or str(garantia_text).upper() == "NAO ENCONTRADO"
    ):
        return 0
    try:
        return int(float(str(garantia_text).replace(",", ".")))
    except:
        pass
    garantia_upper = str(garantia_text).upper().strip()
    for prefix in ["GARANTIA", "WARRANTY", "-", ":"]:
        garantia_upper = garantia_upper.replace(prefix, "").strip()
    for pattern, days in GARANTIA_TEXT_TO_DAYS.items():
        if pattern in garantia_upper:
            return days
    match = re.search(r"(\d+)\s*(MES|MONTH|M)", garantia_upper)
    if match:
        meses = int(match.group(1))
        return int(meses * 30.44)
    match = re.search(r"(\d+)\s*(ANO|YEAR|Y)", garantia_upper)
    if match:
        anos = int(match.group(1))
        return int(anos * 365)
    return 0


def analyze_dispenser_split():
    counts = {
        "RTM": {"total": 0, "elec_active": 0, "norm_active": 0},
        "NON_RTM": {"total": 0, "elec_active": 0, "norm_active": 0},
    }

    rtm_map = {}
    garantia_map = {}

    # Load Caches
    try:
        df = pd.read_csv("rtm_cache.csv", sep=";", dtype=str, encoding="utf-8-sig")
        for _, row in df.iterrows():
            rtm_map[row["ITEM"]] = str(row["RTM"]).upper().strip()
    except:
        pass

    try:
        df = pd.read_csv("garantia_cache.csv", sep=";", dtype=str, encoding="utf-8-sig")
        for _, row in df.iterrows():
            garantia_map[row["ITEM"]] = normalize_garantia_to_days(row["GARANTIA"])
    except:
        pass

    try:
        reader = pd.read_csv(
            INPUT_FILE, sep=";", dtype=str, encoding="latin1", chunksize=CHUNK_SIZE
        )

        for chunk in reader:
            chunk.columns = [c.strip().replace("\ufeff", "") for c in chunk.columns]

            if "SEGMENTO" in chunk.columns:
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
                        mask_2024 = dates.dt.year == TARGET_YEAR
                        df_final = df_chassis[mask_2024].copy()

                        if len(df_final) > 0:
                            # Map RTM and Warranty
                            df_final["RTM_STATUS"] = (
                                df_final["ITEM"].map(rtm_map).fillna("NAO")
                            )
                            df_final["IS_RTM"] = df_final["RTM_STATUS"].str.contains(
                                "SIM", na=False
                            )

                            df_final["WARRANTY_DAYS"] = (
                                df_final["ITEM"].map(garantia_map).fillna(0)
                            )

                            # Dates
                            # Re-parse dates for the filtered slice to be safe/easy
                            dates_final = pd.to_datetime(
                                df_final["DT_NUM_NF"], dayfirst=True, errors="coerce"
                            )

                            elec_expiry = dates_final + timedelta(
                                days=GARANTIA_ELETRONICA_DAYS
                            )
                            norm_expiry = dates_final + pd.to_timedelta(
                                df_final["WARRANTY_DAYS"], unit="D"
                            )

                            df_final["ELEC_ACTIVE"] = elec_expiry >= TODAY
                            df_final["NORM_ACTIVE"] = norm_expiry >= TODAY

                            # Aggregate
                            rtm_df = df_final[df_final["IS_RTM"]]
                            counts["RTM"]["total"] += rtm_df["QUANTIDADE"].sum()
                            counts["RTM"]["elec_active"] += rtm_df[
                                rtm_df["ELEC_ACTIVE"]
                            ]["QUANTIDADE"].sum()
                            counts["RTM"]["norm_active"] += rtm_df[
                                rtm_df["NORM_ACTIVE"]
                            ]["QUANTIDADE"].sum()

                            non_rtm_df = df_final[~df_final["IS_RTM"]]
                            counts["NON_RTM"]["total"] += non_rtm_df["QUANTIDADE"].sum()
                            counts["NON_RTM"]["elec_active"] += non_rtm_df[
                                non_rtm_df["ELEC_ACTIVE"]
                            ]["QUANTIDADE"].sum()
                            counts["NON_RTM"]["norm_active"] += non_rtm_df[
                                non_rtm_df["NORM_ACTIVE"]
                            ]["QUANTIDADE"].sum()

    except Exception as e:
        print(f"Error: {e}")

    print(f"RESULTS FOR 2024 (SEGMENTO=DISPENSER + W7):")
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
    analyze_dispenser_split()
