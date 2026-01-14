import pandas as pd

INPUT_FILE = "o2c.csv"
CHUNK_SIZE = 5000
YEAR = 2025


def inspect_all_2025():
    total_qty = 0
    rtm_map = {}

    # Load RTM Cache
    try:
        df = pd.read_csv("rtm_cache.csv", sep=";", dtype=str, encoding="utf-8-sig")
        for _, row in df.iterrows():
            rtm_map[row["ITEM"]] = str(row["RTM"]).upper().strip()
    except:
        pass

    # To store items that MIGHT be RTM but marked NAO or not in cache
    potential_rtm = []

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

            # Use same filters as "calc_all_years.py"
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
                    df_filtered["DT_NUM_NF"] = pd.to_datetime(
                        df_filtered["DT_NUM_NF"], dayfirst=True, errors="coerce"
                    )

                    mask_year = df_filtered["DT_NUM_NF"].dt.year == YEAR
                    df_year = df_filtered[mask_year].copy()

                    if len(df_year) > 0:
                        df_year["QUANTIDADE"] = (
                            df_year["QUANTIDADE"]
                            .astype(str)
                            .str.replace(",", ".")
                            .astype(float)
                            .fillna(0)
                        )

                        for _, row in df_year.iterrows():
                            item = row["ITEM"]
                            qty = row["QUANTIDADE"]
                            desc = row.get("DESCRICAO", "")
                            rtm_status = rtm_map.get(
                                item,
                                "NAO (Cache Miss)" if item not in rtm_map else "NAO",
                            )

                            total_qty += qty

                            # Log everything for manual inspection if needed, or aggregate
                            potential_rtm.append(
                                {
                                    "ITEM": item,
                                    "QTY": qty,
                                    "RTM_STATUS": rtm_status,
                                    "DESCRICAO": desc,
                                }
                            )

    except Exception as e:
        print(f"Error: {e}")

    print(f"Total 'W7' Dispensers in {YEAR}: {total_qty}")

    df_res = pd.DataFrame(potential_rtm)
    if not df_res.empty:
        # Check if any "NAO" items look like they should be RTM?
        # Or simply list the top items that are NOT RTM to see if we missed any
        print("\nTop 20 NON-RTM items by quantity:")
        non_rtm = df_res[~df_res["RTM_STATUS"].str.contains("SIM")]
        non_rtm_agg = (
            non_rtm.groupby(["ITEM", "DESCRICAO", "RTM_STATUS"])["QTY"]
            .sum()
            .reset_index()
            .sort_values("QTY", ascending=False)
        )
        print(non_rtm_agg.head(20).to_string())


if __name__ == "__main__":
    inspect_all_2025()
