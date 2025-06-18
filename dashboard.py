import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import re
import os
from datetime import datetime, timedelta
import plotly.express as px
import base64
import json

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

aba = st.sidebar.radio("Selecione a aba:", ["📊 Principal", "🗺️ Parque Instalado (Chassis/Estado)"])

# ----------------------------
# Configuração Inicial
# ----------------------------

def extrair_estado(endereco):
    match = re.search(r",\s*([A-Z]{2}),\s*BR", str(endereco))
    return match.group(1) if match else None

def extrair_pais(endereco):
    match = re.findall(r",\s*([A-Z]{2})\s*$", str(endereco).strip())
    return match[-1] if match else None

if aba == "📊 Principal":

    st.set_page_config(page_title="Chamados de Serviços - 2025", layout="wide")
    st.title("Chamados de Serviços - 2025")

    def exibir_logo_sidebar(path_logo, largura=200):
        with open(path_logo, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()
        st.sidebar.markdown(
            f"""
            <div style="display: flex; justify-content: center;">
                <img src="data:image/png;base64,{encoded}" width="{largura}">
            </div>
            """,
            unsafe_allow_html=True
        )

    exibir_logo_sidebar("logo_dfs.png")

    # ----------------------------
    # Última Atualização do Arquivo
    # ----------------------------
    CAMINHO_ARQUIVO = "chamados.csv"
    timestamp = os.path.getmtime(CAMINHO_ARQUIVO)
    data_modificacao = datetime.fromtimestamp(timestamp) - timedelta(hours=3)
    data_formatada = data_modificacao.strftime("%d/%m/%Y %H:%M")
    st.markdown(f"🕒 **Última atualização do arquivo:** {data_formatada}")

    # ----------------------------
    # Carregamento e Limpeza de Dados
    # ----------------------------
    df = pd.read_csv("chamados.csv", sep=";", encoding="utf-8")
    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
    df["Resolvido"] = pd.to_datetime(df["Resolvido"], dayfirst=True, errors="coerce")
    df["Chassi"] = df["Chassi"].fillna("").astype(str).str.strip().str.replace(".0", "", regex=False).replace("", "N/A")
    df["RTM"] = df["RTM"].apply(lambda x: "SIM" if "RTM" in str(x).upper() else "NÃO")

    hoje = pd.Timestamp.now()

    df["Aging"] = pd.NA  # ou None

    mask_aberto = df["Status"] == "ABERTO"
    mask_fechado = ~mask_aberto

    df.loc[mask_aberto, "Aging"] = (hoje - df.loc[mask_aberto, "Data"]).dt.days
    df.loc[mask_fechado, "Aging"] = df.loc[mask_fechado, "Aging2"].astype(float)

    df["Aging"] = pd.to_numeric(df["Aging"], errors="coerce")

    # ----------------------------
    # Padronização de Dados
    # ----------------------------
    # Dicionários de substituição

    de_para_proprietario = {
        "Oliveira, Cassio Fonseca Farias de (Cassio)": "CÁSSIO OLIVEIRA",
        "Simões, Wanderley": "WANDERLEY SIMÕES",
        "Santos de Lima, Antônio Vinicius dos (Antônio Vinicius dos Santos de Lima)": "ANTÔNIO DOS SANTOS",
        "Nogueira, Victor M": "VICTOR NOGUEIRA",
        "QUIRINO, RICARDO": "RICARDO QUIRINO",
        "Ferreira De Araujo, Jose Roberto": "JOSÉ ROBERTO",
        "Lucas, Jefferson Monteiro da Silva": "JEFFERSON LUCAS",
        "Silva, Márcio (Contractor) (Márcio (Contractor) Silva)": "MÁRCIO SILVA",
        "Longo, Dante M (Dante M. Longo)": "DANTE LONGO",
        "dos Santos, Otacílio (Contractor) (Otacílio (Contractor) dos Santos)": "OTACÍLIO DOS SANTOS",
        "de Freitas, Fabio (Contractor) (Fabio (Contractor) de Freitas)": "FÁBIO DE FREITAS",
        "Araujo, Alessandro Fabiano De": "ALESSANDRO ARAUJO",
        "Calado, Marcos Aurelio Cavalcanti": "MARCOS CALADO",
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

    de_para_especialista = {
        "PINTO, ANDREZA - C A INSTALACAO E MANUTENCAO EM POSTOS DE COMBUSTIVEIS LTDA":"LUCAS",
        "MACIEL, FONTES FRANJAKSON - NTEC INSTALACOES HIDRAULICAS LTDA.":"LUCIANO",
        "SALES, - S L INSTALACAO P POSTOS DE SE":"LUCAS",
        "SALES, LUIZ - TECNICA L S COMERCIAL E SERVI":"LUCAS",
        "GONZAGA, MANOEL - LMG COMERCIO SERVICOS E MANUTENCAO LTDA":"LUCIANO",
        "MOURA, ALEXSANDRE - ALEXSANDRE LIZ DE MOURA":"LUCAS",
        "NEVES, - TEKSUL MANUTENÇÃO DE BOMBAS PARA COMBUSTÍVEL EIRELI":"LUCAS",
        "Serafim, Joao - JS DE SOUSA MANUTENCAO ME":"LUCIANO",
        "RIGOBERTO, FRANCISCO - F R RIBEIRO MECANICA SAO CRISTOVAO SERVICOS ELETRONICOS LTDA":"LUCIANO",
        "ANDREZA, - UBERPOSTOS LOGISTICA E EQUIP":"LUCAS",
        "ANTONIO, - A DE JESUS E SOUZA DOURADO LTD":"LUCIANO",
        "SILVA, REGINALD - SHEKINAH SHADDAI MANUTENCAO LTD":"LUCIANO",
        "RAMOS, CARLOS - MECANICA DE BOMBAS RAMOS LTDA":"LUCAS",
        "amaro, florisvaldo - SERVITEC - MANUTENCAO E INSTALACAO DE EQUIPAMENTOS EM POSTOS DE COMBUSTIVEIS LTDA":"ALESSANDRO",
        "Mendes, Andre - M E A SILVA MENDES MANUTENCAO E REPARACAO ME":"LUCAS",
        "SALES, - UBERPOSTOS LOGISTICA E EQUIP":"ALESSANDRO",
        "LUCIANA, - ATENDE COMERCIO DE PECAS E CON":"LUCIANO",
        "AMORIM DE OLIVE, LEONORA - L DE ALMEIDA FERREIRA LTDA":"LUCIANO",
        "HENRIQUE, THIAGO - CM2 COMERCIO E SERVICOS LTDA EPP":"LUCAS",
        "SRA.FERNAN, - FORTE INSTALACAO E MANUTENCAO":"LUCIANO",
        "JESSICA, THAINA - THAINA JESSICA DA COSTA RODRIGUES":"LUCIANO",
        "FREITAS, LUCIANO - BHPUMP DO BRASIL LTDA":"ALESSANDRO",
        "SANTOS, VANDERLEY - VANDERLEY PEREIRA DOS SANTOS":"ALESSANDRO",
        "Silva, Rodrigo - EBENEZER COMECIO E MANUTENCAO":"LUCAS",
        "SERGIO, - SERVTEC COMERCIO E SERVICO LTD":"LUCIANO",
        "., Romario - DINIZ ASSISTENCIA TECNICA LTDA":"LUCAS",
        "UNKNOWN, CASSIA - ARBTEK SOLUCOES INTEGRADAS LTDA":"LUCAS",
        "SALES, LUIZ - SOCIEDADE DE MANUTENCAO TECNICA SOMATEC LTDA":"ALESSANDRO",
        "RODRIGUES, RIVALDO - SMR MANUTENCAO E REPARACAO EIRELI ME":"LUCIANO",
        "MENDES, - IMASEL LTDA":"LUCIANO",
        "ESDRAS ARR, - E PASCOAL COM SERV E ASSIST TE":"LUCIANO",
        "ROCHA, ROBERTO - SIGNOS MRWG MANUTENCAO LTDA ME":"ALESSANDRO",
        "DE MATTOS, PERI JACI - MULTITEC SOLUCOES EM POSTOS AUTOMOTIVOS LTDA":"LUCAS",
        "COSTA, GUSTAVO - CONSERTEC BALANCAS E BOMBAS LTDA ME":"ALESSANDRO",
        "SR. LAZARO, - LAZARO MARTINS SILVA SOUZA ME":"LUCAS",
        "COSTA, HELIO - REAL MANUTENCAO E INSTALACAO EM POSTOS E SERVICOS LTDA":"LUCIANO",
        "Neto, Jorge - EWJ INSTALACAO E MANUTENCAO DE EQUIPAMENTOS PARA POSTOS DE COMBUSTIVEIS LTDA":"LUCIANO",
        "CAMPOS, SANDREIA - CONSTRUTORA CENTAURUS DO BRASIL LTDA":"LUCIANO",
        "JUNIOR, LUIZ ZORZI - ZORZITEC CONSULTORIA EIRELI ME":"LUCAS",
        "MENEZES SOARES, ALTEVIR - JUMPER SERVICOS TECNICOS DE BOMBAS DE COMBUSTIVEIS LTDA":"LUCIANO",
        "DO MONTE, CARLOS JORGE - PERMANENTE MANUTENCAO DE MAQUINAS E EQUIPAMENTOS EIRELI":"LUCIANO",
        "ANDRADE, JAIR - JMA PRESTADORA DE SERVICOS LTDA":"LUCAS",
        "Belarmino, Marcos - SOS SYSTEM TECNOLOGIA EM INFORMATICA LTDA":"LUCAS",
        "EVANDRO, - FLOTECK COMERCIO E SERVICOS ESPECIALIZADOS LTDA":"LUCAS",
        "FAVERO, PAULA - CENTURY FLEX COMERCIO DE PECAS PARA BOMBAS DE COMBUSTIVEIS LTDA":"LUCAS",
        "LUZENILDO, - DANTEC ASSITENCIA TECNICA LTDA":"LUCIANO",
        "SANTANA, DORLAN - TECHPETRO SOLUCOES SERVICOS DE MANUTENCAO LTDA":"LUCIANO",
    }

    df["Especialista"] = df["Mantenedor"].replace(de_para_especialista).fillna("NÃO INFORMADO")
    # Se não estiver no dicionário, também substitui por "NÃO INFORMADO"
    df["Proprietário"] = df["Proprietário"].replace(de_para_proprietario)
    df["Mantenedor"] = df["Mantenedor"].replace(de_para_mantenedor).fillna("NÃO INFORMADO")
    df.rename(columns={"SS": "Chamado"}, inplace=True)
    # 1º Cria a coluna "Especialista"


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
        "Especialista": sorted(df["Especialista"].dropna().unique()),
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
    # Filtro de Status
    # ----------------------------
    status_selecionado = st.sidebar.selectbox(
        "Status",
        options=["GERAL", "ABERTO", "FECHADO"],
        index=1  # "ABERTO" como padrão
    )

    # Aplica filtro pelo status
    if status_selecionado == "GERAL":
        df_status_filtrado = df_exibicao
    else:
        df_status_filtrado = df_exibicao[df_exibicao["Status"] == status_selecionado]

    # ----------------------------
    # Indicadores de Aging
    # ----------------------------
    df_status_filtrado["Aging"] = pd.to_numeric(df_status_filtrado["Aging"], errors="coerce")

    # Proprietário
    aging_stats_proprietario = df_status_filtrado.groupby("Proprietário")["Aging"].agg(["mean", "count"])
    aging_stats_proprietario_filtrado = aging_stats_proprietario[aging_stats_proprietario["count"] >= 2]
    proprietario_maior_aging = aging_stats_proprietario_filtrado["mean"].idxmax()
    maior_aging_proprietario = aging_stats_proprietario_filtrado["mean"].max()

    # Especialista
    aging_stats_especialista = df_status_filtrado.groupby("Especialista")["Aging"].agg(["mean", "count"])
    aging_stats_especialista_filtrado = aging_stats_especialista[aging_stats_especialista["count"] >= 2]
    especialista_maior_aging = aging_stats_especialista_filtrado["mean"].idxmax()
    maior_aging_especialista = aging_stats_especialista_filtrado["mean"].max()

    # Mantenedor
    aging_stats_mantenedor = df_status_filtrado.groupby("Mantenedor")["Aging"].agg(["mean", "count"])
    aging_stats_mantenedor_filtrado = aging_stats_mantenedor[aging_stats_mantenedor["count"] >= 2]
    mantenedor_maior_aging = aging_stats_mantenedor_filtrado["mean"].idxmax()
    maior_aging_mantenedor = aging_stats_mantenedor_filtrado["mean"].max()

    # Maior Aging Médio
    maior_aging_valor = max(maior_aging_proprietario, maior_aging_especialista)

    # Markdown de resumo
    st.markdown("### Resumo (Aging)")
    st.markdown(f"- **Aging Médio (Especialistas):** {aging_stats_especialista['mean'].mean():.1f} dias")
    st.markdown(f"- **Aging Médio (Proprietário):** {aging_stats_proprietario['mean'].mean():.1f} dias")
    st.markdown(f"- **Aging Médio (Mantenedores):** {aging_stats_mantenedor['mean'].mean():.1f} dias")
    st.markdown(f"- **Maior Aging Médio (SAW)**: `{mantenedor_maior_aging}` com {maior_aging_mantenedor:.1f} dias")
    st.markdown(f"- **Maior Aging Médio (Dover):** `{proprietario_maior_aging}` e `{especialista_maior_aging}` com {maior_aging_valor:.1f} dias")

    # Exibe os chamados conforme o status selecionado
    st.subheader(f"Chamados {status_selecionado.capitalize()}")
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
            contagem = df_status_filtrado[campo].value_counts().sort_values(ascending=False)
            fig_bar = px.bar(
                x=contagem.index,
                y=contagem.values,
                labels={"x": campo, "y": "Quantidade", "color": campo},
                color=contagem.values,
                color_continuous_scale=px.colors.sequential.Blues
            )
            fig_bar.update_layout(
                xaxis_title=campo,
                yaxis_title="Quantidade",
                title=f"Distribuição por {campo}",
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("# Agings")

        for campo in ["Proprietário", "Mantenedor", "Especialista"]:
            st.subheader(f"Aging por {campo}")
            aging_medio = df_status_filtrado.groupby(campo)["Aging"].mean().sort_values(ascending=False)
            fig_bar = px.bar(
                x=aging_medio.index,
                y=aging_medio.values,
                labels={"x": campo, "y": "Aging Médio (Dias)", "color": campo},
                color=aging_medio.values,
                color_continuous_scale=px.colors.sequential.Blues
            )
            fig_bar.update_layout(
                xaxis_title=campo,
                yaxis_title="Aging Médio (Dias)",
                title=f"Distribuição por {campo}",
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("Distribuição de Aging (Dias)")
        # Primeiro, converte para número (coerção transforma erros em NaN)
        df_status_filtrado["Aging"] = pd.to_numeric(df_status_filtrado["Aging"], errors="coerce")

        # Agora pode aplicar a categorização com segurança
        aging_categorias = df_status_filtrado["Aging"].dropna().apply(
            lambda x: "Até 7" if x <= 7 else ("8 a 14" if x <= 14 else ">14")
        )
        contagem_aging = aging_categorias.value_counts().reindex(["Até 7", "8 a 14", ">14"], fill_value=0)

        fig = px.pie(
            names=contagem_aging.index,
            values=contagem_aging.values,
            color=contagem_aging.index,
            color_discrete_map={
                "Até 7": "#9ac8e0",
                "8 a 14": "#3989c2",
                ">14": "#08306b"
            },
            labels={"value": "Quantidade", "names": "Intervalo de Aging", "color": "Intervalo de Aging"},
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Distribuição de Tags")

    # Conta as tags e remove as com valor 0
    tags_contagem = (
        df_status_filtrado["Tags"]
        .explode()
        .value_counts()
        .reindex(todas_tags, fill_value=0)
        .sort_values(ascending=False)
    )

    # Filtra tags com valor > 0
    tags_contagem = tags_contagem[tags_contagem > 0]

    # Só exibe o gráfico se houver dados
    if not tags_contagem.empty:
        fig_tags = px.bar(
            x=tags_contagem.index,
            y=tags_contagem.values,
            labels={"x": "Tags", "y": "Quantidade", "color": "Quantidade"},
            color=tags_contagem.values,
            color_continuous_scale=px.colors.sequential.Blues
        )
        fig_tags.update_layout(
            xaxis_title="Tags",
            yaxis_title="Quantidade",
            title="Distribuição de Tags nos Chamados",
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig_tags, use_container_width=True)
    else:
        st.info("Nenhuma tag encontrada com valores acima de 0.")

    # ----------------------------
    # Gráficos Temporais de Aging
    # ----------------------------

    st.subheader("Evolução do Aging Médio por Mês")

    # Reconverte a data de volta para datetime para análise temporal
    df_status_filtrado["Data"] = pd.to_datetime(df_status_filtrado["Data"], dayfirst=True, errors="coerce")

    # Extrai ano-mês para agrupamento
    df_status_filtrado["AnoMes"] = df_status_filtrado["Data"].dt.to_period("M").astype(str)

    # Calcula média por Proprietário
    aging_por_proprietario = (
        df_status_filtrado
        .groupby(["AnoMes", "Proprietário"])["Aging"]
        .mean()
        .reset_index()
        .dropna()
    )

    # Gráfico Proprietário
    fig_prop = px.line(
        aging_por_proprietario,
        x="AnoMes",
        y="Aging",
        color="Proprietário",
        title="Aging Médio por Proprietário ao Longo do Tempo",
        markers=True
    )
    fig_prop.update_layout(xaxis_title="Mês", yaxis_title="Aging Médio (dias)")
    st.plotly_chart(fig_prop, use_container_width=True)

    # Calcula média por Especialista
    aging_por_especialista = (
        df_status_filtrado
        .groupby(["AnoMes", "Especialista"])["Aging"]
        .mean()
        .reset_index()
        .dropna()
    )

    # Gráfico Especialista
    fig_esp = px.line(
        aging_por_especialista,
        x="AnoMes",
        y="Aging",
        color="Especialista",
        title="Aging Médio por Especialista ao Longo do Tempo",
        markers=True
    )
    fig_esp.update_layout(xaxis_title="Mês", yaxis_title="Aging Médio (dias)")
    st.plotly_chart(fig_esp, use_container_width=True)

    # ----------------------------
    # Créditos
    # ----------------------------
    st.markdown("---")
    st.markdown(
        """
        #### Contato
        Um projeto do time de ***Serviços - Dover Fueling Solutions***

        Contato: [Cauã Almeida (BI)](mailto:c-calmeida@doverfs.com), ou, no caso de ausência, [Fernanda Barbieri (Gerente)](mailto:fernanda.barbieri@doverfs.com).
        """
    )

elif aba == "🗺️ Parque Instalado (Chassis/Estado)":
    st.set_page_config(page_title="Chamados de Serviços - 2025", layout="wide")
    st.title("Chamados de Serviços - 2025")

    def exibir_logo_sidebar(path_logo, largura=200):
        with open(path_logo, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()
        st.sidebar.markdown(
            f"""
            <div style="display: flex; justify-content: center;">
                <img src="data:image/png;base64,{encoded}" width="{largura}">
            </div>
            """,
            unsafe_allow_html=True
        )

    exibir_logo_sidebar("logo_dfs.png")

    # ----------------------------
    # Última Atualização do Arquivo
    # ----------------------------
    CAMINHO_ARQUIVO = "chamados.csv"
    timestamp = os.path.getmtime(CAMINHO_ARQUIVO)
    data_modificacao = datetime.fromtimestamp(timestamp) - timedelta(hours=3)
    data_formatada = data_modificacao.strftime("%d/%m/%Y %H:%M")
    st.markdown(f"🕒 **Última atualização do arquivo:** {data_formatada}")

    # ----------------------------
    # Carregamento e Limpeza de Dados
    # ----------------------------
    df = pd.read_csv("chamados.csv", sep=";", encoding="utf-8")
    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
    df["Resolvido"] = pd.to_datetime(df["Resolvido"], dayfirst=True, errors="coerce")
    df["Chassi"] = df["Chassi"].fillna("").astype(str).str.strip().str.replace(".0", "", regex=False).replace("", "N/A")
    df["RTM"] = df["RTM"].apply(lambda x: "SIM" if "RTM" in str(x).upper() else "NÃO")

    hoje = pd.Timestamp.now()

    df["Aging"] = pd.NA  # ou None

    mask_aberto = df["Status"] == "ABERTO"
    mask_fechado = ~mask_aberto

    df.loc[mask_aberto, "Aging"] = (hoje - df.loc[mask_aberto, "Data"]).dt.days
    df.loc[mask_fechado, "Aging"] = df.loc[mask_fechado, "Aging2"].astype(float)

    df["Aging"] = pd.to_numeric(df["Aging"], errors="coerce")

    # ----------------------------
    # Padronização de Dados
    # ----------------------------
    # Dicionários de substituição

    de_para_proprietario = {
        "Oliveira, Cassio Fonseca Farias de (Cassio)": "CÁSSIO OLIVEIRA",
        "Simões, Wanderley": "WANDERLEY SIMÕES",
        "Santos de Lima, Antônio Vinicius dos (Antônio Vinicius dos Santos de Lima)": "ANTÔNIO DOS SANTOS",
        "Nogueira, Victor M": "VICTOR NOGUEIRA",
        "QUIRINO, RICARDO": "RICARDO QUIRINO",
        "Ferreira De Araujo, Jose Roberto": "JOSÉ ROBERTO",
        "Lucas, Jefferson Monteiro da Silva": "JEFFERSON LUCAS",
        "Silva, Márcio (Contractor) (Márcio (Contractor) Silva)": "MÁRCIO SILVA",
        "Longo, Dante M (Dante M. Longo)": "DANTE LONGO",
        "dos Santos, Otacílio (Contractor) (Otacílio (Contractor) dos Santos)": "OTACÍLIO DOS SANTOS",
        "de Freitas, Fabio (Contractor) (Fabio (Contractor) de Freitas)": "FÁBIO DE FREITAS",
        "Araujo, Alessandro Fabiano De": "ALESSANDRO ARAUJO",
        "Calado, Marcos Aurelio Cavalcanti": "MARCOS CALADO",
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

    de_para_especialista = {
        "PINTO, ANDREZA - C A INSTALACAO E MANUTENCAO EM POSTOS DE COMBUSTIVEIS LTDA":"LUCAS",
        "MACIEL, FONTES FRANJAKSON - NTEC INSTALACOES HIDRAULICAS LTDA.":"LUCIANO",
        "SALES, - S L INSTALACAO P POSTOS DE SE":"LUCAS",
        "SALES, LUIZ - TECNICA L S COMERCIAL E SERVI":"LUCAS",
        "GONZAGA, MANOEL - LMG COMERCIO SERVICOS E MANUTENCAO LTDA":"LUCIANO",
        "MOURA, ALEXSANDRE - ALEXSANDRE LIZ DE MOURA":"LUCAS",
        "NEVES, - TEKSUL MANUTENÇÃO DE BOMBAS PARA COMBUSTÍVEL EIRELI":"LUCAS",
        "Serafim, Joao - JS DE SOUSA MANUTENCAO ME":"LUCIANO",
        "RIGOBERTO, FRANCISCO - F R RIBEIRO MECANICA SAO CRISTOVAO SERVICOS ELETRONICOS LTDA":"LUCIANO",
        "ANDREZA, - UBERPOSTOS LOGISTICA E EQUIP":"LUCAS",
        "ANTONIO, - A DE JESUS E SOUZA DOURADO LTD":"LUCIANO",
        "SILVA, REGINALD - SHEKINAH SHADDAI MANUTENCAO LTD":"LUCIANO",
        "RAMOS, CARLOS - MECANICA DE BOMBAS RAMOS LTDA":"LUCAS",
        "amaro, florisvaldo - SERVITEC - MANUTENCAO E INSTALACAO DE EQUIPAMENTOS EM POSTOS DE COMBUSTIVEIS LTDA":"ALESSANDRO",
        "Mendes, Andre - M E A SILVA MENDES MANUTENCAO E REPARACAO ME":"LUCAS",
        "SALES, - UBERPOSTOS LOGISTICA E EQUIP":"ALESSANDRO",
        "LUCIANA, - ATENDE COMERCIO DE PECAS E CON":"LUCIANO",
        "AMORIM DE OLIVE, LEONORA - L DE ALMEIDA FERREIRA LTDA":"LUCIANO",
        "HENRIQUE, THIAGO - CM2 COMERCIO E SERVICOS LTDA EPP":"LUCAS",
        "SRA.FERNAN, - FORTE INSTALACAO E MANUTENCAO":"LUCIANO",
        "JESSICA, THAINA - THAINA JESSICA DA COSTA RODRIGUES":"LUCIANO",
        "FREITAS, LUCIANO - BHPUMP DO BRASIL LTDA":"ALESSANDRO",
        "SANTOS, VANDERLEY - VANDERLEY PEREIRA DOS SANTOS":"ALESSANDRO",
        "Silva, Rodrigo - EBENEZER COMECIO E MANUTENCAO":"LUCAS",
        "SERGIO, - SERVTEC COMERCIO E SERVICO LTD":"LUCIANO",
        "., Romario - DINIZ ASSISTENCIA TECNICA LTDA":"LUCAS",
        "UNKNOWN, CASSIA - ARBTEK SOLUCOES INTEGRADAS LTDA":"LUCAS",
        "SALES, LUIZ - SOCIEDADE DE MANUTENCAO TECNICA SOMATEC LTDA":"ALESSANDRO",
        "RODRIGUES, RIVALDO - SMR MANUTENCAO E REPARACAO EIRELI ME":"LUCIANO",
        "MENDES, - IMASEL LTDA":"LUCIANO",
        "ESDRAS ARR, - E PASCOAL COM SERV E ASSIST TE":"LUCIANO",
        "ROCHA, ROBERTO - SIGNOS MRWG MANUTENCAO LTDA ME":"ALESSANDRO",
        "DE MATTOS, PERI JACI - MULTITEC SOLUCOES EM POSTOS AUTOMOTIVOS LTDA":"LUCAS",
        "COSTA, GUSTAVO - CONSERTEC BALANCAS E BOMBAS LTDA ME":"ALESSANDRO",
        "SR. LAZARO, - LAZARO MARTINS SILVA SOUZA ME":"LUCAS",
        "COSTA, HELIO - REAL MANUTENCAO E INSTALACAO EM POSTOS E SERVICOS LTDA":"LUCIANO",
        "Neto, Jorge - EWJ INSTALACAO E MANUTENCAO DE EQUIPAMENTOS PARA POSTOS DE COMBUSTIVEIS LTDA":"LUCIANO",
        "CAMPOS, SANDREIA - CONSTRUTORA CENTAURUS DO BRASIL LTDA":"LUCIANO",
        "JUNIOR, LUIZ ZORZI - ZORZITEC CONSULTORIA EIRELI ME":"LUCAS",
        "MENEZES SOARES, ALTEVIR - JUMPER SERVICOS TECNICOS DE BOMBAS DE COMBUSTIVEIS LTDA":"LUCIANO",
        "DO MONTE, CARLOS JORGE - PERMANENTE MANUTENCAO DE MAQUINAS E EQUIPAMENTOS EIRELI":"LUCIANO",
        "ANDRADE, JAIR - JMA PRESTADORA DE SERVICOS LTDA":"LUCAS",
        "Belarmino, Marcos - SOS SYSTEM TECNOLOGIA EM INFORMATICA LTDA":"LUCAS",
        "EVANDRO, - FLOTECK COMERCIO E SERVICOS ESPECIALIZADOS LTDA":"LUCAS",
        "FAVERO, PAULA - CENTURY FLEX COMERCIO DE PECAS PARA BOMBAS DE COMBUSTIVEIS LTDA":"LUCAS",
        "LUZENILDO, - DANTEC ASSITENCIA TECNICA LTDA":"LUCIANO",
        "SANTANA, DORLAN - TECHPETRO SOLUCOES SERVICOS DE MANUTENCAO LTDA":"LUCIANO",
    }

    df["Especialista"] = df["Mantenedor"].replace(de_para_especialista).fillna("NÃO INFORMADO")
    # Se não estiver no dicionário, também substitui por "NÃO INFORMADO"
    df["Proprietário"] = df["Proprietário"].replace(de_para_proprietario)
    df["Mantenedor"] = df["Mantenedor"].replace(de_para_mantenedor).fillna("NÃO INFORMADO")
    df.rename(columns={"SS": "Chamado"}, inplace=True)
    # 1º Cria a coluna "Especialista"


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
        "Especialista": sorted(df["Especialista"].dropna().unique()),
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
    # Filtro de Status
    # ----------------------------
    status_selecionado = st.sidebar.selectbox(
        "Status",
        options=["GERAL", "ABERTO", "FECHADO"],
        index=1  # "ABERTO" como padrão
    )

    # Aplica filtro pelo status
    if status_selecionado == "GERAL":
        df_status_filtrado = df_exibicao
    else:
        df_status_filtrado = df_exibicao[df_exibicao["Status"] == status_selecionado]
        
    # Extrai UF
    # Extrai UF no df já filtrado pelo usuário
    df_status_filtrado["estado"] = df_status_filtrado["Endereço"].apply(extrair_estado)

    estado_counts = (
        df_status_filtrado.dropna(subset=["estado"])
                        .groupby("estado")["Chassi"]
                        .count()
                        .reset_index()
                        .rename(columns={"Chassi": "Quantidade"})
    )


    # Carrega GeoJSON local
    with open("brazil_states.geojson", "r", encoding="utf-8") as f:
        geo_brasil = json.load(f)

    fig_uf = px.choropleth_mapbox(
        estado_counts,
        geojson=geo_brasil,
        locations="estado",
        featureidkey="properties.sigla",
        color="Quantidade",
        color_continuous_scale="Blues",
        mapbox_style="carto-positron",
        zoom=3,  # menor zoom para ampliar área
        center={"lat": -14.2350, "lon": -52.0},  # ajuste de centro para o meio do Brasil
        opacity=0.7,
        labels={"Quantidade": "Chassis"},
    )

    fig_uf.update_layout(
        margin={"r":0, "t":0, "l":0, "b":0},  # remove margens para ocupar tudo
        height=700,  # aumenta altura do gráfico
    )

    st.plotly_chart(fig_uf, use_container_width=True)

