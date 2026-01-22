import json

import plotly.express as px
import pandas as pd
from typing import Dict, Any
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
def create_kpi_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Creates KPI metrics with optimizations."""
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
    """Creates model percentage KPIs with optimizations."""
    if len(df) == 0 or "MODELO" not in df.columns:
        return {}

    # Calculate model distribution
    total = len(df)
    model_counts = df["MODELO"].value_counts()
    model_percentages = {}

    # Get the main models and sort them
    main_models = ["HELIX", "VISTA", "CENTURY", "3G", "E123", "7502A"]

    for model in main_models:
        count = model_counts.get(model, 0)
        percentage = (count / total * 100) if total > 0 else 0
        model_percentages[f"pct_{model.lower()}"] = percentage

    # Add "Others" percentage
    others_count = model_counts[~model_counts.index.isin(main_models)].sum()
    model_percentages["pct_others"] = (others_count / total * 100) if total > 0 else 0

    return model_percentages
