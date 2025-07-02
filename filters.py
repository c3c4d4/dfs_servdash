import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional

def sidebar_filters(
    df: pd.DataFrame,
    todas_tags: List[str],
    campos_adicionais: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Cria filtros na sidebar e retorna as seleções do usuário."""
    st.sidebar.header("Filtros")
    # Filtro de tags
    todas_tags = sorted(todas_tags, key=lambda x: df["TAGS"].apply(lambda tags: x in tags).sum(), reverse=True)
    tags_selecionadas = st.sidebar.multiselect("Filtrar por tags", todas_tags)

    # Filtros padrão
    filtros = {
        "ESPECIALISTA": sorted(df["ESPECIALISTA"].dropna().unique()),
        "PROPRIETÁRIO": sorted(df["PROPRIETÁRIO"].dropna().unique()),
        "MANTENEDOR": sorted(df["MANTENEDOR"].dropna().unique()),
        "RTM": sorted(df["RTM"].dropna().unique()),
        "GARANTIA": sorted(df["GARANTIA"].dropna().unique()),
        "TIPO": sorted(df["TIPO"].dropna().unique()),
        "SERVIÇO": sorted(df["SERVIÇO"].dropna().unique()),
    }
    # Adicionais
    if campos_adicionais:
        for campo in campos_adicionais:
            if campo in df.columns:
                filtros[campo] = sorted(df[campo].dropna().unique())

    selecoes = {k: st.sidebar.multiselect(k, v) for k, v in filtros.items()}

    # Filtro de status
    status_selecionado = st.sidebar.selectbox(
        "Status",
        options=["GERAL", "ABERTO", "FECHADO"],
        index=1
    )

    # Filtros de datas
    data_inicio = st.sidebar.date_input("Data início", value=None, key="data_inicio")
    data_fim = st.sidebar.date_input("Data fim", value=None, key="data_fim")

    return {
        "tags_selecionadas": tags_selecionadas,
        "selecoes": selecoes,
        "status_selecionado": status_selecionado,
        "data_inicio": data_inicio,
        "data_fim": data_fim
    }

def aplicar_filtros(
    df: pd.DataFrame,
    tags_selecionadas: List[str],
    selecoes: Dict[str, List[str]],
    termo_pesquisa: str = "",
    status_selecionado: str = "GERAL",
    data_inicio=None,
    data_fim=None
) -> pd.DataFrame:
    """Aplica os filtros selecionados ao DataFrame."""
    df_filtrado = df.copy()
    # Filtro de tags (exatamente as selecionadas)
    if tags_selecionadas:
        df_filtrado = df_filtrado[df_filtrado["TAGS"].apply(lambda tags: set(tags) == set(tags_selecionadas))]
    # Filtros múltiplos
    for coluna, valores in selecoes.items():
        if valores:
            df_filtrado = df_filtrado[df_filtrado[coluna].isin(valores)]
    # Filtro de status
    if status_selecionado == "ABERTO":
        df_filtrado = df_filtrado[df_filtrado["STATUS"] == "ABERTO"]
    elif status_selecionado == "FECHADO":
        df_filtrado = df_filtrado[df_filtrado["STATUS"] != "ABERTO"]
    # Filtros de datas
    if data_inicio:
        df_filtrado = df_filtrado[pd.to_datetime(df_filtrado["INÍCIO"], dayfirst=True, errors="coerce") >= pd.to_datetime(data_inicio)]
    if data_fim:
        df_filtrado = df_filtrado[pd.to_datetime(df_filtrado["FIM"], dayfirst=True, errors="coerce") <= pd.to_datetime(data_fim)]
    # Filtro de texto
    if termo_pesquisa:
        df_filtrado = df_filtrado[df_filtrado.apply(lambda row: row.astype(str).str.contains(termo_pesquisa, case=False).any(), axis=1)]
    return df_filtrado 