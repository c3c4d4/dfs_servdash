import os
import sys
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from datetime import datetime, timedelta
from rich.console import Console
from rich.progress import track

# CONFIG
URL = "https://dfsrioreporting.doverfs.com/ctrlproducao/pt/helpdeskconsultax.asp"
TIMEOUT = 180  # 3 minutes timeout
MAX_RETRIES = 3
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded",
    "Cookie": "usuario%5Fintranet=c%5C-calmeida; idusuario%5Fintranet=3397;",  # Update as needed
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
    "sec-ch-ua-platform": '"Windows"',
}

console = Console()


def create_session():
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=2,  # wait 2, 4, 8 seconds between retries
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# Helper to fetch a single month or partial month
# Se start_day e end_day forem passados, busca só o intervalo
# Senão, busca o mês inteiro


def fetch_month(year, month, start_day=1, end_day=None, session=None):
    if end_day is None:
        end_day = (
            (datetime(year, month % 12 + 1, 1) - timedelta(days=1)).day
            if month < 12
            else 31
        )
    start_date = f"{start_day:02d}/{month:02d}/{year}"
    end_date = f"{end_day:02d}/{month:02d}/{year}"
    data = {"calend1": start_date, "calend2": end_date, "excel": "SIM"}

    if session is None:
        session = create_session()

    for attempt in range(MAX_RETRIES):
        try:
            response = session.post(URL, headers=HEADERS, data=data, timeout=TIMEOUT)
            if response.status_code == 200:
                fname = f"tmp_{year}_{month:02d}.html"
                with open(fname, "wb") as f:
                    f.write(response.content)
                df = pd.read_html(fname, header=0)[0]
                os.remove(fname)
                if len(df) > 0 and "Data" in df.columns:
                    df = df.drop(df.index[-1])  # Drop totals row if present
                return df
            else:
                console.print(
                    f"[red]Failed to fetch {start_date} - {end_date}: {response.status_code}"
                )
                return pd.DataFrame()
        except requests.exceptions.Timeout as e:
            wait_time = (2**attempt) * 5  # 5, 10, 20 seconds
            if attempt < MAX_RETRIES - 1:
                console.print(
                    f"[yellow]Timeout fetching {start_date} - {end_date}. Retrying in {wait_time}s... (attempt {attempt + 1}/{MAX_RETRIES})"
                )
                time.sleep(wait_time)
            else:
                console.print(
                    f"[red]Timeout fetching {start_date} - {end_date} after {MAX_RETRIES} attempts: {e}"
                )
                return pd.DataFrame()
        except Exception as e:
            console.print(f"[red]Exception fetching {start_date} - {end_date}: {e}")
            return pd.DataFrame()

    return pd.DataFrame()


def main():
    today = datetime.now()
    oldest_file = "oldest.txt"
    chamados_file = (
        "chamados.csv"  # Base principal: chamados a partir do aberto mais antigo
    )
    fechados_file = "chamados_fechados.csv"  # Fechados anteriores ao aberto mais antigo

    # 1. Determine fetch range
    if not os.path.exists(oldest_file):
        # First run: fetch all data from 2023
        start = datetime(2023, 1, 1)
        end = today
        console.print(
            "[bold cyan]No oldest.txt found. Fetching all chamados from 2023 month by month..."
        )
    else:
        with open(oldest_file) as f:
            oldest_str = f.read().strip()
        start = datetime.strptime(oldest_str, "%d/%m/%Y")
        end = today
        console.print(
            f"[bold cyan]oldest.txt found. Fetching chamados from {start.strftime('%d/%m/%Y')} to today month by month..."
        )

    # 2. Buscar mês a mês, respeitando o início parcial do primeiro mês
    dfs = []
    current = start
    session = create_session()  # Reuse session for all requests
    while current <= end:
        year = current.year
        month = current.month
        if current.day != 1:
            # Primeiro mês: começa do dia específico
            start_day = current.day
        else:
            start_day = 1
        # Último mês: termina no dia atual
        if year == end.year and month == end.month:
            end_day = end.day
        else:
            # Pega até o fim do mês
            end_day = (
                (datetime(year, month % 12 + 1, 1) - timedelta(days=1)).day
                if month < 12
                else 31
            )
        console.print(f"[blue]Baixando {year}-{month:02d} de {start_day} até {end_day}")
        df = fetch_month(year, month, start_day, end_day, session=session)
        if not df.empty:
            dfs.append(df)
        # Avança para o próximo mês
        if month == 12:
            current = current.replace(year=year + 1, month=1, day=1)
        else:
            current = current.replace(month=month + 1, day=1)

    if not dfs:
        console.print("[red]No data fetched. Exiting.")
        sys.exit(1)
    new_df = pd.concat(dfs, ignore_index=True)

    # 3. Merge com chamados.csv (base principal)
    if os.path.exists(chamados_file):
        base_chamados = pd.read_csv(chamados_file, sep=";", encoding="utf-8-sig")
        all_df = pd.concat([base_chamados, new_df], ignore_index=True)
    else:
        all_df = new_df.copy()

    # 4. Encontrar chamado aberto mais antigo
    if "Status" in all_df.columns and "Data" in all_df.columns:
        open_df = all_df[all_df["Status"].str.upper() == "ABERTO"]
        if not open_df.empty:
            oldest_open = pd.to_datetime(
                open_df["Data"], dayfirst=True, errors="coerce"
            ).min()
            if pd.isna(oldest_open):
                console.print("[yellow]No valid open chamado dates found.")
                oldest_open = today
            else:
                console.print(
                    f"[bold magenta]Oldest open chamado: {oldest_open.strftime('%d/%m/%Y')}"
                )
        else:
            oldest_open = today
            console.print("[yellow]No open chamados found.")
    else:
        console.print("[red]Missing 'Status' or 'Data' columns.")
        oldest_open = today

    # 5. Salvar oldest.txt
    with open(oldest_file, "w") as f:
        f.write(oldest_open.strftime("%d/%m/%Y"))

    # 6. Atualizar chamados_fechados.csv com todos fechados antes do mais antigo aberto
    if "Status" in all_df.columns and "Data" in all_df.columns:
        closed_df = all_df[
            (all_df["Status"].str.upper() != "ABERTO")
            & (
                pd.to_datetime(all_df["Data"], dayfirst=True, errors="coerce")
                < oldest_open
            )
        ]
        # Adiciona ao final do chamados_fechados.csv existente
        if os.path.exists(fechados_file):
            fechados_antigos = pd.read_csv(fechados_file, sep=";", encoding="utf-8-sig")
            fechados_atualizado = pd.concat(
                [fechados_antigos, closed_df], ignore_index=True
            )
        else:
            fechados_atualizado = closed_df.copy()
        fechados_atualizado.to_csv(
            fechados_file, sep=";", encoding="utf-8-sig", index=False
        )
        console.print(
            f"[green]Updated {fechados_file} with all closed chamados before {oldest_open.strftime('%d/%m/%Y')}"
        )

    # 7. Atualizar chamados.csv com todos os chamados a partir do chamado aberto mais antigo (inclusive fechados)
    if "Data" in all_df.columns:
        chamados_atuais = all_df[
            pd.to_datetime(all_df["Data"], dayfirst=True, errors="coerce")
            >= oldest_open
        ]
        chamados_atuais.to_csv(
            chamados_file, sep=";", encoding="utf-8-sig", index=False
        )
        console.print(f"[bold green]Saved merged base to {chamados_file}")


if __name__ == "__main__":
    main()
