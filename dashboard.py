import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import re
import os
from datetime import datetime, timedelta

# ----------------------------
# Procedimentos de Segurança
# ----------------------------

# Configurações de cache para melhorar a performance
@st.cache_data
def carregar_dados():
    df = pd.read_csv("chamados.csv", sep=";", encoding="utf-8")
    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
    df["Resolvido"] = pd.to_datetime(df["Resolvido"], dayfirst=True, errors="coerce")
    return df
# Carrega os dados apenas uma vez
df = carregar_dados()
# 🔐 Senha!
def check_password():
    def password_entered():
        if st.session_state["password"] == "Q5sU1P5jcg25":
            st.session_state["authenticated"] = True
        else:
            st.session_state["authenticated"] = False

    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.text_input("Senha:", type="password", on_change=password_entered, key="password")
        st.stop()

check_password()

# ----------------------------
# Configuração Inicial
# ----------------------------
st.set_page_config(page_title="Chamados de Serviços - 2025", layout="wide")
st.title("Chamados de Serviços - 2025")

# ----------------------------
# Última Atualização do Arquivo
# ----------------------------
CAMINHO_ARQUIVO = "chamados.csv"
timestamp = os.path.getmtime(CAMINHO_ARQUIVO)
data_modificacao = datetime.fromtimestamp(timestamp) - timedelta(hours=3)
data_formatada = data_modificacao.strftime("%d/%m/%Y %H:%M")
st.markdown(f"🕒 **Última atualização do arquivo:** {data_formatada}")
# Exibe no topo da aplicação
st.markdown(f"🕒 **Última atualização do arquivo:** {data_modificacao}")

# ----------------------------
# Carregamento e Limpeza de Dados
# ----------------------------
df = pd.read_csv("chamados.csv", sep=";", encoding="utf-8")
df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
df["Resolvido"] = pd.to_datetime(df["Resolvido"], dayfirst=True, errors="coerce")
df["Chassi"] = df["Chassi"].fillna("").astype(str).str.strip().str.replace(".0", "", regex=False).replace("", "N/A")
df["RTM"] = df["RTM"].apply(lambda x: "SIM" if "RTM" in str(x).upper() else "NÃO")

# ----------------------------
# Padronização de Dados
# ----------------------------
# Dicionários de substituição

de_para_proprietario = {
    "Oliveira, Cassio Fonseca Farias de (Cassio)": "CÁSSIO",
    "Simões, Wanderley": "WANDERLEY",
    "Santos de Lima, Antônio Vinicius dos (Antônio Vinicius dos Santos de Lima)": "ANTÔNIO",
    "Nogueira, Victor M": "VICTOR",
    "QUIRINO, RICARDO": "RICARDO",
    "Ferreira De Araujo, Jose Roberto": "JOSÉ ROBERTO",
    "Lucas, Jefferson Monteiro da Silva": "JEFFERSON LUCAS",
    "Silva, Márcio (Contractor) (Márcio (Contractor) Silva)": "MÁRCIO SILVA",
    "Longo, Dante M (Dante M. Longo)": "INDEFINIDO",
    "dos Santos, Otacílio (Contractor) (Otacílio (Contractor) dos Santos)": "OTACÍLIO",
    "de Freitas, Fabio (Contractor) (Fabio (Contractor) de Freitas)": "FÁBIO",
    "Araujo, Alessandro Fabiano De": "ALESSANDRO",
    "Calado, Marcos Aurelio Cavalcanti": "MARCOS",
}

de_para_mantenedor = {
    "MACIEL, FONTES FRANJAKSON - NTEC INSTALACOES HIDRAULICAS LTDA.":"NTEC",
    "SALES, LUIZ - SOCIEDADE DE MANUTENCAO TECNICA SOMATEC LTDA":"SOMATEC",
    "HENRIQUE, THIAGO - CM2 COMERCIO E SERVICOS LTDA EPP":"CM2",
    "EVANDRO, - FLOTECK COMERCIO E SERVICOS ESPECIALIZADOS LTDA":"FLOTECK",
    "RIGOBERTO, FRANCISCO - F R RIBEIRO MECANICA SAO CRISTOVAO SERVICOS ELETRONICOS LTDA":"MEC. SÃO CRISTÓVÃO",
    "ESDRAS ARR, - E PASCOAL COM SERV E ASSIST TE":"PASCOAL",
    "SALES, - S L INSTALACAO P POSTOS DE SE":"SL INSTALAÇÃO",
    "NEVES, - TEKSUL MANUTENÇÃO DE BOMBAS PARA COMBUSTÍVEL EIRELI":"TEKSUL",
    "MOURA, ALEXSANDRE - ALEXSANDRE LIZ DE MOURA":"BOMBAGAS",
    "JESSICA, THAINA - THAINA JESSICA DA COSTA RODRIGUES":"PETROPOSTO",
    "SERGIO, - SERVTEC COMERCIO E SERVICO LTD":"SERVTEC",
    "SALES, LUIZ - TECNICA L S COMERCIAL E SERVI":"TECNICA LS",
    "PINTO, ANDREZA - C A INSTALACAO E MANUTENCAO EM POSTOS DE COMBUSTIVEIS LTDA":"C A INSTALAÇÃO",
    "LUCIANA, - ATENDE COMERCIO DE PECAS E CON":"ATENDE",
    "SILVA, REGINALD - SHEKINAH SHADDAI MANUTENCAO LTD":"SHEKINAH",
    "SRA.FERNAN, - FORTE INSTALACAO E MANUTENCAO":"FORTE",
    "FREITAS, LUCIANO - BHPUMP DO BRASIL LTDA":"BHPUMP",
    "SANTOS, VANDERLEY - VANDERLEY PEREIRA DOS SANTOS":"PETROLINK",
    "FAVERO, PAULA - CENTURY FLEX COMERCIO DE PECAS PARA BOMBAS DE COMBUSTIVEIS LTDA":"CENTURY",
    "ROCHA, ROBERTO - SIGNOS MRWG MANUTENCAO LTDA ME":"SIGNOS",
    "GONZAGA, MANOEL - LMG COMERCIO SERVICOS E MANUTENCAO LTDA":"LMG",
    "Mendes, Andre - M E A SILVA MENDES MANUTENCAO E REPARACAO ME":"MERIVA",
    "CAMPOS, SANDREIA - CONSTRUTORA CENTAURUS DO BRASIL LTDA":"CENTAURUS",
    "UNKNOWN, CASSIA - ARBTEK SOLUCOES INTEGRADAS LTDA":"ARBTEK",
    "COSTA, GUSTAVO - CONSERTEC BALANCAS E BOMBAS LTDA ME":"CONSERTEC",
    "JUNIOR, LUIZ ZORZI - ZORZITEC CONSULTORIA EIRELI ME":"ZORZITEC",
    "MENEZES SOARES, ALTEVIR - JUMPER SERVICOS TECNICOS DE BOMBAS DE COMBUSTIVEIS LTDA":"JUMPER",
    "DE MATTOS, PERI JACI - MULTITEC SOLUCOES EM POSTOS AUTOMOTIVOS LTDA":"MULTITEC",
    "., Romario - DINIZ ASSISTENCIA TECNICA LTDA":"DINIZ",
    "Serafim, Joao - JS DE SOUSA MANUTENCAO ME":"JS MANUTENÇÃO",
    "Silva, Rodrigo - EBENEZER COMECIO E MANUTENCAO":"EBENEZER",
    "Neto, Jorge - EWJ INSTALACAO E MANUTENCAO DE EQUIPAMENTOS PARA POSTOS DE COMBUSTIVEIS LTDA":"EWJ",
    "AMORIM DE OLIVE, LEONORA - L DE ALMEIDA FERREIRA LTDA":"NOVA ERA",
    "RAMOS, CARLOS - MECANICA DE BOMBAS RAMOS LTDA":"MEC. BOMBAS RAMOS",
    "COSTA, HELIO - REAL MANUTENCAO E INSTALACAO EM POSTOS E SERVICOS LTDA":"REAL MANUTENÇÃO",
    "ANTONIO, - A DE JESUS E SOUZA DOURADO LTD":"FUTURA",
    "RODRIGUES, RIVALDO - SMR MANUTENCAO E REPARACAO EIRELI ME":"SMR",
    "amaro, florisvaldo - SERVITEC - MANUTENCAO E INSTALACAO DE EQUIPAMENTOS EM POSTOS DE COMBUSTIVEIS LTDA":"SERVITEC",
    "SR. LAZARO, - LAZARO MARTINS SILVA SOUZA ME":"LÁZARO",
    "Belarmino, Marcos - SOS SYSTEM TECNOLOGIA EM INFORMATICA LTDA":"SOS SYSTEM",
    "DO MONTE, CARLOS JORGE - PERMANENTE MANUTENCAO DE MAQUINAS E EQUIPAMENTOS EIRELI":"PERMANENTE",
    "MENDES, - IMASEL LTDA":"IMASEL",
    "ANDRADE, JAIR - JMA PRESTADORA DE SERVICOS LTDA":"JMA",
    "ANDREZA, - UBERPOSTOS LOGISTICA E EQUIP":"UBERPOSTOS",
    "LUZENILDO, - DANTEC ASSITENCIA TECNICA LTDA":"DANTEC",
    "SANTANA, DORLAN - TECHPETRO SOLUCOES SERVICOS DE MANUTENCAO LTDA":"TECHPETRO",
    "Soares, Altevir - JUMPER MATERIAIS E SERVICOS PARA POSTOS DE COMBUSTIVEIS EIRELI ME":"JUMPER",
}

df["Proprietário"] = df["Proprietário"].replace(de_para_proprietario)
df["Mantenedor"] = df["Mantenedor"].replace(de_para_mantenedor).fillna("NÃO INFORMADO")
df.rename(columns={"SS": "Chamado"}, inplace=True)

# ----------------------------
# Cálculo de Aging
# ----------------------------
hoje = pd.Timestamp.now()
df["Aging"] = (hoje - df["Data"]).dt.days
df.loc[df["Status"] != "ABERTO", "Aging"] = None

# ----------------------------
# Extração de Tags
# ----------------------------
def extrair_tags(texto):
    if pd.isna(texto): return []
    tags = re.findall(r"\[(.*?)\]", texto)
    tags = [tag.strip().upper() for tag in tags]
    return list(set(tags)) if tags else ["Sem Tags"]

df["Tags"] = df["Sumário"].apply(extrair_tags)
todas_tags = sorted(set(tag for tags in df["Tags"] for tag in tags))

# ----------------------------
# Formatação de Datas
# ----------------------------
df["Data"] = df["Data"].dt.strftime("%d/%m/%Y")
df["Resolvido"] = df["Resolvido"].dt.strftime("%d/%m/%Y")

# ----------------------------
# Filtros - Barra Lateral
# ----------------------------
st.sidebar.header("Filtros")
todas_tags = sorted(todas_tags, key=lambda x: df["Tags"].apply(lambda tags: x in tags).sum(), reverse=True)
tags_selecionadas = st.sidebar.multiselect("Filtrar por tags", todas_tags)

# Filtros diversos
filtros = {
    "Proprietário": sorted(df["Proprietário"].dropna().unique()),
    "Mantenedor": sorted(df["Mantenedor"].dropna().unique()),
    "RTM": sorted(df["RTM"].dropna().unique()),
    "Tipo": sorted(df["Tipo"].dropna().unique()),
    "Serviço": sorted(df["Serviço"].dropna().unique()),
    "Problema": sorted(df["Problema"].dropna().unique()),
    "Resolução": sorted(df["Resolução"].dropna().unique()),
}

selecoes = {k: st.sidebar.multiselect(k, v) for k, v in filtros.items()}

# Campo de busca global
termo_pesquisa = st.text_input("Pesquisar em todos os campos")

# ----------------------------
# Aplicação de Filtros
# ----------------------------
df_filtrado = df.copy()

if tags_selecionadas:
    df_filtrado = df_filtrado[df_filtrado["Tags"].apply(lambda tags: all(tag in tags for tag in tags_selecionadas))]

for coluna, valores in selecoes.items():
    if valores:
        df_filtrado = df_filtrado[df_filtrado[coluna].isin(valores)]

# Busca global com destaque
if termo_pesquisa:
    df_filtrado = df_filtrado[df_filtrado.apply(lambda row: row.astype(str).str.contains(termo_pesquisa, case=False).any(), axis=1)]
    df_exibicao = df_filtrado.copy()
    for col in df_exibicao.columns:
        df_exibicao[col] = df_exibicao[col].apply(lambda x: re.sub(f"(?i)({re.escape(termo_pesquisa)})", r"*\1", str(x)))
else:
    df_exibicao = df_filtrado

# ----------------------------
# Abas: Abertos / Fechados
# ----------------------------
tabs = st.tabs(["Chamados Abertos", "Chamados Fechados"])

# Função para exibir dataframes e gráficos

def exibir_abas(df_alvo, titulo):
    st.subheader(titulo)
    st.markdown(f"**Total: {len(df_alvo)} chamados**")

    if df_alvo.empty:
        st.info("Nenhum chamado encontrado com os filtros aplicados.")
        return

    colunas_exibir = [
        "Tags", "Chamado", "Chassi", "RTM", "Proprietário", "Mantenedor",
        "Tipo", "Serviço", "Problema", "Resolução", "Cliente",
        "Data", "Sumário", "Aging"
    ]
    if "Resolvido" in df_alvo.columns:
        colunas_exibir.insert(colunas_exibir.index("Data") + 1, "Resolvido")

    st.dataframe(df_alvo[colunas_exibir])

    for campo in ["Proprietário", "Mantenedor", "Tipo"]:
        st.subheader(f"Volume por {campo}")
        st.bar_chart(df_alvo[campo].value_counts())

    st.subheader("Distribuição de Aging")
    fig, ax = plt.subplots()
    ax.hist(df_alvo["Aging"].dropna(), bins=20, color='steelblue', edgecolor='black')
    ax.set_xlabel("Dias")
    ax.set_ylabel("Número de Chamados")
    ax.set_title("Histograma de Aging")
    st.pyplot(fig)

# Exibição por abas
with tabs[0]:
    exibir_abas(df_exibicao[df_exibicao["Status"] == "ABERTO"], "Chamados Abertos")

with tabs[1]:
    exibir_abas(df_exibicao[df_exibicao["Status"] != "ABERTO"], "Chamados Fechados")