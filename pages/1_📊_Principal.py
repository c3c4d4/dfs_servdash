import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import base64
import numpy as np

from data_loader import carregar_dados_merged, de_para_proprietario, de_para_mantenedor, de_para_especialista
from utils import extrair_tags
from auth import check_password
from filters import sidebar_filters, aplicar_filtros
import visualization as vz

st.set_page_config(page_title="PRINCIPAL - CHAMADOS DE SERVIÇOS", layout="wide")

check_password()

def load_and_merge_chamados():
    df1 = pd.read_csv('chamados.csv', sep=';', encoding='utf-8', dtype=str)
    df2 = pd.read_csv('chamados_fechados.csv', sep=';', encoding='utf-8', dtype=str)
    # Padronize nomes de colunas para maiúsculo
    df1.columns = df1.columns.str.strip().str.upper()
    df2.columns = df2.columns.str.strip().str.upper()
    for col in df1.columns:
        df1[col] = df1[col].astype(str).str.strip().str.upper()
    for col in df2.columns:
        df2[col] = df2[col].astype(str).str.strip().str.upper()
    df = pd.concat([df1, df2], ignore_index=True)
    # Checagem amigável para TAREFA
    if 'TAREFA' in df.columns:
        df = df.drop_duplicates(subset=['SS', 'TAREFA'], keep='first').reset_index(drop=True)
    else:
        st.warning("Coluna 'TAREFA' não encontrada. Removendo duplicatas apenas por 'SS'. Colunas disponíveis: " + str(df.columns.tolist()))
        df = df.drop_duplicates(subset=['SS'], keep='first').reset_index(drop=True)
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.upper()
    # Checagem amigável para CHASSI
    if 'CHASSI' not in df.columns:
        st.error("Coluna 'CHASSI' não encontrada no dataframe de chamados! Colunas disponíveis: " + str(df.columns.tolist()))
        st.stop()
    return df

def load_o2c():
    df = pd.read_csv('o2c_unpacked.csv', sep=';', encoding='utf-8', dtype=str)
    df.columns = df.columns.str.strip().str.upper()
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip().str.upper()
    return df

def extract_tags(sumario):
    import re
    if not isinstance(sumario, str):
        return []
    tags = re.findall(r'\[([^\]]+)\]', sumario)
    return [tag.strip() for tag in tags]

def extrair_codigo_bomba(desc):
    import re
    if not isinstance(desc, str):
        return ''
    desc = desc.strip()
    if desc.startswith('BOMBA MEDIDORA DE COMBUSTIVEIS LIQUIDOS'):
        partes = desc.split('-')
        if len(partes) > 1:
            return partes[1].strip()
    return ''

def soma_um(x):
    try:
        return str(int(x) + 1) if x != '' else ''
    except:
        return ''

def dias_uteis(inicio, fim):
    try:
        dt_inicio = pd.to_datetime(inicio, dayfirst=True, errors='coerce')
        dt_fim = pd.to_datetime(fim, dayfirst=True, errors='coerce')
        if pd.isna(dt_inicio):
            return ''
        if pd.isna(dt_fim):
            dt_fim = pd.Timestamp.now().normalize()
        return str(np.busday_count(dt_inicio.date(), (dt_fim + pd.Timedelta(days=1)).date()))
    except:
        return ''

def substituir_nans(df, colunas=None):
    if colunas is None:
        return df.replace([np.nan, 'NAN', 'nan'], '', regex=True)
    for col in colunas:
        if col in df.columns:
            df[col] = df[col].replace([np.nan, 'NAN', 'nan'], '', regex=True)
    return df

def exibir_logo_sidebar(path_logo, largura=200):
    with open(path_logo, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    st.sidebar.markdown(
        f"""
        <div style=\"display: flex; justify-content: center;\">
            <img src=\"data:image/png;base64,{encoded}\" width=\"{largura}\">\n        </div>
        """,
        unsafe_allow_html=True
    )

def kpi_section(df):
    total = len(df)
    abertos = (df['STATUS'] == 'ABERTO').sum()
    fechados = (df['STATUS'] != 'ABERTO').sum()
    aging_medio = pd.to_numeric(df['AGING'], errors='coerce').mean()
    pct_garantia = (df['GARANTIA'] == 'DENTRO').mean() * 100
    pct_rtm = (df['RTM'] == 'SIM').mean() * 100
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric('Total de Chamados', total)
    col2.metric('Abertos', abertos)
    col3.metric('Fechados', fechados)
    col4.metric('Aging Médio (dias)', f"{aging_medio:.1f}" if not pd.isna(aging_medio) else '-')
    col5.metric('% Dentro da Garantia', f"{pct_garantia:.1f}%")
    col6.metric('% RTM', f"{pct_rtm:.1f}%")

def formatar_data_excel(val):
    if hasattr(val, 'strftime'):
        return val.strftime('%d/%m/%Y')
    if isinstance(val, (float, int)):
        try:
            return (pd.to_datetime('1899-12-30') + pd.to_timedelta(val, 'D')).strftime('%d/%m/%Y')
        except Exception:
            return str(val)
    if isinstance(val, str):
        try:
            fval = float(val.replace(',', '.'))
            return (pd.to_datetime('1899-12-30') + pd.to_timedelta(fval, 'D')).strftime('%d/%m/%Y')
        except Exception:
            try:
                dt = pd.to_datetime(val, dayfirst=True, errors='coerce')
                if pd.isna(dt):
                    return val
                return dt.strftime('%d/%m/%Y')
            except Exception:
                return val
    return ''

def main():
    df = load_and_merge_chamados()
    o2c_df = load_o2c()[['NUM_SERIAL', 'RTM', 'DT_NUM_NF', 'GARANTIA']]
    df = df.merge(o2c_df, how='left', left_on='CHASSI', right_on='NUM_SERIAL', suffixes=('', '_O2C'))
    df['TAGS'] = df['SUMÁRIO'].apply(extract_tags)
    df['CHAMADO'] = df['SS']
    df['RTM'] = df['RTM_O2C'].str.strip().str.upper().where(
        df['RTM_O2C'].str.strip().str.upper().isin(['SIM', 'NÃO']), 'NÃO'
    )
    df = df.drop(columns=['RTM_O2C'])
    df['ESPECIALISTA'] = df['MANTENEDOR'].replace(de_para_especialista).fillna('')
    df['PROPRIETÁRIO'] = df['PROPRIETÁRIO'].replace(de_para_proprietario).fillna('')
    df['MANTENEDOR'] = df['MANTENEDOR'].replace(de_para_mantenedor).fillna('')
    df['INÍCIO'] = df['DATA']
    df['FIM'] = df['RESOLVIDO']
    dt_inicio = pd.to_datetime(df['INÍCIO'], dayfirst=True, errors='coerce').dt.normalize()
    dt_fim = pd.to_datetime(df['FIM'], dayfirst=True, errors='coerce').dt.normalize()
    hoje = pd.Timestamp.now().normalize()
    dt_fim_corrigido = dt_fim.copy()
    mask_aberto_sem_fim = (df['STATUS'] == 'ABERTO') & (df['FIM'].isna() | (df['FIM'] == ''))
    dt_fim_corrigido[mask_aberto_sem_fim] = hoje
    aging_calc = pd.Series([
        (f - i).days if pd.notna(i) and pd.notna(f) else pd.NA
        for i, f in zip(dt_inicio, dt_fim_corrigido)
    ])
    df['AGING'] = aging_calc.astype('Int64')
    dt_nf = pd.to_datetime(df['DT_NUM_NF'], dayfirst=True, errors='coerce')
    garantia_dias = pd.to_numeric(df['GARANTIA'], errors='coerce')
    garantia_final = dt_nf + pd.to_timedelta(garantia_dias, unit='D')
    dentro = (dt_inicio <= garantia_final)
    df['FIM_GARANTIA'] = garantia_final.dt.strftime('%d/%m/%Y')
    df['GARANTIA'] = np.where(dt_inicio.notna() & garantia_final.notna(), np.where(dentro, 'DENTRO', 'FORA'), '')
    if 'ORDEM' not in df.columns:
        df['ORDEM'] = ''
    if 'DESCRIÇÃO.1' in df.columns:
        df['COD_BOMBA'] = df['DESCRIÇÃO.1'].apply(extrair_codigo_bomba)
    else:
        df['COD_BOMBA'] = ''
    columns = [
        'TAGS', 'CHAMADO', 'CHASSI', 'SÉRIE', 'ORDEM', 'COD_BOMBA', 'RTM', 'ESPECIALISTA', 'PROPRIETÁRIO', 'MANTENEDOR',
        'TIPO', 'SERVIÇO', 'PROBLEMA', 'RESOLUÇÃO', 'CLIENTE', 'INÍCIO', 'FIM', 'SUMÁRIO', 'AGING', 'FIM_GARANTIA', 'GARANTIA', 'STATUS'
    ]
    search = st.text_input("PESQUISAR EM TODOS OS CAMPOS")
    todas_tags = sorted(set(tag for tags in df['TAGS'] for tag in tags))
    filtros = sidebar_filters(df, todas_tags)
    df_filtrado = aplicar_filtros(
        df,
        filtros["tags_selecionadas"],
        filtros["selecoes"],
        termo_pesquisa=search,
        status_selecionado=filtros.get("status_selecionado", "GERAL"),
        data_inicio=filtros.get("data_inicio"),
        data_fim=filtros.get("data_fim")
    )
    df_display = df_filtrado[columns].copy()
    mask_aging_vazio = df_display['AGING'].isna() & df_display['INÍCIO'].notna() & (df_display['INÍCIO'] != '')
    dt_inicio_safeguard = pd.to_datetime(df_display.loc[mask_aging_vazio, 'INÍCIO'], dayfirst=True, errors='coerce').dt.normalize()
    dt_fim_safeguard = pd.to_datetime(df_display.loc[mask_aging_vazio, 'FIM'], dayfirst=True, errors='coerce').dt.normalize()
    dt_fim_safeguard = dt_fim_safeguard.fillna(hoje)
    aging_safeguard = [
        (f - i).days if pd.notna(i) and pd.notna(f) else pd.NA
        for i, f in zip(dt_inicio_safeguard, dt_fim_safeguard)
    ]
    df_display.loc[mask_aging_vazio, 'AGING'] = pd.Series(aging_safeguard, index=df_display.loc[mask_aging_vazio].index).astype('Int64')
    # Recalcule AGING na tabela final a partir das datas INÍCIO e FIM
    def calc_aging(row):
        try:
            ini = pd.to_datetime(row['INÍCIO'], dayfirst=True, errors='coerce')
            fim = pd.to_datetime(row['FIM'], dayfirst=True, errors='coerce')
            if pd.isna(ini):
                return ''
            if pd.isna(fim):
                if str(row.get('STATUS', '')).strip().upper() == 'ABERTO':
                    fim = pd.Timestamp.now().normalize()
                else:
                    return ''
            return str((fim - ini).days)
        except Exception:
            return ''
    df_display['AGING'] = df_display.apply(calc_aging, axis=1)
    df_display = substituir_nans(df_display)
    # Remover a coluna AGING da tabela e renomear DIAS_UTEIS para AGING
    if 'AGING' in df_display.columns:
        df_display = df_display.drop(columns=['AGING'])
    idx_fim = df_display.columns.get_loc('FIM')
    df_display.insert(idx_fim + 1, 'AGING', df_display.apply(lambda row: dias_uteis(row['INÍCIO'], row['FIM']), axis=1))
    # Só depois formate as datas para string para exibição
    df_display['FIM'] = df_display['FIM'].apply(formatar_data_excel)
    df_display['INÍCIO'] = df_display['INÍCIO'].apply(formatar_data_excel)
    st.title('Relatório de Chamados de Serviços')
    exibir_logo_sidebar("logo_dfs.png")
    kpi_section(df_display)
    st.dataframe(df_display, use_container_width=True)
    # --- Performance dos Proprietários (L1) ---
    st.markdown("## Performance dos Proprietários (L1)")
    fig_prop = vz.bar_chart_aging_proprietario(df_display)
    st.plotly_chart(fig_prop, use_container_width=True)
    # --- Performance dos Especialistas (L1) ---
    st.markdown("## Performance dos Especialistas (L1)")
    fig_esp = vz.bar_chart_aging_especialista(df_display)
    st.plotly_chart(fig_esp, use_container_width=True)
    # --- Performance dos Mantenedores (L1) ---
    st.markdown("## Performance dos Mantenedores (L1)")
    fig_mant = vz.bar_chart_aging_mantenedor(df_display)
    st.plotly_chart(fig_mant, use_container_width=True)
    colunas_texto = ['FIM', 'INÍCIO', 'RESOLVIDO', 'SUMÁRIO', 'DESCRIÇÃO.1', 'ORDEM', 'SÉRIE', 'PROPRIETÁRIO', 'MANTENEDOR', 'ESPECIALISTA', 'CLIENTE', 'TIPO', 'SERVIÇO', 'PROBLEMA', 'RESOLUÇÃO']
    df = substituir_nans(df, colunas=colunas_texto)

if __name__ == "__main__":
    main() 