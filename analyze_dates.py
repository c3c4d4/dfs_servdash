import pandas as pd

INPUT_FILE = "o2c.csv"
CHUNK_SIZE = 10000
TARGET_YEAR = 2024


def analyze_dates_and_types():
    counts_by_date = {"NF": 0, "CRIACAO": 0, "BOOKED": 0}
    counts_by_tipo = {}

    try:
        reader = pd.read_csv(
            INPUT_FILE, sep=";", dtype=str, encoding="latin1", chunksize=CHUNK_SIZE
        )

        for chunk in reader:
            chunk.columns = [c.strip().replace("\ufeff", "") for c in chunk.columns]

            # Filter for Chassis (W7 + BOMBA MEDIDORA)
            if "DESCRICAO" in chunk.columns and "ITEM" in chunk.columns:
                mask_desc = (
                    chunk["DESCRICAO"]
                    .astype(str)
                    .str.upper()
                    .str.contains("BOMBA MEDIDORA", na=False)
                )
                mask_item = chunk["ITEM"].astype(str).str.upper().str.startswith("W7")
                df_chassis = chunk[mask_desc & mask_item].copy()

                if len(df_chassis) > 0:
                    df_chassis["QUANTIDADE"] = (
                        df_chassis["QUANTIDADE"]
                        .astype(str)
                        .str.replace(",", ".")
                        .astype(float)
                        .fillna(0)
                    )

                    # Check Invoice Date (NF)
                    if "DT_NUM_NF" in df_chassis.columns:
                        dates = pd.to_datetime(
                            df_chassis["DT_NUM_NF"], dayfirst=True, errors="coerce"
                        )
                        mask_2024 = dates.dt.year == TARGET_YEAR
                        counts_by_date["NF"] += df_chassis[mask_2024][
                            "QUANTIDADE"
                        ].sum()

                        # Analyze TIPO for 2024 NF
                        df_2024_nf = df_chassis[mask_2024]
                        if "TIPO" in df_2024_nf.columns:
                            for tipo, group in df_2024_nf.groupby("TIPO"):
                                counts_by_tipo[tipo] = (
                                    counts_by_tipo.get(tipo, 0)
                                    + group["QUANTIDADE"].sum()
                                )

                    # Check Creation Date
                    if "DATA_CRIACAO" in df_chassis.columns:
                        dates = pd.to_datetime(
                            df_chassis["DATA_CRIACAO"], dayfirst=True, errors="coerce"
                        )
                        mask_2024 = dates.dt.year == TARGET_YEAR
                        counts_by_date["CRIACAO"] += df_chassis[mask_2024][
                            "QUANTIDADE"
                        ].sum()

                    # Check Booked Date
                    if "DATA_BOOKED" in df_chassis.columns:
                        dates = pd.to_datetime(
                            df_chassis["DATA_BOOKED"], dayfirst=True, errors="coerce"
                        )
                        mask_2024 = dates.dt.year == TARGET_YEAR
                        counts_by_date["BOOKED"] += df_chassis[mask_2024][
                            "QUANTIDADE"
                        ].sum()

    except Exception as e:
        print(f"Error: {e}")

    print(f"Counts by Date Field in 2024 (W7 + BOMBA MEDIDORA):")
    print(f"By DT_NUM_NF (Invoice): {counts_by_date['NF']}")
    print(f"By DATA_CRIACAO (Creation): {counts_by_date['CRIACAO']}")
    print(f"By DATA_BOOKED (Booked): {counts_by_date['BOOKED']}")

    print("\nCounts by TIPO (for Invoice Date 2024):")
    for tipo, count in counts_by_tipo.items():
        print(f"{tipo}: {count}")


if __name__ == "__main__":
    analyze_dates_and_types()
