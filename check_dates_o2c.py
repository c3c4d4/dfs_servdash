import pandas as pd

try:
    df = pd.read_csv("o2c.csv", sep=";", dtype=str, encoding="utf-8-sig")
    print(f"Columns: {df.columns.tolist()}")

    if "DT_NUM_NF" in df.columns:
        df["DT_NUM_NF"] = pd.to_datetime(
            df["DT_NUM_NF"], dayfirst=True, errors="coerce"
        )
        print(f"Date Range: {df['DT_NUM_NF'].min()} to {df['DT_NUM_NF'].max()}")
        print("Years found:")
        print(df["DT_NUM_NF"].dt.year.value_counts().sort_index())
    else:
        print("DT_NUM_NF not found")

except Exception as e:
    print(e)
