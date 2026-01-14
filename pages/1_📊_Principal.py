import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import base64
import numpy as np

from data_loader import (
    carregar_dados_merged,
    carregar_o2c,
    process_chamados_data,
    process_o2c_data,
)
from utils import (
    extrair_tags_vectorized,
    extrair_codigo_bomba_vectorized,
    calcular_aging_vectorized,
    calcular_garantia_vectorized,
    formatar_data_excel_vectorized,
    extrair_modelo_vectorized,
)
from auth import check_password
from filters import sidebar_filters, aplicar_filtros
import visualization as vz

st.set_page_config(page_title="PRINCIPAL - CHAMADOS DE SERVIÇOS", layout="wide")

check_password()


def load_and_merge_chamados():
    """Load and merge chamados data with optimizations."""
    df = carregar_dados_merged()
    df.columns = df.columns.str.strip().str.upper()

    # Vectorized string operations
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].str.strip().str.upper()

    # Efficient deduplication
    if "TAREFA" in df.columns:
        df = df.drop_duplicates(subset=["SS", "TAREFA"], keep="first").reset_index(
            drop=True
        )
    else:
        st.warning(
            "Coluna 'TAREFA' não encontrada. Removendo duplicatas apenas por 'SS'."
        )
        df = df.drop_duplicates(subset=["SS"], keep="first").reset_index(drop=True)

    return df


def load_o2c():
    """Load O2C data with optimizations."""
    df = carregar_o2c()
    df.columns = df.columns.str.strip().str.upper()

    # Vectorized string operations
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].str.strip().str.upper()

    # Apply standard O2C processing (including filtering)
    df = process_o2c_data(df)

    return df


def process_data_for_display(df: pd.DataFrame, o2c_df: pd.DataFrame):
    """Process data for display with optimizations."""

    # Merge with O2C data
    o2c_subset = o2c_df[["NUM_SERIAL", "RTM", "DT_NUM_NF", "GARANTIA"]]
    df = df.merge(
        o2c_subset,
        how="left",
        left_on="CHASSI",
        right_on="NUM_SERIAL",
        suffixes=("", "_O2C"),
    )

    # Vectorized operations
    df["TAGS"] = extrair_tags_vectorized(df["SUMÁRIO"])
    df["CHAMADO"] = df["SS"]
    df["RTM"] = (
        df["RTM_O2C"]
        .str.strip()
        .str.upper()
        .where(df["RTM_O2C"].str.strip().str.upper().isin(["SIM", "NÃO"]), "NÃO")
    )
    df = df.drop(columns=["RTM_O2C"])

    # Process chamados data
    df = process_chamados_data(df)

    # Calculate guarantee information
    if "DT_NUM_NF" in df.columns and "GARANTIA" in df.columns:
        status_garantia, fim_garantia = calcular_garantia_vectorized(
            df["DT_NUM_NF"], df["GARANTIA"]
        )
        df["FIM_GARANTIA"] = fim_garantia.dt.strftime("%d/%m/%Y")
        df["GARANTIA"] = status_garantia

    # Add missing columns
    if "ORDEM" not in df.columns:
        df["ORDEM"] = ""

    if "DESCRIÇÃO.1" in df.columns:
        df["COD_BOMBA"] = extrair_codigo_bomba_vectorized(df["DESCRIÇÃO.1"])
    else:
        df["COD_BOMBA"] = ""

    # Extract model from SÉRIE column
    if "SÉRIE" in df.columns:
        df["MODELO"] = extrair_modelo_vectorized(df["SÉRIE"])
    else:
        df["MODELO"] = ""

    # Filter out MODELO "OUTROS"
    if "MODELO" in df.columns:
        df = df[df["MODELO"] != "OUTROS"]

    # Filter out export units (keep only Brazil) from Chamados
    # Logic: Keep if found in Brazil O2C OR Address indicates Brazil
    matched_o2c = (
        df["NUM_SERIAL"].notna()
        if "NUM_SERIAL" in df.columns
        else pd.Series(False, index=df.index)
    )

    address_br = pd.Series(False, index=df.index)
    if "ENDEREÇO" in df.columns:
        # Check for BR or BRASIL in address
        address_br = df["ENDEREÇO"].str.contains(r"\bBR\b|BRASIL", regex=True, na=False)

    # Apply filter: Keep if matched in O2C (Brazil) OR Address is Brazil
    # If a unit is not in O2C but has Brazil address, we keep it.
    # If a unit is in O2C (Brazil), we keep it (even if address is weird).
    # If a unit is not in O2C and address is not Brazil, we drop it (Export).
    df = df[matched_o2c | address_br]

    return df


def exibir_logo_sidebar(path_logo, largura=200):
    """Display logo in sidebar with caching."""

    @st.cache_data(ttl=3600, show_spinner=False)
    def get_encoded_logo():
        with open(path_logo, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()

    encoded = get_encoded_logo()
    st.sidebar.markdown(
        f"""
        <div style=\"display: flex; justify-content: center;\">
            <img src=\"data:image/png;base64,{encoded}\" width=\"{largura}\">\n        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=900, show_spinner=False)
def kpi_section(df):
    """Calculate and display KPIs with optimizations."""
    metrics = vz.create_kpi_metrics(df)

    # First row - main KPIs
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total de Chamados", metrics["total"])
    col2.metric("Abertos", metrics["abertos"])
    col3.metric("Fechados", metrics["fechados"])
    col4.metric(
        "Aging Médio (dias)",
        f"{metrics['aging_medio']:.1f}" if not pd.isna(metrics["aging_medio"]) else "-",
    )
    col5.metric("% Dentro da Garantia", f"{metrics['pct_garantia']:.1f}%")
    col6.metric("% RTM", f"{metrics['pct_rtm']:.1f}%")

    # Second row - model distribution KPIs
    if len(df) > 0 and "MODELO" in df.columns:
        # Calculate model distribution
        total = len(df)
        model_counts = df["MODELO"].value_counts()
        main_models = ["HELIX", "VISTA", "CENTURY", "3G", "E123", "7502A"]

        # Calculate percentages
        pct_helix = (model_counts.get("HELIX", 0) / total * 100) if total > 0 else 0
        pct_vista = (model_counts.get("VISTA", 0) / total * 100) if total > 0 else 0
        pct_century = (model_counts.get("CENTURY", 0) / total * 100) if total > 0 else 0
        pct_3g = (model_counts.get("3G", 0) / total * 100) if total > 0 else 0
        pct_e123 = (model_counts.get("E123", 0) / total * 100) if total > 0 else 0
        pct_7502a = (model_counts.get("7502A", 0) / total * 100) if total > 0 else 0

        # Others percentage
        others_count = model_counts[~model_counts.index.isin(main_models)].sum()
        pct_others = (others_count / total * 100) if total > 0 else 0

        col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
        col1.metric("% HELIX", f"{pct_helix:.1f}%")
        col2.metric("% VISTA", f"{pct_vista:.1f}%")
        col3.metric("% CENTURY", f"{pct_century:.1f}%")
        col4.metric("% 3G", f"{pct_3g:.1f}%")
        col5.metric("% E123", f"{pct_e123:.1f}%")
        col6.metric("% 7502A", f"{pct_7502a:.1f}%")
        col7.metric("% Outros", f"{pct_others:.1f}%")


def main():
    # Load data with optimizations
    df = load_and_merge_chamados()
    o2c_df = load_o2c()

    # Process data for display
    df = process_data_for_display(df, o2c_df)

    # Define display columns
    columns = [
        "TAGS",
        "CHAMADO",
        "CHASSI",
        "SÉRIE",
        "MODELO",
        "ORDEM",
        "COD_BOMBA",
        "RTM",
        "ESPECIALISTA",
        "PROPRIETÁRIO",
        "MANTENEDOR",
        "TIPO",
        "SERVIÇO",
        "PROBLEMA",
        "RESOLUÇÃO",
        "CLIENTE",
        "INÍCIO",
        "FIM",
        "SUMÁRIO",
        "AGING",
        "FIM_GARANTIA",
        "GARANTIA",
        "STATUS",
    ]

    # Search functionality
    search = st.text_input("PESQUISAR EM TODOS OS CAMPOS")

    # Get all tags for filtering
    todas_tags = sorted(set(tag for tags in df["TAGS"] for tag in tags))

    # Apply filters
    filtros = sidebar_filters(df, todas_tags)
    df_filtrado = aplicar_filtros(
        df,
        filtros["tags_selecionadas"],
        filtros["selecoes"],
        termo_pesquisa=search,
        status_selecionado=filtros.get("status_selecionado", "GERAL"),
        data_inicio=filtros.get("data_inicio"),
        data_fim=filtros.get("data_fim"),
    )

    # Prepare display data
    df_display = df_filtrado[columns].copy()

    # Handle missing aging values
    mask_aging_vazio = (
        df_display["AGING"].isna()
        & df_display["INÍCIO"].notna()
        & (df_display["INÍCIO"] != "")
    )
    if mask_aging_vazio.any():
        hoje = pd.Timestamp.now().normalize()
        dt_inicio_safeguard = pd.to_datetime(
            df_display.loc[mask_aging_vazio, "INÍCIO"], dayfirst=True, errors="coerce"
        ).dt.date
        dt_fim_safeguard = pd.to_datetime(
            df_display.loc[mask_aging_vazio, "FIM"], dayfirst=True, errors="coerce"
        ).dt.date
        dt_fim_safeguard = dt_fim_safeguard.fillna(hoje)

        def calc_aging(row):
            try:
                inicio = pd.to_datetime(row["INÍCIO"], dayfirst=True, errors="coerce")
                fim = pd.to_datetime(row["FIM"], dayfirst=True, errors="coerce")
                if pd.isna(inicio):
                    return ""
                if pd.isna(fim):
                    fim = hoje
                return str((fim - inicio).days)
            except:
                return ""

        df_display.loc[mask_aging_vazio, "AGING"] = df_display.loc[
            mask_aging_vazio
        ].apply(calc_aging, axis=1)

    # Display KPIs
    kpi_section(df_filtrado)

    # Display filtered data
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "TAGS": st.column_config.ListColumn("Tags", width="medium"),
            "CHAMADO": st.column_config.TextColumn("Chamado", width="small"),
            "CHASSI": st.column_config.TextColumn("Chassi", width="medium"),
            "SÉRIE": st.column_config.TextColumn("Série", width="small"),
            "MODELO": st.column_config.TextColumn("Modelo", width="small"),
            "ORDEM": st.column_config.TextColumn("Ordem", width="small"),
            "COD_BOMBA": st.column_config.TextColumn("Cód. Bomba", width="small"),
            "RTM": st.column_config.TextColumn("RTM", width="small"),
            "ESPECIALISTA": st.column_config.TextColumn("Especialista", width="medium"),
            "PROPRIETÁRIO": st.column_config.TextColumn("Proprietário", width="medium"),
            "MANTENEDOR": st.column_config.TextColumn("Mantenedor", width="medium"),
            "TIPO": st.column_config.TextColumn("Tipo", width="medium"),
            "SERVIÇO": st.column_config.TextColumn("Serviço", width="medium"),
            "PROBLEMA": st.column_config.TextColumn("Problema", width="large"),
            "RESOLUÇÃO": st.column_config.TextColumn("Resolução", width="large"),
            "CLIENTE": st.column_config.TextColumn("Cliente", width="medium"),
            "INÍCIO": st.column_config.DateColumn(
                "Início", format="DD/MM/YYYY", width="small"
            ),
            "FIM": st.column_config.DateColumn(
                "Fim", format="DD/MM/YYYY", width="small"
            ),
            "SUMÁRIO": st.column_config.TextColumn("Sumário", width="large"),
            "AGING": st.column_config.NumberColumn("Aging", format="%d", width="small"),
            "FIM_GARANTIA": st.column_config.TextColumn("Fim Garantia", width="small"),
            "GARANTIA": st.column_config.TextColumn("Garantia", width="small"),
            "STATUS": st.column_config.TextColumn("Status", width="small"),
        },
    )

    # Charts section
    st.header("📊 Análises e Gráficos")

    # Tag distribution
    if df_filtrado["TAGS"].any():
        tags_contagem = pd.Series(
            [tag for tags in df_filtrado["TAGS"] for tag in tags]
        ).value_counts()
        st.plotly_chart(vz.bar_chart_tags(tags_contagem), use_container_width=True)

    # Aging distribution
    st.plotly_chart(vz.pie_chart_aging(df_filtrado), use_container_width=True)

    # Performance charts
    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            vz.bar_chart_aging_proprietario(df_filtrado), use_container_width=True
        )

    with col2:
        st.plotly_chart(
            vz.bar_chart_aging_especialista(df_filtrado), use_container_width=True
        )

    # Mantenedor performance
    st.plotly_chart(
        vz.bar_chart_aging_mantenedor(df_filtrado), use_container_width=True
    )

    # Time series analysis
    st.plotly_chart(
        vz.line_chart_aging(df_filtrado, "ESPECIALISTA"), use_container_width=True
    )


if __name__ == "__main__":
    main()
