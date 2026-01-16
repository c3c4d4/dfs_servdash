"""
Shared constants for DFS ServiceWatch dashboard.
Centralizes configuration values to avoid duplication and magic numbers.
"""

# =============================================================================
# PUMP MODELS
# =============================================================================
MAIN_MODELS = ["HELIX", "VISTA", "CENTURY", "3G", "E123", "7502A"]

# Model mapping based on serial prefix
MODEL_MAPPING = {
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
    "W9000001": "HELIX",
    "7502A": "7502A",
    "N3G2201PO": "3G",
    "3GV3490P": "3G",
}

# =============================================================================
# WARRANTY PERIODS (in days)
# =============================================================================
GARANTIA_PERIODS = {
    "6_MESES": 183,
    "12_MESES": 365,
    "18_MESES": 548,
    "24_MESES": 730,
    "36_MESES": 1095,
}

GARANTIA_ELETRONICA_DAYS = 365

# =============================================================================
# CACHE TTL VALUES (in seconds)
# =============================================================================
CACHE_TTL_LONG = 3600  # 1 hour - for data loading
CACHE_TTL_MEDIUM = 1800  # 30 minutes - for processing/visualizations
CACHE_TTL_SHORT = 900  # 15 minutes - for filters

# =============================================================================
# STATUS VALUES
# =============================================================================
STATUS_OPEN = "ABERTO"
STATUS_CLOSED = "FECHADO"
STATUS_OPTIONS = ["GERAL", "ABERTO", "FECHADO"]

PARTIDA_OPTIONS = ["TODOS", "NÃO", "SIM - TERCEIRO", "SIM - DFS"]
GARANTIA_STATUS_OPTIONS = ["TODOS", "DENTRO", "FORA"]

# =============================================================================
# AGING CATEGORIES
# =============================================================================
AGING_BINS = [0, 7, 14, float("inf")]
AGING_LABELS = ["Até 7", "8 a 14", ">14"]

# =============================================================================
# FILE PATHS
# =============================================================================
CSV_SEPARATOR = ";"
CSV_ENCODING = "utf-8"
CSV_ENCODING_BOM = "utf-8-sig"

# Data files
DATA_FILE_CHAMADOS = "chamados.csv"
DATA_FILE_CHAMADOS_FECHADOS = "chamados_fechados.csv"
DATA_FILE_O2C = "o2c_unpacked.csv"
DATA_FILE_RTM_ERRORS = "BASE_ERROS_RTM.csv"
DATA_FILE_BRAZIL_GEOJSON = "brazil_states.geojson"

# Cache files
CACHE_FILE_GARANTIA = "garantia_cache.csv"
CACHE_FILE_RTM = "rtm_cache.csv"

# =============================================================================
# VISUALIZATION
# =============================================================================
CHART_HEIGHT_STANDARD = 400
MAP_HEIGHT = 500
MAX_CHART_ITEMS = 20

# Color scales
CHOROPLETH_COLOR_SCALE = [
    [0.0, "#f7fbff"],
    [0.125, "#deebf7"],
    [0.25, "#c6dbef"],
    [0.375, "#9ecae1"],
    [0.5, "#6baed6"],
    [0.625, "#4292c6"],
    [0.75, "#2171b5"],
    [0.875, "#08519c"],
    [1.0, "#08306b"],
]

AGING_COLOR_MAP = {
    "Até 7": "#9ac8e0",
    "8 a 14": "#3989c2",
    ">14": "#08306b",
}

# =============================================================================
# API/NETWORK
# =============================================================================
MAX_RETRIES = 3
REQUEST_TIMEOUT = 180  # seconds
BLOCK_PAUSE = 60  # seconds to pause when rate limited

# =============================================================================
# DATA VALIDATION
# =============================================================================
SERIAL_REGEX_PATTERN = r"^\d{6}$"
