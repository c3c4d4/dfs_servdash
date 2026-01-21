import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List
import streamlit as st
from functools import lru_cache
import warnings
import logging

warnings.filterwarnings("ignore")

# Configure logging for data validation
logger = logging.getLogger(__name__)


# =============================================================================
# DATA VALIDATION LAYER
# =============================================================================
class DataValidationError(Exception):
    """Exception raised when data validation fails."""

    pass


def validate_dataframe(
    df: pd.DataFrame,
    required_columns: List[str],
    df_name: str = "DataFrame"
) -> bool:
    """
    Validate that a DataFrame contains required columns.

    Args:
        df: DataFrame to validate
        required_columns: List of column names that must be present
        df_name: Name for error messages

    Returns:
        True if validation passes

    Raises:
        DataValidationError: If required columns are missing
    """
    if df is None or df.empty:
        logger.warning(f"{df_name} is empty or None")
        return True  # Allow empty dataframes, just warn

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        error_msg = f"{df_name} missing required columns: {missing}"
        logger.error(error_msg)
        raise DataValidationError(error_msg)

    return True


def validate_chamados_df(df: pd.DataFrame) -> bool:
    """Validate chamados DataFrame structure."""
    required = ["SS", "Tarefa", "Status", "Chassi"]
    return validate_dataframe(df, required, "Chamados")


def validate_o2c_df(df: pd.DataFrame) -> bool:
    """Validate O2C DataFrame structure."""
    required = ["NUM_SERIAL", "GARANTIA"]
    return validate_dataframe(df, required, "O2C")


def validate_rtm_errors_df(df: pd.DataFrame) -> bool:
    """Validate RTM errors DataFrame structure."""
    required = ["SS"]
    return validate_dataframe(df, required, "RTM Errors")


# Optimized data loading with caching
@st.cache_data(ttl=3600, show_spinner=False)
def carregar_dados(filepath: str = "chamados.csv") -> pd.DataFrame:
    """Load and preprocess the chamados data from CSV with optimizations."""
    # Use optimized CSV reading
    df = pd.read_csv(
        filepath,
        sep=";",
        encoding="utf-8",
        dtype={
            "SS": "string",
            "Tarefa": "string",
            "Chassi": "string",
            "Série": "string",
            "Proprietário": "string",
            "Mantenedor": "string",
            "Tipo": "string",
            "Serviço": "string",
            "Problema": "string",
            "Resolução": "string",
            "Cliente": "string",
            "Status": "string",
            "RTM": "string",
        },
        parse_dates=["Data", "Resolvido"],
        dayfirst=True,
        cache_dates=True,
    )

    # Optimize string operations
    df["Chassi"] = (
        df["Chassi"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.replace(".0", "", regex=False)
        .replace("", "N/A")
    )
    df["RTM"] = (
        df["RTM"]
        .str.upper()
        .str.contains("RTM", na=False)
        .map({True: "SIM", False: "NÃO"})
    )

    return df


@st.cache_data(ttl=3600, show_spinner=False)
def carregar_dados_merged(
    filepath1: str = "chamados.csv", filepath2: str = "chamados_fechados.csv"
) -> pd.DataFrame:
    """Load, merge, and preprocess chamados and chamados_fechados data with optimizations."""

    # Load data with optimized dtypes
    dtype_dict = {
        "SS": "string",
        "Tarefa": "string",
        "Chassi": "string",
        "Série": "string",
        "Proprietário": "string",
        "Mantenedor": "string",
        "Tipo": "string",
        "Serviço": "string",
        "Problema": "string",
        "Resolução": "string",
        "Cliente": "string",
        "Status": "string",
        "RTM": "string",
        "Sumário": "string",
    }

    df1 = pd.read_csv(filepath1, sep=";", encoding="utf-8", dtype=dtype_dict)
    df2 = pd.read_csv(filepath2, sep=";", encoding="utf-8", dtype=dtype_dict)

    # Optimize column operations
    for df in [df1, df2]:
        df.columns = df.columns.str.strip()
        # Vectorized string operations
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].str.strip()

    # Align columns efficiently
    common_cols = df1.columns.intersection(df2.columns)
    df2 = df2[common_cols]
    df1 = df1[common_cols]

    df = pd.concat([df1, df2], ignore_index=True)

    # Optimize datetime parsing
    for col in ["Data", "Resolvido"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")

    # Optimize string operations
    df["Chassi"] = (
        df["Chassi"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.replace(".0", "", regex=False)
        .replace("", "N/A")
    )
    df["RTM"] = (
        df["RTM"]
        .str.upper()
        .str.contains("RTM", na=False)
        .map({True: "SIM", False: "NÃO"})
    )

    # Efficient deduplication
    if all(col in df.columns for col in ["Data", "SS", "Tarefa"]):
        df = df.sort_values("Data", ascending=False).drop_duplicates(
            subset=["SS", "Tarefa"], keep="first"
        )

    return df.reset_index(drop=True)


@st.cache_data(ttl=3600, show_spinner=False)
def carregar_o2c(filepath: str = "o2c_unpacked.csv") -> pd.DataFrame:
    """Load O2C data with optimizations."""

    # Define columns to keep to reduce memory usage
    cols_to_keep = [
        "Serial",
        "NUM_SERIAL",
        "RTM",
        "GARANTIA",
        "UF",
        "CIDADE",
        "ESTADO",
        "PAIS",
        "NOME_PAIS",
        "DT_NUM_NF",
        "ITEM",
        "MODELO",
        "SÉRIE",
        "SERIE",
        "NUM_SERIE",
        "CLIENTE",
        "DURAÇÃO_GARANTIA",
        "DURACAO_GARANTIA",
    ]

    # Helper to check if column should be loaded (case insensitive)
    def column_filter(col):
        return col.strip() in cols_to_keep or col.strip().upper() in cols_to_keep

    dtype_dict = {
        "Serial": "string",
        "RTM": "string",
        "GARANTIA": "string",
        "UF": "string",
        "CIDADE": "string",
        "ESTADO": "string",
        "PAIS": "string",
        "NOME_PAIS": "string",
        "CLIENTE": "string",
        "ITEM": "string",
        "MODELO": "string",
    }

    try:
        df = pd.read_csv(
            filepath,
            sep=";",
            encoding="utf-8-sig",
            dtype=dtype_dict,
            parse_dates=["DT_NUM_NF"],
            dayfirst=True,
            cache_dates=True,
            usecols=column_filter,
            engine="c",  # Ensure C engine is used for performance
            low_memory=True,
        )
    except ValueError:
        # Fallback if usecols fails (e.g. none of the columns found, unlikely but possible)
        df = pd.read_csv(
            filepath,
            sep=";",
            encoding="utf-8-sig",
            dtype=dtype_dict,
            parse_dates=["DT_NUM_NF"],
            dayfirst=True,
            cache_dates=True,
        )

    # Rename Serial to NUM_SERIAL for compatibility with dashboard
    if "Serial" in df.columns:
        df = df.rename(columns={"Serial": "NUM_SERIAL"})

    # Optimize string operations
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].str.strip().str.upper()

    # Ensure GARANTIA has no NA values for comparisons
    if "GARANTIA" in df.columns:
        df["GARANTIA"] = (
            pd.to_numeric(df["GARANTIA"], errors="coerce").fillna(0).astype(int)
        )

    return df


@st.cache_data(ttl=3600, show_spinner=False)
def carregar_base_erros_rtm():
    """Load RTM errors base with optimizations."""
    try:
        df = pd.read_csv("BASE_ERROS_RTM.csv", sep=";", encoding="utf-8")

        # Remove duplicates from the source data
        df = df.drop_duplicates()

        # Clean and standardize text columns
        for col in ["TIPO_ERRO", "DESC_ERRO", "CÓD_ERRO", "DETALHES_ERRO"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper()

        # Optimize dtypes
        for col in ["SS", "TIPO_ERRO", "DESC_ERRO", "CÓD_ERRO", "DETALHES_ERRO"]:
            if col in df.columns:
                df[col] = df[col].astype("category")

        # Convert numeric columns
        for col in ["VALOR_PECA", "VALOR_TOTAL"]:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].str.replace(",", "."), errors="coerce"
                ).fillna(0)

        return df
    except Exception as e:
        st.error(f"Erro ao carregar BASE_ERROS_RTM.csv: {str(e)}")
        return pd.DataFrame()


# Optimized mapping dictionaries with case-insensitive lookup
@lru_cache(maxsize=1)
def get_mapping_dicts() -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    """Get cached mapping dictionaries for better performance."""

    de_para_proprietario: Dict[str, str] = {
        "OLIVEIRA, CASSIO FONSECA FARIAS DE (CASSIO)": "CÁSSIO OLIVEIRA",
        "SIMÕES, WANDERLEY": "WANDERLEY SIMÕES",
        "SANTOS DE LIMA, ANTÔNIO VINICIUS DOS (ANTÔNIO VINICIUS DOS SANTOS DE LIMA)": "ANTÔNIO DOS SANTOS",
        "NOGUEIRA, VICTOR M": "VICTOR NOGUEIRA",
        "QUIRINO, RICARDO": "RICARDO QUIRINO",
        "FERREIRA DE ARAUJO, JOSE ROBERTO": "JOSÉ ROBERTO",
        "LUCAS, JEFFERSON MONTEIRO DA SILVA": "JEFFERSON LUCAS",
        "SILVA, MÁRCIO (CONTRACTOR) (MÁRCIO (CONTRACTOR) SILVA)": "MÁRCIO SILVA",
        "LONGO, DANTE M (DANTE M. LONGO)": "DANTE LONGO",
        "DOS SANTOS, OTACÍLIO (CONTRACTOR) (OTACÍLIO (CONTRACTOR) DOS SANTOS)": "OTACÍLIO DOS SANTOS",
        "DE FREITAS, FABIO (CONTRACTOR) (FABIO (CONTRACTOR) DE FREITAS)": "FÁBIO DE FREITAS",
        "ARAUJO, ALESSANDRO FABIANO DE": "ALESSANDRO ARAUJO",
        "CALADO, MARCOS AURELIO CAVALCANTI": "MARCOS CALADO",
        "BRAGA, PEDRO XAVIER": "PEDRO BRAGA",
        "OLIVEIRA, LUCAS F": "LUCAS OLIVEIRA",
        "SILVA, RAFAEL DOUGLAS DIAS DA": "RAFAEL SILVA",
        "SILVA, ROBERTO FERNANDES": "ROBERTO SILVA",
        "SILVA, RODRIGO JOSE BUSSOLARO": "RODRIGO SILVA",
        "SOBRINHO, LUAN B": "LUAN SOBRINHO",
    }

    de_para_mantenedor: Dict[str, str] = {
        "MACIEL, FONTES FRANJAKSON - NTEC INSTALACOES HIDRAULICAS LTDA.": "NTEC",
        "SALES, LUIZ - SOCIEDADE DE MANUTENCAO TECNICA SOMATEC LTDA": "SOMATEC",
        "HENRIQUE, THIAGO - CM2 COMERCIO E SERVICOS LTDA EPP": "CM2",
        "EVANDRO, - FLOTECK COMERCIO E SERVICOS ESPECIALIZADOS LTDA": "FLOTECK",
        "RIGOBERTO, FRANCISCO - F R RIBEIRO MECANICA SAO CRISTOVAO SERVICOS ELETRONICOS LTDA": "MEC. SÃO CRISTÓVÃO",
        "ESDRAS ARR, - E PASCOAL COM SERV E ASSIST TE": "PASCOAL",
        "SALES, - S L INSTALACAO P POSTOS DE SE": "SL INSTALAÇÃO",
        "NEVES, - TEKSUL MANUTENÇÃO DE BOMBAS PARA COMBUSTÍVEL EIRELI": "TEKSUL",
        "MOURA, ALEXSANDRE - ALEXSANDRE LIZ DE MOURA": "BOMBAGAS",
        "JESSICA, THAINA - THAINA JESSICA DA COSTA RODRIGUES": "PETROPOSTO",
        "SERGIO, - SERVTEC COMERCIO E SERVICO LTD": "SERVTEC",
        "SALES, LUIZ - TECNICA L S COMERCIAL E SERVI": "TECNICA LS",
        "PINTO, ANDREZA - C A INSTALACAO E MANUTENCAO EM POSTOS DE COMBUSTIVEIS LTDA": "C A INSTALAÇÃO",
        "LUCIANA, - ATENDE COMERCIO DE PECAS E CON": "ATENDE",
        "SILVA, REGINALD - SHEKINAH SHADDAI MANUTENCAO LTD": "SHEKINAH",
        "SRA.FERNAN, - FORTE INSTALACAO E MANUTENCAO": "FORTE",
        "FREITAS, LUCIANO - BHPUMP DO BRASIL LTDA": "BHPUMP",
        "SANTOS, VANDERLEY - VANDERLEY PEREIRA DOS SANTOS": "PETROLINK",
        "FAVERO, PAULA - CENTURY FLEX COMERCIO DE PECAS PARA BOMBAS DE COMBUSTIVEIS LTDA": "CENTURY",
        "ROCHA, ROBERTO - SIGNOS MRWG MANUTENCAO LTDA ME": "SIGNOS",
        "GONZAGA, MANOEL - LMG COMERCIO SERVICOS E MANUTENCAO LTDA": "LMG",
        "MENDES, ANDRE - M E A SILVA MENDES MANUTENCAO E REPARACAO ME": "MERIVA",
        "CAMPOS, SANDREIA - CONSTRUTORA CENTAURUS DO BRASIL LTDA": "CENTAURUS",
        "UNKNOWN, CASSIA - ARBTEK SOLUCOES INTEGRADAS LTDA": "ARBTEK",
        "COSTA, GUSTAVO - CONSERTEC BALANCAS E BOMBAS LTDA ME": "CONSERTEC",
        "JUNIOR, LUIZ ZORZI - ZORZITEC CONSULTORIA EIRELI ME": "ZORZITEC",
        "MENEZES SOARES, ALTEVIR - JUMPER SERVICOS TECNICOS DE BOMBAS DE COMBUSTIVEIS LTDA": "JUMPER",
        "DE MATTOS, PERI JACI - MULTITEC SOLUCOES EM POSTOS AUTOMOTIVOS LTDA": "MULTITEC",
        "., ROMARIO - DINIZ ASSISTENCIA TECNICA LTDA": "DINIZ",
        "SERAFIM, JOAO - JS DE SOUSA MANUTENCAO ME": "JS MANUTENÇÃO",
        "SILVA, RODRIGO - EBENEZER COMECIO E MANUTENCAO": "EBENEZER",
        "NETO, JORGE - EWJ INSTALACAO E MANUTENCAO DE EQUIPAMENTOS PARA POSTOS DE COMBUSTIVEIS LTDA": "EWJ",
        "AMORIM DE OLIVE, LEONORA - L DE ALMEIDA FERREIRA LTDA": "NOVA ERA",
        "RAMOS, CARLOS - MECANICA DE BOMBAS RAMOS LTDA": "MEC. BOMBAS RAMOS",
        "COSTA, HELIO - REAL MANUTENCAO E INSTALACAO EM POSTOS E SERVICOS LTDA": "REAL MANUTENÇÃO",
        "ANTONIO, - A DE JESUS E SOUZA DOURADO LTD": "FUTURA",
        "RODRIGUES, RIVALDO - SMR MANUTENCAO E REPARACAO EIRELI ME": "SMR",
        "AMARO, FLORISVALDO - SERVITEC - MANUTENCAO E INSTALACAO DE EQUIPAMENTOS EM POSTOS DE COMBUSTIVEIS LTDA": "SERVITEC",
        "SR. LAZARO, - LAZARO MARTINS SILVA SOUZA ME": "LÁZARO",
        "BELARMINO, MARCOS - SOS SYSTEM TECNOLOGIA EM INFORMATICA LTDA": "SOS SYSTEM",
        "DO MONTE, CARLOS JORGE - PERMANENTE MANUTENCAO DE MAQUINAS E EQUIPAMENTOS EIRELI": "PERMANENTE",
        "MENDES, - IMASEL LTDA": "IMASEL",
        "ANDRADE, JAIR - JMA PRESTADORA DE SERVICOS LTDA": "JMA",
        "ANDREZA, - UBERPOSTOS LOGISTICA E EQUIP": "UBERPOSTOS",
        "LUZENILDO, - DANTEC ASSITENCIA TECNICA LTDA": "DANTEC",
        "SANTANA, DORLAN - TECHPETRO SOLUCOES SERVICOS DE MANUTENCAO LTDA": "TECHPETRO",
        "SOARES, ALTEVIR - JUMPER MATERIAIS E SERVICOS PARA POSTOS DE COMBUSTIVEIS EIRELI ME": "JUMPER",
        "., RIBAMAR - CENTURY COM E ASSIST TECNICA EM POSTO DE COMBUSTIVEL LTDA": "CENTURY COM E ASSIST",
        "ALIPIO CRUZ, HELENO - H A CRUZ TECNOLOGIA LTDA": "H A CRUZ TECNOLOGIA",
        "CAMPOS, PATRÍCIA - PETROPOSTO COMERCIO E SERVICO LTDA": "PETROPOSTO",
        "DOS SANTOS, GIVONI NATASHA - ATLAS COMERCIO DE MATERIAL ELETRICO E SERVICOS DE INSTALACAO LTDA": "ATLAS COMERCIO",
        "DRESSER INDSTRI, - WAYNE BRASIL DRESSER IND E COM LTDA": "WAYNE BRASIL DRESSER",
        "FERREIRA, RONDINEL - RONDINEL FERREIRA DE SANTANA": "RONDINEL FERREIRA",
        "FERNANDES, ALECIO - UBERPOSTOS INSTALACOES EM POSTOS DE COMBUSTIVEIS LTDA.": "UBERPOSTOS",
        "JAOA, - JI SOLUCOES LTD EPP": "JI SOLUCOES",
        "LACERDA, IVAN - SOFT POSTOS LTDA": "SOFT POSTOS",
        "LEONARDO, - UBERPOSTOS LOGISTICA E EQUIP": "UBERPOSTOS",
        "LUCAS/ANDR, - UBERPOSTOS INSTALACOES EM POSTOS DE COMBUSTIVEIS LTDA": "UBERPOSTOS",
        "MORAES, BRUNO - MOTORVAC EQUIPAMENTOS HIDRAULICOS E MECANICOS LTDA": "MOTORVAC",
        "MOURA, JAIMERSON - J C MOURA ME": "J C MOURA",
        "SANTOS, ABRAHAM - MANOEL GONZAGA DOS SANTOS": "MANOEL GONZAGA",
        "SILVA, RODRIGO - TECNO PUMP COMERCIO DE PECAS PBOMBAS COMBUSTIVEL LTDA - ME": "TECNO PUMP",
        "SALES, - UBERPOSTOS LOGISTICA E EQUIP": "UBERPOSTOS",
    }

    de_para_especialista: Dict[str, str] = {
        "PINTO, ANDREZA - C A INSTALACAO E MANUTENCAO EM POSTOS DE COMBUSTIVEIS LTDA": "LUCAS",
        "MACIEL, FONTES FRANJAKSON - NTEC INSTALACOES HIDRAULICAS LTDA.": "LUCIANO",
        "SALES, - S L INSTALACAO P POSTOS DE SE": "LUCAS",
        "SALES, LUIZ - TECNICA L S COMERCIAL E SERVI": "LUCAS",
        "GONZAGA, MANOEL - LMG COMERCIO SERVICOS E MANUTENCAO LTDA": "LUCIANO",
        "MOURA, ALEXSANDRE - ALEXSANDRE LIZ DE MOURA": "LUCAS",
        "NEVES, - TEKSUL MANUTENÇÃO DE BOMBAS PARA COMBUSTÍVEL EIRELI": "LUCAS",
        "SERAFIM, JOAO - JS DE SOUSA MANUTENCAO ME": "LUCIANO",
        "RIGOBERTO, FRANCISCO - F R RIBEIRO MECANICA SAO CRISTOVAO SERVICOS ELETRONICOS LTDA": "LUCIANO",
        "ANDREZA, - UBERPOSTOS LOGISTICA E EQUIP": "LUCAS",
        "ANTONIO, - A DE JESUS E SOUZA DOURADO LTD": "LUCIANO",
        "SILVA, REGINALD - SHEKINAH SHADDAI MANUTENCAO LTD": "LUCIANO",
        "RAMOS, CARLOS - MECANICA DE BOMBAS RAMOS LTDA": "LUCAS",
        "AMARO, FLORISVALDO - SERVITEC - MANUTENCAO E INSTALACAO DE EQUIPAMENTOS EM POSTOS DE COMBUSTIVEIS LTDA": "ALESSANDRO",
        "MENDES, ANDRE - M E A SILVA MENDES MANUTENCAO E REPARACAO ME": "LUCAS",
        "SALES, - UBERPOSTOS LOGISTICA E EQUIP": "ALESSANDRO",
        "LUCIANA, - ATENDE COMERCIO DE PECAS E CON": "LUCIANO",
        "AMORIM DE OLIVE, LEONORA - L DE ALMEIDA FERREIRA LTDA": "LUCIANO",
        "HENRIQUE, THIAGO - CM2 COMERCIO E SERVICOS LTDA EPP": "LUCAS",
        "SRA.FERNAN, - FORTE INSTALACAO E MANUTENCAO": "LUCIANO",
        "JESSICA, THAINA - THAINA JESSICA DA COSTA RODRIGUES": "LUCIANO",
        "FREITAS, LUCIANO - BHPUMP DO BRASIL LTDA": "ALESSANDRO",
        "SANTOS, VANDERLEY - VANDERLEY PEREIRA DOS SANTOS": "ALESSANDRO",
        "SILVA, RODRIGO - EBENEZER COMECIO E MANUTENCAO": "LUCAS",
        "SERGIO, - SERVTEC COMERCIO E SERVICO LTD": "LUCIANO",
        "., ROMARIO - DINIZ ASSISTENCIA TECNICA LTDA": "LUCAS",
        "UNKNOWN, CASSIA - ARBTEK SOLUCOES INTEGRADAS LTDA": "LUCAS",
        "SALES, LUIZ - SOCIEDADE DE MANUTENCAO TECNICA SOMATEC LTDA": "ALESSANDRO",
        "RODRIGUES, RIVALDO - SMR MANUTENCAO E REPARACAO EIRELI ME": "LUCIANO",
        "MENDES, - IMASEL LTDA": "LUCIANO",
        "ESDRAS ARR, - E PASCOAL COM SERV E ASSIST TE": "LUCIANO",
        "ROCHA, ROBERTO - SIGNOS MRWG MANUTENCAO LTDA ME": "ALESSANDRO",
        "DE MATTOS, PERI JACI - MULTITEC SOLUCOES EM POSTOS AUTOMOTIVOS LTDA": "LUCAS",
        "COSTA, GUSTAVO - CONSERTEC BALANCAS E BOMBAS LTDA ME": "ALESSANDRO",
        "SR. LAZARO, - LAZARO MARTINS SILVA SOUZA ME": "LUCAS",
        "COSTA, HELIO - REAL MANUTENCAO E INSTALACAO EM POSTOS E SERVICOS LTDA": "LUCIANO",
        "NETO, JORGE - EWJ INSTALACAO E MANUTENCAO DE EQUIPAMENTOS PARA POSTOS DE COMBUSTIVEIS LTDA": "LUCIANO",
        "CAMPOS, SANDREIA - CONSTRUTORA CENTAURUS DO BRASIL LTDA": "LUCIANO",
        "JUNIOR, LUIZ ZORZI - ZORZITEC CONSULTORIA EIRELI ME": "LUCAS",
        "MENEZES SOARES, ALTEVIR - JUMPER SERVICOS TECNICOS DE BOMBAS DE COMBUSTIVEIS LTDA": "LUCIANO",
        "DO MONTE, CARLOS JORGE - PERMANENTE MANUTENCAO DE MAQUINAS E EQUIPAMENTOS EIRELI": "LUCIANO",
        "ANDRADE, JAIR - JMA PRESTADORA DE SERVICOS LTDA": "LUCAS",
        "BELARMINO, MARCOS - SOS SYSTEM TECNOLOGIA EM INFORMATICA LTDA": "LUCAS",
        "EVANDRO, - FLOTECK COMERCIO E SERVICOS ESPECIALIZADOS LTDA": "LUCAS",
        "FAVERO, PAULA - CENTURY FLEX COMERCIO DE PECAS PARA BOMBAS DE COMBUSTIVEIS LTDA": "LUCAS",
        "LUZENILDO, - DANTEC ASSITENCIA TECNICA LTDA": "LUCIANO",
        "SANTANA, DORLAN - TECHPETRO SOLUCOES SERVICOS DE MANUTENCAO LTDA": "LUCIANO",
        "SOARES, ALTEVIR - JUMPER MATERIAIS E SERVICOS PARA POSTOS DE COMBUSTIVEIS EIRELI ME": "LUCIANO",
        "., RIBAMAR - CENTURY COM E ASSIST TECNICA EM POSTO DE COMBUSTIVEL LTDA": "TBD",
        "ALIPIO CRUZ, HELENO - H A CRUZ TECNOLOGIA LTDA": "TBD",
        "CAMPOS, PATRÍCIA - PETROPOSTO COMERCIO E SERVICO LTDA": "TBD",
        "DOS SANTOS, GIVONI NATASHA - ATLAS COMERCIO DE MATERIAL ELETRICO E SERVICOS DE INSTALACAO LTDA": "TBD",
        "DRESSER INDSTRI, - WAYNE BRASIL DRESSER IND E COM LTDA": "TBD",
        "FERREIRA, RONDINEL - RONDINEL FERREIRA DE SANTANA": "TBD",
        "FERNANDES, ALECIO - UBERPOSTOS INSTALACOES EM POSTOS DE COMBUSTIVEIS LTDA.": "TBD",
        "JAOA, - JI SOLUCOES LTD EPP": "TBD",
        "LACERDA, IVAN - SOFT POSTOS LTDA": "TBD",
        "LEONARDO, - UBERPOSTOS LOGISTICA E EQUIP": "LUCAS",
        "LUCAS/ANDR, - UBERPOSTOS INSTALACOES EM POSTOS DE COMBUSTIVEIS LTDA": "LUCAS",
        "MORAES, BRUNO - MOTORVAC EQUIPAMENTOS HIDRAULICOS E MECANICOS LTDA": "TBD",
        "MOURA, JAIMERSON - J C MOURA ME": "TBD",
        "SANTOS, ABRAHAM - MANOEL GONZAGA DOS SANTOS": "TBD",
        "SILVA, RODRIGO - TECNO PUMP COMERCIO DE PECAS PBOMBAS COMBUSTIVEL LTDA - ME": "TBD",
        "SALES, - UBERPOSTOS LOGISTICA E EQUIP": "LUCAS",
    }

    return de_para_proprietario, de_para_mantenedor, de_para_especialista


# Optimized data processing functions
def process_chamados_data(df: pd.DataFrame) -> pd.DataFrame:
    """Process and enrich chamados data with optimizations."""
    df = df.copy()

    # Get mapping dictionaries
    de_para_proprietario, de_para_mantenedor, de_para_especialista = get_mapping_dicts()

    # Optimize column operations
    df.columns = df.columns.str.strip().str.upper()

    # Vectorized operations for better performance
    df["ESPECIALISTA"] = df["MANTENEDOR"].map(de_para_especialista).fillna("")
    df["PROPRIETÁRIO"] = df["PROPRIETÁRIO"].map(de_para_proprietario).fillna("")
    df["MANTENEDOR"] = df["MANTENEDOR"].map(de_para_mantenedor).fillna("")

    # Optimize aging calculation
    df["INÍCIO"] = pd.to_datetime(df["DATA"], dayfirst=True, errors="coerce")
    df["FIM"] = pd.to_datetime(df["RESOLVIDO"], dayfirst=True, errors="coerce")

    hoje = pd.Timestamp.now().normalize()
    mask_aberto_sem_fim = (df["STATUS"] == "ABERTO") & df["FIM"].isna()
    df.loc[mask_aberto_sem_fim, "FIM"] = hoje

    # Vectorized aging calculation
    df["AGING"] = (df["FIM"] - df["INÍCIO"]).dt.days

    return df


def process_o2c_data(df: pd.DataFrame) -> pd.DataFrame:
    """Process and enrich O2C data with optimizations."""
    from utils import extrair_modelo_vectorized

    df = df.copy()

    # Optimize datetime operations
    if "DT_NUM_NF" in df.columns:
        df["DT_NUM_NF"] = pd.to_datetime(
            df["DT_NUM_NF"], dayfirst=True, errors="coerce", format="mixed"
        )
        df["ANO_NF"] = df["DT_NUM_NF"].dt.year

    # Optimize guarantee calculations
    if "GARANTIA" in df.columns:
        garantia_dias = pd.to_numeric(df["GARANTIA"], errors="coerce")
        df["FIM_GARANTIA"] = df["DT_NUM_NF"] + pd.to_timedelta(garantia_dias, unit="D")

        hoje = pd.Timestamp.now().normalize()
        df["STATUS_GARANTIA"] = np.where(
            df["FIM_GARANTIA"].notna(),
            np.where(df["FIM_GARANTIA"] >= hoje, "DENTRO", "FORA"),
            "",
        )

    # Extract model from ITEM column (checking multiple possible column names)
    if "ITEM" in df.columns:
        df["MODELO"] = extrair_modelo_vectorized(df["ITEM"])
    elif "NUM_SERIAL" in df.columns:
        df["MODELO"] = extrair_modelo_vectorized(df["NUM_SERIAL"])
    elif "NUM_SERIE" in df.columns:
        df["MODELO"] = extrair_modelo_vectorized(df["NUM_SERIE"])
    elif "SÉRIE" in df.columns:
        df["MODELO"] = extrair_modelo_vectorized(df["SÉRIE"])
    elif "SERIE" in df.columns:
        df["MODELO"] = extrair_modelo_vectorized(df["SERIE"])
    else:
        df["MODELO"] = ""

    # Filter out export units (keep only Brazil)
    if "PAIS" in df.columns:
        # Check for BR with potential whitespace
        df = df[df["PAIS"].astype(str).str.strip() == "BR"]
    elif "NOME_PAIS" in df.columns:
        df = df[df["NOME_PAIS"].astype(str).str.strip().str.upper() == "BRASIL"]

    # Filter out MODELO "OUTROS"
    if "MODELO" in df.columns:
        df = df[df["MODELO"] != "OUTROS"]

    return df


# Legacy compatibility
de_para_proprietario, de_para_mantenedor, de_para_especialista = get_mapping_dicts()
