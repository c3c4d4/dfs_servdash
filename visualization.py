import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from typing import List, Dict, Any
import streamlit as st

@st.cache_data(ttl=1800, show_spinner=False)
def bar_chart_count(df: pd.DataFrame, campo: str) -> Any:
    """Returns a bar chart of counts for the specified field with optimizations."""
    # Optimize by using value_counts directly
    contagem = df[campo].value_counts().sort_values(ascending=False)
    
    # Limit to top 20 for better performance
    if len(contagem) > 20:
        contagem = contagem.head(20)
    
    fig = px.bar(
        x=contagem.index,
        y=contagem.values,
        labels={"x": campo, "y": "Quantidade", "color": campo},
        color=contagem.values,
        color_continuous_scale=px.colors.sequential.Blues
    )
    fig.update_layout(
        xaxis_title=campo,
        yaxis_title="Quantidade",
        title=f"Distribuição por {campo}",
        xaxis_tickangle=-45,
        height=400
    )
    return fig

@st.cache_data(ttl=1800, show_spinner=False)
def bar_chart_aging(df: pd.DataFrame, campo: str) -> Any:
    """Returns a bar chart of mean aging for the specified field with optimizations."""
    # Optimize aging calculation
    df_clean = df.copy()
    df_clean["Aging"] = pd.to_numeric(df_clean["Aging"], errors="coerce")
    
    # Group and calculate mean aging
    aging_medio = df_clean.groupby(campo)["Aging"].mean().sort_values(ascending=False)
    
    # Limit to top 20 for better performance
    if len(aging_medio) > 20:
        aging_medio = aging_medio.head(20)
    
    fig = px.bar(
        x=aging_medio.index,
        y=aging_medio.values,
        labels={"x": campo, "y": "Aging Médio (Dias)", "color": campo},
        color=aging_medio.values,
        color_continuous_scale=px.colors.sequential.Blues
    )
    fig.update_layout(
        xaxis_title=campo,
        yaxis_title="Aging Médio (Dias)",
        title=f"Distribuição por {campo}",
        xaxis_tickangle=-45,
        height=400
    )
    return fig

@st.cache_data(ttl=1800, show_spinner=False)
def pie_chart_aging(df: pd.DataFrame) -> Any:
    """Returns a pie chart of aging categories with optimizations."""
    df_clean = df.copy()
    df_clean["AGING"] = pd.to_numeric(df_clean["AGING"], errors="coerce")
    
    # Vectorized categorization
    aging_categorias = pd.cut(
        df_clean["AGING"].dropna(),
        bins=[0, 7, 14, float('inf')],
        labels=["Até 7", "8 a 14", ">14"],
        include_lowest=True
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
    fig.update_layout(
        title="Distribuição de Aging (Dias)",
        height=400
    )
    return fig

@st.cache_data(ttl=1800, show_spinner=False)
def bar_chart_tags(tags_contagem: pd.Series) -> Any:
    """Returns a bar chart for tag distribution with optimizations."""
    # Limit to top 20 tags for better performance
    if len(tags_contagem) > 20:
        tags_contagem = tags_contagem.head(20)
    
    fig = px.bar(
        x=tags_contagem.index,
        y=tags_contagem.values,
        labels={"x": "Tags", "y": "Quantidade", "color": "Quantidade"},
        color=tags_contagem.values,
        color_continuous_scale=px.colors.sequential.Blues
    )
    fig.update_layout(
        xaxis_title="Tags",
        yaxis_title="Quantidade",
        title="Distribuição de Tags nos Chamados",
        xaxis_tickangle=-45,
        height=400
    )
    return fig

@st.cache_data(ttl=1800, show_spinner=False)
def line_chart_aging(df: pd.DataFrame, campo: str) -> Any:
    """Returns a line chart of mean aging by month for the specified field with optimizations."""
    df_clean = df.copy()
    df_clean["Data"] = pd.to_datetime(df_clean["Data"], dayfirst=True, errors="coerce")
    df_clean["AnoMes"] = df_clean["Data"].dt.to_period("M").astype(str)
    
    # Optimize grouping and calculation
    aging_por_campo = (
        df_clean.groupby(["AnoMes", campo])["Aging"]
        .mean()
        .reset_index()
        .dropna()
    )
    
    # Limit to top 10 categories for better visualization
    if campo in aging_por_campo.columns:
        top_categories = aging_por_campo[campo].value_counts().head(10).index
        aging_por_campo = aging_por_campo[aging_por_campo[campo].isin(top_categories)]
    
    fig = px.line(
        aging_por_campo,
        x="AnoMes",
        y="Aging",
        color=campo,
        title=f"Aging Médio por {campo} ao Longo do Tempo",
        markers=True
    )
    fig.update_layout(
        xaxis_title="Mês", 
        yaxis_title="Aging Médio (dias)",
        height=400
    )
    return fig

@st.cache_data(ttl=1800, show_spinner=False)
def bar_chart_aging_proprietario(df: pd.DataFrame) -> Any:
    """Performance chart for proprietários with optimizations."""
    df_clean = df.copy()
    df_clean["AGING"] = pd.to_numeric(df_clean["AGING"], errors="coerce")
    
    # Optimize grouping
    aging_medio = df_clean.groupby("PROPRIETÁRIO")["AGING"].mean().sort_values()
    
    # Limit to top 20 for better performance
    if len(aging_medio) > 20:
        aging_medio = aging_medio.head(20)
    
    custom_scale = [
        [0.0, "#0000FF"],
        [0.5, "#333B66"],
        [1.0, "#282B3C"]
    ]
    
    df_plot = pd.DataFrame({
        "Proprietário": aging_medio.index,
        "Aging Médio (Dias)": aging_medio.values
    })
    
    fig = px.bar(
        df_plot,
        x="Proprietário",
        y="Aging Médio (Dias)",
        color="Aging Médio (Dias)",
        color_continuous_scale=custom_scale,
        labels={"Aging Médio (Dias)": "Aging Médio (Dias)", "Proprietário": "Proprietário"}
    )
    fig.update_layout(
        xaxis_title="Proprietário",
        yaxis_title="Aging Médio (Dias)",
        title="Performance dos Proprietários (Aging Médio)",
        xaxis_tickangle=-45,
        height=400
    )
    return fig

@st.cache_data(ttl=1800, show_spinner=False)
def bar_chart_aging_especialista(df: pd.DataFrame) -> Any:
    """Performance chart for especialistas with optimizations."""
    df_clean = df.copy()
    df_clean["AGING"] = pd.to_numeric(df_clean["AGING"], errors="coerce")
    
    # Optimize grouping
    aging_medio = df_clean.groupby("ESPECIALISTA")["AGING"].mean().sort_values()
    
    # Limit to top 20 for better performance
    if len(aging_medio) > 20:
        aging_medio = aging_medio.head(20)
    
    custom_scale = [
        [0.0, "#0000FF"],
        [0.5, "#333B66"],
        [1.0, "#282B3C"]
    ]
    
    df_plot = pd.DataFrame({
        "Especialista": aging_medio.index,
        "Aging Médio (Dias)": aging_medio.values
    })
    
    fig = px.bar(
        df_plot,
        x="Especialista",
        y="Aging Médio (Dias)",
        color="Aging Médio (Dias)",
        color_continuous_scale=custom_scale,
        labels={"Aging Médio (Dias)": "Aging Médio (Dias)", "Especialista": "Especialista"}
    )
    fig.update_layout(
        xaxis_title="Especialista",
        yaxis_title="Aging Médio (Dias)",
        title="Performance dos Especialistas (Aging Médio)",
        xaxis_tickangle=-45,
        height=400
    )
    return fig

@st.cache_data(ttl=1800, show_spinner=False)
def bar_chart_aging_mantenedor(df: pd.DataFrame) -> Any:
    """Performance chart for mantenedores with optimizations."""
    df_clean = df.copy()
    df_clean["AGING"] = pd.to_numeric(df_clean["AGING"], errors="coerce")
    
    # Optimize grouping
    aging_medio = df_clean.groupby("MANTENEDOR")["AGING"].mean().sort_values()
    
    # Limit to top 20 for better performance
    if len(aging_medio) > 20:
        aging_medio = aging_medio.head(20)
    
    custom_scale = [
        [0.0, "#0000FF"],
        [0.5, "#333B66"],
        [1.0, "#282B3C"]
    ]
    
    df_plot = pd.DataFrame({
        "Mantenedor": aging_medio.index,
        "Aging Médio (Dias)": aging_medio.values
    })
    
    fig = px.bar(
        df_plot,
        x="Mantenedor",
        y="Aging Médio (Dias)",
        color="Aging Médio (Dias)",
        color_continuous_scale=custom_scale,
        labels={"Aging Médio (Dias)": "Aging Médio (Dias)", "Mantenedor": "Mantenedor"}
    )
    fig.update_layout(
        xaxis_title="Mantenedor",
        yaxis_title="Aging Médio (Dias)",
        title="Performance dos Mantenedores (Aging Médio)",
        xaxis_tickangle=-45,
        height=400
    )
    return fig

@st.cache_data(ttl=1800, show_spinner=False)
def choropleth_map_brazil(df: pd.DataFrame, estado_counts: pd.DataFrame) -> Any:
    """Creates a choropleth map of Brazil with optimizations."""
    try:
        # Try to load GeoJSON data
        with open('brazil_states.geojson', 'r', encoding='utf-8') as f:
            import json
            brazil_states = json.load(f)
        
        # Check if we have matching states - try different property names
        geojson_states = set()
        geojson_properties = set()
        
        for feature in brazil_states.get('features', []):
            if 'properties' in feature:
                props = feature['properties']
                geojson_properties.update(props.keys())
                
                # Try different possible property names for state
                for prop_name in ['UF', 'uf', 'UF_05', 'SIGLA', 'sigla', 'ESTADO', 'estado', 'name', 'NAME']:
                    if prop_name in props:
                        geojson_states.add(str(props[prop_name]))
                        break
        
        data_states = set(estado_counts['UF'].astype(str))
        
        # If no matching states found, use the first available property
        if not geojson_states and geojson_properties:
            first_prop = sorted(geojson_properties)[0]
            featureidkey = f"properties.{first_prop}"
        else:
            # Try to find the correct property name
            for prop_name in ['UF', 'uf', 'UF_05', 'SIGLA', 'sigla', 'ESTADO', 'estado', 'name', 'NAME']:
                if prop_name in geojson_properties:
                    featureidkey = f"properties.{prop_name}"
                    break
            else:
                featureidkey = "properties.UF"  # fallback
        
        # Create a mapping for state names if needed
        estado_mapping = {
            'AC': 'ACRE', 'AL': 'ALAGOAS', 'AM': 'AMAZONAS', 'AP': 'AMAPA', 'BA': 'BAHIA',
            'CE': 'CEARA', 'DF': 'DISTRITO FEDERAL', 'ES': 'ESPIRITO SANTO', 'GO': 'GOIAS',
            'MA': 'MARANHAO', 'MG': 'MINAS GERAIS', 'MS': 'MATO GROSSO DO SUL', 'MT': 'MATO GROSSO',
            'PA': 'PARA', 'PB': 'PARAIBA', 'PE': 'PERNAMBUCO', 'PI': 'PIAUI',
            'PR': 'PARANA', 'RJ': 'RIO DE JANEIRO', 'RN': 'RIO GRANDE DO NORTE', 'RO': 'RONDONIA',
            'RR': 'RORAIMA', 'RS': 'RIO GRANDE DO SUL', 'SC': 'SANTA CATARINA', 'SE': 'SERGIPE',
            'SP': 'SAO PAULO', 'TO': 'TOCANTINS'
        }
        
        # Check if we need to map state names
        if not geojson_states.intersection(data_states):
            # Create a copy with mapped state names
            estado_counts_mapped = estado_counts.copy()
            estado_counts_mapped['UF_MAPPED'] = estado_counts_mapped['UF'].map(estado_mapping)
            
            # Check if mapped names match
            mapped_states = set(estado_counts_mapped['UF_MAPPED'].dropna())
            matching_mapped = len(geojson_states.intersection(mapped_states))
            
            if matching_mapped > 0:
                # Use mapped data
                estado_counts = estado_counts_mapped.rename(columns={'UF_MAPPED': 'UF'})
        
        fig = px.choropleth(
            estado_counts,
            geojson=brazil_states,
            locations='UF',
            featureidkey=featureidkey,
            color='Quantidade',
            color_continuous_scale="Blues",
            title="Distribuição de Bombas por Estado",
            labels={'Quantidade': 'Quantidade de Bombas'}
        )
        
        fig.update_geos(
            showcountries=False,
            showcoastlines=False,
            showland=False,
            showocean=False,
            showframe=False,
            showlakes=False,
            showrivers=False,
            coastlinewidth=0,
            landcolor='white',
            oceancolor='white',
            fitbounds="locations"
        )
        
        fig.update_layout(
            height=500,
            margin={"r":0,"t":30,"l":0,"b":0},
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        return fig
        
    except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
        # Fallback: Create a simple bar chart if GeoJSON is not available
        st.warning(f"⚠️ Erro ao carregar mapa geográfico: {str(e)}. Exibindo gráfico de barras como alternativa.")
        
        fig = px.bar(
            estado_counts,
            x='UF',
            y='Quantidade',
            color='Quantidade',
            color_continuous_scale="Blues",
            title="Distribuição de Bombas por Estado",
            labels={'Quantidade': 'Quantidade de Bombas', 'UF': 'Estado'}
        )
        
        fig.update_layout(
            xaxis_title="Estado",
            yaxis_title="Quantidade de Bombas",
            height=500,
            xaxis_tickangle=-45
        )
        
        return fig

@st.cache_data(ttl=1800, show_spinner=False)
def create_kpi_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Creates KPI metrics with optimizations."""
    total = len(df)
    abertos = (df['STATUS'] == 'ABERTO').sum()
    fechados = (df['STATUS'] != 'ABERTO').sum()
    
    # Optimize aging calculation
    aging_medio = pd.to_numeric(df['AGING'], errors='coerce').mean()
    
    # Optimize percentage calculations
    pct_garantia = (df['GARANTIA'] == 'DENTRO').mean() * 100
    pct_rtm = (df['RTM'] == 'SIM').mean() * 100
    
    return {
        'total': total,
        'abertos': abertos,
        'fechados': fechados,
        'aging_medio': aging_medio,
        'pct_garantia': pct_garantia,
        'pct_rtm': pct_rtm
    } 