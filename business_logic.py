"""
Business logic module for Parque Instalado calculations.
Separates data processing from UI logic for better maintainability.
"""

import pandas as pd
import numpy as np
import streamlit as st
from datetime import timedelta
from typing import Dict, Set, List

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

    # Maximum reasonable warranty period (10 years = ~3650 days)
    MAX_WARRANTY_DAYS = 3650

    def map_garantia(x):
        # Handle NaN/None values first
        if pd.isna(x) or x == 0 or x == "":
            return "Não informado"
        # Convert to int for comparison with bounds checking
        try:
            float_val = float(x)
            # Handle special float values (inf, -inf, nan)
            if not np.isfinite(float_val):
                return "Outros"
            # Handle negative values and unreasonably large values
            if float_val < 0 or float_val > MAX_WARRANTY_DAYS:
                return "Outros"
            val = int(float_val)
        except (ValueError, TypeError, OverflowError):
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


def calculate_rtm_analysis_by_year(
    o2c_df: pd.DataFrame,
    chamados_df: pd.DataFrame,
    erros_rtm_df: pd.DataFrame,
    rtm_filter: str,  # "SIM" or "NAO"
) -> pd.DataFrame:
    """
    Calculate RTM analysis metrics by year for comparative analysis.

    Returns a DataFrame with metrics per year:
    - Units Sales
    - Start up DFS %
    - % Chassis with tickets
    - % Chassis Under Warranty
    - % Chassis Under Electronic Warranty
    - % Chassis Error RTM Ticket
    """
    hoje = pd.Timestamp.now().normalize()

    # Filter by RTM
    df = o2c_df[o2c_df["RTM"] == rtm_filter].copy()

    if len(df) == 0:
        return pd.DataFrame()

    # Ensure ANO_NF exists
    if "ANO_NF" not in df.columns:
        df["ANO_NF"] = pd.to_datetime(df["DT_NUM_NF"], errors="coerce").dt.year

    # Get unique years
    anos = sorted(df["ANO_NF"].dropna().unique())

    # Prepare chamados data
    chamados_clean = chamados_df.copy()
    chamados_clean.columns = chamados_clean.columns.str.strip().str.upper()

    # Identify partida inicial and warranty calls (convert to string for matching)
    partida_mask = chamados_clean["SERVIÇO"].str.contains("PARTIDA INICIAL", na=False)
    partida_set = set(chamados_clean[partida_mask]["CHASSI"].dropna().astype(str))

    # All chassis with any call (excluding STB)
    chamados_validos = chamados_clean[
        ~chamados_clean["SUMÁRIO"].str.contains(r"\[STB\]", case=False, na=False)
    ]
    chassis_com_chamado = set(
        chamados_validos[~chamados_validos["SERVIÇO"].str.contains("PARTIDA INICIAL", na=False)]["CHASSI"].dropna().astype(str)
    )

    # Chassis with RTM errors (convert SS to string for matching)
    erros_rtm_ss = set(erros_rtm_df["SS"].astype(str).str.strip())
    chamados_com_erro = chamados_clean[chamados_clean["SS"].astype(str).str.strip().isin(erros_rtm_ss)]
    chassis_com_erro_rtm = set(chamados_com_erro["CHASSI"].dropna().astype(str))

    results = []

    for ano in anos:
        df_ano = df[df["ANO_NF"] == ano].drop_duplicates(subset=["NUM_SERIAL"])
        chassis_ano = set(df_ano["NUM_SERIAL"].dropna().astype(str))
        total = len(chassis_ano)

        if total == 0:
            continue

        # Units Sales
        units_sales = total

        # Start up DFS %
        com_partida_dfs = len(chassis_ano & partida_set)
        pct_startup_dfs = 100 * com_partida_dfs / total

        # % Chassis with tickets (excluding partida inicial)
        com_chamado = len(chassis_ano & chassis_com_chamado)
        pct_com_chamado = 100 * com_chamado / total

        # % Chassis Under Warranty
        df_ano_garantia = df_ano[df_ano["STATUS_GARANTIA"] == "DENTRO"]
        pct_under_warranty = 100 * len(df_ano_garantia) / total

        # % Chassis Under Electronic Warranty
        # Calculate electronic warranty status
        fim_garan_eletr = pd.to_datetime(df_ano["DT_NUM_NF"], errors="coerce") + timedelta(days=GARANTIA_ELETRONICA_DAYS)
        dentro_eletr = (fim_garan_eletr >= hoje).sum()
        pct_under_eletr_warranty = 100 * dentro_eletr / total

        # % Chassis Error RTM Ticket
        com_erro_rtm = len(chassis_ano & chassis_com_erro_rtm)
        pct_erro_rtm = 100 * com_erro_rtm / total

        results.append({
            "Ano": int(ano),
            "Units Sales": units_sales,
            "Start up DFS": pct_startup_dfs,
            "% Chassis with tickets": pct_com_chamado,
            "% Chassis Under Warranty": pct_under_warranty,
            "% Chassis Under Electronic Warranty": pct_under_eletr_warranty,
            "% Chassis Error RTM Ticket": pct_erro_rtm,
        })

    # Add Total column
    if results:
        df_total = df.drop_duplicates(subset=["NUM_SERIAL"])
        chassis_total = set(df_total["NUM_SERIAL"].dropna().astype(str))
        total_all = len(chassis_total)

        if total_all > 0:
            com_partida_total = len(chassis_total & partida_set)
            com_chamado_total = len(chassis_total & chassis_com_chamado)
            com_erro_rtm_total = len(chassis_total & chassis_com_erro_rtm)

            dentro_garantia_total = len(df_total[df_total["STATUS_GARANTIA"] == "DENTRO"])

            fim_garan_eletr_total = pd.to_datetime(df_total["DT_NUM_NF"], errors="coerce") + timedelta(days=GARANTIA_ELETRONICA_DAYS)
            dentro_eletr_total = (fim_garan_eletr_total >= hoje).sum()

            results.append({
                "Ano": "Total",
                "Units Sales": total_all,
                "Start up DFS": 100 * com_partida_total / total_all,
                "% Chassis with tickets": 100 * com_chamado_total / total_all,
                "% Chassis Under Warranty": 100 * dentro_garantia_total / total_all,
                "% Chassis Under Electronic Warranty": 100 * dentro_eletr_total / total_all,
                "% Chassis Error RTM Ticket": 100 * com_erro_rtm_total / total_all,
            })

    return pd.DataFrame(results)


def get_rtm_summary_metrics(
    o2c_df: pd.DataFrame,
    chamados_df: pd.DataFrame,
    rtm_filter: str,
) -> Dict[str, any]:
    """
    Get summary metrics for RTM analysis.
    """
    hoje = pd.Timestamp.now().normalize()

    df = o2c_df[o2c_df["RTM"] == rtm_filter].drop_duplicates(subset=["NUM_SERIAL"]).copy()

    if len(df) == 0:
        return {
            "total_units": 0,
            "chassis_36m_warranty": 0,
            "chassis_under_electronic_warranty": 0,
            "installed_base_known": 0,
        }

    # Total units sold
    total_units = len(df)

    # Chassis with 36 months warranty still active
    df_36m = df[df["GARANTIA"] == GARANTIA_PERIODS["36_MESES"]]
    chassis_36m_dentro = len(df_36m[df_36m["STATUS_GARANTIA"] == "DENTRO"])

    # Chassis under electronic warranty
    fim_garan_eletr = pd.to_datetime(df["DT_NUM_NF"], errors="coerce") + timedelta(days=GARANTIA_ELETRONICA_DAYS)
    chassis_eletr_dentro = (fim_garan_eletr >= hoje).sum()

    # Installed base known by DFS (chassis with any call)
    chamados_clean = chamados_df.copy()
    chamados_clean.columns = chamados_clean.columns.str.strip().str.upper()
    chassis_com_chamado = set(chamados_clean["CHASSI"].dropna())
    installed_base = len(set(df["NUM_SERIAL"]) & chassis_com_chamado)

    return {
        "total_units": total_units,
        "chassis_36m_warranty": chassis_36m_dentro,
        "chassis_under_electronic_warranty": int(chassis_eletr_dentro),
        "installed_base_known": installed_base,
    }
