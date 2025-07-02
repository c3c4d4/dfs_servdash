import plotly.express as px
import pandas as pd
from typing import List, Dict, Any

def bar_chart_count(df: pd.DataFrame, campo: str) -> Any:
    """Returns a bar chart of counts for the specified field."""
    contagem = df[campo].value_counts().sort_values(ascending=False)
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
        xaxis_tickangle=-45
    )
    return fig

def bar_chart_aging(df: pd.DataFrame, campo: str) -> Any:
    """Returns a bar chart of mean aging for the specified field."""
    aging_medio = df.groupby(campo)["Aging"].mean().sort_values(ascending=False)
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
        xaxis_tickangle=-45
    )
    return fig

def pie_chart_aging(df: pd.DataFrame) -> Any:
    """Returns a pie chart of aging categories."""
    df["Aging"] = pd.to_numeric(df["Aging"], errors="coerce")
    aging_categorias = df["Aging"].dropna().apply(
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
    fig.update_layout(title="Distribuição de Aging (Dias)")
    return fig

def bar_chart_tags(tags_contagem: pd.Series) -> Any:
    """Returns a bar chart for tag distribution."""
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
        xaxis_tickangle=-45
    )
    return fig

def line_chart_aging(df: pd.DataFrame, campo: str) -> Any:
    """Returns a line chart of mean aging by month for the specified field."""
    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")
    df["AnoMes"] = df["Data"].dt.to_period("M").astype(str)
    aging_por_campo = (
        df.groupby(["AnoMes", campo])["Aging"].mean().reset_index().dropna()
    )
    fig = px.line(
        aging_por_campo,
        x="AnoMes",
        y="Aging",
        color=campo,
        title=f"Aging Médio por {campo} ao Longo do Tempo",
        markers=True
    )
    fig.update_layout(xaxis_title="Mês", yaxis_title="Aging Médio (dias)")
    return fig

def bar_chart_aging_proprietario(df: pd.DataFrame) -> Any:
    df = df.copy()
    df["AGING"] = pd.to_numeric(df["AGING"], errors="coerce")
    aging_medio = df.groupby("PROPRIETÁRIO")["AGING"].mean().sort_values()
    custom_scale = [
        [0.0, "#0000FF"],
        [0.5, "#333B66"],
        [1.0, "#282B3C"]
    ]
    fig = px.bar(
        x=aging_medio.index,
        y=aging_medio.values,
        labels={"x": "Proprietário", "y": "Aging Médio (Dias)", "color": "Aging Médio"},
        color=aging_medio.values,
        color_continuous_scale=custom_scale
    )
    fig.update_layout(
        xaxis_title="Proprietário",
        yaxis_title="Aging Médio (Dias)",
        title="Performance dos Proprietários (Aging Médio)",
        xaxis_tickangle=-45
    )
    return fig

def bar_chart_aging_especialista(df: pd.DataFrame) -> Any:
    df = df.copy()
    df["AGING"] = pd.to_numeric(df["AGING"], errors="coerce")
    aging_medio = df.groupby("ESPECIALISTA")["AGING"].mean().sort_values()
    custom_scale = [
        [0.0, "#0000FF"],
        [0.5, "#333B66"],
        [1.0, "#282B3C"]
    ]
    fig = px.bar(
        x=aging_medio.index,
        y=aging_medio.values,
        labels={"x": "Especialista", "y": "Aging Médio (Dias)", "color": "Aging Médio"},
        color=aging_medio.values,
        color_continuous_scale=custom_scale
    )
    fig.update_layout(
        xaxis_title="Especialista",
        yaxis_title="Aging Médio (Dias)",
        title="Performance dos Especialistas (Aging Médio)",
        xaxis_tickangle=-45
    )
    return fig

def bar_chart_aging_mantenedor(df: pd.DataFrame) -> Any:
    df = df.copy()
    df["AGING"] = pd.to_numeric(df["AGING"], errors="coerce")
    aging_medio = df.groupby("MANTENEDOR")["AGING"].mean().sort_values()
    custom_scale = [
        [0.0, "#0000FF"],
        [0.5, "#333B66"],
        [1.0, "#282B3C"]
    ]
    fig = px.bar(
        x=aging_medio.index,
        y=aging_medio.values,
        labels={"x": "Mantenedor", "y": "Aging Médio (Dias)", "color": "Aging Médio"},
        color=aging_medio.values,
        color_continuous_scale=custom_scale
    )
    fig.update_layout(
        xaxis_title="Mantenedor",
        yaxis_title="Aging Médio (Dias)",
        title="Performance dos Mantenedores (Aging Médio)",
        xaxis_tickangle=-45
    )
    return fig 