# Enhancements for DFS ServiceWatch

## High Impact

- [x] ENH-001: [HIGH] Extract model percentage KPI calculation into reusable function in business_logic.py to eliminate duplication between Principal.py and Parque_Instalado.py | Files: pages/1_📊_Principal.py, pages/2_🗺️_Parque_Instalado.py, business_logic.py

## Medium Impact

- [x] ENH-002: [MEDIUM] Use constants from constants.py for MAIN_MODELS instead of hardcoded lists | Files: pages/1_📊_Principal.py:183, pages/2_🗺️_Parque_Instalado.py:349
- [ ] ENH-003: [MEDIUM] Add type hints to create_kpi_metrics function return type | File: visualization.py:737
