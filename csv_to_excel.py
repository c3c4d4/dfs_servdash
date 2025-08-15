import pandas as pd

def csv_to_excel():
    """
    Read chamados_fechados.csv and chamados.csv files and filter only rows containing "ANGELONI"
    """
    
    # Read the CSV files
    try:
        df_fechados = pd.read_csv('chamados_fechados.csv', sep=';', encoding='utf-8-sig')
        print(f"Loaded {len(df_fechados)} rows from chamados_fechados.csv")
    except Exception as e:
        print(f"Error reading chamados_fechados.csv: {e}")
        return
    
    try:
        df_abertos = pd.read_csv('chamados.csv', sep=';', encoding='utf-8-sig')
        print(f"Loaded {len(df_abertos)} rows from chamados.csv")
    except Exception as e:
        print(f"Error reading chamados.csv: {e}")
        return
    
    # Filter rows containing "ANGELONI" in any column
    def contains_angeloni(df):
        # Convert all columns to string and check if any contains "ANGELONI"
        mask = df.astype(str).apply(lambda x: x.str.contains('ANGELONI', case=False, na=False)).any(axis=1)
        return df[mask]
    
    df_fechados_angeloni = contains_angeloni(df_fechados)
    df_abertos_angeloni = contains_angeloni(df_abertos)
    
    print(f"Found {len(df_fechados_angeloni)} ANGELONI rows in chamados_fechados.csv")
    print(f"Found {len(df_abertos_angeloni)} ANGELONI rows in chamados.csv")
    
    # Create Excel writer object
    with pd.ExcelWriter('chamados_angeloni.xlsx', engine='openpyxl') as writer:
        # Write filtered dataframes to separate sheets
        if len(df_fechados_angeloni) > 0:
            df_fechados_angeloni.to_excel(writer, sheet_name='Fechados ANGELONI', index=False)
        if len(df_abertos_angeloni) > 0:
            df_abertos_angeloni.to_excel(writer, sheet_name='Abertos ANGELONI', index=False)
        
        # Also create a combined sheet
        df_combined = pd.concat([df_fechados_angeloni, df_abertos_angeloni], ignore_index=True)
        if len(df_combined) > 0:
            df_combined.to_excel(writer, sheet_name='Todos ANGELONI', index=False)
    
    print(f"Excel file 'chamados_angeloni.xlsx' created successfully!")
    print(f"Total ANGELONI rows: {len(df_combined)}")

if __name__ == "__main__":
    csv_to_excel()