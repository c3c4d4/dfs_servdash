import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re

# Constants
GARANTIA_ELETRONICA_DAYS = 365
TARGET_YEAR = 2024
TODAY = datetime(2026, 1, 13)
INPUT_FILE = "o2c.csv"
CHUNK_SIZE = 10000

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


def load_caches():
    print("Loading caches...")
    rtm_map = {}
    try:
        df = pd.read_csv("rtm_cache.csv", sep=";", dtype=str, encoding="utf-8-sig")
        for _, row in df.iterrows():
            rtm_map[row["ITEM"]] = str(row["RTM"]).upper().strip()
    except Exception as e:
        print(f"RTM cache error: {e}")

    garantia_map = {}
    try:
        df = pd.read_csv("garantia_cache.csv", sep=";", dtype=str, encoding="utf-8-sig")
        for _, row in df.iterrows():
            days = normalize_garantia_to_days(row["GARANTIA"])
            garantia_map[row["ITEM"]] = days
    except Exception as e:
        print(f"Warranty cache error: {e}")

    return rtm_map, garantia_map


def process_chunk(chunk, rtm_map, garantia_map):
    if "DT_NUM_NF" not in chunk.columns:
        return None

    chunk["DT_NUM_NF"] = pd.to_datetime(
        chunk["DT_NUM_NF"], dayfirst=True, errors="coerce"
    )

    # Filter by Year first
    mask_2024 = chunk["DT_NUM_NF"].dt.year == TARGET_YEAR
    df = chunk[mask_2024].copy()

    if len(df) == 0:
        return None

    # Filter for Dispensers/Pumps using DESCRIPTION
    if "DESCRICAO" in df.columns:
        mask_bomba = (
            df["DESCRICAO"].astype(str).str.upper().str.contains("BOMBA", na=False)
        )
        df = df[mask_bomba]
    else:
        # If no description, we can't be sure, so skip to avoid counting parts
        return None

    if len(df) == 0:
        return None

    # Parse Quantity
    df["QUANTIDADE"] = (
        df["QUANTIDADE"].astype(str).str.replace(",", ".").astype(float).fillna(0)
    )

    # Map RTM
    df["RTM_STATUS"] = df["ITEM"].map(rtm_map).fillna("NAO")
    df["IS_RTM"] = df["RTM_STATUS"].str.contains("SIM", na=False)

    # Map Warranty Days
    df["WARRANTY_DAYS"] = df["ITEM"].map(garantia_map).fillna(0)

    # Calculate Expiration Dates
    df["ELEC_EXPIRY"] = df["DT_NUM_NF"] + timedelta(days=GARANTIA_ELETRONICA_DAYS)
    df["NORM_EXPIRY"] = df["DT_NUM_NF"] + pd.to_timedelta(df["WARRANTY_DAYS"], unit="D")

    # Check Status vs Today
    df["ELEC_ACTIVE"] = df["ELEC_EXPIRY"] >= TODAY
    df["NORM_ACTIVE"] = df["NORM_EXPIRY"] >= TODAY

    return df[["IS_RTM", "ELEC_ACTIVE", "NORM_ACTIVE", "QUANTIDADE"]]


def main():
    rtm_map, garantia_map = load_caches()

    stats = {
        "RTM": {"total": 0, "elec_active": 0, "norm_active": 0},
        "NON_RTM": {"total": 0, "elec_active": 0, "norm_active": 0},
    }

    print(f"Processing {INPUT_FILE} in chunks of {CHUNK_SIZE}...")

    try:
        reader = pd.read_csv(
            INPUT_FILE, sep=";", dtype=str, encoding="latin1", chunksize=CHUNK_SIZE
        )

        for i, chunk in enumerate(reader):
            chunk.columns = [c.strip().replace("\ufeff", "") for c in chunk.columns]

            processed = process_chunk(chunk, rtm_map, garantia_map)

            if processed is not None:
                # Aggregate RTM
                rtm_df = processed[processed["IS_RTM"]]
                stats["RTM"]["total"] += rtm_df["QUANTIDADE"].sum()
                stats["RTM"]["elec_active"] += rtm_df[rtm_df["ELEC_ACTIVE"]][
                    "QUANTIDADE"
                ].sum()
                stats["RTM"]["norm_active"] += rtm_df[rtm_df["NORM_ACTIVE"]][
                    "QUANTIDADE"
                ].sum()

                # Aggregate Non-RTM
                non_rtm_df = processed[~processed["IS_RTM"]]
                stats["NON_RTM"]["total"] += non_rtm_df["QUANTIDADE"].sum()
                stats["NON_RTM"]["elec_active"] += non_rtm_df[
                    non_rtm_df["ELEC_ACTIVE"]
                ]["QUANTIDADE"].sum()
                stats["NON_RTM"]["norm_active"] += non_rtm_df[
                    non_rtm_df["NORM_ACTIVE"]
                ]["QUANTIDADE"].sum()

            if (i + 1) % 10 == 0:
                print(f"Processed {i + 1} chunks...")

    except Exception as e:
        print(f"Error processing file: {e}")

    print("\n" + "=" * 50)
    print(f"RESULTS FOR 2024 (Reference Date: {TODAY.strftime('%Y-%m-%d')})")
    print("=" * 50)

    for category in ["RTM", "NON_RTM"]:
        data = stats[category]
        total = data["total"]
        print(f"\nCategory: {category}")
        print(f"Total Chassis (Pumps): {int(total)}")
        if total > 0:
            elec_pct = (data["elec_active"] / total) * 100
            norm_pct = (data["norm_active"] / total) * 100
            print(
                f"Electronics Warranty Active: {int(data['elec_active'])} ({elec_pct:.2f}%)"
            )
            print(
                f"Normal Warranty Active:      {int(data['norm_active'])} ({norm_pct:.2f}%)"
            )
        else:
            print("No chassis found.")


if __name__ == "__main__":
    main()
