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

# --- Carregar dados ---
def load():
    df = pd.read_csv('o2c_unpacked.csv', sep=';', encoding='utf-8', dtype={
        'NUM_SERIAL': str,
        'RTM': str,
        'GARANTIA': str,
        'DT_NUM_NF': str,
        'UF': str,
        'CIDADE': str
    })
    # Convert only necessary columns to uppercase
    upper_cols = ['NUM_SERIAL', 'RTM', 'UF', 'CIDADE']
    df.columns = df.columns.str.strip().str.upper()
    for col in upper_cols:
        if col in df.columns:
            df[col] = df[col].str.strip().str.upper()
    return df

def load_chamados():
    df = carregar_dados_merged()
    df.columns = df.columns.str.strip().str.upper()
    # Convert only necessary columns to uppercase
    upper_cols = ['CHASSI', 'SERVIÇO', 'SS', 'TIPO_ERRO', 'DESC_ERRO', 'COD_ERRO']
    for col in upper_cols:
        if col in df.columns:
            df[col] = df[col].str.strip().str.upper()
    return df

# --- Preparar dados principais ---
# Optimize dtypes for filtering
@st.cache_data(ttl=3600)
def prepare_o2c():
    df = load()
    for col in ['RTM', 'UF', 'STATUS_GARANTIA']:
        if col in df.columns:
            df[col] = df[col].astype('category')
    df['DT_NF'] = pd.to_datetime(df['DT_NUM_NF'], dayfirst=True, errors='coerce')
    df['DIAS_GARANTIA'] = pd.to_numeric(df['GARANTIA'], errors='coerce')
    fim_garantia = df['DT_NF'] + pd.to_timedelta(df['DIAS_GARANTIA'], unit='D')
    df['FIM_GARANTIA'] = fim_garantia.dt.strftime('%d/%m/%Y').fillna('')
    hoje = pd.Timestamp.now().normalize()
    df['STATUS_GARANTIA'] = np.where(
        fim_garantia >= hoje, 'DENTRO', 'FORA'
    )
    df['STATUS_GARANTIA'] = pd.Categorical(df['STATUS_GARANTIA'], categories=['DENTRO', 'FORA'])
    df.set_index('NUM_SERIAL', inplace=True, drop=False)
    df['ANO_NF'] = df['DT_NF'].dt.year.astype('Int64')
    return df

o2c = prepare_o2c()

@st.cache_data(ttl=3600)
def prepare_chamados():
    chamados = load_chamados()
    chamados['SERVIÇO'] = chamados['SERVIÇO'].fillna('')
    chamados['CHASSI'] = chamados['CHASSI'].fillna('')
    chamados['SS'] = chamados['SS'].fillna('')
    return chamados

chamados = prepare_chamados()

# Precompute dicts and counts for fast lookup
@st.cache_data(ttl=3600)
def precompute_chamados_dicts(chamados, filtered_chassis):
    chamados_filtrados = chamados[chamados['CHASSI'].isin(filtered_chassis)].copy()
    chamados_por_chassi_dict = chamados_filtrados.groupby('CHASSI')['SS'].apply(list).to_dict()
    servico_partida = chamados_filtrados[chamados_filtrados['SERVIÇO'].str.contains('PARTIDA INICIAL', na=False)]
    partida_dict = servico_partida.groupby('CHASSI')['SS'].apply(list).to_dict()
    chassi_counts = chamados_filtrados.groupby('CHASSI').size()
    return chamados_filtrados, chamados_por_chassi_dict, partida_dict, chassi_counts

filtered_chassis = set(o2c['NUM_SERIAL'])
chamados_filtrados, chamados_por_chassi_dict, partida_dict, chassi_counts = precompute_chamados_dicts(chamados, filtered_chassis)

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

# Filtrar chamados para conter apenas os chassis presentes em filtered
chamados_filtrados = chamados[chamados['CHASSI'].isin(filtered_chassis)].copy()

# Index e sets auxiliares baseados apenas nos dados filtrados
chamados_filtrados['SERVIÇO'] = chamados_filtrados['SERVIÇO'].fillna('')
chamados_filtrados['CHASSI'] = chamados_filtrados['CHASSI'].fillna('')
chamados_filtrados['SS'] = chamados_filtrados['SS'].fillna('')
chamados_por_chassi_dict = chamados_filtrados.groupby('CHASSI')['SS'].apply(list).to_dict()
servico_partida = chamados_filtrados[chamados_filtrados['SERVIÇO'].str.contains('PARTIDA INICIAL', na=False)]
partida_dict = servico_partida.groupby('CHASSI')['SS'].apply(list).to_dict()
chassi_counts = chamados_filtrados.groupby('CHASSI').size()

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

# Filtros TIPO_ERRO, DESC_ERRO, COD_ERRO
# Use multiselect for multiple selection
all_tipo_erro = sorted(chamados['TIPO_ERRO'].dropna().unique())
all_desc_erro = sorted(chamados['DESC_ERRO'].dropna().unique())
all_cod_erro = sorted(chamados['COD_ERRO'].dropna().unique())

tipo_erro_sel = st.sidebar.multiselect('Tipo Erro', options=all_tipo_erro, default=[])
desc_erro_sel = st.sidebar.multiselect('Descrição Erro', options=all_desc_erro, default=[])
cod_erro_sel = st.sidebar.multiselect('Código Erro', options=all_cod_erro, default=[])

# --- Aplicar filtros ---
@st.cache_data(ttl=3600)
def apply_filters(df, rtm_sel, garantia_sel, partida_sel, ano_range, chamados_range, tipo_erro_sel, desc_erro_sel, cod_erro_sel, chamados, chassi_counts_full):
    mask = np.ones(len(df), dtype=bool)
    idx = df.index
    if rtm_sel != 'TODOS':
        mask &= (df['RTM'].values == rtm_sel)
    if garantia_sel != 'TODOS':
        mask &= (df['STATUS_GARANTIA'].values == garantia_sel)
    if partida_sel != 'TODOS':
        # We'll build partida_dict after filtering
        pass
    mask &= (df['ANO_NF'].values >= ano_range[0]) & (df['ANO_NF'].values <= ano_range[1])
    qtd_chamados_filtros = chassi_counts_full.reindex(idx, fill_value=0).values
    mask &= (qtd_chamados_filtros >= chamados_range[0]) & (qtd_chamados_filtros <= chamados_range[1])
    filtered_df = df[mask]
    filtered_chassis = set(filtered_df['NUM_SERIAL'].values)
    chamados_filtrados = chamados[chamados['CHASSI'].isin(filtered_chassis)]
    chamados_por_chassi_dict = chamados_filtrados.groupby('CHASSI')['SS'].apply(list).to_dict()
    servico_partida = chamados_filtrados[chamados_filtrados['SERVIÇO'].str.contains('PARTIDA INICIAL', na=False)]
    partida_dict = servico_partida.groupby('CHASSI')['SS'].apply(list).to_dict()
    chassi_counts = chamados_filtrados.groupby('CHASSI').size()
    if partida_sel != 'TODOS':
        has_partida = filtered_df['NUM_SERIAL'].isin(partida_dict.keys()).values
        filtered_df = filtered_df[has_partida] if partida_sel == 'SIM' else filtered_df[~has_partida]
        filtered_chassis = set(filtered_df['NUM_SERIAL'].values)
        chamados_filtrados = chamados_filtrados[chamados_filtrados['CHASSI'].isin(filtered_chassis)]
        chamados_por_chassi_dict = chamados_filtrados.groupby('CHASSI')['SS'].apply(list).to_dict()
        servico_partida = chamados_filtrados[chamados_filtrados['SERVIÇO'].str.contains('PARTIDA INICIAL', na=False)]
        partida_dict = servico_partida.groupby('CHASSI')['SS'].apply(list).to_dict()
        chassi_counts = chamados_filtrados.groupby('CHASSI').size()
    # Error filters: support multiple selection
    if tipo_erro_sel or desc_erro_sel or cod_erro_sel:
        chamados_mask = np.ones(len(chamados_filtrados), dtype=bool)
        if tipo_erro_sel:
            chamados_mask &= chamados_filtrados['TIPO_ERRO'].isin(tipo_erro_sel).values
        if desc_erro_sel:
            chamados_mask &= chamados_filtrados['DESC_ERRO'].isin(desc_erro_sel).values
        if cod_erro_sel:
            chamados_mask &= chamados_filtrados['COD_ERRO'].isin(cod_erro_sel).values
        chassis_filtros_erro = chamados_filtrados.loc[chamados_mask, 'CHASSI'].unique()
        filtered_df = filtered_df[filtered_df['NUM_SERIAL'].isin(chassis_filtros_erro)]
        filtered_chassis = set(filtered_df['NUM_SERIAL'].values)
        chamados_filtrados = chamados_filtrados[chamados_filtrados['CHASSI'].isin(filtered_chassis)]
        chamados_por_chassi_dict = chamados_filtrados.groupby('CHASSI')['SS'].apply(list).to_dict()
        servico_partida = chamados_filtrados[chamados_filtrados['SERVIÇO'].str.contains('PARTIDA INICIAL', na=False)]
        partida_dict = servico_partida.groupby('CHASSI')['SS'].apply(list).to_dict()
        chassi_counts = chamados_filtrados.groupby('CHASSI').size()
    return filtered_df, chamados_filtrados, chamados_por_chassi_dict, partida_dict, chassi_counts

# Aplicar filtros usando a função cacheada
filtered_filtros, chamados_filtrados, chamados_por_chassi_dict, partida_dict, chassi_counts = apply_filters(
    o2c,
    rtm_sel,
    garantia_sel,
    partida_sel,
    ano_range,
    chamados_range,
    tipo_erro_sel,
    desc_erro_sel,
    cod_erro_sel,
    chamados,
    chassi_counts
)

# === A PARTIR DAQUI, USAR filtered_filtros PARA KPIs, MAPA E TABELA ===
# ... KPIs, mapa e tabela ...

# Total de bombas na base (sem filtro)
all_bombas = o2c['NUM_SERIAL'].dropna().nunique()

# Chassis únicos filtrados
chassis_filtros = filtered_filtros['NUM_SERIAL'].dropna().unique()
total_bombas_filtro = len(chassis_filtros)

# % sem partida inicial
chassi_set_partida = set(partida_dict.keys())
sem_partida = [ch not in chassi_set_partida for ch in chassis_filtros]
pct_sem_partida = 100 * sum(sem_partida) / total_bombas_filtro if total_bombas_filtro else 0

# % com chamado (exceto PI)
chassi_com_chamado = set(chamados_filtrados[~chamados_filtrados['SERVIÇO'].str.contains('PARTIDA INICIAL', na=False)]['CHASSI'])
com_chamado = [ch in chassi_com_chamado for ch in chassis_filtros]
pct_com_chamado = 100 * sum(com_chamado) / total_bombas_filtro if total_bombas_filtro else 0

# % RTM
rtm_chassis = filtered_filtros.drop_duplicates('NUM_SERIAL')
pct_rtm = 100 * sum(rtm_chassis['RTM'] == 'SIM') / total_bombas_filtro if total_bombas_filtro else 0

# Média de chamados por bomba
media_chamados = chassi_counts.reindex(chassis_filtros, fill_value=0).mean() if total_bombas_filtro else 0

# Média de chamados por bomba RTM
rtm_serials = rtm_chassis[rtm_chassis['RTM'] == 'SIM']['NUM_SERIAL']
media_chamados_rtm = chassi_counts.reindex(rtm_serials, fill_value=0).mean() if not rtm_serials.empty else 0

col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
col1.metric('Total Bombas (Base)', all_bombas)
col2.metric('Total Bombas (Filtro)', total_bombas_filtro)
col3.metric('% Sem Partida Inicial', f'{pct_sem_partida:.1f}%')
col4.metric('% Com Chamado (exceto PI)', f'{pct_com_chamado:.1f}%')
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
@st.cache_data(ttl=3600)  # Cache the table generation for 1 hour
def generate_table(filtered_filtros, chamados_por_chassi_dict, partida_dict, chassi_counts):
    # Create base DataFrame
    df_tabela = filtered_filtros[['NUM_SERIAL', 'RTM', 'NUM_NF', 'DT_NUM_NF', 'FIM_GARANTIA', 'STATUS_GARANTIA', 'UF', 'CIDADE']].copy()
    
    # Add QTD_CHAMADOS
    df_tabela['QTD_CHAMADOS'] = df_tabela['NUM_SERIAL'].map(chassi_counts).fillna(0)
    
    # Add PARTIDA INICIAL
    df_tabela['PARTIDA INICIAL'] = df_tabela['NUM_SERIAL'].map(
        lambda x: 'SIM' if x in partida_dict else 'NÃO'
    )
    
    # Add CHAMADOS
    df_tabela['CHAMADOS'] = df_tabela['NUM_SERIAL'].map(
        lambda x: ', '.join(chamados_por_chassi_dict.get(x, []))
    )
    
    # Rename NUM_SERIAL to CHASSI for display
    df_tabela.rename(columns={'NUM_SERIAL': 'CHASSI'}, inplace=True)
    
    # Reorder columns with correct names
    cols = ['CHASSI', 'RTM', 'NUM_NF', 'DT_NUM_NF', 'FIM_GARANTIA', 'STATUS_GARANTIA', 'UF', 'CIDADE', 'QTD_CHAMADOS', 'PARTIDA INICIAL', 'CHAMADOS']
    return df_tabela[cols]

# Generate table using the cached function
df_tabela = generate_table(filtered_filtros, chamados_por_chassi_dict, partida_dict, chassi_counts)

st.markdown('### Bombas Instaladas')
st.dataframe(df_tabela, use_container_width=True)

# ... KPIs, mapa e tabela ...