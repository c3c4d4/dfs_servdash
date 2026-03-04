"""
DFS ServiceWatch


## Páginas disponíveis

### 1. Principal (Chamados)
- Relatório detalhado de todos os chamados (abertos e fechados).
- Permite pesquisar, filtrar por múltiplos campos, status, datas, tags e mais.
- KPIs de volume, aging, % garantia, % RTM, e gráficos de performance por mantenedor, proprietário e especialista.
- Ideal para análise operacional e acompanhamento do ciclo de chamados.

### 2. Parque Instalado (Mapa)
- Visualização do parque instalado de bombas por estado em mapa interativo.
- Filtros avançados: RTM, Garantia, Partida Inicial, Ano da NF, Nº de chamados.
- KPIs de cobertura, % com partida, % com chamado, % RTM, médias de chamados.
- Tabela detalhada com todos os dados das bombas filtradas.
- Ideal para análise estratégica, cobertura e histórico de atuação.

**Como usar:**
- Utilize o menu lateral para navegar entre as páginas.
- Use os filtros disponíveis em cada página para refinar sua análise.
- Clique nos mapas e tabelas para explorar os dados de forma interativa.
"""

import streamlit as st
from auth import check_password

# Configuração da página principal
st.set_page_config(page_title="DFS ServiceWatch", page_icon="🛠️", layout="wide")

# Enforce authentication on homepage before any data is loaded.
check_password()

# Título e mensagem de boas-vindas
st.title("🛠️ DFS ServiceWatch")
st.markdown("### Monitoramento Inteligente de Serviços")

st.markdown("---")

# Instrução para navegação
st.sidebar.success("Selecione uma página acima.")

# Descrição e informações institucionais e de uso das páginas
col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown(
        """
        Este é um dashboard interativo para análise de chamados de serviços.
        
        **Selecione uma página no menu lateral** para visualizar diferentes análises e relatórios.
        
        ### 🚀 Funcionalidades
        
        **1. 📊 Principal (Chamados)**
        *   **Visão Geral:** KPIs de volume, aging e distribuição.
        *   **Dados Detalhados:** Tabela pesquisável com filtros avançados.
        *   **Análise Gráfica:** Performance por mantenedor e especialista.
        
        **2. 🗺️ Parque Instalado (Mapa)**
        *   **Geolocalização:** Mapa interativo das bombas por estado.
        *   **Filtros Inteligentes:** RTM, Garantia, Ano da NF.
        *   **Análise de Cobertura:** Identificação de gaps de serviço.
        """
    )

with col_right:
    st.info(
        """
        ### ℹ️ Sobre
        
        **Equipe de Serviços**
        Dover Fueling Solutions
        
        **Acesso seguro:**
        * Use o menu lateral para abrir as páginas de análise.
        * Métricas e dados detalhados ficam disponíveis apenas nas páginas internas.
        """
    )
