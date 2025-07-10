"""
Página: Parque Instalado (Mapa e Detalhamento das Bombas)

- Exibe o parque instalado de bombas por estado em mapa interativo.
- Permite filtrar por RTM, Garantia, Partida Inicial, Ano da NF e Nº de chamados.
- KPIs, mapa e tabela detalhada são atualizados conforme os filtros.
- Desenvolvido para análise operacional e estratégica do parque instalado.
"""


import streamlit as st
import pandas as pd
import json
from data_loader import carregar_dados_merged, de_para_proprietario, de_para_mantenedor, de_para_especialista
from utils import extrair_estado
from auth import check_password
import plotly.express as px
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Parque Instalado - Chamados de Serviços", layout="wide")

check_password()

# --- Carregamento dos dados principais ---
# Carrega base de bombas (o2c) e chamados (abertos e fechados)

# --- Caching for faster reloads ---
@st.cache_data(show_spinner=False)
def load():
    df = pd.read_csv('o2c_unpacked.csv', sep=';', encoding='utf-8', dtype=str)
    df.columns = df.columns.str.strip().str.upper()
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.upper()
    # Optimize dtypes for filtering and ensure '' is a category
    for cat_col in ['UF', 'RTM', 'STATUS_GARANTIA', 'CIDADE']:
        if cat_col in df.columns:
            df[cat_col] = df[cat_col].astype('category')
            if '' not in df[cat_col].cat.categories:
                df[cat_col] = df[cat_col].cat.add_categories([''])
    return df

@st.cache_data(show_spinner=False)
def load_chamados():
    df = carregar_dados_merged()
    df.columns = df.columns.str.strip().str.upper()
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.upper()
    # Optimize dtypes for filtering and ensure '' is a category
    for cat_col in ['CHASSI', 'SERVIÇO', 'SS']:
        if cat_col in df.columns:
            df[cat_col] = df[cat_col].astype('category')
            if '' not in df[cat_col].cat.categories:
                df[cat_col] = df[cat_col].cat.add_categories([''])
    return df

o2c = load()
chamados = load_chamados()

# --- Pré-processamento e enriquecimento das bases ---
# Adiciona colunas de estado, cidade, ano da NF, fim de garantia e status de garantia
if 'UF' in o2c.columns:
    o2c['UF'] = o2c['UF'].str.strip().str.upper()
else:
    o2c['UF'] = o2c['ESTADO']
if 'CIDADE' not in o2c.columns:
    o2c['CIDADE'] = ''
if 'DT_NUM_NF' in o2c.columns:
    o2c['ANO_NF'] = pd.to_datetime(o2c['DT_NUM_NF'], dayfirst=True, errors='coerce').dt.year
else:
    o2c['ANO_NF'] = np.nan

def calcular_fim_garantia(row):
    try:
        dt_nf = pd.to_datetime(row.get('DT_NUM_NF', ''), dayfirst=True, errors='coerce')
        dias_garantia = pd.to_numeric(row.get('GARANTIA', ''), errors='coerce')
        if pd.isna(dt_nf) or pd.isna(dias_garantia):
            return ''
        fim = dt_nf + pd.to_timedelta(dias_garantia, unit='D')
        return fim.strftime('%d/%m/%Y')
    except:
        return ''

def calcular_status_garantia(row):
    try:
        dt_nf = pd.to_datetime(row.get('DT_NUM_NF', ''), dayfirst=True, errors='coerce')
        dias_garantia = pd.to_numeric(row.get('GARANTIA', ''), errors='coerce')
        if pd.isna(dt_nf) or pd.isna(dias_garantia):
            return ''
        fim = dt_nf + pd.to_timedelta(dias_garantia, unit='D')
        hoje = pd.Timestamp.now().normalize()
        return 'DENTRO' if hoje <= fim else 'FORA'
    except:
        return ''

o2c['FIM_GARANTIA'] = o2c.apply(calcular_fim_garantia, axis=1)
o2c['STATUS_GARANTIA'] = o2c.apply(calcular_status_garantia, axis=1)

# Remover filtro de ano: filtered começa como todos os dados
filtered = o2c.copy()

# Se existir UF e CIDADE, usar para o mapa e tabela
if 'UF' in filtered.columns:
    filtered['UF'] = filtered['UF'].str.strip().str.upper()
else:
    filtered['UF'] = filtered['ESTADO']
if 'CIDADE' not in filtered.columns:
    filtered['CIDADE'] = ''

# Contagem de bombas por estado (usando UF)
estado_counts = filtered.groupby('UF').size().reset_index(name='Quantidade')

# Após aplicar todos os filtros em filtered:
all_bombas = o2c['NUM_SERIAL'].dropna().nunique()
total_bombas = filtered['NUM_SERIAL'].nunique()
filtered_chassis = set(filtered['NUM_SERIAL'])


# --- Precompute dicts and sets for fast filtering ---
@st.cache_data(show_spinner=False)
def precompute_chamados_dicts(chamados):
    chamados = chamados.copy()
    # Ensure '' is a category before fillna
    for cat_col in ['SERVIÇO', 'CHASSI', 'SS']:
        if cat_col in chamados.columns and '' not in chamados[cat_col].cat.categories:
            chamados[cat_col] = chamados[cat_col].cat.add_categories([''])
    chamados['SERVIÇO'] = chamados['SERVIÇO'].fillna('')
    chamados['CHASSI'] = chamados['CHASSI'].fillna('')
    chamados['SS'] = chamados['SS'].fillna('')
    chamados_por_chassi_dict = chamados.groupby('CHASSI')['SS'].apply(list).to_dict()
    servico_partida = chamados[chamados['SERVIÇO'].str.contains('PARTIDA INICIAL', na=False)]
    partida_set = set(servico_partida['CHASSI'])
    chassi_counts = chamados.groupby('CHASSI').size()
    chassi_com_chamado = set(chamados[~chamados['SERVIÇO'].str.contains('PARTIDA INICIAL', na=False)]['CHASSI'])
    return chamados_por_chassi_dict, partida_set, chassi_counts, chassi_com_chamado

chamados_por_chassi_dict, partida_set, chassi_counts, chassi_com_chamado = precompute_chamados_dicts(chamados)

# Use filtered_filtros para KPIs, mapa e tabela
# --- Sidebar Filtros ---
st.sidebar.header('Filtros')

# RTM
rtm_options = ['TODOS'] + sorted(filtered['RTM'].dropna().unique())
rtm_sel = st.sidebar.selectbox('RTM', rtm_options)

# Garantia
garantia_options = ['TODOS', 'DENTRO', 'FORA']
garantia_sel = st.sidebar.selectbox('Garantia', garantia_options)

# Partida Inicial
partida_options = ['TODOS', 'SIM', 'NÃO']
partida_sel = st.sidebar.selectbox('Partida Inicial', partida_options)

# Range Ano NF
anos_validos = filtered['ANO_NF'].dropna().astype(int)
if not anos_validos.empty:
    ano_min, ano_max = int(anos_validos.min()), int(anos_validos.max())
else:
    ano_min, ano_max = 2000, 2030
ano_range = st.sidebar.slider('Ano da NF', ano_min, ano_max, (ano_min, ano_max))

# Range Nº de chamados
qtd_chamados_validos = chassi_counts.reindex(filtered['NUM_SERIAL'].dropna().unique(), fill_value=0)
chamados_min, chamados_max = int(qtd_chamados_validos.min()), int(qtd_chamados_validos.max())
chamados_range = st.sidebar.slider('Nº de chamados', chamados_min, chamados_max, (chamados_min, chamados_max))

# --- Aplicar filtros ---
filtered_filtros = filtered.copy()

if rtm_sel != 'TODOS':
    filtered_filtros = filtered_filtros[filtered_filtros['RTM'] == rtm_sel]
if garantia_sel != 'TODOS':
    filtered_filtros = filtered_filtros[filtered_filtros['STATUS_GARANTIA'] == garantia_sel]
if partida_sel != 'TODOS':
    if partida_sel == 'SIM':
        filtered_filtros = filtered_filtros[filtered_filtros['NUM_SERIAL'].isin(partida_set)]
    else:
        filtered_filtros = filtered_filtros[~filtered_filtros['NUM_SERIAL'].isin(partida_set)]
filtered_filtros = filtered_filtros[(filtered_filtros['ANO_NF'] >= ano_range[0]) & (filtered_filtros['ANO_NF'] <= ano_range[1])]

# Filtro por número de chamados
chassis_filtros = filtered_filtros['NUM_SERIAL'].dropna().unique()
qtd_chamados_filtros = chassi_counts.reindex(chassis_filtros, fill_value=0)
filtered_filtros = filtered_filtros[filtered_filtros['NUM_SERIAL'].isin(qtd_chamados_filtros[(qtd_chamados_filtros >= chamados_range[0]) & (qtd_chamados_filtros <= chamados_range[1])].index)]

# === A PARTIR DAQUI, USAR filtered_filtros PARA KPIs, MAPA E TABELA ===
# ... KPIs, mapa e tabela ...

# Total de bombas na base (sem filtro)
all_bombas = o2c['NUM_SERIAL'].dropna().nunique()

# Chassis únicos filtrados
chassis_filtros = filtered_filtros['NUM_SERIAL'].dropna().unique()
total_bombas_filtro = len(chassis_filtros)


# % sem partida inicial
sem_partida = ~pd.Series(chassis_filtros).isin(partida_set)
pct_sem_partida = 100 * sem_partida.sum() / total_bombas_filtro if total_bombas_filtro else 0

# % COM chamado (exceto PI)
com_chamado = pd.Series(chassis_filtros).isin(chassi_com_chamado)
pct_com_chamado = 100 * com_chamado.sum() / total_bombas_filtro if total_bombas_filtro else 0

# % RTM
rtm_chassis = filtered_filtros.drop_duplicates('NUM_SERIAL')
pct_rtm = 100 * sum(rtm_chassis['RTM'] == 'SIM') / total_bombas_filtro if total_bombas_filtro else 0

# Média de chamados por bomba
media_chamados = chassi_counts.reindex(chassis_filtros, fill_value=0).mean() if total_bombas_filtro else 0

# Média de chamados por bomba RTM
rtm_serials = rtm_chassis[rtm_chassis['RTM'] == 'SIM']['NUM_SERIAL']
media_chamados_rtm = chassi_counts.reindex(rtm_serials, fill_value=0).mean() if not rtm_serials.empty else 0

col2, col3, col4, col5, col6, col7 = st.columns(6)
col2.metric('Total Bombas', total_bombas_filtro)
col3.metric('% Sem Partida Inicial', f'{pct_sem_partida:.1f}%')
col4.metric('% Com Chamado', f'{pct_com_chamado:.1f}%')
col5.metric('% RTM', f'{pct_rtm:.1f}%')
col6.metric('Média Chamados/Bomba', f'{media_chamados:.2f}')
col7.metric('Média Chamados/Bomba RTM', f'{media_chamados_rtm:.2f}')

# --- Mapa ---
with open('brazil_states.geojson', 'r', encoding='utf-8') as f:
    geo_brasil = json.load(f)

# Atualizar contagem após filtro
estado_counts_filtered = filtered_filtros.groupby('UF').size().reset_index(name='Quantidade')

fig_uf = px.choropleth_mapbox(
    estado_counts_filtered,
    geojson=geo_brasil,
    locations="UF",
    featureidkey="properties.sigla",
    color="Quantidade",
    color_continuous_scale="Blues",
    mapbox_style="carto-positron",
    zoom=3,
    center={"lat": -14.2350, "lon": -52.0},
    opacity=0.7,
    labels={"Quantidade": "Bombas"},
)
fig_uf.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=700)
st.plotly_chart(fig_uf, use_container_width=True)

# --- Tabela detalhada ---
# Para cada chassi, buscar info de partida inicial e lista de chamados
chamados['SERVIÇO'] = chamados['SERVIÇO'].fillna('')
chamados['CHASSI'] = chamados['CHASSI'].fillna('')
chamados['SS'] = chamados['SS'].fillna('')

def partida_inicial_info(chassi):
    if chassi in partida_dict:
        return f"SIM"
    return "NÃO"

def chamados_lista(chassi):
    return ', '.join(chamados_por_chassi_dict.get(chassi, []))


# Montar tabela de forma vetorizada para performance
df_tabela = filtered_filtros.copy()
df_tabela['QTD_CHAMADOS'] = df_tabela['NUM_SERIAL'].map(chassi_counts).fillna(0).astype(int)
df_tabela['PARTIDA INICIAL'] = df_tabela['NUM_SERIAL'].isin(partida_set).map({True: 'SIM', False: 'NÃO'})
df_tabela['CHAMADOS'] = df_tabela['NUM_SERIAL'].map(chamados_por_chassi_dict).apply(lambda x: ', '.join(x) if isinstance(x, list) else '')


# Ajuste de nomes de colunas para evitar KeyError
col_map = {
    'CHASSI': 'NUM_SERIAL',
    'NF': 'NUM_NF',
    'DATA_NF': 'DT_NUM_NF',
}
cols = [col_map.get(c, c) for c in ['CHASSI', 'CLIENTE', 'RTM', 'NF', 'DATA_NF', 'FIM_GARANTIA', 'GARANTIA', 'UF', 'CIDADE', 'QTD_CHAMADOS', 'PARTIDA INICIAL', 'CHAMADOS']]
# Renomear colunas temporariamente para exibição
df_tabela = df_tabela.rename(columns={v: k for k, v in col_map.items() if v in df_tabela.columns})
df_tabela = df_tabela[cols]

st.markdown('### Bombas Instaladas')
st.dataframe(df_tabela, use_container_width=True)

# ... KPIs, mapa e tabela ... 