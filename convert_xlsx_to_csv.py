import pandas as pd
import sys

try:
    print("Reading o2c.xlsx...")
    df = pd.read_excel('o2c.xlsx')
    print(f"Read {len(df)} rows. Saving to o2c.csv...")
    # Save as CSV compatible with unpack_by_serial.py
    # sep=';', encoding='latin1' (using errors='replace' to avoid crash on unsupported chars, though better to know)
    df.to_csv('o2c.csv', sep=';', encoding='latin1', index=False, errors='replace')
    print("Successfully converted o2c.xlsx to o2c.csv")
except Exception as e:
    print(f"Error converting: {e}")
    sys.exit(1)
