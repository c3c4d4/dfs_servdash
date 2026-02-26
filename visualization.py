import json

import plotly.express as px
import pandas as pd
from typing import Dict, Any, TypedDict, Tuple, Optional
import streamlit as st
from constants import MAIN_MODELS


class KpiMetrics(TypedDict):
    """Type definition for KPI metrics returned by create_kpi_metrics."""

    total: int
    abertos: int
    fechados: int
    aging_medio: float
    pct_garantia: float
    pct_rtm: float


RELATIONSHIP_SCORE_LABELS = {
    1: "1 · Alto volume + alta rapidez",
    2: "2 · Baixo volume + alta rapidez",
    3: "3 · Baixo volume + baixa rapidez",
    4: "4 · Alto volume + baixa rapidez",
}

RELATIONSHIP_SCORE_COLORS = {
    1: "#2E8B57",
    2: "#88B04B",
    3: "#F4A259",
    4: "#D1495B",
}

RELATIONSHIP_SCORE_BAND_COLORS = {
    1: "rgba(46, 139, 87, 0.14)",
    2: "rgba(136, 176, 75, 0.14)",
    3: "rgba(244, 162, 89, 0.14)",
    4: "rgba(209, 73, 91, 0.14)",
}


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
        color_continuous_scale=px.colors.sequential.Blues,
        template="plotly_white",
    )
    fig.update_layout(
        xaxis_title=campo,
        yaxis_title="Quantidade",
        title=dict(text=f"Distribuição por {campo}", x=0.5, xanchor="center"),
        xaxis_tickangle=-45,
        height=400,
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Arial"),
    )
    return fig


@st.cache_data(ttl=1800, show_spinner=False)
def bar_chart_aging(df: pd.DataFrame, campo: str) -> Any:
    """Returns a bar chart of mean aging for the specified field with optimizations."""
    # Optimize aging calculation
    df_clean = df.copy()
    df_clean["AGING"] = pd.to_numeric(df_clean["AGING"], errors="coerce")

    # Group and calculate mean aging
    aging_medio = df_clean.groupby(campo)["AGING"].mean().sort_values(ascending=False)

    # Limit to top 20 for better performance
    if len(aging_medio) > 20:
        aging_medio = aging_medio.head(20)

    fig = px.bar(
        x=aging_medio.index,
        y=aging_medio.values,
        labels={"x": campo, "y": "Aging Médio (Dias)", "color": campo},
        color=aging_medio.values,
        color_continuous_scale=px.colors.sequential.Blues,
        template="plotly_white",
    )
    fig.update_layout(
        xaxis_title=campo,
        yaxis_title="Aging Médio (Dias)",
        title=dict(text=f"Distribuição por {campo}", x=0.5, xanchor="center"),
        xaxis_tickangle=-45,
        height=400,
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Arial"),
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
        bins=[0, 7, 14, float("inf")],
        labels=["Até 7", "8 a 14", ">14"],
        include_lowest=True,
    )

    contagem_aging = aging_categorias.value_counts().reindex(
        ["Até 7", "8 a 14", ">14"], fill_value=0
    )

    fig = px.pie(
        names=contagem_aging.index,
        values=contagem_aging.values,
        color=contagem_aging.index,
        color_discrete_map={"Até 7": "#9ac8e0", "8 a 14": "#3989c2", ">14": "#08306b"},
        labels={
            "value": "Quantidade",
            "names": "Intervalo de Aging",
            "color": "Intervalo de Aging",
        },
        hole=0.4,
        template="plotly_white",
    )
    fig.update_layout(
        title=dict(text="Distribuição de Aging (Dias)", x=0.5, xanchor="center"),
        height=400,
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Arial"),
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
        color_continuous_scale=px.colors.sequential.Blues,
        template="plotly_white",
    )
    fig.update_layout(
        xaxis_title="Tags",
        yaxis_title="Quantidade",
        title=dict(text="Distribuição de Tags nos Chamados", x=0.5, xanchor="center"),
        xaxis_tickangle=-45,
        height=400,
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Arial"),
    )
    return fig


@st.cache_data(ttl=1800, show_spinner=False)
def line_chart_aging(df: pd.DataFrame, campo: str) -> Any:
    """Returns a line chart of mean aging by month for the specified field with optimizations."""
    df_clean = df.copy()

    # Standardized to uppercase column names
    date_col = "DATA"
    aging_col = "AGING"

    df_clean[date_col] = pd.to_datetime(
        df_clean[date_col], dayfirst=True, errors="coerce"
    )
    df_clean["AnoMes"] = df_clean[date_col].dt.to_period("M").astype(str)

    # Optimize grouping and calculation
    aging_por_campo = (
        df_clean.groupby(["AnoMes", campo])[aging_col].mean().reset_index().dropna()
    )

    # Limit to top 10 categories for better visualization
    if campo in aging_por_campo.columns:
        top_categories = aging_por_campo[campo].value_counts().head(10).index
        aging_por_campo = aging_por_campo[aging_por_campo[campo].isin(top_categories)]

    # Rename column for chart display
    aging_por_campo = aging_por_campo.rename(columns={aging_col: "Aging"})

    fig = px.line(
        aging_por_campo,
        x="AnoMes",
        y="Aging",
        color=campo,
        title=f"Aging Médio por {campo} ao Longo do Tempo",
        markers=True,
        template="plotly_white",
    )
    fig.update_layout(
        xaxis_title="Mês",
        yaxis_title="Aging Médio (dias)",
        height=400,
        title=dict(x=0.5, xanchor="center"),
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Arial"),
    )
    return fig


def calculate_relationship_score(
    volume: float,
    aging_medio_dias: float,
    volume_corte: float,
    aging_corte: float,
) -> int:
    """Classify maintainer relationship score (1 best, 4 worst)."""
    if pd.isna(volume) or pd.isna(aging_medio_dias):
        return 3

    alto_volume = volume >= volume_corte
    alta_rapidez = aging_medio_dias <= aging_corte  # menor aging = mais rápido

    if alto_volume and alta_rapidez:
        return 1
    if (not alto_volume) and alta_rapidez:
        return 2
    if (not alto_volume) and (not alta_rapidez):
        return 3
    return 4


def _prepare_relationship_source(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize source dataframe for relationship matrix calculations."""
    base_cols = {"MANTENEDOR", "DATA_BASE", "AGING_NUM", "CHAMADO_KEY"}
    if df is None or df.empty:
        return pd.DataFrame(columns=list(base_cols))

    if base_cols.issubset(df.columns):
        base = df.copy()
        base["DATA_BASE"] = pd.to_datetime(base["DATA_BASE"], errors="coerce")
        base["AGING_NUM"] = pd.to_numeric(base["AGING_NUM"], errors="coerce")
        base["CHAMADO_KEY"] = base["CHAMADO_KEY"].astype(str)
        base["MANTENEDOR"] = base["MANTENEDOR"].astype(str).str.strip()
        return base[
            (base["DATA_BASE"].notna())
            & (base["AGING_NUM"].notna())
            & (base["MANTENEDOR"] != "")
        ]

    data_col = (
        "INÍCIO" if "INÍCIO" in df.columns else "DATA" if "DATA" in df.columns else None
    )
    if data_col is None or "MANTENEDOR" not in df.columns:
        return pd.DataFrame(columns=list(base_cols))

    base = df.copy()
    base["DATA_BASE"] = pd.to_datetime(base[data_col], dayfirst=True, errors="coerce")
    base["MANTENEDOR"] = base["MANTENEDOR"].fillna("").astype(str).str.strip()

    if "AGING" in base.columns:
        base["AGING_NUM"] = pd.to_numeric(base["AGING"], errors="coerce")
    else:
        base["AGING_NUM"] = pd.NA

    # Fallback when AGING is unavailable: calculate from INÍCIO/FIM.
    if base["AGING_NUM"].isna().all() and "FIM" in base.columns:
        base["FIM_CALC"] = pd.to_datetime(base["FIM"], dayfirst=True, errors="coerce")
        hoje = pd.Timestamp.now().normalize()
        base.loc[base["FIM_CALC"].isna(), "FIM_CALC"] = hoje
        base["AGING_NUM"] = (base["FIM_CALC"] - base["DATA_BASE"]).dt.days

    if "CHAMADO" in base.columns:
        base["CHAMADO_KEY"] = base["CHAMADO"].fillna("").astype(str).str.strip()
    elif "SS" in base.columns:
        base["CHAMADO_KEY"] = base["SS"].fillna("").astype(str).str.strip()
    else:
        base["CHAMADO_KEY"] = base.index.astype(str)

    base.loc[base["CHAMADO_KEY"] == "", "CHAMADO_KEY"] = base.index.astype(str)
    base["AGING_NUM"] = pd.to_numeric(base["AGING_NUM"], errors="coerce").clip(lower=0)

    base = base[
        (base["MANTENEDOR"] != "")
        & base["DATA_BASE"].notna()
        & base["AGING_NUM"].notna()
    ]
    return base[["MANTENEDOR", "DATA_BASE", "AGING_NUM", "CHAMADO_KEY"]]


@st.cache_data(ttl=900, show_spinner=False)
def filter_customer_relationship_period(
    df: pd.DataFrame,
    periodo: str = "All time",
) -> pd.DataFrame:
    """Filter dataframe for customer relationship analysis period."""
    base = _prepare_relationship_source(df)
    if base.empty:
        return base

    if periodo == "All time":
        return base

    data_max = base["DATA_BASE"].max()
    months = 6 if periodo == "Últimos 6 meses" else 12
    limite = data_max - pd.DateOffset(months=months)
    return base[base["DATA_BASE"] >= limite].copy()


@st.cache_data(ttl=900, show_spinner=False)
def get_customer_relationship_matrix_data(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, float, float]:
    """Aggregate maintainer volume/rapidez and assign score 1-4."""
    base = _prepare_relationship_source(df)
    if base.empty:
        return pd.DataFrame(), 0.0, 0.0

    matrix = (
        base.groupby("MANTENEDOR", as_index=False)
        .agg(
            VOLUME=("CHAMADO_KEY", "nunique"),
            AGING_MEDIO_DIAS=("AGING_NUM", "mean"),
        )
        .sort_values("VOLUME", ascending=False)
    )

    if matrix.empty:
        return pd.DataFrame(), 0.0, 0.0

    volume_corte = float(matrix["VOLUME"].median())
    aging_corte = float(matrix["AGING_MEDIO_DIAS"].median())

    matrix["SCORE"] = matrix.apply(
        lambda row: calculate_relationship_score(
            row["VOLUME"],
            row["AGING_MEDIO_DIAS"],
            volume_corte,
            aging_corte,
        ),
        axis=1,
    )
    matrix["PERFIL"] = matrix["SCORE"].map(RELATIONSHIP_SCORE_LABELS)
    matrix["AGING_MEDIO_DIAS"] = matrix["AGING_MEDIO_DIAS"].round(1)
    matrix = matrix.sort_values(["SCORE", "VOLUME"], ascending=[True, False])

    return matrix, volume_corte, aging_corte


@st.cache_data(ttl=900, show_spinner=False)
def get_customer_relationship_monthly_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate monthly score progression for each SAW (mantenedor)."""
    base = _prepare_relationship_source(df)
    if base.empty:
        return pd.DataFrame()

    base["ANO_MES"] = base["DATA_BASE"].dt.to_period("M").dt.to_timestamp()
    monthly = (
        base.groupby(["ANO_MES", "MANTENEDOR"], as_index=False)
        .agg(
            VOLUME=("CHAMADO_KEY", "nunique"),
            AGING_MEDIO_DIAS=("AGING_NUM", "mean"),
        )
        .sort_values(["ANO_MES", "MANTENEDOR"])
    )

    if monthly.empty:
        return pd.DataFrame()

    monthly["VOLUME_CORTE_MES"] = monthly.groupby("ANO_MES")["VOLUME"].transform(
        "median"
    )
    monthly["AGING_CORTE_MES"] = monthly.groupby("ANO_MES")[
        "AGING_MEDIO_DIAS"
    ].transform("median")
    monthly["SCORE"] = monthly.apply(
        lambda row: calculate_relationship_score(
            row["VOLUME"],
            row["AGING_MEDIO_DIAS"],
            row["VOLUME_CORTE_MES"],
            row["AGING_CORTE_MES"],
        ),
        axis=1,
    )
    monthly["PERFIL"] = monthly["SCORE"].map(RELATIONSHIP_SCORE_LABELS)
    monthly["AGING_MEDIO_DIAS"] = monthly["AGING_MEDIO_DIAS"].round(1)

    return monthly


def customer_relationship_matrix_chart(
    df: pd.DataFrame, mantenedor_destaque: Optional[str] = None
) -> Any:
    """Scatter matrix by maintainer with score classification."""
    matrix, volume_corte, aging_corte = get_customer_relationship_matrix_data(df)
    if matrix.empty:
        return None

    matrix_plot = matrix.copy()
    # Small jitter avoids complete overlap when maintainers have identical coordinates.
    matrix_plot["DUP_COUNT"] = matrix_plot.groupby(["VOLUME", "AGING_MEDIO_DIAS"])[
        "MANTENEDOR"
    ].transform("size")
    matrix_plot["DUP_IDX"] = matrix_plot.groupby(["VOLUME", "AGING_MEDIO_DIAS"]).cumcount()
    x_span = max(float(matrix_plot["VOLUME"].max() - matrix_plot["VOLUME"].min()), 1.0)
    y_span = max(
        float(
            matrix_plot["AGING_MEDIO_DIAS"].max() - matrix_plot["AGING_MEDIO_DIAS"].min()
        ),
        1.0,
    )
    matrix_plot["VOLUME_PLOT"] = matrix_plot["VOLUME"] + (
        matrix_plot["DUP_IDX"] - (matrix_plot["DUP_COUNT"] - 1) / 2
    ) * x_span * 0.012
    matrix_plot["AGING_PLOT"] = matrix_plot["AGING_MEDIO_DIAS"] + (
        matrix_plot["DUP_IDX"] - (matrix_plot["DUP_COUNT"] - 1) / 2
    ) * y_span * 0.012

    color_map = {
        RELATIONSHIP_SCORE_LABELS[k]: v for k, v in RELATIONSHIP_SCORE_COLORS.items()
    }

    fig = px.scatter(
        matrix_plot,
        x="VOLUME_PLOT",
        y="AGING_PLOT",
        color="PERFIL",
        category_orders={"PERFIL": list(RELATIONSHIP_SCORE_LABELS.values())},
        color_discrete_map=color_map,
        hover_data={
            "MANTENEDOR": True,
            "VOLUME": True,
            "AGING_MEDIO_DIAS": True,
            "SCORE": True,
            "PERFIL": False,
            "VOLUME_PLOT": False,
            "AGING_PLOT": False,
            "DUP_COUNT": False,
            "DUP_IDX": False,
        },
        labels={
            "VOLUME_PLOT": "VOLUME",
            "AGING_PLOT": "RAPIDEZ",
            "PERFIL": "Score / Quadrante",
        },
        template="plotly_white",
    )

    fig.update_traces(
        marker=dict(size=14, opacity=0.88, line=dict(color="#FFFFFF", width=1.2)),
    )
    if mantenedor_destaque:
        destaque = matrix_plot[matrix_plot["MANTENEDOR"] == mantenedor_destaque]
        if not destaque.empty:
            row = destaque.iloc[0]
            fig.add_scatter(
                x=[row["VOLUME_PLOT"]],
                y=[row["AGING_PLOT"]],
                mode="markers+text",
                text=[row["MANTENEDOR"]],
                textposition="top center",
                marker=dict(
                    size=22,
                    color="#0F172A",
                    line=dict(color="#FFFFFF", width=2),
                    symbol="diamond",
                ),
                name="Mantenedor selecionado",
                hovertemplate=(
                    f"<b>{row['MANTENEDOR']}</b><br>"
                    f"VOLUME: {row['VOLUME']}<br>"
                    f"RAPIDEZ (dias): {row['AGING_MEDIO_DIAS']}<br>"
                    f"SCORE: {row['SCORE']}<extra></extra>"
                ),
            )

    fig.add_vline(
        x=volume_corte,
        line_dash="dash",
        line_color="#64748B",
        annotation_text="Corte",
        annotation_position="top left",
    )
    fig.add_hline(
        y=aging_corte,
        line_dash="dash",
        line_color="#64748B",
        annotation_text="Corte",
        annotation_position="bottom left",
    )

    fig.update_layout(
        height=620,
        legend_title_text="Quadrante / Score",
        font=dict(family="IBM Plex Sans, Segoe UI, sans-serif"),
        hoverlabel=dict(bgcolor="white", font_size=12),
    )
    fig.update_xaxes(title="VOLUME")
    fig.update_yaxes(
        autorange="reversed",
        title="RAPIDEZ",
    )
    return fig


def customer_relationship_monthly_score_chart(df: pd.DataFrame) -> Any:
    """Monthly score trend for each SAW with colored score bands."""
    monthly = get_customer_relationship_monthly_scores(df)
    if monthly.empty:
        return None

    fig = px.line(
        monthly,
        x="ANO_MES",
        y="SCORE",
        color="MANTENEDOR",
        markers=True,
        hover_data={
            "MANTENEDOR": True,
            "VOLUME": True,
            "AGING_MEDIO_DIAS": True,
            "SCORE": True,
            "PERFIL": True,
        },
        labels={
            "ANO_MES": "Mês",
            "SCORE": "Score",
            "MANTENEDOR": "SAW",
        },
        template="plotly_white",
        title="Evolução Mensal de Score por SAW",
    )

    for score, color in RELATIONSHIP_SCORE_BAND_COLORS.items():
        fig.add_shape(
            type="rect",
            xref="paper",
            x0=0,
            x1=1,
            yref="y",
            y0=score - 0.5,
            y1=score + 0.5,
            fillcolor=color,
            line_width=0,
            layer="below",
        )

    fig.update_layout(
        height=520,
        title=dict(x=0.5, xanchor="center"),
        hovermode="x unified",
        legend_title_text="SAW",
        font=dict(family="IBM Plex Sans, Segoe UI, sans-serif"),
    )
    fig.update_yaxes(
        range=[0.8, 4.2],
        tickvals=[1, 2, 3, 4],
        ticktext=["1", "2", "3", "4"],
        title="Score (1 melhor → 4 pior)",
    )
    fig.update_xaxes(title="Mês")
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

    custom_scale = [[0.0, "#0000FF"], [0.5, "#333B66"], [1.0, "#282B3C"]]

    df_plot = pd.DataFrame(
        {"Proprietário": aging_medio.index, "Aging Médio (Dias)": aging_medio.values}
    )

    fig = px.bar(
        df_plot,
        x="Proprietário",
        y="Aging Médio (Dias)",
        color="Aging Médio (Dias)",
        color_continuous_scale=custom_scale,
        labels={
            "Aging Médio (Dias)": "Aging Médio (Dias)",
            "Proprietário": "Proprietário",
        },
        template="plotly_white",
    )
    fig.update_layout(
        xaxis_title="Proprietário",
        yaxis_title="Aging Médio (Dias)",
        title=dict(
            text="Performance dos Proprietários (Aging Médio)", x=0.5, xanchor="center"
        ),
        xaxis_tickangle=-45,
        height=400,
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Arial"),
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

    custom_scale = [[0.0, "#0000FF"], [0.5, "#333B66"], [1.0, "#282B3C"]]

    df_plot = pd.DataFrame(
        {"Especialista": aging_medio.index, "Aging Médio (Dias)": aging_medio.values}
    )

    fig = px.bar(
        df_plot,
        x="Especialista",
        y="Aging Médio (Dias)",
        color="Aging Médio (Dias)",
        color_continuous_scale=custom_scale,
        labels={
            "Aging Médio (Dias)": "Aging Médio (Dias)",
            "Especialista": "Especialista",
        },
        template="plotly_white",
    )
    fig.update_layout(
        xaxis_title="Especialista",
        yaxis_title="Aging Médio (Dias)",
        title=dict(
            text="Performance dos Especialistas (Aging Médio)", x=0.5, xanchor="center"
        ),
        xaxis_tickangle=-45,
        height=400,
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Arial"),
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

    custom_scale = [[0.0, "#0000FF"], [0.5, "#333B66"], [1.0, "#282B3C"]]

    df_plot = pd.DataFrame(
        {"Mantenedor": aging_medio.index, "Aging Médio (Dias)": aging_medio.values}
    )

    fig = px.bar(
        df_plot,
        x="Mantenedor",
        y="Aging Médio (Dias)",
        color="Aging Médio (Dias)",
        color_continuous_scale=custom_scale,
        labels={"Aging Médio (Dias)": "Aging Médio (Dias)", "Mantenedor": "Mantenedor"},
        template="plotly_white",
    )
    fig.update_layout(
        xaxis_title="Mantenedor",
        yaxis_title="Aging Médio (Dias)",
        title=dict(
            text="Performance dos Mantenedores (Aging Médio)", x=0.5, xanchor="center"
        ),
        xaxis_tickangle=-45,
        height=400,
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Arial"),
    )
    return fig


@st.cache_data(ttl=1800, show_spinner=False)
def choropleth_map_brazil(df: pd.DataFrame, estado_counts: pd.DataFrame) -> Any:
    """Creates a choropleth map of Brazil with optimizations and percentages."""
    try:
        # Try to load GeoJSON data
        with open("brazil_states.geojson", "r", encoding="utf-8") as f:
            brazil_states = json.load(f)

        # Calculate total and percentages
        total_bombas = estado_counts["Quantidade"].sum()
        estado_counts = estado_counts.copy()
        estado_counts["Percentual"] = (
            estado_counts["Quantidade"] / total_bombas * 100
        ).round(1)
        estado_counts["Hover_Text"] = (
            estado_counts["UF"]
            + "<br>"
            + "Quantidade: "
            + estado_counts["Quantidade"].astype(str)
            + "<br>"
            + "Percentual: "
            + estado_counts["Percentual"].astype(str)
            + "%"
        )

        # Check if we have matching states - try different property names
        geojson_states = set()
        geojson_properties = set()

        for feature in brazil_states.get("features", []):
            if "properties" in feature:
                props = feature["properties"]
                geojson_properties.update(props.keys())

                # Try different possible property names for state
                for prop_name in [
                    "UF",
                    "uf",
                    "UF_05",
                    "SIGLA",
                    "sigla",
                    "ESTADO",
                    "estado",
                    "name",
                    "NAME",
                ]:
                    if prop_name in props:
                        geojson_states.add(str(props[prop_name]))
                        break

        data_states = set(estado_counts["UF"].astype(str))

        # If no matching states found, use the first available property
        if not geojson_states and geojson_properties:
            first_prop = sorted(geojson_properties)[0]
            featureidkey = f"properties.{first_prop}"
        else:
            # Try to find the correct property name
            for prop_name in [
                "UF",
                "uf",
                "UF_05",
                "SIGLA",
                "sigla",
                "ESTADO",
                "estado",
                "name",
                "NAME",
            ]:
                if prop_name in geojson_properties:
                    featureidkey = f"properties.{prop_name}"
                    break
            else:
                featureidkey = "properties.UF"  # fallback

        # Create a mapping for state names if needed
        estado_mapping = {
            "AC": "ACRE",
            "AL": "ALAGOAS",
            "AM": "AMAZONAS",
            "AP": "AMAPA",
            "BA": "BAHIA",
            "CE": "CEARA",
            "DF": "DISTRITO FEDERAL",
            "ES": "ESPIRITO SANTO",
            "GO": "GOIAS",
            "MA": "MARANHAO",
            "MG": "MINAS GERAIS",
            "MS": "MATO GROSSO DO SUL",
            "MT": "MATO GROSSO",
            "PA": "PARA",
            "PB": "PARAIBA",
            "PE": "PERNAMBUCO",
            "PI": "PIAUI",
            "PR": "PARANA",
            "RJ": "RIO DE JANEIRO",
            "RN": "RIO GRANDE DO NORTE",
            "RO": "RONDONIA",
            "RR": "RORAIMA",
            "RS": "RIO GRANDE DO SUL",
            "SC": "SANTA CATARINA",
            "SE": "SERGIPE",
            "SP": "SAO PAULO",
            "TO": "TOCANTINS",
        }

        # Check if we need to map state names
        if not geojson_states.intersection(data_states):
            # Create a copy with mapped state names
            estado_counts_mapped = estado_counts.copy()
            estado_counts_mapped["UF_MAPPED"] = estado_counts_mapped["UF"].map(
                estado_mapping
            )

            # Check if mapped names match
            mapped_states = set(estado_counts_mapped["UF_MAPPED"].dropna())
            matching_mapped = len(geojson_states.intersection(mapped_states))

            if matching_mapped > 0:
                # Use mapped data
                estado_counts = estado_counts_mapped.rename(columns={"UF_MAPPED": "UF"})
                # Recalculate hover text after mapping
                estado_counts["Hover_Text"] = (
                    estado_counts["UF"]
                    + "<br>"
                    + "Quantidade: "
                    + estado_counts["Quantidade"].astype(str)
                    + "<br>"
                    + "Percentual: "
                    + estado_counts["Percentual"].astype(str)
                    + "%"
                )

        # Use a more contrasting color scale for better proportional visualization
        fig = px.choropleth(
            estado_counts,
            geojson=brazil_states,
            locations="UF",
            featureidkey=featureidkey,
            color="Quantidade",
            hover_data=["Percentual"],
            color_continuous_scale=[
                [0.0, "#f7fbff"],
                [0.125, "#deebf7"],
                [0.25, "#c6dbef"],
                [0.375, "#9ecae1"],
                [0.5, "#6baed6"],
                [0.625, "#4292c6"],
                [0.75, "#2171b5"],
                [0.875, "#08519c"],
                [1.0, "#08306b"],
            ],
            title="Distribuição de Bombas por Estado (com %)",
            labels={
                "Quantidade": "Quantidade de Bombas",
                "Percentual": "Percentual (%)",
            },
        )

        # Update hover template to show percentages
        fig.update_traces(
            hovertemplate="<b>%{location}</b><br>"
            + "Quantidade: %{z}<br>"
            + "Percentual: %{customdata[0]:.1f}%<extra></extra>",
            customdata=estado_counts[["Percentual"]].values,
        )

        # Calculate actual centroids using polylabel from GeoJSON polygons
        try:
            from polylabel import polylabel

            state_centroids = {}

            # Calculate centroids from actual polygon geometries
            for feature in brazil_states.get("features", []):
                if "properties" in feature and "geometry" in feature:
                    props = feature["properties"]
                    geometry = feature["geometry"]

                    # Try different possible property names for state
                    state_id = None
                    for prop_name in [
                        "UF",
                        "uf",
                        "UF_05",
                        "SIGLA",
                        "sigla",
                        "ESTADO",
                        "estado",
                        "name",
                        "NAME",
                    ]:
                        if prop_name in props:
                            state_id = str(props[prop_name])
                            break

                    if state_id and geometry["type"] in ["Polygon", "MultiPolygon"]:
                        try:
                            # Handle both Polygon and MultiPolygon
                            if geometry["type"] == "Polygon":
                                # For Polygon, coordinates is [exterior_ring, hole1, hole2, ...]
                                polygon_coords = geometry["coordinates"][
                                    0
                                ]  # Just the exterior ring
                            else:  # MultiPolygon
                                # For MultiPolygon, take the largest polygon
                                largest_polygon = max(
                                    geometry["coordinates"],
                                    key=lambda poly: len(poly[0]),
                                )
                                polygon_coords = largest_polygon[
                                    0
                                ]  # Exterior ring of largest polygon

                            # Calculate polylabel (optimal label position)
                            centroid = polylabel([polygon_coords])
                            state_centroids[state_id] = (
                                centroid[0],
                                centroid[1],
                            )  # (lon, lat)

                        except Exception:
                            # Fallback to simple geometric center if polylabel fails
                            if geometry["type"] == "Polygon":
                                coords = geometry["coordinates"][0]
                            else:
                                coords = geometry["coordinates"][0][0]

                            lons = [coord[0] for coord in coords]
                            lats = [coord[1] for coord in coords]
                            centroid_lon = sum(lons) / len(lons)
                            centroid_lat = sum(lats) / len(lats)
                            state_centroids[state_id] = (centroid_lon, centroid_lat)

        except ImportError:
            # Fallback to hardcoded centroids if polylabel is not available
            state_centroids = {
                "AC": (-70.55, -9.0238),
                "AL": (-36.782, -9.5713),
                "AP": (-51.9777, 1.4558),
                "AM": (-64.0685, -3.4168),
                "BA": (-41.5756, -12.5797),
                "CE": (-39.5182, -5.4984),
                "DF": (-47.9292, -15.7801),
                "ES": (-40.3377, -19.1834),
                "GO": (-49.2532, -16.3544),
                "MA": (-45.0183, -4.9609),
                "MG": (-45.2471, -18.5122),
                "MS": (-54.7972, -20.7722),
                "MT": (-56.0926, -12.6819),
                "PA": (-52.9336, -6.7719),
                "PB": (-36.72, -7.24),
                "PE": (-37.9717, -8.8137),
                "PI": (-42.7098, -8.5014),
                "PR": (-51.6059, -24.89),
                "RJ": (-43.7729, -22.4756),
                "RN": (-36.9541, -5.4026),
                "RO": (-63.5806, -11.5057),
                "RR": (-61.4194, 2.7376),
                "RS": (-53.5233, -30.8283),
                "SC": (-50.1978, -27.2423),
                "SE": (-37.3045, -10.5741),
                "SP": (-48.6753, -23.9618),
                "TO": (-48.2982, -10.6632),
            }

        # Create data for percentage labels
        label_data = []
        for idx, row in estado_counts.iterrows():
            uf = row["UF"]
            if (
                uf in state_centroids and row["Percentual"] >= 1.0
            ):  # Only show % for states with >= 1%
                lon, lat = state_centroids[uf]
                label_data.append(
                    {
                        "UF": uf,
                        "lon": lon,
                        "lat": lat,
                        "text": f"{row['Percentual']:.1f}%",
                    }
                )

        # Add percentage labels as scatter trace
        if label_data:
            import pandas as pd

            label_df = pd.DataFrame(label_data)

            # Create a separate scatter_geo figure for labels
            fig_labels = px.scatter_geo(
                label_df, lat="lat", lon="lon", text="text", fitbounds="locations"
            )

            # Update the labels trace to show only text with border
            fig_labels.update_traces(
                mode="text",
                textfont=dict(size=14, color="white", family="Arial Black"),
                textposition="middle center",
                marker=dict(size=0),  # Hide markers
                showlegend=False,
                hoverinfo="skip",
            )

            # Add black text shadow/border effect by adding multiple text traces with slight offsets
            shadow_offsets = [
                (-0.1, -0.1),
                (-0.1, 0),
                (-0.1, 0.1),
                (0, -0.1),
                (0, 0.1),
                (0.1, -0.1),
                (0.1, 0),
                (0.1, 0.1),
            ]

            for offset_x, offset_y in shadow_offsets:
                shadow_df = label_df.copy()
                shadow_df["lat"] = shadow_df["lat"] + offset_y
                shadow_df["lon"] = shadow_df["lon"] + offset_x

                fig_shadow = px.scatter_geo(
                    shadow_df, lat="lat", lon="lon", text="text"
                )

                fig_shadow.update_traces(
                    mode="text",
                    textfont=dict(size=14, color="black", family="Arial Black"),
                    textposition="middle center",
                    marker=dict(size=0),
                    showlegend=False,
                    hoverinfo="skip",
                )

                # Add shadow traces first (they'll be behind the white text)
                for trace in fig_shadow.data:
                    fig.add_trace(trace)

            # Add the text traces to the main figure
            for trace in fig_labels.data:
                fig.add_trace(trace)

        fig.update_geos(
            showcountries=False,
            showcoastlines=False,
            showland=False,
            showocean=False,
            showframe=False,
            showlakes=False,
            showrivers=False,
            coastlinewidth=0,
            landcolor="white",
            oceancolor="white",
            fitbounds="locations",
        )

        fig.update_layout(
            height=500,
            margin={"r": 0, "t": 30, "l": 0, "b": 0},
            plot_bgcolor="white",
            paper_bgcolor="white",
        )

        return fig

    except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
        # Fallback: Create a simple bar chart if GeoJSON is not available with percentages
        st.warning(
            f"⚠️ Erro ao carregar mapa geográfico: {str(e)}. Exibindo gráfico de barras como alternativa."
        )

        # Calculate percentages for fallback chart
        total_bombas = estado_counts["Quantidade"].sum()
        estado_counts = estado_counts.copy()
        estado_counts["Percentual"] = (
            estado_counts["Quantidade"] / total_bombas * 100
        ).round(1)

        fig = px.bar(
            estado_counts,
            x="UF",
            y="Quantidade",
            color="Quantidade",
            hover_data=["Percentual"],
            text="Percentual",  # Add percentages as text on bars
            color_continuous_scale=[
                [0.0, "#f7fbff"],
                [0.125, "#deebf7"],
                [0.25, "#c6dbef"],
                [0.375, "#9ecae1"],
                [0.5, "#6baed6"],
                [0.625, "#4292c6"],
                [0.75, "#2171b5"],
                [0.875, "#08519c"],
                [1.0, "#08306b"],
            ],
            title="Distribuição de Bombas por Estado (com %)",
            labels={
                "Quantidade": "Quantidade de Bombas",
                "UF": "Estado",
                "Percentual": "Percentual (%)",
            },
        )

        # Update hover template for bar chart and format text on bars
        fig.update_traces(
            hovertemplate="<b>%{x}</b><br>"
            + "Quantidade: %{y}<br>"
            + "Percentual: %{customdata[0]:.1f}%<extra></extra>",
            texttemplate="%{text:.1f}%",
            textposition="outside",
        )

        fig.update_layout(
            xaxis_title="Estado",
            yaxis_title="Quantidade de Bombas",
            height=500,
            xaxis_tickangle=-45,
        )

        return fig


@st.cache_data(ttl=1800, show_spinner=False)
def create_kpi_metrics(df: pd.DataFrame) -> KpiMetrics:
    """Creates KPI metrics with optimizations.

    Returns:
        KpiMetrics: A typed dictionary containing:
            - total: Total number of records
            - abertos: Count of open tickets (STATUS == "ABERTO")
            - fechados: Count of closed tickets
            - aging_medio: Average aging in days
            - pct_garantia: Percentage under warranty
            - pct_rtm: Percentage with RTM
    """
    total = len(df)
    abertos = (df["STATUS"] == "ABERTO").sum()
    fechados = (df["STATUS"] != "ABERTO").sum()

    # Optimize aging calculation
    aging_medio = pd.to_numeric(df["AGING"], errors="coerce").mean()

    # Optimize percentage calculations
    pct_garantia = (df["GARANTIA"] == "DENTRO").mean() * 100
    pct_rtm = (df["RTM"] == "SIM").mean() * 100

    return {
        "total": total,
        "abertos": abertos,
        "fechados": fechados,
        "aging_medio": aging_medio,
        "pct_garantia": pct_garantia,
        "pct_rtm": pct_rtm,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def create_model_kpi_metrics(df: pd.DataFrame) -> Dict[str, float]:
    """Creates model percentage KPIs with optimizations.

    Uses MAIN_MODELS from constants.py to ensure consistency across the codebase.
    """
    if len(df) == 0 or "MODELO" not in df.columns:
        return {}

    # Calculate model distribution
    total = len(df)
    model_counts = df["MODELO"].value_counts()
    model_percentages = {}

    for model in MAIN_MODELS:
        count = model_counts.get(model, 0)
        percentage = (count / total * 100) if total > 0 else 0
        model_percentages[f"pct_{model.lower()}"] = percentage

    # Add "Others" percentage
    others_count = model_counts[~model_counts.index.isin(MAIN_MODELS)].sum()
    model_percentages["pct_others"] = (others_count / total * 100) if total > 0 else 0

    return model_percentages


# =============================================================================
# KPI VISUALIZATION COMPONENTS - Progress Bar Style
# =============================================================================

def render_kpi_card(label: str, value: str, icon: str = "", color: str = "#1f77b4") -> None:
    """Render a styled KPI card with large value and label.

    Args:
        label: The KPI label/description
        value: The formatted value to display
        icon: Optional emoji icon
        color: Accent color for the card
    """
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {color}15 0%, {color}05 100%);
            border-left: 4px solid {color};
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 8px;
        ">
            <div style="font-size: 28px; font-weight: 700; color: inherit; margin-bottom: 4px;">
                {icon} {value}
            </div>
            <div style="font-size: 13px; color: inherit; opacity: 0.7; text-transform: uppercase; letter-spacing: 0.5px;">
                {label}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_progress_bar(
    label: str,
    value: float,
    max_value: float = 100.0,
    color: str = "#1f77b4",
    show_percentage: bool = True,
) -> None:
    """Render a horizontal progress bar with label.

    Args:
        label: The metric label
        value: Current value
        max_value: Maximum value (default 100 for percentages)
        color: Bar fill color
        show_percentage: Whether to show % symbol
    """
    percentage = min((value / max_value) * 100, 100) if max_value > 0 else 0
    display_value = f"{value:.1f}%" if show_percentage else f"{value:.1f}"

    st.markdown(
        f"""
        <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                <span style="font-size: 13px; color: inherit; opacity: 0.8; font-weight: 500;">{label}</span>
                <span style="font-size: 13px; color: inherit; font-weight: 600;">{display_value}</span>
            </div>
            <div style="
                background: rgba(128, 128, 128, 0.25);
                border-radius: 4px;
                height: 8px;
                overflow: hidden;
            ">
                <div style="
                    background: {color};
                    width: {percentage}%;
                    height: 100%;
                    border-radius: 4px;
                    transition: width 0.3s ease;
                "></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_section_cards(metrics: KpiMetrics) -> None:
    """Render the main KPI cards in a clean grid layout.

    Args:
        metrics: KpiMetrics dictionary from create_kpi_metrics()
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_kpi_card("Total de Chamados", f"{metrics['total']:,}", "📋", "#2196F3")

    with col2:
        render_kpi_card("Abertos", f"{metrics['abertos']:,}", "🔴", "#f44336")

    with col3:
        render_kpi_card("Fechados", f"{metrics['fechados']:,}", "✅", "#4CAF50")

    with col4:
        aging_value = f"{metrics['aging_medio']:.1f}" if not pd.isna(metrics["aging_medio"]) else "-"
        render_kpi_card("Aging Médio (dias)", aging_value, "⏱️", "#FF9800")


def render_percentage_bars(metrics: KpiMetrics) -> None:
    """Render percentage KPIs as progress bars.

    Args:
        metrics: KpiMetrics dictionary from create_kpi_metrics()
    """
    col1, col2 = st.columns(2)

    with col1:
        render_progress_bar("Dentro da Garantia", metrics["pct_garantia"], color="#4CAF50")

    with col2:
        render_progress_bar("RTM", metrics["pct_rtm"], color="#FF5722")


def render_model_distribution_bars(model_metrics: Dict[str, float]) -> None:
    """Render model distribution as horizontal progress bars.

    Args:
        model_metrics: Dictionary from create_model_kpi_metrics()
    """
    if not model_metrics:
        return

    # Color palette for models
    colors = {
        "pct_helix": "#2196F3",
        "pct_vista": "#9C27B0",
        "pct_century": "#00BCD4",
        "pct_3g": "#FF9800",
        "pct_e123": "#4CAF50",
        "pct_7502a": "#E91E63",
        "pct_others": "#9E9E9E",
    }

    labels = {
        "pct_helix": "HELIX",
        "pct_vista": "VISTA",
        "pct_century": "CENTURY",
        "pct_3g": "3G",
        "pct_e123": "E123",
        "pct_7502a": "7502A",
        "pct_others": "Outros",
    }

    # Sort by value descending, but keep "Outros" last
    # Filter out items with 0% value
    sorted_items = sorted(
        [(k, v) for k, v in model_metrics.items() if k != "pct_others" and v > 0],
        key=lambda x: x[1],
        reverse=True,
    )
    if "pct_others" in model_metrics and model_metrics["pct_others"] > 0:
        sorted_items.append(("pct_others", model_metrics["pct_others"]))

    # Render in two columns for better layout
    col1, col2 = st.columns(2)

    for i, (key, value) in enumerate(sorted_items):
        with col1 if i % 2 == 0 else col2:
            render_progress_bar(labels[key], value, color=colors.get(key, "#1f77b4"))


def render_section_header(title: str, icon: str = "") -> None:
    """Render a styled section header.

    Args:
        title: Section title
        icon: Optional emoji icon
    """
    st.markdown(
        f"""
        <div style="
            font-size: 14px;
            font-weight: 600;
            color: inherit;
            margin: 20px 0 12px 0;
            padding-bottom: 8px;
            border-bottom: 2px solid currentColor;
            opacity: 0.8;
        ">
            {icon} {title}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_currency_card(label: str, value: float, icon: str = "💰", color: str = "#4CAF50") -> None:
    """Render a currency KPI card with Brazilian formatting.

    Args:
        label: The KPI label
        value: The numeric value
        icon: Optional emoji icon
        color: Accent color
    """
    # Format as Brazilian currency
    formatted = f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {color}15 0%, {color}05 100%);
            border-left: 4px solid {color};
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 8px;
        ">
            <div style="font-size: 18px; font-weight: 700; color: inherit; margin-bottom: 2px;">
                {icon} {formatted}
            </div>
            <div style="font-size: 11px; color: inherit; opacity: 0.7; text-transform: uppercase; letter-spacing: 0.5px;">
                {label}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_warranty_distribution_bars(garantia_dist: Dict[str, float]) -> None:
    """Render warranty period distribution as progress bars.

    Args:
        garantia_dist: Dictionary with pct_6m, pct_12m, pct_18m, pct_24m, pct_36m
    """
    labels = {
        "pct_6m": "6 meses",
        "pct_12m": "12 meses",
        "pct_18m": "18 meses",
        "pct_24m": "24 meses",
        "pct_36m": "36 meses",
    }

    colors = {
        "pct_6m": "#FF5722",
        "pct_12m": "#FF9800",
        "pct_18m": "#FFC107",
        "pct_24m": "#8BC34A",
        "pct_36m": "#4CAF50",
    }

    col1, col2 = st.columns(2)

    for i, (key, label) in enumerate(labels.items()):
        value = garantia_dist.get(key, 0)
        with col1 if i % 2 == 0 else col2:
            render_progress_bar(label, value, color=colors.get(key, "#1f77b4"))


def render_multi_progress_bars(
    items: list,
    title: str = "",
    columns: int = 2,
) -> None:
    """Render multiple progress bars in a grid layout.

    Args:
        items: List of tuples (label, value, color)
        title: Optional section title
        columns: Number of columns (default 2)
    """
    if title:
        render_section_header(title)

    cols = st.columns(columns)

    for i, (label, value, color) in enumerate(items):
        with cols[i % columns]:
            render_progress_bar(label, value, color=color)
