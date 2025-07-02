import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import base64

from data_loader import carregar_dados_merged, de_para_proprietario, de_para_mantenedor, de_para_especialista
from utils import extrair_tags
from auth import check_password
from filters import sidebar_filters, aplicar_filtros
import visualization as vz

st.set_page_config(page_title="Principal - Chamados de Serviços", layout="wide")

check_password()

df = carregar_dados_merged()
df["Proprietário"] = df["Proprietário"].replace(de_para_proprietario)
df["Especialista"] = df["Mantenedor"].replace(de_para_especialista).fillna("NÃO INFORMADO")
df["Mantenedor"] = df["Mantenedor"].replace(de_para_mantenedor).fillna("NÃO INFORMADO")
df.rename(columns={"SS": "Chamado"}, inplace=True)

hoje = pd.Timestamp.now()
df["Aging"] = pd.NA
mask_aberto = df["Status"] == "ABERTO"
mask_fechado = ~mask_aberto
df.loc[mask_aberto, "Aging"] = (hoje - pd.to_datetime(df.loc[mask_aberto, "Data"], dayfirst=True, errors="coerce")).dt.days
if "Aging2" in df.columns:
    df.loc[mask_fechado, "Aging"] = pd.to_numeric(df.loc[mask_fechado, "Aging1"], errors="coerce")
df["Aging"] = pd.to_numeric(df["Aging"], errors="coerce")

df["Tags"] = df["Sumário"].apply(extrair_tags)
todas_tags = sorted(set(tag for tags in df["Tags"] for tag in tags))

filter_values = sidebar_filters(df, todas_tags)
termo_pesquisa = st.text_input("Pesquisar em todos os campos")

df_filtrado = aplicar_filtros(
    df,
    filter_values["tags_selecionadas"],
    filter_values["selecoes"],
    termo_pesquisa
)

df_exibicao = df_filtrado.copy()
if termo_pesquisa:
    for col in df_exibicao.columns:
        df_exibicao[col] = df_exibicao[col].apply(lambda x: x.replace(termo_pesquisa, f"*{termo_pesquisa}") if isinstance(x, str) else x)

status_selecionado = filter_values["status_selecionado"]
if status_selecionado == "GERAL":
    df_status_filtrado = df_exibicao
else:
    df_status_filtrado = df_exibicao[df_exibicao["Status"] == status_selecionado]

CAMINHO_ARQUIVO = "chamados.csv"
timestamp = os.path.getmtime(CAMINHO_ARQUIVO)
data_modificacao = datetime.fromtimestamp(timestamp) - timedelta(hours=3)
data_formatada = data_modificacao.strftime("%d/%m/%Y %H:%M")
st.markdown(f"⏒ **Última atualização do arquivo:** {data_formatada}")

def exibir_logo_sidebar(path_logo, largura=200):
    with open(path_logo, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    st.sidebar.markdown(
        f"""
        <div style=\"display: flex; justify-content: center;\">
            <img src=\"data:image/png;base64,{encoded}\" width=\"{largura}\">
        </div>
        """,
        unsafe_allow_html=True
    )

exibir_logo_sidebar("logo_dfs.png")

st.title("Chamados de Serviços")
st.markdown(f"**Total: {len(df_status_filtrado)} chamados**")
if df_status_filtrado.empty:
    st.info("Nenhum chamado encontrado com os filtros aplicados.")
else:
    colunas_exibir = [
        "Tags", "Chamado", "Chassi", "RTM", "Especialista", "Proprietário", "Mantenedor",
        "Tipo", "Serviço", "Problema", "Resolução", "Cliente",
        "Data", "Sumário", "Aging"
    ]
    if "Resolvido" in df_status_filtrado.columns:
        colunas_exibir.insert(colunas_exibir.index("Data") + 1, "Resolvido")
    st.dataframe(df_status_filtrado[colunas_exibir])

    st.markdown("# Quantidade")
    for campo in ["Proprietário", "Mantenedor", "Especialista"]:
        st.subheader(f"Quantidade por {campo}")
        st.plotly_chart(vz.bar_chart_count(df_status_filtrado, campo), use_container_width=True)

    st.markdown("# Agings")
    for campo in ["Proprietário", "Mantenedor", "Especialista"]:
        st.subheader(f"Aging por {campo}")
        st.plotly_chart(vz.bar_chart_aging(df_status_filtrado, campo), use_container_width=True)

    st.subheader("Distribuição de Aging (Dias)")
    st.plotly_chart(vz.pie_chart_aging(df_status_filtrado), use_container_width=True)

st.subheader("Distribuição de Tags")
tags_contagem = (
    df_status_filtrado["Tags"]
    .explode()
    .value_counts()
    .reindex(todas_tags, fill_value=0)
    .sort_values(ascending=False)
)
tags_contagem = tags_contagem[tags_contagem > 0]
if not tags_contagem.empty:
    st.plotly_chart(vz.bar_chart_tags(tags_contagem), use_container_width=True)
else:
    st.info("Nenhuma tag encontrada com valores acima de 0.")

st.subheader("Evolução do Aging Médio por Mês")
st.plotly_chart(vz.line_chart_aging(df_status_filtrado, "Proprietário"), use_container_width=True)
st.plotly_chart(vz.line_chart_aging(df_status_filtrado, "Especialista"), use_container_width=True)

st.markdown("---")
st.markdown(
    """
    #### Contato
    Um projeto do time de ***Serviços - Dover Fueling Solutions***

    Contato: [Cauã Almeida (BI)](mailto:c-calmeida@doverfs.com), ou, no caso de ausência, [Fernanda Barbieri (Gerente)](mailto:fernanda.barbieri@doverfs.com).
    """
) 