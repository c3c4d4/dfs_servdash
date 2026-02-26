import streamlit as st
import pandas as pd
import base64

from data_loader import (
    carregar_dados_merged,
    carregar_o2c,
    process_chamados_data,
    process_o2c_data,
)
from utils import (
    extrair_tags_vectorized,
    extrair_codigo_bomba_vectorized,
    calcular_garantia_vectorized,
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


def kpi_section(df):
    """Calculate and display KPIs with progress bar visualization."""
    metrics = vz.create_kpi_metrics(df)

    # Main KPI cards (Total, Abertos, Fechados, Aging)
    vz.render_kpi_section_cards(metrics)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Percentage bars (Garantia, RTM)
    vz.render_percentage_bars(metrics)

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # Model distribution bars
    model_metrics = vz.create_model_kpi_metrics(df)
    if model_metrics:
        st.markdown(
            "<div style='font-size: 14px; font-weight: 600; color: #444; margin-bottom: 12px;'>"
            "📊 Distribuição por Modelo"
            "</div>",
            unsafe_allow_html=True,
        )
        vz.render_model_distribution_bars(model_metrics)


def render_customer_relationship_section(df: pd.DataFrame):
    """Render customer relationship matrix and monthly SAW score trends."""
    st.markdown(
        """
        <style>
        .crm-header {
            border: 1px solid #d5e3f0;
            border-radius: 14px;
            padding: 0.9rem 1rem;
            background: linear-gradient(120deg, #f4faf7 0%, #f7f8ff 55%, #fff7f5 100%);
            margin-bottom: 0.6rem;
        }
        .crm-title {
            color: #133b4a;
            font-weight: 700;
            font-size: 1.02rem;
            margin: 0;
            font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
        }
        .crm-subtitle {
            color: #51677d;
            margin: 0.2rem 0 0 0;
            font-size: 0.9rem;
            line-height: 1.35;
            font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
        }
        </style>
        <div class="crm-header">
            <p class="crm-title">Customer Relationship Matrix</p>
            <p class="crm-subtitle">
                Score 1: alto volume + alta rapidez · Score 2: baixo volume + alta rapidez ·
                Score 3: baixo volume + baixa rapidez · Score 4: alto volume + baixa rapidez.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    periodo = st.radio(
        "Período",
        options=["Últimos 6 meses", "Último ano", "All time"],
        horizontal=True,
        key="crm_periodo",
    )
    df_rel = vz.filter_customer_relationship_period(df, periodo)

    if df_rel.empty:
        st.info("Sem dados válidos para montar a matriz no período selecionado.")
        return

    fig_matrix = vz.customer_relationship_matrix_chart(df_rel)
    if fig_matrix is not None:
        st.plotly_chart(fig_matrix, width="stretch")
    else:
        st.info("Não foi possível montar a matriz de relacionamento.")

    fig_monthly = vz.customer_relationship_monthly_score_chart(df_rel)
    if fig_monthly is not None:
        st.plotly_chart(fig_monthly, width="stretch")
    else:
        st.info("Sem histórico mensal suficiente para calcular score por SAW.")


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
    st.sidebar.markdown("---")
    search = st.sidebar.text_input(
        "🔍 Pesquisar Global", placeholder="Ex: Número série, cliente..."
    )

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

        def calc_aging(row):
            try:
                inicio = pd.to_datetime(row["INÍCIO"], dayfirst=True, errors="coerce")
                fim = pd.to_datetime(row["FIM"], dayfirst=True, errors="coerce")
                if pd.isna(inicio):
                    return ""
                if pd.isna(fim):
                    fim = hoje
                return str((fim - inicio).days)
            except Exception:
                return ""

        df_display.loc[mask_aging_vazio, "AGING"] = df_display.loc[
            mask_aging_vazio
        ].apply(calc_aging, axis=1)

    # --- TABS LAYOUT ---
    st.title("📊 Painel Principal")

    tab_overview, tab_data, tab_charts = st.tabs(
        ["📈 Visão Geral", "📋 Dados Detalhados", "📊 Análise Gráfica"]
    )

    # --- TAB 1: OVERVIEW ---
    with tab_overview:
        st.subheader("Indicadores Principais")
        # Display KPIs
        kpi_section(df_filtrado)

        st.markdown("---")

        # Top-level charts for overview
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(vz.pie_chart_aging(df_filtrado), width="stretch")
        with col2:
            if df_filtrado["TAGS"].any():
                tags_contagem = pd.Series(
                    [tag for tags in df_filtrado["TAGS"] for tag in tags]
                ).value_counts()
                st.plotly_chart(
                    vz.bar_chart_tags(tags_contagem), width="stretch"
                )

    # --- TAB 2: DATA ---
    with tab_data:
        st.subheader(f"Listagem de Chamados ({len(df_display)})")

        # Display filtered data
        st.dataframe(
            df_display,
            width="stretch",
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
                "ESPECIALISTA": st.column_config.TextColumn(
                    "Especialista", width="medium"
                ),
                "PROPRIETÁRIO": st.column_config.TextColumn(
                    "Proprietário", width="medium"
                ),
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
                "AGING": st.column_config.NumberColumn(
                    "Aging", format="%d", width="small"
                ),
                "FIM_GARANTIA": st.column_config.TextColumn(
                    "Fim Garantia", width="small"
                ),
                "GARANTIA": st.column_config.TextColumn("Garantia", width="small"),
                "STATUS": st.column_config.TextColumn("Status", width="small"),
            },
        )

    # --- TAB 3: CHARTS ---
    with tab_charts:
        st.subheader("Análise Detalhada de Performance")

        render_customer_relationship_section(df_filtrado)
        st.markdown("---")

        # Performance charts
        col1, col2 = st.columns(2)

        with col1:
            st.plotly_chart(
                vz.bar_chart_aging_proprietario(df_filtrado), width="stretch"
            )

        with col2:
            st.plotly_chart(
                vz.bar_chart_aging_especialista(df_filtrado), width="stretch"
            )

        # Mantenedor performance
        st.plotly_chart(
            vz.bar_chart_aging_mantenedor(df_filtrado), width="stretch"
        )

        # Time series analysis
        st.plotly_chart(
            vz.line_chart_aging(df_filtrado, "ESPECIALISTA"), width="stretch"
        )


if __name__ == "__main__":
    main()
