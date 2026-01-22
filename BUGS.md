# Bugs Discovered in DFS ServiceWatch

## Important Bugs

- [x] BUG-001: [IMPORTANT] Unused variable `mask_aberto_sem_fim` calculated but never applied - closed tickets with missing end dates get aging calculated to today instead of being handled correctly | File: utils.py:81
- [x] BUG-002: [IMPORTANT] Dead code: variables `dt_inicio_safeguard` and `dt_fim_safeguard` calculated but never used; row-by-row function used instead | File: pages/1_📊_Principal.py:274-280

## Minor Bugs (Lint Issues in Core Files)

- [x] BUG-003: [MINOR] Unused exception variable `e` in Home.py exception handler | File: Home.py:88
- [x] BUG-004: [MINOR] Unused exception variable `e` in visualization.py polylabel fallback | File: visualization.py:534
- [x] BUG-005: [MINOR] Unused imports in visualization.py (plotly.graph_objects, numpy, List) | File: visualization.py:4-7
- [x] BUG-006: [MINOR] Unused imports in pages/2_🗺️_Parque_Instalado.py (timedelta, extrair_estado) | File: pages/2_🗺️_Parque_Instalado.py:1,11
- [x] BUG-007: [MINOR] Unused import in utils.py (Set from typing) | File: utils.py:4
- [x] BUG-008: [MINOR] Unused import in tests/test_filters.py (datetime) | File: tests/test_filters.py:7
