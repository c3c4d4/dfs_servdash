import os
import requests
import pandas as pd
from datetime import datetime

# URL and headers for the request
url = "https://dfsrioreporting.doverfs.com/ctrlproducao/pt/helpdeskconsultax.asp"
headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded",
    "Cookie": "usuario%5Fintranet=c%5C-calmeida; idusuario%5Fintranet=3397;",  # Add all cookie data
    "Origin": "https://dfsrioreporting.doverfs.com",
    "Referer": "https://dfsrioreporting.doverfs.com/ctrlproducao/pt/helpdeskconsulta.asp?tipo=NOVO",
    "Sec-Fetch-Dest": "frame",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "sec-ch-ua": '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"'
}

# Format today's date as DD/MM/YYYY
today_date = datetime.now().strftime("%d/%m/%Y")

data = {
    "calend1": "01/01/2025",
    "calend2": today_date,
    # "nf":"SIM",
    "excel":"SIM"
}

# Send the POST request to download the XLS file
response = requests.post(url, headers=headers, data=data)

# Check if the request was successful
if response.status_code == 200:
    # Save the file temporarily as XLS
    with open("downloaded_file.html", "wb") as f:
        f.write(response.content)
    
    # Load the HTML file as a pandas DataFrame
    df = pd.read_html("downloaded_file.html", header=0)[0]  # Assuming the first table is the one you need
    df = df.drop(df.index[-1])  # Drop the last row if it contains totals
    # Save the DataFrame as a CSV with semicolon separator and UTF-8 encoding
    df.to_csv("chamados.csv", sep=';', encoding='utf-8-sig', index=False)
    os.remove("downloaded_file.html")
    print("CSV file saved successfully.")
else:
    print(f"Failed to download file. Status code: {response.status_code}")
