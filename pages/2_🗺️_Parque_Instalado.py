import streamlit as st
import pandas as pd
import json
from data_loader import carregar_dados, de_para_proprietario, de_para_mantenedor, de_para_especialista
from utils import extrair_estado
from auth import check_password
import plotly.express as px

st.set_page_config(page_title="Parque Instalado - Chamados de Serviços", layout="wide")

check_password()

df = carregar_dados()
df["Proprietário"] = df["Proprietário"].replace(de_para_proprietario)
df["Especialista"] = df["Mantenedor"].replace(de_para_especialista).fillna("NÃO INFORMADO")
df["Mantenedor"] = df["Mantenedor"].replace(de_para_mantenedor).fillna("NÃO INFORMADO")
df.rename(columns={"SS": "Chamado"}, inplace=True)

st.title("Chamados de Serviços - Parque Instalado (Chassis/Estado)")

# Extrai UF
st.markdown(f"**Total: {len(df)} chamados**")
df["estado"] = df["Endereço"].apply(extrair_estado)
estado_counts = (
    df.dropna(subset=["estado"])
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
    zoom=3,
    center={"lat": -14.2350, "lon": -52.0},
    opacity=0.7,
    labels={"Quantidade": "Chassis"},
)

st.plotly_chart(fig_uf, use_container_width=True) 