"""
DFS ServiceWatch


## Páginas disponíveis

### 1. Principal (Chamados)
- Relatório detalhado de todos os chamados (abertos e fechados).
- Permite pesquisar, filtrar por múltiplos campos, status, datas, tags e mais.
- KPIs de volume, aging, % garantia, % RTM, e gráficos de performance por mantenedor, proprietário e especialista.
- Ideal para análise operacional e acompanhamento do ciclo de chamados.

### 2. Parque Instalado (Mapa)
- Visualização do parque instalado de bombas por estado em mapa interativo.
- Filtros avançados: RTM, Garantia, Partida Inicial, Ano da NF, Nº de chamados.
- KPIs de cobertura, % com partida, % com chamado, % RTM, médias de chamados.
- Tabela detalhada com todos os dados das bombas filtradas.
- Ideal para análise estratégica, cobertura e histórico de atuação.

**Como usar:**
- Utilize o menu lateral para navegar entre as páginas.
- Use os filtros disponíveis em cada página para refinar sua análise.
- Clique nos mapas e tabelas para explorar os dados de forma interativa.
"""

import os
import streamlit as st
import pandas as pd
from data_loader import carregar_dados_merged, carregar_o2c, process_o2c_data
from datetime import datetime
from pathlib import Path

# Configuração da página principal
st.set_page_config(page_title="DFS ServiceWatch", page_icon="🛠️", layout="wide")


# Load data for summary metrics
@st.cache_data(ttl=1800, show_spinner=False)
def load_summary_data():
    chamados = carregar_dados_merged()
    o2c = carregar_o2c()
    # Filter O2C for Brazil
    o2c = process_o2c_data(o2c)
    return chamados, o2c


try:
    chamados_df, o2c_df = load_summary_data()

    # Calculate metrics
    # 1. Total Active Calls (Open)
    if "Status" in chamados_df.columns:
        total_active = (chamados_df["Status"].str.upper() == "ABERTO").sum()
    elif "STATUS" in chamados_df.columns:
        total_active = (chamados_df["STATUS"].str.upper() == "ABERTO").sum()
    else:
        total_active = 0

    # 2. Total Units in Field (Brazil)
    # Ensure we count unique serials
    if "NUM_SERIAL" in o2c_df.columns:
        total_units = o2c_df["NUM_SERIAL"].nunique()
    elif "Serial" in o2c_df.columns:
        total_units = o2c_df["Serial"].nunique()
    else:
        total_units = 0

    # 3. Today's Incoming Calls
    today = datetime.now().date()
    if "Data" in chamados_df.columns:
        date_col = "Data"
    elif "DATA" in chamados_df.columns:
        date_col = "DATA"
    else:
        date_col = None

    if date_col:
        # Convert to datetime if needed
        if not pd.api.types.is_datetime64_any_dtype(chamados_df[date_col]):
            chamados_df[date_col] = pd.to_datetime(
                chamados_df[date_col], dayfirst=True, errors="coerce"
            )

        todays_calls = (chamados_df[date_col].dt.date == today).sum()
    else:
        todays_calls = 0

except Exception:
    total_active = "-"
    total_units = "-"
    todays_calls = "-"


# Título e mensagem de boas-vindas
st.title("🛠️ DFS ServiceWatch")
st.markdown("### Monitoramento Inteligente de Serviços")

# Executive Summary Metrics
st.markdown("---")
col1, col2, col3 = st.columns(3)
col1.metric("Chamados Abertos Hoje", total_active, delta=None)
col2.metric(
    "Total Bombas (Brasil)", f"{total_units:,.0f}".replace(",", "."), delta=None
)
col3.metric("Novos Chamados (Hoje)", todays_calls, delta=None)


# Data freshness indicator
def get_data_freshness():
    """Get the last modified time of key data files."""
    base_path = Path(__file__).parent
    data_files = {
        "Chamados": base_path / "chamados.csv",
        "O2C": base_path / "o2c_unpacked.csv",
    }
    freshness = {}
    for name, path in data_files.items():
        if path.exists():
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            freshness[name] = mtime
    return freshness


try:
    freshness = get_data_freshness()
    if freshness:
        freshness_items = []
        for name, mtime in freshness.items():
            age_hours = (datetime.now() - mtime).total_seconds() / 3600
            if age_hours < 24:
                status = "ok"
            elif age_hours < 48:
                status = "warning"
            else:
                status = "stale"
            freshness_items.append(f"**{name}**: {mtime.strftime('%d/%m/%Y %H:%M')}")
        st.caption("Atualizado em: " + " | ".join(freshness_items))
except Exception:
    pass  # Silently fail if freshness check fails

st.markdown("---")

# Instrução para navegação
st.sidebar.success("Selecione uma página acima.")

# Descrição e informações institucionais e de uso das páginas
col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown(
        """
        Este é um dashboard interativo para análise de chamados de serviços.
        
        **Selecione uma página no menu lateral** para visualizar diferentes análises e relatórios.
        
        ### 🚀 Funcionalidades
        
        **1. 📊 Principal (Chamados)**
        *   **Visão Geral:** KPIs de volume, aging e distribuição.
        *   **Dados Detalhados:** Tabela pesquisável com filtros avançados.
        *   **Análise Gráfica:** Performance por mantenedor e especialista.
        
        **2. 🗺️ Parque Instalado (Mapa)**
        *   **Geolocalização:** Mapa interativo das bombas por estado.
        *   **Filtros Inteligentes:** RTM, Garantia, Ano da NF.
        *   **Análise de Cobertura:** Identificação de gaps de serviço.
        """
    )

with col_right:
    st.info(
        """
        ### ℹ️ Sobre
        
        **Equipe de Serviços**
        Dover Fueling Solutions
        
        **Contato:**
        *   [Cauã Almeida (BI)](mailto:c-calmeida@doverfs.com)
        *   [Fernanda Barbieri (Gerente)](mailto:fernanda.barbieri@doverfs.com)
        """
    )
