import pandas as pd
from datetime import datetime, timedelta

INPUT_FILE = "o2c.csv"
CHUNK_SIZE = 5000
TARGET_YEAR = 2024
TODAY = datetime(2026, 1, 13)
GARANTIA_ELETRONICA_DAYS = 365

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
    for pattern, days in GARANTIA_TEXT_TO_DAYS.items():
        if pattern in str(garantia_text).upper():
            return days
    return 0


def final_calc():
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
            garantia_map[row["ITEM"]] = normalize_garantia_to_days(row["GARANTIA"])
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
                        mask_2024 = dates.dt.year == TARGET_YEAR
                        df_final = df_chassis[mask_2024].copy()

                        if len(df_final) > 0:
                            for _, row in df_final.iterrows():
                                item = row["ITEM"]
                                qty = row["QUANTIDADE"]

                                # RTM
                                is_rtm = "SIM" in rtm_map.get(item, "NAO")

                                # Warranty
                                w_days = garantia_map.get(item, 0)
                                if pd.notna(row["GARANTIA"]) and row["GARANTIA"] != "":
                                    # Prefer inline warranty if available and valid?
                                    # But for consistency with caches use map or normalize inline
                                    w_inline = normalize_garantia_to_days(
                                        row["GARANTIA"]
                                    )
                                    if w_inline > 0:
                                        w_days = w_inline

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
    final_calc()
