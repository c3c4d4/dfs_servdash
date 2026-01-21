from datetime import timedelta
import streamlit as st
import pandas as pd
import plotly.express as px
from data_loader import (
    carregar_dados_merged,
    carregar_o2c,
    process_o2c_data,
    carregar_base_erros_rtm,
)
from utils import extrair_estado
from auth import check_password
from filters import sidebar_filters_rtm_errors, aplicar_filtros_rtm_errors
import visualization as vz
import numpy as np
from datetime import datetime
from streamlit_dynamic_filters import DynamicFilters  # NEW IMPORT
import business_logic as bl

st.set_page_config(page_title="Parque Instalado - Chamados de Serviços", layout="wide")

check_password()


# --- Carregamento dos dados principais com otimizações ---
def load_o2c_data():
    """Load O2C data with optimizations."""
    df = carregar_o2c()

    # Optimize dtypes for filtering
    for cat_col in ["UF", "RTM", "STATUS_GARANTIA", "CIDADE"]:
        if cat_col in df.columns:
            df[cat_col] = df[cat_col].astype("category")
            if "" not in df[cat_col].cat.categories:
                df[cat_col] = df[cat_col].cat.add_categories([""])

    return df


def load_chamados_data():
    """Load chamados data with optimizations."""
    df = carregar_dados_merged()
    df.columns = df.columns.str.strip().str.upper()

    # Vectorized string operations
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].str.strip().str.upper()

    # Optimize dtypes for filtering
    for cat_col in ["CHASSI", "SERVIÇO", "SS"]:
        if cat_col in df.columns:
            df[cat_col] = df[cat_col].astype("category")
            if "" not in df[cat_col].cat.categories:
                df[cat_col] = df[cat_col].cat.add_categories([""])

    return df


# Load data
o2c = load_o2c_data()
chamados = load_chamados_data()
erros_rtm = carregar_base_erros_rtm()


# --- Pré-processamento e enriquecimento das bases ---
def preprocess_o2c_data(o2c_df: pd.DataFrame):
    """Preprocess O2C data with optimizations."""
    df = o2c_df.copy()

    # Add state column
    if "UF" in df.columns:
        df["UF"] = df["UF"].str.strip().str.upper()
    else:
        df["UF"] = df["ESTADO"]

    if "CIDADE" not in df.columns:
        df["CIDADE"] = ""

    # Add year column
    if "DT_NUM_NF" in df.columns:
        df["ANO_NF"] = pd.to_datetime(
            df["DT_NUM_NF"], dayfirst=True, errors="coerce"
        ).dt.year
    else:
        df["ANO_NF"] = np.nan

    # Process guarantee information
    df = process_o2c_data(df)

    return df


@st.cache_data(ttl=3600, show_spinner=False)
def precompute_chamados_dicts(chamados_df: pd.DataFrame):
    """Precompute chamados dictionaries for fast filtering."""
    df = chamados_df.copy()

    # Ensure '' is a category before fillna
    for cat_col in ["SERVIÇO", "CHASSI", "SS"]:
        if cat_col in df.columns and "" not in df[cat_col].cat.categories:
            df[cat_col] = df[cat_col].cat.add_categories([""])

    df["SERVIÇO"] = df["SERVIÇO"].fillna("")
    df["CHASSI"] = df["CHASSI"].fillna("")
    df["SS"] = df["SS"].fillna("")

    # Filter out [STB] calls from summary
    if "SUMÁRIO" in df.columns:
        df["SUMÁRIO"] = df["SUMÁRIO"].fillna("")
        # Exclude calls with [STB] in summary
        df_valid_chamados = df[
            ~df["SUMÁRIO"].str.contains(r"\[STB\]", case=False, na=False)
        ]
    else:
        df_valid_chamados = df

    # Create dictionaries and sets for fast lookup
    chamados_por_chassi_dict = df.groupby("CHASSI")["SS"].apply(list).to_dict()
    servico_partida = df[df["SERVIÇO"].str.contains("PARTIDA INICIAL", na=False)]
    partida_set = set(servico_partida["CHASSI"])
    chassi_counts = df.groupby("CHASSI").size()
    # Use valid chamados (excluding [STB]) for chamado metrics
    chassi_com_chamado = set(
        df_valid_chamados[
            ~df_valid_chamados["SERVIÇO"].str.contains("PARTIDA INICIAL", na=False)
        ]["CHASSI"]
    )

    return chamados_por_chassi_dict, partida_set, chassi_counts, chassi_com_chamado


# Preprocess data
o2c = preprocess_o2c_data(o2c)
chamados_por_chassi_dict, partida_set, chassi_counts, chassi_com_chamado = (
    precompute_chamados_dicts(chamados)
)

# --- Sidebar Filtros Dinâmicos ---
# Check available columns and add DURAÇÃO_GARANTIA if it exists
available_filter_columns = ["UF", "RTM", "STATUS_GARANTIA", "ANO_NF"]

# Add MODELO column to filters if it exists
if "MODELO" in o2c.columns:
    available_filter_columns.append("MODELO")

if "DURAÇÃO_GARANTIA" in o2c.columns:
    available_filter_columns.append("DURAÇÃO_GARANTIA")
elif "DURACAO_GARANTIA" in o2c.columns:
    available_filter_columns.append("DURACAO_GARANTIA")
elif "GARANTIA" in o2c.columns:
    # If GARANTIA column exists, we'll create DURAÇÃO_GARANTIA categories using business logic
    o2c["DURAÇÃO_GARANTIA"] = bl.create_duracao_garantia_column(o2c["GARANTIA"])
    available_filter_columns.append("DURAÇÃO_GARANTIA")

# Clean filter columns to avoid sorted() errors with mixed types
for col in available_filter_columns:
    if col in o2c.columns:
        # Convert categorical to object first, then fill NaN to avoid category errors
        if hasattr(o2c[col], "cat"):
            o2c[col] = o2c[col].astype(str)
        o2c[col] = o2c[col].fillna("N/A").astype(str)

with st.sidebar:
    st.write("Aplique os filtros em qualquer ordem 👇")
    dynamic_filters = DynamicFilters(o2c, filters=available_filter_columns)
    dynamic_filters.display_filters(location="sidebar")
    considerar_stb = st.checkbox("Remover [STB]", value=False)

# Use precomputed values and apply STB filter if needed
if considerar_stb:
    # Include STB calls - use original counts
    chassi_counts_validos = chassi_counts
    # Recalculate chassi_com_chamado including STB
    chassi_com_chamado = set(
        chamados[~chamados["SERVIÇO"].str.contains("PARTIDA INICIAL", na=False)][
            "CHASSI"
        ]
    )
else:
    # Exclude STB calls - use precomputed valid counts
    chamados_considerados = chamados[
        ~chamados["SUMÁRIO"].str.contains(r"\[STB\]", case=False, na=False)
    ]
    chassi_counts_validos = chamados_considerados.groupby("CHASSI").size()
    chassi_com_chamado = set(
        chamados_considerados[
            ~chamados_considerados["SERVIÇO"].str.contains("PARTIDA INICIAL", na=False)
        ]["CHASSI"]
    )

# Now filter the dataframe after all filter variables are set
filtered_filtros_unique = dynamic_filters.filter_df().drop_duplicates(
    subset=["NUM_SERIAL"], keep="first"
)

# Remove rows where NUM_SERIAL is not exactly 6 digits
filtered_filtros_unique = filtered_filtros_unique[
    filtered_filtros_unique["NUM_SERIAL"].astype(str).str.match(r"^\d{6}$", na=False)
]

# Add a new column with all chamados for each chassi, comma separated
filtered_filtros_unique["CHAMADOS_LISTA"] = filtered_filtros_unique["NUM_SERIAL"].apply(
    lambda chassi: ", ".join(str(ss) for ss in chamados_por_chassi_dict.get(chassi, []))
)

# --- RTM Error Filters (mantém como estava) ---
filtros_rtm = sidebar_filters_rtm_errors(erros_rtm)
filtered_filtros_unique = aplicar_filtros_rtm_errors(
    filtered_filtros_unique, filtros_rtm, erros_rtm, chamados_por_chassi_dict
)

# RTM filtering is now handled entirely in the filters module
# No need for duplicate logic here

# Data is already deduplicated and validated above


# Total de bombas na base (sem filtro)
all_bombas = o2c["NUM_SERIAL"].dropna().nunique()

# After all filters, including RTM error, recalculate chassis_filtros and KPIs based only on the filtered context
chassis_filtros = filtered_filtros_unique["NUM_SERIAL"].dropna().unique()
total_bombas_filtro = len(chassis_filtros)

# Calculate KPIs using business logic module
chassis_filtrados_series = pd.Series(chassis_filtros)
qtd_chamados_por_chassi = chassi_counts_validos.reindex(
    chassis_filtrados_series, fill_value=0
)
media_chamados_por_bomba = qtd_chamados_por_chassi.mean() if total_bombas_filtro else 0

# Get guarantee calls chassis
chamados_base_para_garantia = chamados if considerar_stb else chamados_considerados
chamados_de_garantia = chamados_base_para_garantia[
    chamados_base_para_garantia["SERVIÇO"].str.contains("GARANTIA", na=False)
]
chassis_com_chamado_garantia = set(chamados_de_garantia["CHASSI"].unique())

# Calculate all KPI percentages using business logic
kpis_percentuais = bl.calculate_kpi_percentages(
    filtered_filtros_unique,
    partida_set,
    chassi_counts_validos,
    chassis_com_chamado_garantia,
)

# Extract individual KPIs
pct_com_partida_dfs = kpis_percentuais["pct_com_partida_dfs"]
pct_com_partida_terceiros = kpis_percentuais["pct_com_partida_terceiros"]
pct_com_chamado = kpis_percentuais["pct_com_chamado"]
pct_sem_chamado = kpis_percentuais["pct_sem_chamado"]
pct_rtm = kpis_percentuais["pct_rtm"]
pct_em_garantia = kpis_percentuais["pct_em_garantia"]
pct_fora_garantia = kpis_percentuais["pct_fora_garantia"]

# --- Cálculo de Valores RTM usando business logic ---
ss_das_bombas_filtradas = bl.get_ss_for_chassis(
    chassis_filtros, chamados_por_chassi_dict
)
erros_rtm_das_bombas = erros_rtm[
    erros_rtm["SS"].astype(str).isin(ss_das_bombas_filtradas)
]

# Calculate RTM values using business logic
rtm_values = bl.calculate_rtm_values(erros_rtm_das_bombas)
media_valor_total = rtm_values["media_valor_total"]
media_valor_peca = rtm_values["media_valor_peca"]
soma_valor_total = rtm_values["soma_valor_total"]
soma_valor_peca = rtm_values["soma_valor_peca"]

# --- Add calculated columns using business logic ---
# Add QTD_CHAMADOS column
filtered_filtros_unique["QTD_CHAMADOS"] = bl.calculate_qtd_chamados(
    filtered_filtros_unique, chassi_counts_validos
)

# Add electronic warranty columns
filtered_filtros_unique = bl.add_garantia_eletronica_columns(filtered_filtros_unique)

# --- Download functionality ---
@st.cache_data(ttl=900, show_spinner=False)
def prepare_download_data(df: pd.DataFrame):
    """Prepare data for download with optimizations."""
    download_df = df.copy()

    # Format dates for download
    if "DT_NUM_NF" in download_df.columns:
        download_df["DT_NUM_NF"] = download_df["DT_NUM_NF"].dt.strftime("%d/%m/%Y")

    if "FIM_GARANTIA" in download_df.columns:
        # Check if FIM_GARANTIA is already a string (formatted) or datetime
        if pd.api.types.is_datetime64_any_dtype(download_df["FIM_GARANTIA"]):
            download_df["FIM_GARANTIA"] = download_df["FIM_GARANTIA"].dt.strftime(
                "%d/%m/%Y"
            )
        # If it's already a string, leave it as is

    return download_df

# --- KPIs ---
st.title("🗺️ Parque Instalado - Análise por Estado")
tab_kpis, tab_tabela, tab_rtm_analysis = st.tabs(["📌 KPIs", "📋 Parque Instalado", "📊 Análise RTM"])

with tab_kpis:
    # Primeira linha de KPIs
    col1, col2, col3, col4, col5, col6, col7, col8, col9 = st.columns(9)
    col1.metric("Total de Bombas", total_bombas_filtro)
    col2.metric("% Com Partida (DFS)", f"{pct_com_partida_dfs:.1f}%")
    col3.metric("% Com Partida (Terceiros)", f"{pct_com_partida_terceiros:.1f}%")
    col4.metric("% Com Chamado Garantia", f"{pct_com_chamado:.1f}%")
    col5.metric("% Sem Chamado Garantia", f"{pct_sem_chamado:.1f}%")
    col6.metric("% RTM", f"{pct_rtm:.1f}%")
    col7.metric("% Em Garantia", f"{pct_em_garantia:.1f}%")
    col8.metric("% Fora de Garantia", f"{pct_fora_garantia:.1f}%")
    col9.metric("Média Chamados/Bomba", f"{media_chamados_por_bomba:.1f}")

    # Segunda linha de KPIs - Valores
    col10, col11, col12, col13 = st.columns(4)
    col10.metric(
        "Média Valor Total (R$)",
        f"R$ {media_valor_total:,.2f}".replace(",", "X")
        .replace(".", ",")
        .replace("X", "."),
    )
    col11.metric(
        "Média Valor Peça (R$)",
        f"R$ {media_valor_peca:,.2f}".replace(",", "X")
        .replace(".", ",")
        .replace("X", "."),
    )
    col12.metric(
        "Soma Valor Total (R$)",
        f"R$ {soma_valor_total:,.2f}".replace(",", "X")
        .replace(".", ",")
        .replace("X", "."),
    )
    col13.metric(
        "Soma Valor Peça (R$)",
        f"R$ {soma_valor_peca:,.2f}".replace(",", "X")
        .replace(".", ",")
        .replace("X", "."),
    )

    # Terceira linha de KPIs - Distribuição por Modelo
    if len(filtered_filtros_unique) > 0 and "MODELO" in filtered_filtros_unique.columns:
        # Calculate model distribution
        total = len(filtered_filtros_unique)
        model_counts = filtered_filtros_unique["MODELO"].value_counts()
        main_models = ["HELIX", "VISTA", "CENTURY", "3G", "E123", "7502A"]

        # Calculate percentages
        pct_helix = (model_counts.get("HELIX", 0) / total * 100) if total > 0 else 0
        pct_vista = (model_counts.get("VISTA", 0) / total * 100) if total > 0 else 0
        pct_century = (
            model_counts.get("CENTURY", 0) / total * 100 if total > 0 else 0
        )
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

    # Terceira linha de KPIs - Garantia Eletrônica e Distribuição por Faixas
    col14, col15, col16, col17, col18, col19, col20 = st.columns(7)

    # Garantia Eletrônica
    media_garan_eletr = (
        filtered_filtros_unique["GARANTIA_ELETRONICA"].mean()
        if len(filtered_filtros_unique) > 0
        else 0
    )
    qtd_dentro_eletr = (
        filtered_filtros_unique["STATUS_GARAN_ELETRICA"] == "DENTRO"
    ).sum()
    qtd_fora_eletr = (
        filtered_filtros_unique["STATUS_GARAN_ELETRICA"] == "FORA"
    ).sum()
    total_eletr = qtd_dentro_eletr + qtd_fora_eletr
    pct_dentro_eletr = 100 * qtd_dentro_eletr / total_eletr if total_eletr else 0
    pct_fora_eletr = 100 * qtd_fora_eletr / total_eletr if total_eletr else 0

    # Calculate warranty distribution using business logic
    garantia_dist = bl.calculate_garantia_distribution(filtered_filtros_unique)
    pct_6m = garantia_dist["pct_6m"]
    pct_12m = garantia_dist["pct_12m"]
    pct_18m = garantia_dist["pct_18m"]
    pct_24m = garantia_dist["pct_24m"]
    pct_36m = garantia_dist["pct_36m"]

    # Exibir métricas
    col14.metric("% Dentro Gar. Eletrônica", f"{pct_dentro_eletr:.1f}%")
    col15.metric("% Fora Gar. Eletrônica", f"{pct_fora_eletr:.1f}%")
    col16.metric("% Garantia 6m", f"{pct_6m:.1f}%")
    col17.metric("% Garantia 12m", f"{pct_12m:.1f}%")
    col18.metric("% Garantia 18m", f"{pct_18m:.1f}%")
    col19.metric("% Garantia 24m", f"{pct_24m:.1f}%")
    col20.metric("% Garantia 36m", f"{pct_36m:.1f}%")

    # --- Mapa ---
    st.header("📊 Distribuição Geográfica")

    # Check if we have data for the map
    if len(filtered_filtros_unique) > 0:
        # Ensure UF column exists and has valid data
        if "UF" in filtered_filtros_unique.columns:
            # Remove rows with empty or invalid UF
            filtered_filtros_map = filtered_filtros_unique[
                (filtered_filtros_unique["UF"].notna())
                & (filtered_filtros_unique["UF"].astype(str).str.strip() != "")
                & (filtered_filtros_unique["UF"].astype(str).str.strip() != "NAN")
            ].copy()

            if len(filtered_filtros_map) > 0:
                # Update state counts for filtered data (deduplicated)
                estado_counts_filtrado = (
                    filtered_filtros_map.groupby("UF")
                    .size()
                    .reset_index(name="Quantidade")
                )

                # Create map
                try:
                    fig_mapa = vz.choropleth_map_brazil(
                        filtered_filtros_map, estado_counts_filtrado
                    )
                    st.plotly_chart(fig_mapa, width="stretch")
                except Exception as e:
                    st.error(f"❌ Erro ao criar mapa: {str(e)}")

                    # Fallback: Simple bar chart
                    st.info("📊 Exibindo gráfico de barras como alternativa:")
                    fig_bar = px.bar(
                        estado_counts_filtrado,
                        x="UF",
                        y="Quantidade",
                        color="Quantidade",
                        color_continuous_scale="Blues",
                        title="Distribuição de Bombas por Estado",
                    )
                    fig_bar.update_layout(
                        xaxis_title="Estado",
                        yaxis_title="Quantidade de Bombas",
                        height=500,
                        xaxis_tickangle=-45,
                    )
                    st.plotly_chart(fig_bar, width="stretch")
            else:
                st.warning(
                    "⚠️ Nenhum dado válido encontrado para exibir no mapa após a filtragem."
                )
        else:
            st.warning("⚠️ Coluna 'UF' não encontrada nos dados.")
            # Try to use ESTADO column instead
            if "ESTADO" in filtered_filtros_unique.columns:
                st.info("🔄 Tentando usar coluna 'ESTADO'...")
                filtered_filtros_map = filtered_filtros_unique[
                    (filtered_filtros_unique["ESTADO"].notna())
                    & (filtered_filtros_unique["ESTADO"].astype(str).str.strip() != "")
                    & (filtered_filtros_unique["ESTADO"].astype(str).str.strip() != "NAN")
                ].copy()

                if len(filtered_filtros_map) > 0:
                    estado_counts_filtrado = (
                        filtered_filtros_map.groupby("ESTADO")
                        .size()
                        .reset_index(name="Quantidade")
                    )
                    try:
                        fig_mapa = vz.choropleth_map_brazil(
                            filtered_filtros_map, estado_counts_filtrado
                        )
                        st.plotly_chart(fig_mapa, width="stretch")
                    except Exception as e:
                        st.error(f"❌ Erro ao criar mapa com ESTADO: {str(e)}")
    else:
        st.warning("⚠️ Nenhum dado encontrado após a aplicação dos filtros.")

with tab_tabela:
    # --- Tabela Detalhada ---
    st.header("📋 Detalhamento das Bombas")

    # Ensure missing columns are added with default values
    if "MODELO" not in filtered_filtros_unique.columns:
        # If MODELO doesn't exist, try to create it from available columns (prioritize ITEM)
        from utils import extrair_modelo_vectorized

        if "ITEM" in filtered_filtros_unique.columns:
            filtered_filtros_unique["MODELO"] = extrair_modelo_vectorized(
                filtered_filtros_unique["ITEM"]
            )
        else:
            # Fallback to serial columns
            serial_columns = [
                col
                for col in filtered_filtros_unique.columns
                if "SERIAL" in col or "SERIE" in col
            ]
            if serial_columns:
                filtered_filtros_unique["MODELO"] = extrair_modelo_vectorized(
                    filtered_filtros_unique[serial_columns[0]]
                )
            else:
                filtered_filtros_unique["MODELO"] = "N/A"

    # Prepare table data
    colunas_tabela_requested = [
        "NUM_SERIAL",
        "MODELO",
        "UF",
        "CIDADE",
        "CLIENTE",
        "RTM",
        "STATUS_GARANTIA",
        "FIM_GARANTIA",
        "ANO_NF",
        "DT_NUM_NF",
        "GARANTIA",
        "GARANTIA_ELETRONICA",
        "FIM_GARAN_ELETRICA",
        "STATUS_GARAN_ELETRICA",
    ]

    # Only use columns that actually exist in the dataframe
    colunas_tabela = [
        col for col in colunas_tabela_requested if col in filtered_filtros_unique.columns
    ]

    # QTD_CHAMADOS already calculated above using centralized function

    # Ensure CLIENTE column exists
    if "CLIENTE" not in filtered_filtros_unique.columns:
        filtered_filtros_unique["CLIENTE"] = ""

    # Ensure electronic warranty columns exist (in case they weren't added properly)
    if "GARANTIA_ELETRONICA" not in filtered_filtros_unique.columns:
        filtered_filtros_unique["GARANTIA_ELETRONICA"] = 365
    if "FIM_GARAN_ELETRICA" not in filtered_filtros_unique.columns:
        filtered_filtros_unique["FIM_GARAN_ELETRICA"] = "N/A"
    if "STATUS_GARAN_ELETRICA" not in filtered_filtros_unique.columns:
        filtered_filtros_unique["STATUS_GARAN_ELETRICA"] = "N/A"

    # Add partida inicial info using business logic
    filtered_filtros_unique["PARTIDA_INICIAL"] = filtered_filtros_unique.apply(
        lambda row: bl.determine_partida_inicial_status(
            row["NUM_SERIAL"], partida_set, row["QTD_CHAMADOS"]
        ),
        axis=1,
    )

    # Format FIM_GARANTIA as date string
    if "FIM_GARANTIA" in filtered_filtros_unique.columns:
        filtered_filtros_unique["FIM_GARANTIA"] = filtered_filtros_unique[
            "FIM_GARANTIA"
        ].dt.strftime("%d/%m/%Y")

    # Prepare columns for display
    display_columns = colunas_tabela + ["QTD_CHAMADOS", "PARTIDA_INICIAL", "CHAMADOS_LISTA"]
    display_columns = [
        col for col in display_columns if col in filtered_filtros_unique.columns
    ]

    # Create column config only for existing columns
    column_config = {}
    if "NUM_SERIAL" in filtered_filtros_unique.columns:
        column_config["NUM_SERIAL"] = st.column_config.TextColumn(
            "Número Serial", width="medium"
        )
    if "MODELO" in filtered_filtros_unique.columns:
        column_config["MODELO"] = st.column_config.TextColumn("Modelo", width="small")
    if "UF" in filtered_filtros_unique.columns:
        column_config["UF"] = st.column_config.TextColumn("UF", width="small")
    if "CIDADE" in filtered_filtros_unique.columns:
        column_config["CIDADE"] = st.column_config.TextColumn("Cidade", width="medium")
    if "CLIENTE" in filtered_filtros_unique.columns:
        column_config["CLIENTE"] = st.column_config.TextColumn("Cliente", width="medium")
    if "RTM" in filtered_filtros_unique.columns:
        column_config["RTM"] = st.column_config.TextColumn("RTM", width="small")
    if "STATUS_GARANTIA" in filtered_filtros_unique.columns:
        column_config["STATUS_GARANTIA"] = st.column_config.TextColumn(
            "Status Garantia", width="small"
        )
    if "FIM_GARANTIA" in filtered_filtros_unique.columns:
        column_config["FIM_GARANTIA"] = st.column_config.TextColumn(
            "Fim Garantia", width="small"
        )
    if "ANO_NF" in filtered_filtros_unique.columns:
        column_config["ANO_NF"] = st.column_config.NumberColumn(
            "Ano NF", format="%d", width="small"
        )
    if "DT_NUM_NF" in filtered_filtros_unique.columns:
        column_config["DT_NUM_NF"] = st.column_config.DateColumn(
            "Data NF", format="DD/MM/YYYY", width="small"
        )
    if "GARANTIA" in filtered_filtros_unique.columns:
        column_config["GARANTIA"] = st.column_config.TextColumn(
            "Garantia (dias)", width="small"
        )
    if "QTD_CHAMADOS" in filtered_filtros_unique.columns:
        column_config["QTD_CHAMADOS"] = st.column_config.NumberColumn(
            "Qtd Chamados", format="%d", width="small"
        )
    if "PARTIDA_INICIAL" in filtered_filtros_unique.columns:
        column_config["PARTIDA_INICIAL"] = st.column_config.TextColumn(
            "Partida Inicial", width="small"
        )
    if "CHAMADOS_LISTA" in filtered_filtros_unique.columns:
        column_config["CHAMADOS_LISTA"] = st.column_config.TextColumn(
            "Chamados (SS)", width="large"
        )
    if "GARANTIA_ELETRONICA" in filtered_filtros_unique.columns:
        column_config["GARANTIA_ELETRONICA"] = st.column_config.TextColumn(
            "Garantia Eletrônica", width="small"
        )
    if "FIM_GARAN_ELETRICA" in filtered_filtros_unique.columns:
        column_config["FIM_GARAN_ELETRICA"] = st.column_config.TextColumn(
            "Fim Garantia Eletrônica", width="small"
        )
    if "STATUS_GARAN_ELETRICA" in filtered_filtros_unique.columns:
        column_config["STATUS_GARAN_ELETRICA"] = st.column_config.TextColumn(
            "Status Garantia Eletrônica", width="small"
        )

    # Display table
    st.dataframe(
        filtered_filtros_unique[display_columns],
        width="stretch",
        hide_index=True,
        column_config=column_config,
    )

    # Download button
    download_data = prepare_download_data(filtered_filtros_unique)
    csv = download_data.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button(
        label="📥 Download dos Dados Filtrados",
        data=csv,
        file_name=f"parque_instalado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )

with tab_rtm_analysis:
    st.header("📊 Análise Comparativa RTM")
    st.caption("Visão geral comparativa entre bombas NEW RTM (com RTM) e OLD RTM (sem RTM), independente dos filtros aplicados.")

    # Load raw data for RTM analysis (ignoring sidebar filters)
    o2c_raw = carregar_o2c()
    o2c_processed = process_o2c_data(o2c_raw.copy())

    # Calculate RTM analysis for NEW RTM (RTM: SIM)
    df_new_rtm = bl.calculate_rtm_analysis_by_year(
        o2c_processed, chamados, erros_rtm, "SIM"
    )
    summary_new_rtm = bl.get_rtm_summary_metrics(o2c_processed, chamados, "SIM")

    # Calculate RTM analysis for OLD RTM (RTM: NAO - without accent in data)
    df_old_rtm = bl.calculate_rtm_analysis_by_year(
        o2c_processed, chamados, erros_rtm, "NAO"
    )
    summary_old_rtm = bl.get_rtm_summary_metrics(o2c_processed, chamados, "NAO")

    # Initialize comparison variables
    corrective_idx_new = 0.0
    startup_idx_new = 0.0
    corrective_idx_old = 0.0
    startup_idx_old = 0.0

    # --- NEW RTM Section ---
    st.subheader("🆕 NEW RTM")

    if not df_new_rtm.empty:
        # Format the dataframe for display
        df_new_display = df_new_rtm.copy()
        df_new_display["Start up DFS"] = df_new_display["Start up DFS"].apply(lambda x: f"{x:.1f}%")
        df_new_display["% Chassis with tickets"] = df_new_display["% Chassis with tickets"].apply(lambda x: f"{x:.1f}%")
        df_new_display["% Chassis Under Warranty"] = df_new_display["% Chassis Under Warranty"].apply(lambda x: f"{x:.1f}%")
        df_new_display["% Chassis Under Electronic Warranty"] = df_new_display["% Chassis Under Electronic Warranty"].apply(lambda x: f"{x:.1f}%")
        df_new_display["% Chassis Error RTM Ticket"] = df_new_display["% Chassis Error RTM Ticket"].apply(lambda x: f"{x:.1f}%")

        # Transpose for better visualization (years as columns)
        df_new_transposed = df_new_display.set_index("Ano").T
        # Convert all columns to string to avoid Arrow serialization issues
        df_new_transposed = df_new_transposed.astype(str)
        st.dataframe(df_new_transposed, width="stretch")

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Units Sold", f"{summary_new_rtm['total_units']:,}")
        col2.metric("Installed Base (known by DFS)", f"{summary_new_rtm['installed_base_known']:,}")
        col3.metric("Chassis Under Warranty (36m)", f"{summary_new_rtm['chassis_36m_warranty']:,}")
        col4.metric("Chassis Under Electronic Warranty", f"{summary_new_rtm['chassis_under_electronic_warranty']:,}")

        # Comparison insights
        if len(df_new_rtm) > 1:
            total_row = df_new_rtm[df_new_rtm["Ano"] == "Total"]
            if not total_row.empty:
                corrective_idx_new = total_row["% Chassis with tickets"].values[0]
                startup_idx_new = total_row["Start up DFS"].values[0]
    else:
        st.warning("Sem dados de NEW RTM disponíveis.")

    st.divider()

    # --- OLD RTM Section ---
    st.subheader("📦 OLD RTM")

    if not df_old_rtm.empty:
        # Format the dataframe for display
        df_old_display = df_old_rtm.copy()
        # Remove RTM Error column - not applicable for OLD RTM (always 0%)
        if "% Chassis Error RTM Ticket" in df_old_display.columns:
            df_old_display = df_old_display.drop(columns=["% Chassis Error RTM Ticket"])
        df_old_display["Start up DFS"] = df_old_display["Start up DFS"].apply(lambda x: f"{x:.1f}%")
        df_old_display["% Chassis with tickets"] = df_old_display["% Chassis with tickets"].apply(lambda x: f"{x:.1f}%")
        df_old_display["% Chassis Under Warranty"] = df_old_display["% Chassis Under Warranty"].apply(lambda x: f"{x:.1f}%")
        df_old_display["% Chassis Under Electronic Warranty"] = df_old_display["% Chassis Under Electronic Warranty"].apply(lambda x: f"{x:.1f}%")

        # Transpose for better visualization (years as columns)
        df_old_transposed = df_old_display.set_index("Ano").T
        # Convert all columns to string to avoid Arrow serialization issues
        df_old_transposed = df_old_transposed.astype(str)
        st.dataframe(df_old_transposed, width="stretch")

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Units Sold", f"{summary_old_rtm['total_units']:,}")
        col2.metric("Installed Base (known by DFS)", f"{summary_old_rtm['installed_base_known']:,}")
        col3.metric("Chassis Under Warranty (36m)", f"{summary_old_rtm['chassis_36m_warranty']:,}")
        col4.metric("Chassis Under Electronic Warranty", f"{summary_old_rtm['chassis_under_electronic_warranty']:,}")

        # Get corrective index for comparison
        if len(df_old_rtm) > 1:
            total_row_old = df_old_rtm[df_old_rtm["Ano"] == "Total"]
            if not total_row_old.empty:
                corrective_idx_old = total_row_old["% Chassis with tickets"].values[0]
                startup_idx_old = total_row_old["Start up DFS"].values[0]
    else:
        st.warning("Sem dados de OLD RTM disponíveis.")

    st.divider()

    # --- Comparison Insights ---
    st.subheader("📈 Comparativo NEW RTM vs OLD RTM")

    if not df_new_rtm.empty and not df_old_rtm.empty:
        # Build comparison table by year
        # Get all years from both dataframes (excluding "Total")
        new_rtm_years = df_new_rtm[df_new_rtm["Ano"] != "Total"].set_index("Ano")
        old_rtm_years = df_old_rtm[df_old_rtm["Ano"] != "Total"].set_index("Ano")

        all_years = sorted(set(new_rtm_years.index.tolist() + old_rtm_years.index.tolist()))

        # Build comparison data
        comparison_data = []

        for ano in all_years:
            new_corr = new_rtm_years.loc[ano, "% Chassis with tickets"] if ano in new_rtm_years.index else 0
            old_corr = old_rtm_years.loc[ano, "% Chassis with tickets"] if ano in old_rtm_years.index else 0
            ratio_corr = new_corr / old_corr if old_corr > 0 else 0

            new_startup = new_rtm_years.loc[ano, "Start up DFS"] if ano in new_rtm_years.index else 0
            old_startup = old_rtm_years.loc[ano, "Start up DFS"] if ano in old_rtm_years.index else 0
            ratio_startup = new_startup / old_startup if old_startup > 0 else 0

            comparison_data.append({
                "Ano": int(ano),
                "Corretivo NEW RTM": new_corr,
                "Corretivo OLD RTM": old_corr,
                "Razão Corretivo": ratio_corr,
                "Startup NEW RTM": new_startup,
                "Startup OLD RTM": old_startup,
                "Razão Startup": ratio_startup,
            })

        # Add Total row
        new_total = df_new_rtm[df_new_rtm["Ano"] == "Total"]
        old_total = df_old_rtm[df_old_rtm["Ano"] == "Total"]

        if not new_total.empty and not old_total.empty:
            new_corr_total = new_total["% Chassis with tickets"].values[0]
            old_corr_total = old_total["% Chassis with tickets"].values[0]
            ratio_corr_total = new_corr_total / old_corr_total if old_corr_total > 0 else 0

            new_startup_total = new_total["Start up DFS"].values[0]
            old_startup_total = old_total["Start up DFS"].values[0]
            ratio_startup_total = new_startup_total / old_startup_total if old_startup_total > 0 else 0

            comparison_data.append({
                "Ano": "Total",
                "Corretivo NEW RTM": new_corr_total,
                "Corretivo OLD RTM": old_corr_total,
                "Razão Corretivo": ratio_corr_total,
                "Startup NEW RTM": new_startup_total,
                "Startup OLD RTM": old_startup_total,
                "Razão Startup": ratio_startup_total,
            })

        df_comparison = pd.DataFrame(comparison_data)

        # Format percentages and ratios
        df_comparison_display = df_comparison.copy()
        df_comparison_display["Corretivo NEW RTM"] = df_comparison_display["Corretivo NEW RTM"].apply(lambda x: f"{x:.1f}%")
        df_comparison_display["Corretivo OLD RTM"] = df_comparison_display["Corretivo OLD RTM"].apply(lambda x: f"{x:.1f}%")
        df_comparison_display["Razão Corretivo"] = df_comparison_display["Razão Corretivo"].apply(lambda x: f"{x:.2f}x" if x > 0 else "-")
        df_comparison_display["Startup NEW RTM"] = df_comparison_display["Startup NEW RTM"].apply(lambda x: f"{x:.1f}%")
        df_comparison_display["Startup OLD RTM"] = df_comparison_display["Startup OLD RTM"].apply(lambda x: f"{x:.1f}%")
        df_comparison_display["Razão Startup"] = df_comparison_display["Razão Startup"].apply(lambda x: f"{x:.2f}x" if x > 0 else "-")

        # Transpose for better visualization
        df_comparison_transposed = df_comparison_display.set_index("Ano").T
        # Convert all columns to string to avoid Arrow serialization issues
        df_comparison_transposed = df_comparison_transposed.astype(str)
        st.dataframe(df_comparison_transposed, width="stretch")


# --- Funções auxiliares para detalhamento ---
def partida_inicial_info(chassi):
    """Get partida inicial information for a chassis."""
    return "SIM" if chassi in partida_set else "NÃO"


def chamados_lista(chassi):
    """Get list of calls for a chassis."""
    return chamados_por_chassi_dict.get(chassi, [])
