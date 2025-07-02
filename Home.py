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
- KPIs de cobertura, % sem partida, % sem chamado, % RTM, médias de chamados.
- Tabela detalhada com todos os dados das bombas filtradas.
- Ideal para análise estratégica, cobertura e histórico de atuação.

**Como usar:**
- Utilize o menu lateral para navegar entre as páginas.
- Use os filtros disponíveis em cada página para refinar sua análise.
- Clique nos mapas e tabelas para explorar os dados de forma interativa.
"""

import streamlit as st

# Configuração da página principal
st.set_page_config(
    page_title="DFS ServiceWatch",
    page_icon="🛠️",
)


# Título e mensagem de boas-vindas
st.write("# Bem-vindo ao DFS ServiceWatch!")

# Instrução para navegação
st.sidebar.success("Selecione uma página acima.")

# Descrição e informações institucionais e de uso das páginas
st.markdown(
    """
    Este é um dashboard interativo para análise de chamados de serviços.
    
    **Selecione uma página no menu lateral** para visualizar diferentes análises e relatórios.
    
    ### Sobre
    - Projeto do time de Serviços - Dover Fueling Solutions
    - Contato: [Cauã Almeida (BI)](mailto:c-calmeida@doverfs.com), [Fernanda Barbieri (Gerente)](mailto:fernanda.barbieri@doverfs.com)
    
    ---
    
    ### Como utilizar as páginas:
    
    **1. Principal (Chamados):**
    - Relatório detalhado de todos os chamados (abertos e fechados).
    - Pesquise, filtre por status, datas, tags, mantenedor, proprietário, especialista e mais.
    - Veja KPIs de volume, aging, % garantia, % RTM e gráficos de performance.
    - Ideal para acompanhamento operacional e análise de ciclo de chamados.
    
    **2. Parque Instalado (Mapa):**
    - Visualize o parque instalado de bombas por estado em mapa interativo.
    - Use filtros avançados: RTM, Garantia, Partida Inicial, Ano da NF, Nº de chamados.
    - Veja KPIs de cobertura, % sem partida, % sem chamado, % RTM, médias de chamados.
    - Tabela detalhada com todos os dados das bombas filtradas.
    - Ideal para análise estratégica, cobertura e histórico de atuação.
    """
) 