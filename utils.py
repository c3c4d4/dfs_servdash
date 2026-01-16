import re
import pandas as pd
import numpy as np
from typing import Optional, List, Set
import streamlit as st
from functools import lru_cache


@lru_cache(maxsize=128)
def extrair_estado(endereco: str) -> Optional[str]:
    """Extracts the state (UF) from the address string with caching."""
    if pd.isna(endereco) or not isinstance(endereco, str):
        return None
    match = re.search(r",\s*([A-Z]{2}),\s*BR", endereco)
    return match.group(1) if match else None


@lru_cache(maxsize=128)
def extrair_pais(endereco: str) -> Optional[str]:
    """Extracts the country code from the address string with caching."""
    if pd.isna(endereco) or not isinstance(endereco, str):
        return None
    match = re.findall(r",\s*([A-Z]{2})\s*$", endereco.strip())
    return match[-1] if match else None


@st.cache_data(ttl=1800, show_spinner=False)
def extrair_tags_vectorized(texto_series: pd.Series) -> pd.Series:
    """Extracts tags from a pandas Series of text with vectorized operations."""

    def extract_tags_single(texto):
        if pd.isna(texto) or not isinstance(texto, str):
            return ["Sem Tags"]
        tags = re.findall(r"\[(.*?)\]", texto)
        tags = [tag.strip().upper() for tag in tags]
        return list(set(tags)) if tags else ["Sem Tags"]

    return texto_series.apply(extract_tags_single)


def extrair_tags(texto: str) -> List[str]:
    """Extracts tags from the summary text (legacy function)."""
    if pd.isna(texto) or not isinstance(texto, str):
        return ["Sem Tags"]
    tags = re.findall(r"\[(.*?)\]", texto)
    tags = [tag.strip().upper() for tag in tags]
    return list(set(tags)) if tags else ["Sem Tags"]


@st.cache_data(ttl=1800, show_spinner=False)
def extrair_codigo_bomba_vectorized(desc_series: pd.Series) -> pd.Series:
    """Extracts pump codes from description series with vectorized operations."""

    def extract_code(desc):
        if pd.isna(desc) or not isinstance(desc, str):
            return ""
        desc = desc.strip()
        if desc.startswith("BOMBA MEDIDORA DE COMBUSTIVEIS LIQUIDOS"):
            partes = desc.split("-")
            if len(partes) > 1:
                return partes[1].strip()
        return ""

    return desc_series.apply(extract_code)


@st.cache_data(ttl=1800, show_spinner=False)
def calcular_aging_vectorized(
    inicio_series: pd.Series, fim_series: pd.Series, status_series: pd.Series
) -> pd.Series:
    """Calculate aging days with vectorized operations."""
    hoje = pd.Timestamp.now().normalize()

    # Convert to datetime
    inicio_dt = pd.to_datetime(inicio_series, dayfirst=True, errors="coerce")
    fim_dt = pd.to_datetime(fim_series, dayfirst=True, errors="coerce")

    # Handle open tickets without end date
    mask_aberto_sem_fim = (status_series == "ABERTO") & fim_dt.isna()
    fim_dt = fim_dt.fillna(hoje)

    # Calculate aging
    aging = (fim_dt - inicio_dt).dt.days

    return aging


@st.cache_data(ttl=1800, show_spinner=False)
def calcular_garantia_vectorized(
    dt_nf_series: pd.Series, garantia_dias_series: pd.Series
) -> tuple:
    """Calculate guarantee status and end date with vectorized operations."""
    hoje = pd.Timestamp.now().normalize()

    # Convert to datetime and numeric
    dt_nf = pd.to_datetime(dt_nf_series, dayfirst=True, errors="coerce")
    garantia_dias = pd.to_numeric(garantia_dias_series, errors="coerce")

    # Calculate guarantee end date
    fim_garantia = dt_nf + pd.to_timedelta(garantia_dias, unit="D")

    # Calculate status
    status_garantia = np.where(
        fim_garantia.notna(), np.where(fim_garantia >= hoje, "DENTRO", "FORA"), ""
    )

    return status_garantia, fim_garantia


@st.cache_data(ttl=1800, show_spinner=False)
def formatar_data_excel_vectorized(val_series: pd.Series) -> pd.Series:
    """Format Excel dates with vectorized operations."""

    def format_single(val):
        if pd.isna(val):
            return ""

        if hasattr(val, "strftime"):
            return val.strftime("%d/%m/%Y")

        if isinstance(val, (float, int)):
            try:
                return (
                    pd.to_datetime("1899-12-30") + pd.to_timedelta(val, "D")
                ).strftime("%d/%m/%Y")
            except Exception:
                return str(val)

        if isinstance(val, str):
            try:
                fval = float(val.replace(",", "."))
                return (
                    pd.to_datetime("1899-12-30") + pd.to_timedelta(fval, "D")
                ).strftime("%d/%m/%Y")
            except Exception:
                try:
                    dt = pd.to_datetime(val, dayfirst=True, errors="coerce")
                    if pd.isna(dt):
                        return val
                    return dt.strftime("%d/%m/%Y")
                except Exception:
                    return val

        return str(val)

    return val_series.apply(format_single)


@st.cache_data(ttl=1800, show_spinner=False)
def extrair_modelo_vectorized(serie_series: pd.Series) -> pd.Series:
    """Extract model from series column based on prefix before '-'.

    Optimized version using vectorized string operations and .map().
    """
    # Model mapping based on prefix before '-'
    model_mapping = {
        "W7E123": "E123",
        "W7HX2": "HELIX",
        "W7HXH": "HELIX",
        "3G2209P": "3G",
        "W7HX6": "HELIX",
        "W7HX1": "HELIX",
        "3G2203P": "3G",
        "3G3389P": "3G",
        "3G3390P": "3G",
        "3G2201P": "3G",
        "3G3394P": "3G",
        "3G3490P": "3G",
        "E123LARLA3": "E123",
        "3G2204P": "3G",
        "3G2202P": "3G",
        "3G3384P": "3G",
        "3G2207P": "3G",
        "3G3494P": "3G",
        "3G2221P": "3G",
        "W7GCEN": "CENTURY",
        "W7GVIS": "VISTA",
        # Legacy mappings (keeping for compatibility)
        "W9000001": "HELIX",
        "7502A": "7502A",
        "N3G2201PO": "3G",
        "3GV3490P": "3G",
    }

    # Vectorized: Extract prefix before '-' or use the whole string if no '-'
    # Handle NaN/None values by filling with empty string first
    clean_series = serie_series.fillna("").astype(str)

    # Split by '-' and take first part, then uppercase
    prefixes = clean_series.str.split("-").str[0].str.strip().str.upper()

    # Map prefixes to models using pandas Series.map()
    result = prefixes.map(model_mapping).fillna("OUTROS")

    return result


@st.cache_data(ttl=3600, show_spinner=False)
def precompute_filter_options(df: pd.DataFrame) -> dict:
    """Precompute filter options for better performance."""
    options = {}

    # Precompute unique values for common filter columns
    filter_columns = [
        "ESPECIALISTA",
        "PROPRIETÁRIO",
        "MANTENEDOR",
        "RTM",
        "GARANTIA",
        "TIPO",
        "SERVIÇO",
        "MODELO",
    ]

    for col in filter_columns:
        if col in df.columns:
            options[col] = sorted(df[col].dropna().unique())

    # Precompute tags
    if "TAGS" in df.columns:
        todas_tags = set()
        for tags in df["TAGS"]:
            if isinstance(tags, list):
                todas_tags.update(tags)
        options["TAGS"] = sorted(todas_tags)

    return options
