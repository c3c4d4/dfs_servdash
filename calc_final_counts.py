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


def calc_final_counts():
    # Adjusted Logic based on user feedback (RTM count should be around 130 for 2025)
    # The previous "SEGMENTO=DISPENSER + W7" filter yielded 79 RTMs.
    # We will try expanding the RTM check to anything in the file, OR stick to the strict filter if the user is mistaken or referring to a different dataset.
    # However, since the user challenged the data, let's present the strict filter we have but acknowledge the potential discrepancy or check if we missed something simple.
    # Let's double check if we are missing RTMs by NOT filtering for SEGMENTO first?
    # No, let's stick to the consistent methodology that yielded sensible results for other years, but ensure we catch all W7 + BOMBA.

    # Actually, let's use the W7 + BOMBA logic which is safer than SEGMENTO sometimes.

    results = {
        year: {
            "RTM": {"sales": 0, "norm": 0, "elec": 0},
            "NON_RTM": {"sales": 0, "norm": 0, "elec": 0},
        }
        for year in YEARS
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

            # Using W7 + BOMBA MEDIDORA Logic (Broader than SEGMENTO=DISPENSER sometimes)
            if (
                "DESCRICAO" in chunk.columns
                and "ITEM" in chunk.columns
                and "DT_NUM_NF" in chunk.columns
            ):
                mask_desc = (
                    chunk["DESCRICAO"]
                    .astype(str)
                    .str.upper()
                    .str.contains("BOMBA MEDIDORA", na=False)
                )
                mask_item = chunk["ITEM"].astype(str).str.upper().str.startswith("W7")

                # Combine
                df_filtered = chunk[mask_desc & mask_item].copy()

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

                                w_days = garantia_map.get(item, 0)

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

    print("Year,Category,Sales,Norm_Active,Elec_Active")
    for year in YEARS:
        for cat in ["RTM", "NON_RTM"]:
            d = results[year][cat]
            print(f"{year},{cat},{int(d['sales'])},{int(d['norm'])},{int(d['elec'])}")


if __name__ == "__main__":
    calc_final_counts()
