import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Constants
GARANTIA_ELETRONICA_DAYS = 365
TARGET_YEAR = 2024
TODAY = datetime(2026, 1, 13)  # Using the date provided in the prompt environment


def load_data():
    print("Loading data...")
    # Load O2C
    o2c = pd.read_csv("o2c_unpacked.csv", sep=";", dtype=str, encoding="utf-8-sig")

    # Clean columns
    o2c.columns = [c.strip() for c in o2c.columns]

    # Parse dates
    o2c["DT_NUM_NF"] = pd.to_datetime(
        o2c["DT_NUM_NF"], dayfirst=True, errors="coerce", format="mixed"
    )

    # Filter for Target Year
    o2c = o2c[o2c["DT_NUM_NF"].dt.year == TARGET_YEAR].copy()
    print(f"Filtered {len(o2c)} records for year {TARGET_YEAR}")

    # Load RTM Cache
    try:
        rtm_cache = pd.read_csv(
            "rtm_cache.csv", sep=";", dtype=str, encoding="utf-8-sig"
        )
        rtm_map = dict(zip(rtm_cache["ITEM"], rtm_cache["RTM"]))
    except FileNotFoundError:
        rtm_map = {}
        print("Warning: rtm_cache.csv not found")

    # Load Warranty Cache
    try:
        garantia_cache = pd.read_csv(
            "garantia_cache.csv", sep=";", dtype=str, encoding="utf-8-sig"
        )
        garantia_map = dict(zip(garantia_cache["ITEM"], garantia_cache["GARANTIA"]))
    except FileNotFoundError:
        garantia_map = {}
        print("Warning: garantia_cache.csv not found")

    return o2c, rtm_map, garantia_map


def process_data(o2c, rtm_map, garantia_map):
    # Apply RTM
    # Prioritize RTM column in o2c if it exists and is not empty, otherwise use cache
    if "RTM" not in o2c.columns:
        o2c["RTM"] = ""

    # Fill missing RTM from cache
    mask_missing_rtm = (o2c["RTM"].isna()) | (o2c["RTM"] == "")
    o2c.loc[mask_missing_rtm, "RTM"] = o2c.loc[mask_missing_rtm, "ITEM"].map(rtm_map)

    # Fill remaining missing RTM with 'NAO' (default)
    o2c["RTM"] = o2c["RTM"].fillna("NAO").replace("", "NAO")

    # Normalize RTM to SIM/NAO just in case
    o2c["RTM"] = o2c["RTM"].astype(str).str.upper().str.strip()

    # Apply Warranty
    # Prioritize GARANTIA column in o2c
    if "GARANTIA" not in o2c.columns:
        o2c["GARANTIA"] = ""

    mask_missing_garantia = (
        (o2c["GARANTIA"].isna())
        | (o2c["GARANTIA"] == "")
        | (o2c["GARANTIA"] == "NAO ENCONTRADO")
    )
    o2c.loc[mask_missing_garantia, "GARANTIA"] = o2c.loc[
        mask_missing_garantia, "ITEM"
    ].map(garantia_map)

    # Convert Warranty to numeric days
    o2c["GARANTIA_DAYS"] = pd.to_numeric(o2c["GARANTIA"], errors="coerce").fillna(0)

    # Calculate Status
    # Electronics Warranty (Fixed 365 days)
    o2c["FIM_GARANTIA_ELETRONICA"] = o2c["DT_NUM_NF"] + timedelta(
        days=GARANTIA_ELETRONICA_DAYS
    )
    o2c["STATUS_ELETRONICA"] = np.where(
        o2c["FIM_GARANTIA_ELETRONICA"] >= TODAY, "DENTRO", "FORA"
    )

    # Normal Warranty
    o2c["FIM_GARANTIA_NORMAL"] = o2c["DT_NUM_NF"] + pd.to_timedelta(
        o2c["GARANTIA_DAYS"], unit="D"
    )
    o2c["STATUS_NORMAL"] = np.where(
        o2c["FIM_GARANTIA_NORMAL"] >= TODAY, "DENTRO", "FORA"
    )

    return o2c


def analyze(df):
    # Split by RTM
    rtm_sim = df[df["RTM"] == "SIM"]
    rtm_nao = df[df["RTM"] != "SIM"]

    results = {}

    for label, subset in [("RTM (SIM)", rtm_sim), ("Non-RTM (NAO)", rtm_nao)]:
        total = len(subset)
        if total == 0:
            results[label] = {
                "total": 0,
                "elec_in": 0,
                "elec_in_pct": 0,
                "norm_in": 0,
                "norm_in_pct": 0,
            }
            continue

        elec_in = len(subset[subset["STATUS_ELETRONICA"] == "DENTRO"])
        norm_in = len(subset[subset["STATUS_NORMAL"] == "DENTRO"])

        results[label] = {
            "total": total,
            "elec_in": elec_in,
            "elec_in_pct": (elec_in / total) * 100,
            "norm_in": norm_in,
            "norm_in_pct": (norm_in / total) * 100,
        }

    return results


if __name__ == "__main__":
    o2c, rtm_map, garantia_map = load_data()
    df = process_data(o2c, rtm_map, garantia_map)
    results = analyze(df)

    print("\n--- Results for 2024 Chassis (Reference Date: 2026-01-13) ---")
    for label, data in results.items():
        print(f"\n{label}:")
        print(f"  Total Chassis: {data['total']}")
        print(
            f"  Under Electronics Warranty (1 yr): {data['elec_in']} ({data['elec_in_pct']:.2f}%)"
        )
        print(
            f"  Under Normal Warranty (Variable):  {data['norm_in']} ({data['norm_in_pct']:.2f}%)"
        )
