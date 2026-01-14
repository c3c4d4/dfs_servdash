import pandas as pd
from datetime import datetime, timedelta

INPUT_FILE = "o2c.csv"
CHUNK_SIZE = 5000
YEARS = [2023, 2024, 2025]
TODAY = datetime(2026, 1, 13)
GARANTIA_ELETRONICA_DAYS = 365


def normalize_garantia_to_days(garantia_text):
    if pd.isna(garantia_text):
        return 0
    try:
        return int(float(str(garantia_text).replace(",", ".")))
    except:
        return 0


def calc_all_years():
    # Structure: Year -> RTM/NON_RTM -> metrics
    results = {
        year: {
            "RTM": {"sales": 0, "norm": 0, "elec": 0},
            "NON_RTM": {"sales": 0, "norm": 0, "elec": 0},
        }
        for year in YEARS
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
            # Use cached numeric value if possible, else 0
            val = row["GARANTIA"]
            if str(val).isdigit():
                garantia_map[row["ITEM"]] = int(val)
            else:
                garantia_map[row["ITEM"]] = normalize_garantia_to_days(val)
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

                    for year in YEARS:
                        mask_year = df_filtered["DT_NUM_NF"].dt.year == year
                        df_year = df_filtered[mask_year]

                        if len(df_year) > 0:
                            for _, row in df_year.iterrows():
                                qty = row["QUANTIDADE"]
                                item = row["ITEM"]

                                is_rtm = "SIM" in rtm_map.get(item, "NAO")
                                cat = "RTM" if is_rtm else "NON_RTM"

                                # Check warranty
                                w_days = garantia_map.get(item, 0)
                                # Inline override if available? (Keeping simple/consistent with previous logic)

                                date_nf = row["DT_NUM_NF"]
                                if pd.isna(date_nf):
                                    continue

                                elec_active = (
                                    date_nf + timedelta(days=GARANTIA_ELETRONICA_DAYS)
                                ) >= TODAY
                                norm_active = (
                                    date_nf + timedelta(days=w_days)
                                ) >= TODAY

                                results[year][cat]["sales"] += qty
                                if elec_active:
                                    results[year][cat]["elec"] += qty
                                if norm_active:
                                    results[year][cat]["norm"] += qty

    except Exception as e:
        print(f"Error: {e}")

    # Print Results
    print("--- RAW VALUES ---")

    # Non-RTM
    print("\nNon-RTM Data:")
    total_sales = 0
    total_norm = 0
    total_elec = 0

    # 2023, 2024, 2025
    for year in YEARS:
        d = results[year]["NON_RTM"]
        total_sales += d["sales"]
        total_norm += d["norm"]
        total_elec += d["elec"]

        pct_norm = (d["norm"] / d["sales"] * 100) if d["sales"] else 0
        pct_elec = (d["elec"] / d["sales"] * 100) if d["sales"] else 0

        print(f"Year {year}:")
        print(f"Sales: {int(d['sales'])}")
        print(f"Warranty: {pct_norm:.1f}% ({int(d['norm'])})")
        print(f"Elec Warranty: {pct_elec:.1f}% ({int(d['elec'])})")

    # Total
    pct_norm_tot = (total_norm / total_sales * 100) if total_sales else 0
    pct_elec_tot = (total_elec / total_sales * 100) if total_sales else 0
    print("Total:")
    print(f"Sales: {int(total_sales)}")
    print(f"Warranty: {pct_norm_tot:.1f}% ({int(total_norm)})")
    print(f"Elec Warranty: {pct_elec_tot:.1f}% ({int(total_elec)})")

    # RTM
    print("\nRTM Data:")
    total_sales = 0
    total_norm = 0
    total_elec = 0

    for year in YEARS:
        d = results[year]["RTM"]
        total_sales += d["sales"]
        total_norm += d["norm"]
        total_elec += d["elec"]

        pct_norm = (d["norm"] / d["sales"] * 100) if d["sales"] else 0
        pct_elec = (d["elec"] / d["sales"] * 100) if d["sales"] else 0

        print(f"Year {year}:")
        print(f"Sales: {int(d['sales'])}")
        print(f"Warranty: {pct_norm:.1f}% ({int(d['norm'])})")
        print(f"Elec Warranty: {pct_elec:.1f}% ({int(d['elec'])})")

    # Total
    pct_norm_tot = (total_norm / total_sales * 100) if total_sales else 0
    pct_elec_tot = (total_elec / total_sales * 100) if total_sales else 0
    print("Total:")
    print(f"Sales: {int(total_sales)}")
    print(f"Warranty: {pct_norm_tot:.1f}% ({int(total_norm)})")
    print(f"Elec Warranty: {pct_elec_tot:.1f}% ({int(total_elec)})")


if __name__ == "__main__":
    calc_all_years()
