import streamlit as st
import pandas as pd
from typing import Dict, List, Any

def sidebar_filters(df: pd.DataFrame, todas_tags: List[str]) -> Dict[str, Any]:
    """Creates sidebar filters and returns selected values."""
    st.sidebar.header("Filtros")
    todas_tags = sorted(todas_tags, key=lambda x: df["Tags"].apply(lambda tags: x in tags).sum(), reverse=True)
    tags_selecionadas = st.sidebar.multiselect("Filtrar por tags", todas_tags)

    filtros = {
        "Especialista": sorted(df["Especialista"].dropna().unique()),
        "Proprietário": sorted(df["Proprietário"].dropna().unique()),
        "Mantenedor": sorted(df["Mantenedor"].dropna().unique()),
        "RTM": sorted(df["RTM"].dropna().unique()),
        "Tipo": sorted(df["Tipo"].dropna().unique()),
        "Serviço": sorted(df["Serviço"].dropna().unique()),
        "Problema": sorted(df["Problema"].dropna().unique()),
        "Resolução": sorted(df["Resolução"].dropna().unique()),
    }
    selecoes = {k: st.sidebar.multiselect(k, v) for k, v in filtros.items()}
    status_selecionado = st.sidebar.selectbox(
        "Status",
        options=["GERAL", "ABERTO", "FECHADO"],
        index=1  # "ABERTO" como padrão
    )
    return {
        "tags_selecionadas": tags_selecionadas,
        "selecoes": selecoes,
        "status_selecionado": status_selecionado
    }

def aplicar_filtros(
    df: pd.DataFrame,
    tags_selecionadas: List[str],
    selecoes: Dict[str, List[str]],
    termo_pesquisa: str = ""
) -> pd.DataFrame:
    """Applies selected filters and search term to the DataFrame."""
    df_filtrado = df.copy()
    if tags_selecionadas:
        df_filtrado = df_filtrado[df_filtrado["Tags"].apply(lambda tags: all(tag in tags for tag in tags_selecionadas))]
    for coluna, valores in selecoes.items():
        if valores:
            df_filtrado = df_filtrado[df_filtrado[coluna].isin(valores)]
    if termo_pesquisa:
        df_filtrado = df_filtrado[df_filtrado.apply(lambda row: row.astype(str).str.contains(termo_pesquisa, case=False).any(), axis=1)]
    return df_filtrado 