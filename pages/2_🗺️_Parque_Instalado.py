from datetime import timedelta
import streamlit as st
import pandas as pd
import json
import plotly.express as px
from data_loader import carregar_dados_merged, carregar_o2c, process_o2c_data, carregar_base_erros_rtm
from utils import extrair_estado
from auth import check_password
from filters import sidebar_filters_rtm_errors, aplicar_filtros_rtm_errors
import visualization as vz
import numpy as np
from datetime import datetime
from streamlit_dynamic_filters import DynamicFilters  # NEW IMPORT

st.set_page_config(page_title="Parque Instalado - Chamados de Serviços", layout="wide")

check_password()

# --- Carregamento dos dados principais com otimizações ---
@st.cache_data(ttl=3600, show_spinner=False)
def load_o2c_data():
    """Load O2C data with optimizations."""
    df = carregar_o2c()
    
    # Optimize dtypes for filtering
    for cat_col in ['UF', 'RTM', 'STATUS_GARANTIA', 'CIDADE']:
        if cat_col in df.columns:
            df[cat_col] = df[cat_col].astype('category')
            if '' not in df[cat_col].cat.categories:
                df[cat_col] = df[cat_col].cat.add_categories([''])
    
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def load_chamados_data():
    """Load chamados data with optimizations."""
    df = carregar_dados_merged()
    df.columns = df.columns.str.strip().str.upper()
    
    # Vectorized string operations
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].str.strip().str.upper()
    
    # Optimize dtypes for filtering
    for cat_col in ['CHASSI', 'SERVIÇO', 'SS']:
        if cat_col in df.columns:
            df[cat_col] = df[cat_col].astype('category')
            if '' not in df[cat_col].cat.categories:
                df[cat_col] = df[cat_col].cat.add_categories([''])
    
    return df

# Load data
o2c = load_o2c_data()
chamados = load_chamados_data()
erros_rtm = carregar_base_erros_rtm()

# --- Pré-processamento e enriquecimento das bases ---
@st.cache_data(ttl=1800, show_spinner=False)
def preprocess_o2c_data(o2c_df: pd.DataFrame):
    """Preprocess O2C data with optimizations."""
    df = o2c_df.copy()
    
    # Add state column
    if 'UF' in df.columns:
        df['UF'] = df['UF'].str.strip().str.upper()
    else:
        df['UF'] = df['ESTADO']
    
    if 'CIDADE' not in df.columns:
        df['CIDADE'] = ''
    
    # Add year column
    if 'DT_NUM_NF' in df.columns:
        df['ANO_NF'] = pd.to_datetime(df['DT_NUM_NF'], dayfirst=True, errors='coerce').dt.year
    else:
        df['ANO_NF'] = np.nan
    
    # Process guarantee information
    df = process_o2c_data(df)
    
    return df

@st.cache_data(ttl=1800, show_spinner=False)
def precompute_chamados_dicts(chamados_df: pd.DataFrame):
    """Precompute chamados dictionaries for fast filtering."""
    df = chamados_df.copy()
    
    # Ensure '' is a category before fillna
    for cat_col in ['SERVIÇO', 'CHASSI', 'SS']:
        if cat_col in df.columns and '' not in df[cat_col].cat.categories:
            df[cat_col] = df[cat_col].cat.add_categories([''])
    
    df['SERVIÇO'] = df['SERVIÇO'].fillna('')
    df['CHASSI'] = df['CHASSI'].fillna('')
    df['SS'] = df['SS'].fillna('')
    
    # Filter out [STB] calls from summary
    if 'SUMÁRIO' in df.columns:
        df['SUMÁRIO'] = df['SUMÁRIO'].fillna('')
        # Exclude calls with [STB] in summary
        df_valid_chamados = df[~df['SUMÁRIO'].str.contains('\\[STB\\]', case=False, na=False)]
    else:
        df_valid_chamados = df
    
    # Create dictionaries and sets for fast lookup
    chamados_por_chassi_dict = df.groupby('CHASSI')['SS'].apply(list).to_dict()
    servico_partida = df[df['SERVIÇO'].str.contains('PARTIDA INICIAL', na=False)]
    partida_set = set(servico_partida['CHASSI'])
    chassi_counts = df.groupby('CHASSI').size()
    # Use valid chamados (excluding [STB]) for chamado metrics
    chassi_com_chamado = set(df_valid_chamados[~df_valid_chamados['SERVIÇO'].str.contains('PARTIDA INICIAL', na=False)]['CHASSI'])
    
    return chamados_por_chassi_dict, partida_set, chassi_counts, chassi_com_chamado

# Preprocess data
o2c = preprocess_o2c_data(o2c)
chamados_por_chassi_dict, partida_set, chassi_counts, chassi_com_chamado = precompute_chamados_dicts(chamados)

# --- Sidebar Filtros Dinâmicos ---
filter_columns = ['UF', 'RTM', 'STATUS_GARANTIA', 'ANO_NF']  # You can add/remove columns as needed
with st.sidebar:
    st.write("Aplique os filtros em qualquer ordem 👇")
    dynamic_filters = DynamicFilters(o2c, filters=filter_columns)
    dynamic_filters.display_filters(location='sidebar')
    considerar_stb = st.checkbox("Remover [STB]", value=False)

# Use the checkbox value to filter chamados for calculations
if considerar_stb:
    chamados_considerados = chamados.copy()
else:
    chamados_considerados = chamados[~chamados['SUMÁRIO'].str.contains('\\[STB\\]', case=False, na=False)].copy()

chassi_counts_validos = chamados_considerados.groupby('CHASSI').size()
chassi_com_chamado = set(
    chamados_considerados[~chamados_considerados['SERVIÇO'].str.contains('PARTIDA INICIAL', na=False)]['CHASSI']
)

# Now filter the dataframe after all filter variables are set
filtered_filtros_unique = dynamic_filters.filter_df().drop_duplicates(subset=['NUM_SERIAL'], keep='first')

# Remove rows where NUM_SERIAL is not exactly 6 digits
filtered_filtros_unique = filtered_filtros_unique[
    filtered_filtros_unique['NUM_SERIAL'].astype(str).str.match(r'^\d{6}$', na=False)
]

# Add a new column with all chamados for each chassi, comma separated
filtered_filtros_unique['CHAMADOS_LISTA'] = filtered_filtros_unique['NUM_SERIAL'].apply(
    lambda chassi: ', '.join(str(ss) for ss in chamados_por_chassi_dict.get(chassi, []))
)

# --- RTM Error Filters (mantém como estava) ---
filtros_rtm = sidebar_filters_rtm_errors(erros_rtm)
filtered_filtros_unique = aplicar_filtros_rtm_errors(filtered_filtros_unique, filtros_rtm, erros_rtm, chamados_por_chassi_dict)

# Recalculate QTD_CHAMADOS based on filtered RTM error context
# Get only the SS present in the filtered RTM error set
ss_filtrados = set(erros_rtm['SS'].astype(str))
erros_filtrados = erros_rtm.copy()
if filtros_rtm["tipo_erro_sel"] != 'TODOS':
    erros_filtrados = erros_filtrados[erros_filtrados['TIPO_ERRO'] == filtros_rtm["tipo_erro_sel"]]
if filtros_rtm["desc_erro_sel"] != 'TODOS':
    erros_filtrados = erros_filtrados[erros_filtrados['DESC_ERRO'] == filtros_rtm["desc_erro_sel"]]
if filtros_rtm["cod_erro_sel"] != 'TODOS':
    erros_filtrados = erros_filtrados[erros_filtrados['CÓD_ERRO'] == filtros_rtm["cod_erro_sel"]]
if filtros_rtm["detalhes_erro_sel"] != 'TODOS':
    erros_filtrados = erros_filtrados[erros_filtrados['DETALHES_ERRO'] == filtros_rtm["detalhes_erro_sel"]]
ss_filtrados = set(erros_filtrados['SS'].astype(str))

def count_chamados_for_chassi(chassi):
    ss_list = chamados_por_chassi_dict.get(chassi, [])
    return sum(1 for ss in ss_list if ss in ss_filtrados)

if any([
    filtros_rtm["tipo_erro_sel"] != 'TODOS',
    filtros_rtm["desc_erro_sel"] != 'TODOS',
    filtros_rtm["cod_erro_sel"] != 'TODOS',
    filtros_rtm["detalhes_erro_sel"] != 'TODOS',
]):
    filtered_filtros_unique['QTD_CHAMADOS'] = filtered_filtros_unique['NUM_SERIAL'].apply(count_chamados_for_chassi)
    # Remove everything with QTD_CHAMADOS < 1
    filtered_filtros_unique = filtered_filtros_unique[filtered_filtros_unique['QTD_CHAMADOS'] > 0]

# Remove duplicates based on NUM_SERIAL to ensure accurate counts
# filtered_filtros_unique = filtered_filtros_unique.drop_duplicates(subset=['NUM_SERIAL'], keep='first')

# Remove rows where NUM_SERIAL is not exactly 6 digits
# filtered_filtros_unique = filtered_filtros_unique[
#     filtered_filtros_unique['NUM_SERIAL'].astype(str).str.match(r'^\d{6}$', na=False)
# ]



# Total de bombas na base (sem filtro)
all_bombas = o2c['NUM_SERIAL'].dropna().nunique()

# After all filters, including RTM error, recalculate chassis_filtros and KPIs based only on the filtered context
chassis_filtros = filtered_filtros_unique['NUM_SERIAL'].dropna().unique()
total_bombas_filtro = len(chassis_filtros)

# Média de chamados por bomba (excluindo [STB])
chassis_filtros_series = pd.Series(chassis_filtros)
qtd_chamados_filtros = chassi_counts_validos.reindex(chassis_filtros_series, fill_value=0)
media_chamados = qtd_chamados_filtros.mean() if total_bombas_filtro else 0

# % com chamado e % sem chamado: agora baseados apenas no contexto filtrado
# Se QTD_CHAMADOS > 0, então tem chamado
com_chamado = qtd_chamados_filtros > 0
pct_com_chamado = 100 * com_chamado.sum() / total_bombas_filtro if total_bombas_filtro else 0
sem_chamado = ~com_chamado
pct_sem_chamado = 100 * sem_chamado.sum() / total_bombas_filtro if total_bombas_filtro else 0

# % com partida inicial (DFS)
com_partida_dfs = pd.Series(chassis_filtros).isin(partida_set)
pct_com_partida_dfs = 100 * com_partida_dfs.sum() / total_bombas_filtro if total_bombas_filtro else 0

# Define the determine_partida_inicial function for KPI calculation
def determine_partida_inicial_kpi(row):
    """Determine partida inicial status based on new rules for KPI calculation."""
    has_partida_inicial = row['NUM_SERIAL'] in partida_set
    qtd_chamados = row['QTD_CHAMADOS']
    if has_partida_inicial:
        return 'SIM - DFS'
    elif qtd_chamados > 0:
        return 'SIM - TERCEIRO'
    else:
        return 'NÃO'

# % com partida inicial (Terceiros) - based on actual PARTIDA_INICIAL values
filtered_filtros_temp = filtered_filtros_unique.copy()
filtered_filtros_temp['QTD_CHAMADOS'] = filtered_filtros_temp['NUM_SERIAL'].map(chassi_counts_validos).fillna(0)
filtered_filtros_temp['PARTIDA_INICIAL'] = filtered_filtros_temp.apply(determine_partida_inicial_kpi, axis=1)
sim_terceiro_count = (filtered_filtros_temp['PARTIDA_INICIAL'] == 'SIM - TERCEIRO').sum()
pct_com_partida_terceiros = 100 * sim_terceiro_count / total_bombas_filtro if total_bombas_filtro else 0

# % RTM
rtm_count = filtered_filtros_unique[filtered_filtros_unique['RTM'] == 'SIM']['NUM_SERIAL'].nunique()
pct_rtm = 100 * rtm_count / total_bombas_filtro if total_bombas_filtro else 0

# % Em Garantia
em_garantia_count = filtered_filtros_unique[filtered_filtros_unique['STATUS_GARANTIA'] == 'DENTRO']['NUM_SERIAL'].nunique()
pct_em_garantia = 100 * em_garantia_count / total_bombas_filtro if total_bombas_filtro else 0

# % Fora de Garantia
fora_garantia_count = filtered_filtros_unique[filtered_filtros_unique['STATUS_GARANTIA'] == 'FORA']['NUM_SERIAL'].nunique()
pct_fora_garantia = 100 * fora_garantia_count / total_bombas_filtro if total_bombas_filtro else 0

# --- Cálculo de Valores RTM ---
# Get SS numbers for filtered pumps
ss_filtrados = set()
for chassi in chassis_filtros:
    if chassi in chamados_por_chassi_dict:
        ss_filtrados.update(chamados_por_chassi_dict[chassi])

# Filter RTM errors for these SS numbers
erros_filtrados = erros_rtm[erros_rtm['SS'].astype(str).isin(ss_filtrados)]

# Calculate value metrics
if len(erros_filtrados) > 0:
    media_valor_total = erros_filtrados['VALOR_TOTAL'].mean()
    media_valor_peca = erros_filtrados['VALOR_PECA'].mean()
    soma_valor_total = erros_filtrados['VALOR_TOTAL'].sum()
    soma_valor_peca = erros_filtrados['VALOR_PECA'].sum()
else:
    media_valor_total = 0
    media_valor_peca = 0
    soma_valor_total = 0
    soma_valor_peca = 0


# --- Adiciona colunas de Garantia Eletrônica (após todos os filtros) ---
filtered_filtros_unique['GARANTIA_ELETRONICA'] = 365
filtered_filtros_unique['FIM_GARAN_ELETRICA'] = pd.to_datetime(filtered_filtros_unique['DT_NUM_NF'], errors='coerce') + timedelta(days=365)
filtered_filtros_unique['FIM_GARAN_ELETRICA'] = filtered_filtros_unique['FIM_GARAN_ELETRICA'].dt.strftime('%d/%m/%Y')
hoje = pd.Timestamp.now().normalize()
fim_garan_eletrica_dt = pd.to_datetime(filtered_filtros_unique['FIM_GARAN_ELETRICA'], format='%d/%m/%Y', errors='coerce')
filtered_filtros_unique['STATUS_GARAN_ELETRICA'] = ['DENTRO' if (pd.notnull(fim) and hoje <= fim) else 'FORA' for fim in fim_garan_eletrica_dt]

# --- KPIs ---
st.title('🗺️ Parque Instalado - Análise por Estado')

# Primeira linha de KPIs
col1, col2, col3, col4, col5, col6, col7, col8, col9 = st.columns(9)
col1.metric('Total de Bombas', total_bombas_filtro)
col2.metric('% Com Partida (DFS)', f"{pct_com_partida_dfs:.1f}%")
col3.metric('% Com Partida (Terceiros)', f"{pct_com_partida_terceiros:.1f}%")
col4.metric('% Com Chamado', f"{pct_com_chamado:.1f}%")
col5.metric('% Sem Chamado', f"{pct_sem_chamado:.1f}%")
col6.metric('% RTM', f"{pct_rtm:.1f}%")
col7.metric('% Em Garantia', f"{pct_em_garantia:.1f}%")
col8.metric('% Fora de Garantia', f"{pct_fora_garantia:.1f}%")
col9.metric('Média Chamados/Bomba', f"{media_chamados:.1f}")


# Segunda linha de KPIs - Valores
col10, col11, col12, col13 = st.columns(4)
col10.metric('Média Valor Total (R$)', f"R$ {media_valor_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
col11.metric('Média Valor Peça (R$)', f"R$ {media_valor_peca:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
col12.metric('Soma Valor Total (R$)', f"R$ {soma_valor_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
col13.metric('Soma Valor Peça (R$)', f"R$ {soma_valor_peca:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

# Terceira linha de KPIs - Garantia Eletrônica
col14, col15, col16, col17 = st.columns(4)
media_garan_eletr = filtered_filtros_unique['GARANTIA_ELETRONICA'].mean() if len(filtered_filtros_unique) > 0 else 0
qtd_dentro_eletr = (filtered_filtros_unique['STATUS_GARAN_ELETRICA'] == 'DENTRO').sum()
qtd_fora_eletr = (filtered_filtros_unique['STATUS_GARAN_ELETRICA'] == 'FORA').sum()
total_eletr = qtd_dentro_eletr + qtd_fora_eletr
pct_dentro_eletr = 100 * qtd_dentro_eletr / total_eletr if total_eletr else 0
pct_fora_eletr = 100 * qtd_fora_eletr / total_eletr if total_eletr else 0
fim_garan_eletrica_min = filtered_filtros_unique['FIM_GARAN_ELETRICA'].min() if len(filtered_filtros_unique) > 0 else ''
fim_garan_eletrica_max = filtered_filtros_unique['FIM_GARAN_ELETRICA'].max() if len(filtered_filtros_unique) > 0 else ''
col14.metric('Média Garantia Eletrônica (dias)', f"{media_garan_eletr:.0f}")
col15.metric('% Dentro Garantia Eletrônica', f"{pct_dentro_eletr:.1f}%")
col16.metric('% Fora Garantia Eletrônica', f"{pct_fora_eletr:.1f}%")
col17.metric('FIM Garantia Eletrônica (min/max)', f"{fim_garan_eletrica_min} / {fim_garan_eletrica_max}")

# --- Mapa ---
st.header('📊 Distribuição Geográfica')

# Check if we have data for the map
if len(filtered_filtros_unique) > 0:
    # Ensure UF column exists and has valid data
    if 'UF' in filtered_filtros_unique.columns:
        # Remove rows with empty or invalid UF
        filtered_filtros_map = filtered_filtros_unique[
            (filtered_filtros_unique['UF'].notna()) & 
            (filtered_filtros_unique['UF'].astype(str).str.strip() != '') &
            (filtered_filtros_unique['UF'].astype(str).str.strip() != 'NAN')
        ].copy()
        
        if len(filtered_filtros_map) > 0:
            # Update state counts for filtered data (deduplicated)
            estado_counts_filtrado = filtered_filtros_map.groupby('UF').size().reset_index(name='Quantidade')
            
            # Create map
            try:
                fig_mapa = vz.choropleth_map_brazil(filtered_filtros_map, estado_counts_filtrado)
                st.plotly_chart(fig_mapa, use_container_width=True)
            except Exception as e:
                st.error(f"❌ Erro ao criar mapa: {str(e)}")
                
                # Fallback: Simple bar chart
                st.info("📊 Exibindo gráfico de barras como alternativa:")
                fig_bar = px.bar(
                    estado_counts_filtrado,
                    x='UF',
                    y='Quantidade',
                    color='Quantidade',
    color_continuous_scale="Blues",
                    title="Distribuição de Bombas por Estado"
                )
                fig_bar.update_layout(
                    xaxis_title="Estado",
                    yaxis_title="Quantidade de Bombas",
                    height=500,
                    xaxis_tickangle=-45
                )
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.warning("⚠️ Nenhum dado válido encontrado para exibir no mapa após a filtragem.")
    else:
        st.warning("⚠️ Coluna 'UF' não encontrada nos dados.")
        # Try to use ESTADO column instead
        if 'ESTADO' in filtered_filtros_unique.columns:
            st.info("🔄 Tentando usar coluna 'ESTADO'...")
            filtered_filtros_map = filtered_filtros_unique[
                (filtered_filtros_unique['ESTADO'].notna()) & 
                (filtered_filtros_unique['ESTADO'].astype(str).str.strip() != '') &
                (filtered_filtros_unique['ESTADO'].astype(str).str.strip() != 'NAN')
            ].copy()
            
            if len(filtered_filtros_map) > 0:
                estado_counts_filtrado = filtered_filtros_map.groupby('ESTADO').size().reset_index(name='Quantidade')
                try:
                    fig_mapa = vz.choropleth_map_brazil(filtered_filtros_map, estado_counts_filtrado)
                    st.plotly_chart(fig_mapa, use_container_width=True)
                except Exception as e:
                    st.error(f"❌ Erro ao criar mapa com ESTADO: {str(e)}")
else:
    st.warning("⚠️ Nenhum dado encontrado após a aplicação dos filtros.")

# --- Tabela Detalhada ---
st.header('📋 Detalhamento das Bombas')


# Prepare table data
colunas_tabela = [
    'NUM_SERIAL', 'UF', 'CIDADE', 'CLIENTE', 'RTM', 'STATUS_GARANTIA', 'FIM_GARANTIA', 
    'ANO_NF', 'DT_NUM_NF', 'GARANTIA', 'GARANTIA_ELETRONICA', 'FIM_GARAN_ELETRICA', 'STATUS_GARAN_ELETRICA'
]

# Add call count column (excluindo [STB])
filtered_filtros_unique['QTD_CHAMADOS'] = filtered_filtros_unique['NUM_SERIAL'].map(chassi_counts_validos).fillna(0)

# Ensure CLIENTE column exists
if 'CLIENTE' not in filtered_filtros_unique.columns:
    filtered_filtros_unique['CLIENTE'] = ''

# Add partida inicial info with new logic
def determine_partida_inicial(row):
    """Determine partida inicial status based on new rules."""
    has_partida_inicial = row['NUM_SERIAL'] in partida_set
    qtd_chamados = row['QTD_CHAMADOS']
    
    if has_partida_inicial:
        return 'SIM - DFS'
    elif qtd_chamados > 0:
        return 'SIM - TERCEIRO'
    else:
        return 'NÃO'

# Apply the new logic
filtered_filtros_unique['PARTIDA_INICIAL'] = filtered_filtros_unique.apply(determine_partida_inicial, axis=1)

# Format FIM_GARANTIA as date string
if 'FIM_GARANTIA' in filtered_filtros_unique.columns:
    filtered_filtros_unique['FIM_GARANTIA'] = filtered_filtros_unique['FIM_GARANTIA'].dt.strftime('%d/%m/%Y')

# Display table
st.dataframe(
    filtered_filtros_unique[colunas_tabela + ['QTD_CHAMADOS', 'PARTIDA_INICIAL', 'CHAMADOS_LISTA']],
    use_container_width=True,
    hide_index=True,
    column_config={
        "NUM_SERIAL": st.column_config.TextColumn("Número Serial", width="medium"),
        "UF": st.column_config.TextColumn("UF", width="small"),
        "CIDADE": st.column_config.TextColumn("Cidade", width="medium"),
        "CLIENTE": st.column_config.TextColumn("Cliente", width="medium"),
        "RTM": st.column_config.TextColumn("RTM", width="small"),
        "STATUS_GARANTIA": st.column_config.TextColumn("Status Garantia", width="small"),
        "FIM_GARANTIA": st.column_config.TextColumn("Fim Garantia", width="small"),
        "ANO_NF": st.column_config.NumberColumn("Ano NF", format="%d", width="small"),
        "DT_NUM_NF": st.column_config.DateColumn("Data NF", format="DD/MM/YYYY", width="small"),
        "GARANTIA": st.column_config.TextColumn("Garantia (dias)", width="small"),
        "QTD_CHAMADOS": st.column_config.NumberColumn("Qtd Chamados", format="%d", width="small"),
        "PARTIDA_INICIAL": st.column_config.TextColumn("Partida Inicial", width="small"),
        "CHAMADOS_LISTA": st.column_config.TextColumn("Chamados (SS)", width="large")
    }
)

# --- Funções auxiliares para detalhamento ---
def partida_inicial_info(chassi):
    """Get partida inicial information for a chassis."""
    return "SIM" if chassi in partida_set else "NÃO"

def chamados_lista(chassi):
    """Get list of calls for a chassis."""
    return chamados_por_chassi_dict.get(chassi, [])

# --- Download functionality ---
@st.cache_data(ttl=900, show_spinner=False)
def prepare_download_data(df: pd.DataFrame):
    """Prepare data for download with optimizations."""
    download_df = df.copy()
    
    # Format dates for download
    if 'DT_NUM_NF' in download_df.columns:
        download_df['DT_NUM_NF'] = download_df['DT_NUM_NF'].dt.strftime('%d/%m/%Y')
    
    if 'FIM_GARANTIA' in download_df.columns:
        # Check if FIM_GARANTIA is already a string (formatted) or datetime
        if pd.api.types.is_datetime64_any_dtype(download_df['FIM_GARANTIA']):
            download_df['FIM_GARANTIA'] = download_df['FIM_GARANTIA'].dt.strftime('%d/%m/%Y')
        # If it's already a string, leave it as is
    
    return download_df

# Download button
download_data = prepare_download_data(filtered_filtros_unique)
csv = download_data.to_csv(index=False, sep=';', encoding='utf-8-sig')
st.download_button(
    label="📥 Download dos Dados Filtrados",
    data=csv,
    file_name=f"parque_instalado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv"
) 