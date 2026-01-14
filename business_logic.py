"""
Business logic module for Parque Instalado calculations.
Separates data processing from UI logic for better maintainability.
"""

import pandas as pd
import numpy as np
import streamlit as st
from datetime import timedelta
from typing import Dict, Set, List, Tuple

# Configuration constants
GARANTIA_PERIODS = {
    "6_MESES": 183,
    "12_MESES": 365,
    "18_MESES": 548,
    "24_MESES": 730,
    "36_MESES": 1095,
}

GARANTIA_ELETRONICA_DAYS = 365


def get_ss_for_chassis(
    chassis_list: List[str], chamados_dict: Dict[str, List[str]]
) -> Set[str]:
    """Get all SS numbers for a list of chassis."""
    ss_set = set()
    for chassi in chassis_list:
        if chassi in chamados_dict:
            ss_set.update(chamados_dict[chassi])
    return ss_set


def calculate_qtd_chamados(
    df: pd.DataFrame, chassi_counts_series: pd.Series
) -> pd.Series:
    """Centralized calculation for QTD_CHAMADOS."""
    return df["NUM_SERIAL"].map(chassi_counts_series).fillna(0).astype(int)


def create_duracao_garantia_column(garantia_series: pd.Series) -> pd.Series:
    """Create user-friendly warranty duration labels."""

    def map_garantia(x):
        # Handle NaN/None values first
        if pd.isna(x) or x == 0 or x == "":
            return "Não informado"
        # Convert to int for comparison
        try:
            val = int(float(x))
        except (ValueError, TypeError):
            return "Outros"

        if val == GARANTIA_PERIODS["6_MESES"]:
            return "6 meses (183 dias)"
        elif val == GARANTIA_PERIODS["12_MESES"]:
            return "12 meses (365 dias)"
        elif val == GARANTIA_PERIODS["18_MESES"]:
            return "18 meses (548 dias)"
        elif val == GARANTIA_PERIODS["24_MESES"]:
            return "24 meses (730 dias)"
        elif val == GARANTIA_PERIODS["36_MESES"]:
            return "36 meses (1095 dias)"
        else:
            return "Outros"

    return garantia_series.apply(map_garantia)


def determine_partida_inicial_status(
    num_serial: str, partida_set: Set[str], qtd_chamados: int
) -> str:
    """Determine partida inicial status based on business rules."""
    has_partida_inicial = num_serial in partida_set

    if has_partida_inicial:
        return "SIM - DFS"
    elif qtd_chamados > 0:
        return "SIM - TERCEIRO"
    else:
        return "NÃO"


def calculate_kpi_percentages(
    filtered_df: pd.DataFrame,
    partida_set: Set[str],
    chassi_counts_validos: pd.Series,
    chamados_garantia_chassis: Set[str],
) -> Dict[str, float]:
    """Calculate all KPI percentages in one place."""

    if len(filtered_df) == 0:
        return {
            key: 0.0
            for key in [
                "pct_com_partida_dfs",
                "pct_com_partida_terceiros",
                "pct_com_chamado",
                "pct_sem_chamado",
                "pct_rtm",
                "pct_em_garantia",
                "pct_fora_garantia",
            ]
        }

    total_bombas = len(filtered_df)
    chassis_filtros = filtered_df["NUM_SERIAL"].dropna().unique()

    # Partida DFS
    com_partida_dfs = pd.Series(chassis_filtros).isin(partida_set)
    pct_com_partida_dfs = 100 * com_partida_dfs.sum() / total_bombas

    # Partida Terceiros
    filtered_temp = filtered_df.copy()
    filtered_temp["QTD_CHAMADOS"] = calculate_qtd_chamados(
        filtered_temp, chassi_counts_validos
    )
    filtered_temp["PARTIDA_INICIAL"] = filtered_temp.apply(
        lambda row: determine_partida_inicial_status(
            row["NUM_SERIAL"], partida_set, row["QTD_CHAMADOS"]
        ),
        axis=1,
    )
    sim_terceiro_count = (filtered_temp["PARTIDA_INICIAL"] == "SIM - TERCEIRO").sum()
    pct_com_partida_terceiros = 100 * sim_terceiro_count / total_bombas

    # Chamados de garantia
    com_chamado_garantia = pd.Series(chassis_filtros).isin(chamados_garantia_chassis)
    pct_com_chamado = 100 * com_chamado_garantia.sum() / total_bombas
    pct_sem_chamado = 100 * (~com_chamado_garantia).sum() / total_bombas

    # RTM
    rtm_count = filtered_df[filtered_df["RTM"] == "SIM"]["NUM_SERIAL"].nunique()
    pct_rtm = 100 * rtm_count / total_bombas

    # Garantia status
    em_garantia_count = filtered_df[filtered_df["STATUS_GARANTIA"] == "DENTRO"][
        "NUM_SERIAL"
    ].nunique()
    pct_em_garantia = 100 * em_garantia_count / total_bombas

    fora_garantia_count = filtered_df[filtered_df["STATUS_GARANTIA"] == "FORA"][
        "NUM_SERIAL"
    ].nunique()
    pct_fora_garantia = 100 * fora_garantia_count / total_bombas

    return {
        "pct_com_partida_dfs": pct_com_partida_dfs,
        "pct_com_partida_terceiros": pct_com_partida_terceiros,
        "pct_com_chamado": pct_com_chamado,
        "pct_sem_chamado": pct_sem_chamado,
        "pct_rtm": pct_rtm,
        "pct_em_garantia": pct_em_garantia,
        "pct_fora_garantia": pct_fora_garantia,
    }


def calculate_garantia_distribution(df: pd.DataFrame) -> Dict[str, float]:
    """Calculate warranty period distribution with error handling."""
    try:
        if "GARANTIA" not in df.columns or len(df) == 0:
            return {
                key: 0.0
                for key in ["pct_6m", "pct_12m", "pct_18m", "pct_24m", "pct_36m"]
            }

        garantia_numerica = pd.to_numeric(df["GARANTIA"], errors="coerce")
        total_valido = garantia_numerica.notna().sum()

        if total_valido == 0:
            return {
                key: 0.0
                for key in ["pct_6m", "pct_12m", "pct_18m", "pct_24m", "pct_36m"]
            }

        # Count by warranty periods
        qtd_6m = (garantia_numerica == GARANTIA_PERIODS["6_MESES"]).sum()
        qtd_12m = (garantia_numerica == GARANTIA_PERIODS["12_MESES"]).sum()
        qtd_18m = (garantia_numerica == GARANTIA_PERIODS["18_MESES"]).sum()
        qtd_24m = (garantia_numerica == GARANTIA_PERIODS["24_MESES"]).sum()
        qtd_36m = (garantia_numerica == GARANTIA_PERIODS["36_MESES"]).sum()

        return {
            "pct_6m": 100 * qtd_6m / total_valido,
            "pct_12m": 100 * qtd_12m / total_valido,
            "pct_18m": 100 * qtd_18m / total_valido,
            "pct_24m": 100 * qtd_24m / total_valido,
            "pct_36m": 100 * qtd_36m / total_valido,
        }
    except Exception as e:
        st.error(f"⚠️ Erro ao calcular distribuição de garantias: {str(e)}")
        return {
            key: 0.0 for key in ["pct_6m", "pct_12m", "pct_18m", "pct_24m", "pct_36m"]
        }


def calculate_rtm_values(erros_rtm_df: pd.DataFrame) -> Dict[str, float]:
    """Calculate RTM value metrics with error handling."""
    try:
        if len(erros_rtm_df) == 0:
            return {
                "media_valor_total": 0.0,
                "media_valor_peca": 0.0,
                "soma_valor_total": 0.0,
                "soma_valor_peca": 0.0,
            }

        # Ensure numeric columns for calculations
        df_copy = erros_rtm_df.copy()
        df_copy["VALOR_TOTAL"] = pd.to_numeric(df_copy["VALOR_TOTAL"], errors="coerce")
        df_copy["VALOR_PECA"] = pd.to_numeric(df_copy["VALOR_PECA"], errors="coerce")

        media_valor_total = df_copy["VALOR_TOTAL"].mean()
        media_valor_peca = df_copy["VALOR_PECA"].mean()
        soma_valor_total = df_copy["VALOR_TOTAL"].sum()
        soma_valor_peca = df_copy["VALOR_PECA"].sum()

        # Handle NaN values
        return {
            "media_valor_total": media_valor_total
            if pd.notna(media_valor_total)
            else 0.0,
            "media_valor_peca": media_valor_peca if pd.notna(media_valor_peca) else 0.0,
            "soma_valor_total": soma_valor_total if pd.notna(soma_valor_total) else 0.0,
            "soma_valor_peca": soma_valor_peca if pd.notna(soma_valor_peca) else 0.0,
        }
    except Exception as e:
        st.error(f"⚠️ Erro ao calcular valores RTM: {str(e)}")
        return {
            "media_valor_total": 0.0,
            "media_valor_peca": 0.0,
            "soma_valor_total": 0.0,
            "soma_valor_peca": 0.0,
        }


def add_garantia_eletronica_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add electronic warranty columns to dataframe."""
    df_copy = df.copy()
    df_copy["GARANTIA_ELETRONICA"] = GARANTIA_ELETRONICA_DAYS
    df_copy["FIM_GARAN_ELETRICA"] = pd.to_datetime(
        df_copy["DT_NUM_NF"], errors="coerce"
    ) + timedelta(days=GARANTIA_ELETRONICA_DAYS)
    df_copy["FIM_GARAN_ELETRICA"] = df_copy["FIM_GARAN_ELETRICA"].dt.strftime(
        "%d/%m/%Y"
    )

    hoje = pd.Timestamp.now().normalize()
    fim_garan_eletrica_dt = pd.to_datetime(
        df_copy["FIM_GARAN_ELETRICA"], format="%d/%m/%Y", errors="coerce"
    )
    df_copy["STATUS_GARAN_ELETRICA"] = [
        "DENTRO" if (pd.notnull(fim) and hoje <= fim) else "FORA"
        for fim in fim_garan_eletrica_dt
    ]

    return df_copy
