import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional
from collections import Counter
from utils import precompute_filter_options


@st.cache_data(ttl=1800, show_spinner=False)
def prepare_filter_options(df: pd.DataFrame, todas_tags: List[str]) -> Dict[str, Any]:
    """Prepare filter options for the sidebar with caching."""
    # Precompute filter options for better performance
    filter_options = precompute_filter_options(df)

    # Filtro de tags - sorted by frequency for better UX
    if "TAGS" in filter_options:
        todas_tags = filter_options["TAGS"]
        # Sort by frequency (most common first) - optimized version
        tag_counts = Counter(tag for tags in df["TAGS"] for tag in tags)
        todas_tags = sorted(
            todas_tags,
            key=lambda x: tag_counts.get(x, 0),
            reverse=True,
        )

    # Filtros padrão usando opções pré-computadas
    filtros = {}
    for campo in [
        "ESPECIALISTA",
        "PROPRIETÁRIO",
        "MANTENEDOR",
        "RTM",
        "GARANTIA",
        "TIPO",
        "SERVIÇO",
        "MODELO",
    ]:
        if campo in filter_options:
            filtros[campo] = filter_options[campo]

    return {"todas_tags": todas_tags, "filtros": filtros}


def sidebar_filters(
    df: pd.DataFrame,
    todas_tags: List[str],
    campos_adicionais: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Cria filtros na sidebar e retorna as seleções do usuário."""
    st.sidebar.header("Filtros")

    # Get prepared filter options
    filter_data = prepare_filter_options(df, todas_tags)
    todas_tags = filter_data["todas_tags"]
    filtros = filter_data["filtros"]

    # Adicionais
    if campos_adicionais:
        for campo in campos_adicionais:
            if campo in df.columns:
                filtros[campo] = sorted(df[campo].dropna().unique())

    # --- Group 1: Periodo & Status ---
    with st.sidebar.expander("📅 Período & Status", expanded=True):
        status_selecionado = st.selectbox(
            "Status",
            options=["GERAL", "ABERTO", "FECHADO"],
            index=1,
            key="status_filter",
        )
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Início", value=None, key="data_inicio")
        with col2:
            data_fim = st.date_input("Fim", value=None, key="data_fim")

    # --- Group 2: Atributos da Bomba ---
    selecoes = {}
    with st.sidebar.expander("⛽ Atributos da Bomba", expanded=False):
        for campo in ["MODELO", "RTM", "GARANTIA"]:
            if campo in filtros:
                selecoes[campo] = st.multiselect(
                    campo, filtros[campo], key=f"filter_{campo}"
                )

    # --- Group 3: Envolvidos (Pessoas) ---
    with st.sidebar.expander("👥 Envolvidos", expanded=False):
        for campo in ["ESPECIALISTA", "PROPRIETÁRIO", "MANTENEDOR"]:
            if campo in filtros:
                selecoes[campo] = st.multiselect(
                    campo, filtros[campo], key=f"filter_{campo}"
                )

    # --- Group 4: Classificação (Tipo/Serviço/Tags) ---
    with st.sidebar.expander("🏷️ Classificação", expanded=False):
        tags_selecionadas = st.multiselect("Tags", todas_tags, key="filter_tags")
        for campo in ["TIPO", "SERVIÇO"]:
            if campo in filtros:
                selecoes[campo] = st.multiselect(
                    campo, filtros[campo], key=f"filter_{campo}"
                )

        # Add remaining fields if any
        remaining_fields = [
            k
            for k in filtros.keys()
            if k
            not in [
                "MODELO",
                "RTM",
                "GARANTIA",
                "ESPECIALISTA",
                "PROPRIETÁRIO",
                "MANTENEDOR",
                "TIPO",
                "SERVIÇO",
            ]
        ]
        for campo in remaining_fields:
            selecoes[campo] = st.multiselect(
                campo, filtros[campo], key=f"filter_{campo}"
            )

    return {
        "tags_selecionadas": tags_selecionadas,
        "selecoes": selecoes,
        "status_selecionado": status_selecionado,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
    }


def _convert_to_hashable(selecoes: Dict[str, List[str]]) -> tuple:
    """Convert dict of lists to hashable tuple of tuples for caching."""
    return tuple(sorted((k, tuple(sorted(v))) for k, v in selecoes.items()))


@st.cache_data(ttl=900, show_spinner=False)
def _aplicar_filtros_cached(
    df: pd.DataFrame,
    tags_selecionadas_tuple: tuple,
    selecoes_tuple: tuple,
    termo_pesquisa: str,
    status_selecionado: str,
    data_inicio_str: Optional[str],
    data_fim_str: Optional[str],
) -> pd.DataFrame:
    """Internal cached filter function with hashable parameters."""
    df_filtrado = df.copy()

    # Convert back from hashable types
    tags_selecionadas = list(tags_selecionadas_tuple)
    selecoes = {k: list(v) for k, v in selecoes_tuple}

    # Parse dates back from strings
    data_inicio = pd.to_datetime(data_inicio_str) if data_inicio_str else None
    data_fim = pd.to_datetime(data_fim_str) if data_fim_str else None

    # Filtro de tags (exatamente as selecionadas)
    if tags_selecionadas:
        df_filtrado = df_filtrado[
            df_filtrado["TAGS"].apply(lambda tags: set(tags) == set(tags_selecionadas))
        ]

    # Filtros múltiplos - otimizado com vectorização
    for coluna, valores in selecoes.items():
        if valores and coluna in df_filtrado.columns:
            df_filtrado = df_filtrado[df_filtrado[coluna].isin(valores)]

    # Filtro de status
    if status_selecionado == "ABERTO":
        df_filtrado = df_filtrado[df_filtrado["STATUS"] == "ABERTO"]
    elif status_selecionado == "FECHADO":
        df_filtrado = df_filtrado[df_filtrado["STATUS"] != "ABERTO"]

    # Filtros de datas - otimizado
    if data_inicio:
        df_filtrado = df_filtrado[
            pd.to_datetime(df_filtrado["INÍCIO"], dayfirst=True, errors="coerce")
            >= data_inicio
        ]
    if data_fim:
        df_filtrado = df_filtrado[
            pd.to_datetime(df_filtrado["FIM"], dayfirst=True, errors="coerce")
            <= data_fim
        ]

    # Filtro de texto - otimizado
    if termo_pesquisa:
        # Use vectorized string operations for better performance
        # Create boolean mask for each column, then check if any column matches per row
        mask = df_filtrado.astype(str).apply(
            lambda col: col.str.contains(termo_pesquisa, case=False, na=False)
        ).any(axis=1)
        df_filtrado = df_filtrado[mask]

    return df_filtrado


def aplicar_filtros(
    df: pd.DataFrame,
    tags_selecionadas: List[str],
    selecoes: Dict[str, List[str]],
    termo_pesquisa: str = "",
    status_selecionado: str = "GERAL",
    data_inicio=None,
    data_fim=None,
) -> pd.DataFrame:
    """Aplica os filtros selecionados ao DataFrame com otimizações.

    Wrapper function that converts mutable parameters to hashable types
    for proper cache key generation.
    """
    # Convert mutable types to hashable for caching
    tags_tuple = tuple(sorted(tags_selecionadas)) if tags_selecionadas else ()
    selecoes_tuple = _convert_to_hashable(selecoes) if selecoes else ()

    # Convert dates to string for hashable cache key
    data_inicio_str = str(data_inicio) if data_inicio else None
    data_fim_str = str(data_fim) if data_fim else None

    return _aplicar_filtros_cached(
        df,
        tags_tuple,
        selecoes_tuple,
        termo_pesquisa,
        status_selecionado,
        data_inicio_str,
        data_fim_str,
    )


@st.cache_data(ttl=1800, show_spinner=False)
def prepare_parque_filter_options(
    df: pd.DataFrame, chassi_counts: pd.Series
) -> Dict[str, Any]:
    """Prepare filter options for the parque instalado page with caching."""
    # RTM
    rtm_options = ["TODOS"] + sorted(df["RTM"].dropna().unique())

    # Garantia
    garantia_options = ["TODOS", "DENTRO", "FORA"]

    # Partida Inicial
    partida_options = ["TODOS", "NÃO", "SIM - TERCEIRO", "SIM - DFS"]

    # Range Ano NF
    anos_validos = df["ANO_NF"].dropna().astype(int)
    if not anos_validos.empty:
        ano_min, ano_max = int(anos_validos.min()), int(anos_validos.max())
    else:
        ano_min, ano_max = 2000, 2030

    # Range Nº de chamados
    qtd_chamados_validos = chassi_counts.reindex(
        df["NUM_SERIAL"].dropna().unique(), fill_value=0
    )
    chamados_min, chamados_max = (
        int(qtd_chamados_validos.min()),
        int(qtd_chamados_validos.max()),
    )

    return {
        "rtm_options": rtm_options,
        "garantia_options": garantia_options,
        "partida_options": partida_options,
        "ano_min": ano_min,
        "ano_max": ano_max,
        "chamados_min": chamados_min,
        "chamados_max": chamados_max,
    }


def sidebar_filters_parque(
    df: pd.DataFrame, chassi_counts: pd.Series
) -> Dict[str, Any]:
    """Cria filtros específicos para a página do parque instalado."""
    st.sidebar.header("Filtros")

    # Get prepared filter options
    filter_data = prepare_parque_filter_options(df, chassi_counts)

    # RTM
    rtm_sel = st.sidebar.selectbox("RTM", filter_data["rtm_options"])

    # Garantia
    garantia_sel = st.sidebar.selectbox("Garantia", filter_data["garantia_options"])

    # Partida Inicial
    partida_sel = st.sidebar.selectbox(
        "Partida Inicial", filter_data["partida_options"]
    )

    # Range Ano NF
    ano_range = st.sidebar.slider(
        "Ano da NF",
        filter_data["ano_min"],
        filter_data["ano_max"],
        (filter_data["ano_min"], filter_data["ano_max"]),
    )

    # Range Nº de chamados
    chamados_range = st.sidebar.slider(
        "Nº de chamados",
        filter_data["chamados_min"],
        filter_data["chamados_max"],
        (filter_data["chamados_min"], filter_data["chamados_max"]),
    )

    return {
        "rtm_sel": rtm_sel,
        "garantia_sel": garantia_sel,
        "partida_sel": partida_sel,
        "ano_range": ano_range,
        "chamados_range": chamados_range,
    }


@st.cache_data(ttl=900, show_spinner=False)
def aplicar_filtros_parque(
    df: pd.DataFrame,
    filtros: Dict[str, Any],
    partida_set: set,
    chassi_counts: pd.Series,
    chassi_counts_validos: pd.Series = None,
) -> pd.DataFrame:
    """Aplica filtros específicos para a página do parque instalado."""
    df_filtrado = df.copy()

    # RTM
    if filtros["rtm_sel"] != "TODOS":
        df_filtrado = df_filtrado[df_filtrado["RTM"] == filtros["rtm_sel"]]

    # Garantia
    if filtros["garantia_sel"] != "TODOS":
        df_filtrado = df_filtrado[
            df_filtrado["STATUS_GARANTIA"] == filtros["garantia_sel"]
        ]

    # Partida Inicial
    if filtros["partida_sel"] != "TODOS":
        if filtros["partida_sel"] == "SIM - DFS":
            # Only DFS startup
            df_filtrado = df_filtrado[df_filtrado["NUM_SERIAL"].isin(partida_set)]
        elif filtros["partida_sel"] == "SIM - TERCEIRO":
            # Third-party service (no DFS startup, but has calls)
            # Use valid counts (excluding [STB]) if available
            counts_to_use = (
                chassi_counts_validos
                if chassi_counts_validos is not None
                else chassi_counts
            )
            df_filtrado = df_filtrado[
                (~df_filtrado["NUM_SERIAL"].isin(partida_set))
                & (df_filtrado["NUM_SERIAL"].map(counts_to_use) > 0)
            ]
        elif filtros["partida_sel"] == "NÃO":
            # No startup and no calls
            # Use valid counts (excluding [STB]) if available
            counts_to_use = (
                chassi_counts_validos
                if chassi_counts_validos is not None
                else chassi_counts
            )
            df_filtrado = df_filtrado[
                (~df_filtrado["NUM_SERIAL"].isin(partida_set))
                & (df_filtrado["NUM_SERIAL"].map(counts_to_use) == 0)
            ]

    # Ano NF
    df_filtrado = df_filtrado[
        (df_filtrado["ANO_NF"] >= filtros["ano_range"][0])
        & (df_filtrado["ANO_NF"] <= filtros["ano_range"][1])
    ]

    # Número de chamados
    chassis_filtros = df_filtrado["NUM_SERIAL"].dropna().unique()
    qtd_chamados_filtros = chassi_counts.reindex(chassis_filtros, fill_value=0)
    df_filtrado = df_filtrado[
        df_filtrado["NUM_SERIAL"].isin(
            qtd_chamados_filtros[
                (qtd_chamados_filtros >= filtros["chamados_range"][0])
                & (qtd_chamados_filtros <= filtros["chamados_range"][1])
            ].index
        )
    ]

    return df_filtrado


@st.cache_data(ttl=1800, show_spinner=False)
def prepare_rtm_error_filter_options(erros_rtm_df: pd.DataFrame) -> Dict[str, Any]:
    """Prepare RTM error filter options with caching."""
    if erros_rtm_df.empty:
        return {
            "tipo_erro_options": ["TODOS"],
            "desc_erro_options": ["TODOS"],
            "cod_erro_options": ["TODOS"],
            "detalhes_erro_options": ["TODOS"],
        }

    # TIPO_ERRO options
    tipo_erro_options = ["TODOS"] + sorted(
        erros_rtm_df["TIPO_ERRO"]
        .dropna()
        .replace("", pd.NA)
        .dropna()
        .drop_duplicates()
        .unique()
    )

    # DESC_ERRO options
    desc_erro_options = ["TODOS"] + sorted(
        erros_rtm_df["DESC_ERRO"]
        .dropna()
        .replace("", pd.NA)
        .dropna()
        .drop_duplicates()
        .unique()
    )

    # CÓD_ERRO options
    cod_erro_options = ["TODOS"] + sorted(
        erros_rtm_df["CÓD_ERRO"]
        .dropna()
        .replace("", pd.NA)
        .dropna()
        .drop_duplicates()
        .unique()
    )

    # DETALHES_ERRO options
    detalhes_erro_options = ["TODOS"] + sorted(
        erros_rtm_df["DETALHES_ERRO"]
        .dropna()
        .replace("", pd.NA)
        .dropna()
        .drop_duplicates()
        .unique()
    )

    return {
        "tipo_erro_options": tipo_erro_options,
        "desc_erro_options": desc_erro_options,
        "cod_erro_options": cod_erro_options,
        "detalhes_erro_options": detalhes_erro_options,
    }


def sidebar_filters_rtm_errors(erros_rtm_df: pd.DataFrame) -> Dict[str, Any]:
    """Create RTM error filters in the sidebar with multiple selection."""
    st.sidebar.header("🔧 Filtros de Erros RTM")

    # Get prepared filter options
    filter_data = prepare_rtm_error_filter_options(erros_rtm_df)

    # Remove 'TODOS' from options for multiselect and use empty list as default (all selected)
    tipo_erro_options = [
        opt for opt in filter_data["tipo_erro_options"] if opt != "TODOS"
    ]
    desc_erro_options = [
        opt for opt in filter_data["desc_erro_options"] if opt != "TODOS"
    ]
    cod_erro_options = [
        opt for opt in filter_data["cod_erro_options"] if opt != "TODOS"
    ]
    detalhes_erro_options = [
        opt for opt in filter_data["detalhes_erro_options"] if opt != "TODOS"
    ]

    # TIPO_ERRO (multiselect - empty means all)
    tipo_erro_sel = st.sidebar.multiselect(
        "Tipo de Erro",
        tipo_erro_options,
        help="Selecione um ou mais tipos de erro. Deixe vazio para incluir todos.",
    )

    # DESC_ERRO (multiselect)
    desc_erro_sel = st.sidebar.multiselect(
        "Descrição do Erro",
        desc_erro_options,
        help="Selecione uma ou mais descrições. Deixe vazio para incluir todas.",
    )

    # CÓD_ERRO (multiselect)
    cod_erro_sel = st.sidebar.multiselect(
        "Código do Erro",
        cod_erro_options,
        help="Selecione um ou mais códigos. Deixe vazio para incluir todos.",
    )

    # DETALHES_ERRO (multiselect)
    detalhes_erro_sel = st.sidebar.multiselect(
        "Detalhes do Erro",
        detalhes_erro_options,
        help="Selecione um ou mais detalhes. Deixe vazio para incluir todos.",
    )

    return {
        "tipo_erro_sel": tipo_erro_sel,
        "desc_erro_sel": desc_erro_sel,
        "cod_erro_sel": cod_erro_sel,
        "detalhes_erro_sel": detalhes_erro_sel,
    }


@st.cache_data(ttl=900, show_spinner=False)
def aplicar_filtros_rtm_errors(
    df: pd.DataFrame,
    filtros_rtm: Dict[str, Any],
    erros_rtm_df: pd.DataFrame,
    chamados_por_chassi_dict: Dict[str, List[str]],
) -> pd.DataFrame:
    """Apply RTM error filters with multiple selection support."""
    df_filtrado = df.copy()

    # If no RTM filters are selected (all lists empty), return original data
    if (
        not filtros_rtm["tipo_erro_sel"]
        and not filtros_rtm["desc_erro_sel"]
        and not filtros_rtm["cod_erro_sel"]
        and not filtros_rtm["detalhes_erro_sel"]
    ):
        return df_filtrado

    # Filter RTM errors based on selections
    erros_filtrados = erros_rtm_df.copy()

    # Apply filters - empty list means "all" (no filter)
    if filtros_rtm["tipo_erro_sel"]:  # If not empty
        erros_filtrados = erros_filtrados[
            erros_filtrados["TIPO_ERRO"].isin(filtros_rtm["tipo_erro_sel"])
        ]

    if filtros_rtm["desc_erro_sel"]:  # If not empty
        erros_filtrados = erros_filtrados[
            erros_filtrados["DESC_ERRO"].isin(filtros_rtm["desc_erro_sel"])
        ]

    if filtros_rtm["cod_erro_sel"]:  # If not empty
        erros_filtrados = erros_filtrados[
            erros_filtrados["CÓD_ERRO"].isin(filtros_rtm["cod_erro_sel"])
        ]

    if filtros_rtm["detalhes_erro_sel"]:  # If not empty
        erros_filtrados = erros_filtrados[
            erros_filtrados["DETALHES_ERRO"].isin(filtros_rtm["detalhes_erro_sel"])
        ]

    # Get SS numbers from filtered errors
    ss_filtrados = set(erros_filtrados["SS"].astype(str))

    # Find chassis that have any of these SS numbers in their chamados
    chassis_com_erros = set()
    for chassi, ss_list in chamados_por_chassi_dict.items():
        if any(ss in ss_filtrados for ss in ss_list):
            chassis_com_erros.add(chassi)

    # Filter the main dataframe to only include chassis with matching errors
    df_filtrado = df_filtrado[df_filtrado["NUM_SERIAL"].isin(chassis_com_erros)]

    return df_filtrado
