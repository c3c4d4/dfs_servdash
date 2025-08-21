"""
Advanced Analytics Dashboard - DFS ServiceWatch
AI-powered insights, predictive analytics, and advanced business intelligence.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# Import modules
from data_loader import carregar_dados_merged, carregar_o2c, carregar_base_erros_rtm
from auth import check_password
import advanced_analytics as aa
import business_logic as bl

st.set_page_config(
    page_title="Analytics Avançado - EM DESENVOLVIMENTO", 
    layout="wide",
    page_icon="🧠"
)

check_password()

# Load data
@st.cache_data(ttl=3600, show_spinner=False)
def load_all_data():
    """Load all required data for analytics."""
    try:
        chamados = carregar_dados_merged()
        chamados.columns = chamados.columns.str.strip().str.upper()
        
        # Clean data
        for col in chamados.select_dtypes(include=['object']).columns:
            chamados[col] = chamados[col].str.strip().str.upper()
        
        bombas = carregar_o2c()
        erros_rtm = carregar_base_erros_rtm()
        
        return chamados, bombas, erros_rtm
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# Load data
with st.spinner("Carregando dados para análise avançada..."):
    chamados_df, bombas_df, erros_rtm_df = load_all_data()

if len(chamados_df) == 0:
    st.error("❌ Não foi possível carregar os dados. Verifique os arquivos de dados.")
    st.stop()

# Page header
st.title("🧠 Analytics Avançado - EM DESENVOLVIMENTO")

# Sidebar for analytics options
st.sidebar.header("🔬 Opções de Análise")
analysis_type = st.sidebar.selectbox(
    "Escolha o tipo de análise:",
    [
        "Predição de Falhas",
        # "Análise Temporal",
        # "Análise de Correlação", 
        # "Otimização de Manutenção",
        # "Previsão de Performance",
    ]
)

# Analysis sections
if analysis_type == "Predição de Falhas":
    st.header("Predição de Falhas")
    st.markdown("**Modelo de Machine Learning para prever riscos de falha em bombas**")
    
    with st.expander("ℹ️ Como funciona"):
        st.markdown("""
        - **Algoritmo**: Random Forest Regressor
        - **Características**: Idade da bomba, histórico de chamados, tipo de serviços
        - **Saída**: Score de risco (0-10+) e categoria (Baixo/Médio/Alto/Crítico)
        - **Atualização**: Modelo retreinado automaticamente com novos dados
        """)
    
    # Prepare features
    with st.spinner("Preparando dados para análise preditiva..."):
        features_df = aa.failure_predictor.prepare_features(bombas_df, chamados_df)
    
    if len(features_df) > 0:
        # Train model
        with st.spinner("Treinando modelo de predição..."):
            model_results = aa.failure_predictor.train_model(features_df)
        
        if 'error' not in model_results:
            # Model performance metrics
            st.subheader("Performance do Modelo")
            col1, col2, col3, col4 = st.columns(4)
            
            col1.metric("Bombas Analisadas", f"{len(features_df):,}")
            col2.metric("MAE (Erro Médio)", f"{model_results['mae']:.2f}")
            col3.metric("RMSE", f"{model_results['rmse']:.2f}")
            col4.metric("Features Utilizadas", len(model_results['features']))
            
            # # Feature importance
            # st.subheader("🎯 Importância das Características")
            # fig_importance = px.bar(
            #     model_results['feature_importance'].head(10),
            #     x='importance',
            #     y='feature',
            #     orientation='h',
            #     title="Top 10 Características Mais Importantes",
            #     color='importance',
            #     color_continuous_scale='viridis'
            # )
            # fig_importance.update_layout(height=400)
            # st.plotly_chart(fig_importance, use_container_width=True)
            
            # Predictions
            predictions_df = aa.failure_predictor.predict_failures(features_df, model_results)
            
            if len(predictions_df) > 0:
                st.subheader("🚨 Bombas de Alto Risco")
                
                # Risk distribution
                                                
                # High-risk pumps table
                high_risk = predictions_df[predictions_df['RISK_CATEGORY'].isin(['Alto', 'Crítico'])]
                
                if len(high_risk) > 0:
                    st.dataframe(
                        high_risk[['NUM_SERIAL', 'UF', 'CIDADE', 'RISK_SCORE', 'RISK_CATEGORY']],
                        column_config={
                            "NUM_SERIAL": "Número Serial",
                            "UF": "Estado", 
                            "CIDADE": "Cidade",
                            "RISK_SCORE": st.column_config.NumberColumn("Score de Risco", format="%.2f"),
                            "RISK_CATEGORY": "Categoria de Risco"
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("✅ Nenhuma bomba identificada como alto risco!")
        else:
            st.error(f"Erro no modelo: {model_results['error']}")
    else:
        st.warning("⚠️ Dados insuficientes para análise preditiva.")

elif analysis_type == "Análise Temporal":
    st.header("Análise Temporal")
    st.markdown("**Análise avançada de tendências e padrões temporais**")
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Data Início", value=datetime.now() - timedelta(days=730))
    with col2:
        end_date = st.date_input("Data Fim", value=datetime.now())
    
    # Filter data by date range
    chamados_filtered = chamados_df.copy()
    chamados_filtered['DATA'] = pd.to_datetime(chamados_filtered['DATA'], errors='coerce')
    chamados_filtered = chamados_filtered[
        (chamados_filtered['DATA'] >= pd.Timestamp(start_date)) & 
        (chamados_filtered['DATA'] <= pd.Timestamp(end_date))
    ]
    
    if len(chamados_filtered) > 0:
        # Prepare time series data
        with st.spinner("Analisando padrões temporais..."):
            ts_data = aa.time_series_analyzer.prepare_time_series(chamados_filtered)
        
        if len(ts_data) > 0:
            # Create visualizations
            charts = aa.time_series_analyzer.create_time_series_charts(ts_data)
            
            # Display charts
            if 'volume' in charts:
                st.subheader("Evolução do Volume")
                st.plotly_chart(charts['volume'], use_container_width=True)
            
            if 'dashboard' in charts:
                st.subheader("Dashboard Multi-Métricas")
                st.plotly_chart(charts['dashboard'], use_container_width=True)
            
            if 'seasonal' in charts:
                st.subheader("🗓️ Análise Sazonal")
                st.plotly_chart(charts['seasonal'], use_container_width=True)
            
            # Trend Analysis
            st.subheader("Análise de Tendências")
            with st.spinner("Analisando tendências..."):
                trends = aa.time_series_analyzer.create_trend_analysis(ts_data)
            
            if trends:
                trend_cols = st.columns(4)
                
                metrics_labels = {
                    'TOTAL_CHAMADOS': 'Total de Chamados',
                    'TAXA_GARANTIA': 'Taxa de Garantia (%)',
                    'TAXA_RTM': 'Taxa RTM (%)',
                    'CHAMADOS_POR_BOMBA': 'Chamados/Bomba'
                }
                
                for i, (metric, data) in enumerate(trends.items()):
                    if i < 4:
                        with trend_cols[i]:
                            direction_icon = {
                                'Crescente': '📈',
                                'Decrescente': '📉',
                                'Estável': '➡️'
                            }.get(data['trend_direction'], '➡️')
                            
                            st.metric(
                                f"{direction_icon} {metrics_labels.get(metric, metric)}",
                                f"{data['current_value']:.1f}",
                                f"{data['trend_direction']} (R²: {data['r_squared']:.2f})"
                            )
            
            # Seasonality Analysis
            st.subheader("🗓️ Análise de Sazonalidade")
            metric_for_season = st.selectbox(
                "Selecione a métrica para análise sazonal:",
                ['TOTAL_CHAMADOS', 'TAXA_GARANTIA', 'TAXA_RTM', 'CHAMADOS_POR_BOMBA'],
                format_func=lambda x: metrics_labels.get(x, x)
            )
            
            with st.spinner("Detectando padrões sazonais..."):
                seasonality = aa.time_series_analyzer.detect_seasonality(ts_data, metric_for_season)
            
            if seasonality and seasonality.get('has_seasonality', False):
                col1, col2, col3 = st.columns(3)
                col1.metric("🏔️ Pico Sazonal", seasonality['peak_month'])
                col2.metric("🏝️ Vale Sazonal", seasonality['trough_month']) 
                col3.metric("Força Sazonal", f"{seasonality['seasonality_strength']:.2f}")
                
                # Monthly averages chart
                month_data = seasonality['monthly_averages']
                months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                         'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
                
                fig_season = go.Figure()
                fig_season.add_trace(go.Scatter(
                    x=months,
                    y=[month_data.get(i+1, 0) for i in range(12)],
                    mode='lines+markers',
                    name=metrics_labels.get(metric_for_season, metric_for_season),
                    line=dict(color='#ff6b6b', width=3),
                    marker=dict(size=8)
                ))
                
                fig_season.update_layout(
                    title=f'Padrão Sazonal - {metrics_labels.get(metric_for_season, metric_for_season)}',
                    xaxis_title='Mês',
                    yaxis_title=metrics_labels.get(metric_for_season, metric_for_season),
                    height=400
                )
                
                st.plotly_chart(fig_season, use_container_width=True)
            else:
                st.info("ℹ️ Não foram detectados padrões sazonais significativos para esta métrica.")
            
            # Forecasting
            st.subheader("Previsão")
            forecast_periods = st.slider("Períodos para prever (meses):", 3, 12, 6)
            forecast_metric = st.selectbox(
                "Métrica para previsão:",
                ['TOTAL_CHAMADOS', 'TAXA_GARANTIA', 'TAXA_RTM', 'CHAMADOS_POR_BOMBA'],
                format_func=lambda x: metrics_labels.get(x, x),
                key='forecast_metric'
            )
            
            with st.spinner("Gerando previsões..."):
                forecast_data = aa.time_series_analyzer.forecast_metric(ts_data, forecast_metric, forecast_periods)
            
            if len(forecast_data) > 0:
                # Create forecast chart
                fig_forecast = go.Figure()
                
                # Historical data
                historical_data = forecast_data[forecast_data['TIPO'] == 'Histórico']
                fig_forecast.add_trace(go.Scatter(
                    x=historical_data['DATA'],
                    y=historical_data['VALOR_PREVISTO'],
                    mode='lines+markers',
                    name='Histórico',
                    line=dict(color='#1f77b4', width=2),
                    marker=dict(size=4)
                ))
                
                # Forecast data
                forecast_future = forecast_data[forecast_data['TIPO'] == 'Previsão']
                fig_forecast.add_trace(go.Scatter(
                    x=forecast_future['DATA'],
                    y=forecast_future['VALOR_PREVISTO'],
                    mode='lines+markers',
                    name='Previsão',
                    line=dict(color='#ff7f0e', width=3, dash='dash'),
                    marker=dict(size=6)
                ))
                
                fig_forecast.update_layout(
                    title=f'Previsão - {metrics_labels.get(forecast_metric, forecast_metric)}',
                    xaxis_title='Período',
                    yaxis_title=metrics_labels.get(forecast_metric, forecast_metric),
                    hovermode='x unified',
                    height=500
                )
                
                st.plotly_chart(fig_forecast, use_container_width=True)
                
                # Show forecast values
                st.subheader("Valores Previstos")
                forecast_display = forecast_future[['DATA', 'VALOR_PREVISTO']].copy()
                forecast_display['DATA'] = forecast_display['DATA'].dt.strftime('%Y-%m')
                forecast_display.columns = ['Período', 'Valor Previsto']
                forecast_display['Valor Previsto'] = forecast_display['Valor Previsto'].round(1)
                
                st.dataframe(forecast_display, use_container_width=True, hide_index=True)
            else:
                st.warning("⚠️ Não foi possível gerar previsões com os dados disponíveis.")
            
            # Summary statistics
            st.subheader("📋 Estatísticas do Período")
            col1, col2, col3, col4 = st.columns(4)
            
            col1.metric("Total de Chamados", f"{ts_data['TOTAL_CHAMADOS'].sum():,}")
            col2.metric("Média Mensal", f"{ts_data['TOTAL_CHAMADOS'].mean():.0f}")
            col3.metric("Pico Mensal", f"{ts_data['TOTAL_CHAMADOS'].max():,}")
            col4.metric("Taxa Média Garantia", f"{ts_data['TAXA_GARANTIA'].mean():.1f}%")
        else:
            st.warning("⚠️ Dados insuficientes para análise temporal.")
    else:
        st.warning("⚠️ Nenhum dado encontrado no período selecionado.")

elif analysis_type == "Análise de Correlação":
    st.header("Análise de Correlação")
    st.markdown("**Descubra relacionamentos e dependências entre variáveis**")
    
    # Prepare numerical dataset
    with st.spinner("Calculando correlações..."):
        # Combine relevant numerical data
        analysis_df = bombas_df.copy()
        
        # Add aggregated chamados data
        chamados_agg = chamados_df.groupby('CHASSI').agg({
            'SS': 'count',
            'SERVIÇO': lambda x: (x.str.contains('GARANTIA', na=False)).sum(),
            'STATUS': lambda x: (x == 'ABERTO').sum()
        }).reset_index()
        chamados_agg.columns = ['NUM_SERIAL', 'TOTAL_CHAMADOS', 'CHAMADOS_GARANTIA', 'CHAMADOS_ABERTOS']
        
        # Merge data
        analysis_df = analysis_df.merge(chamados_agg, on='NUM_SERIAL', how='left')
        analysis_df = analysis_df.fillna(0)
        
        # Calculate correlations
        corr_matrix = aa.correlation_analyzer.calculate_correlations(analysis_df)
    
    if len(corr_matrix) > 0:
        # Correlation heatmap
        st.subheader("🔥 Mapa de Correlação")
        fig_corr = aa.correlation_analyzer.create_correlation_heatmap(corr_matrix)
        st.plotly_chart(fig_corr, use_container_width=True)
        
        # Strong correlations table
        st.subheader("💪 Correlações Fortes")
        threshold = st.slider("Limite de correlação", 0.3, 0.9, 0.5, 0.1)
        
        strong_corr = aa.correlation_analyzer.find_strong_correlations(corr_matrix, threshold)
        
        if len(strong_corr) > 0:
            st.dataframe(
                strong_corr,
                column_config={
                    "Correlação": st.column_config.NumberColumn("Correlação", format="%.3f")
                },
                use_container_width=True,
                hide_index=True
            )
            
            # Scatter plots for strongest correlations
            st.subheader("Gráficos de Dispersão")
            
            # Select top 3 correlations for visualization
            top_correlations = strong_corr.head(3)
            
            for i, row in top_correlations.iterrows():
                var1, var2, corr_val = row['Variável 1'], row['Variável 2'], row['Correlação']
                
                if var1 in analysis_df.columns and var2 in analysis_df.columns:
                    fig_scatter = px.scatter(
                        analysis_df, 
                        x=var1, 
                        y=var2,
                        title=f'{var1} vs {var2} (r={corr_val:.3f})',
                        trendline="ols",
                        height=400
                    )
                    
                    fig_scatter.update_traces(marker=dict(size=8, opacity=0.6))
                    fig_scatter.update_layout(
                        showlegend=False,
                        xaxis_title=var1,
                        yaxis_title=var2
                    )
                    
                    st.plotly_chart(fig_scatter, use_container_width=True)
            
            # Correlation insights
            st.subheader("🔍 Insights de Correlação")
            
            with st.expander("💡 Interpretação das Correlações", expanded=True):
                st.markdown("""
                **Como interpretar as correlações:**
                - **0.7 a 1.0**: Correlação muito forte (positiva)
                - **0.5 a 0.7**: Correlação forte (positiva) 
                - **0.3 a 0.5**: Correlação moderada (positiva)
                - **-0.3 a -0.5**: Correlação moderada (negativa)
                - **-0.5 a -0.7**: Correlação forte (negativa)
                - **-0.7 a -1.0**: Correlação muito forte (negativa)
                
                **Correlações positivas**: Quando uma variável aumenta, a outra também tende a aumentar.
                **Correlações negativas**: Quando uma variável aumenta, a outra tende a diminuir.
                """)
                
                # Generate automatic insights
                for _, row in top_correlations.iterrows():
                    var1, var2, corr_val = row['Variável 1'], row['Variável 2'], row['Correlação']
                    
                    if corr_val > 0.7:
                        strength = "muito forte"
                        direction = "positiva"
                        interpretation = f"existe uma relação {strength} {direction}"
                    elif corr_val > 0.5:
                        strength = "forte"  
                        direction = "positiva"
                        interpretation = f"existe uma relação {strength} {direction}"
                    elif corr_val > 0.3:
                        strength = "moderada"
                        direction = "positiva"
                        interpretation = f"existe uma relação {strength} {direction}"
                    elif corr_val < -0.7:
                        strength = "muito forte"
                        direction = "negativa"
                        interpretation = f"existe uma relação {strength} {direction}"
                    elif corr_val < -0.5:
                        strength = "forte"
                        direction = "negativa"
                        interpretation = f"existe uma relação {strength} {direction}"
                    else:
                        strength = "moderada"
                        direction = "negativa"
                        interpretation = f"existe uma relação {strength} {direction}"
                    
                    st.info(f"**{var1}** e **{var2}**: {interpretation} (r={corr_val:.3f})")
        else:
            st.info(f"Nenhuma correlação forte encontrada acima de {threshold}")
            
            # Show summary statistics instead
            st.subheader("Estatísticas Descritivas")
            numeric_cols = analysis_df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                desc_stats = analysis_df[numeric_cols].describe().round(2)
                st.dataframe(desc_stats, use_container_width=True)
    else:
        st.warning("⚠️ Dados insuficientes para análise de correlação.")

elif analysis_type == "Otimização de Manutenção":
    st.header("Otimização de Manutenção")
    st.markdown("**Análise inteligente para otimizar cronogramas de manutenção**")
    
    with st.spinner("Analisando padrões de manutenção..."):
        maintenance_analysis = aa.maintenance_optimizer.analyze_maintenance_patterns(chamados_df)
    
    if maintenance_analysis:
        # Summary metrics
        st.subheader("Resumo da Manutenção")
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Total de Serviços", f"{maintenance_analysis['total_services']:,}")
        col2.metric("Serviços Preventivos", f"{maintenance_analysis['preventive_count']:,}")
        col3.metric("Serviços Reativos", f"{maintenance_analysis['reactive_count']:,}")
        col4.metric("Taxa Preventiva", f"{maintenance_analysis['preventive_ratio']:.1f}%")
        
        # Service frequency analysis
        if len(maintenance_analysis['service_analysis']) > 0:
            st.subheader("🔍 Análise por Tipo de Serviço")
            
            service_df = maintenance_analysis['service_analysis'].head(10)
            fig_services = px.bar(
                service_df,
                x='FREQUENCIA_MEDIA',
                y='SERVIÇO',
                orientation='h',
                title="Frequência Média por Tipo de Serviço",
                color='FREQUENCIA_MEDIA',
                color_continuous_scale='reds'
            )
            fig_services.update_layout(height=500)
            st.plotly_chart(fig_services, use_container_width=True)
            
            # Recommendations
            st.subheader("🎯 Recomendações de Otimização")
            recommendations = aa.maintenance_optimizer.recommend_maintenance_schedule(maintenance_analysis)
            
            if len(recommendations) > 0:
                # Priority filter
                priority_filter = st.multiselect(
                    "Filtrar por prioridade:",
                    ["Crítica", "Alta", "Média", "Baixa"],
                    default=["Crítica", "Alta"]
                )
                
                filtered_recommendations = recommendations[
                    recommendations['Prioridade'].isin(priority_filter)
                ]
                
                if len(filtered_recommendations) > 0:
                    st.dataframe(
                        filtered_recommendations.head(20),
                        column_config={
                            "Frequência Atual": st.column_config.NumberColumn("Frequência Atual", format="%.2f"),
                            "Score de Impacto": st.column_config.NumberColumn("Score de Impacto", format="%.1f")
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # ROI Analysis
                    st.subheader("💰 Análise de ROI")
                    roi_data = aa.maintenance_optimizer.calculate_maintenance_roi(maintenance_analysis)
                    
                    if roi_data:
                        roi_cols = st.columns(4)
                        
                        roi_cols[0].metric(
                            "💸 Custo Atual Total",
                            f"R$ {roi_data['current_total_cost']:,.0f}"
                        )
                        roi_cols[1].metric(
                            "💵 Custo Otimizado",
                            f"R$ {roi_data['optimized_total_cost']:,.0f}"
                        )
                        roi_cols[2].metric(
                            "💰 Economia Anual",
                            f"R$ {roi_data['annual_savings']:,.0f}",
                            f"{roi_data['roi_percentage']:+.1f}%"
                        )
                        roi_cols[3].metric(
                            "⏱️ Payback",
                            f"{roi_data['payback_period_months']:.0f} meses"
                        )
                        
                        # Cost comparison chart
                        cost_comparison = pd.DataFrame({
                            'Cenário': ['Atual', 'Otimizado'],
                            'Preventiva': [roi_data['current_preventive_cost'], roi_data['optimized_preventive_cost']],
                            'Reativa': [roi_data['current_reactive_cost'], roi_data['optimized_reactive_cost']]
                        })
                        
                        fig_cost = px.bar(
                            cost_comparison.melt(id_vars='Cenário', var_name='Tipo', value_name='Custo'),
                            x='Cenário',
                            y='Custo',
                            color='Tipo',
                            title='Comparação de Custos: Atual vs Otimizado',
                            color_discrete_map={'Preventiva': '#2E8B57', 'Reativa': '#DC143C'}
                        )
                        fig_cost.update_layout(height=400)
                        st.plotly_chart(fig_cost, use_container_width=True)
                    
                    # Maintenance Calendar
                    st.subheader("📅 Calendário de Manutenção")
                    
                    calendar_data = aa.maintenance_optimizer.create_maintenance_calendar(filtered_recommendations)
                    
                    if len(calendar_data) > 0:
                        # Show next 6 months
                        next_6_months = calendar_data.head(20)
                        
                        st.dataframe(
                            next_6_months,
                            column_config={
                                "Data Planejada": st.column_config.DateColumn("Data Planejada")
                            },
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Calendar visualization
                        calendar_counts = calendar_data.groupby('Data Planejada').size().reset_index(name='Quantidade')
                        calendar_counts['Data Planejada'] = pd.to_datetime(calendar_counts['Data Planejada'])
                        
                        fig_calendar = px.bar(
                            calendar_counts,
                            x='Data Planejada',
                            y='Quantidade',
                            title='Distribuição de Manutenções Planejadas',
                            color='Quantidade',
                            color_continuous_scale='Viridis'
                        )
                        fig_calendar.update_layout(height=400)
                        st.plotly_chart(fig_calendar, use_container_width=True)
                        
                        # Export calendar
                        csv_calendar = calendar_data.to_csv(index=False)
                        st.download_button(
                            label="📥 Baixar Calendário de Manutenção (CSV)",
                            data=csv_calendar,
                            file_name=f"calendario_manutencao_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("Nenhuma manutenção prioritária programada.")
                else:
                    st.info("Nenhuma recomendação encontrada para os filtros selecionados.")
            else:
                st.info("Nenhuma recomendação específica no momento.")
    else:
        st.warning("⚠️ Dados insuficientes para análise de manutenção.")

elif analysis_type == "Previsão de Performance":
    st.header("Previsão de Performance")
    st.markdown("**Previsões avançadas de KPIs e métricas de performance usando Machine Learning**")
    
    with st.expander("ℹ️ Como funciona"):
        st.markdown("""
        - **Modelo**: Random Forest com características temporais e de lag
        - **Granularidade**: Previsões semanais para maior precisão
        - **Métricas**: Volume de chamados, taxas de garantia/RTM, eficiência
        - **Horizonte**: Até 12 semanas no futuro
        - **Confiança**: Intervalos de confiança para incerteza
        """)
    
    # Forecast configuration
    col1, col2 = st.columns(2)
    with col1:
        forecast_weeks = st.slider("Semanas para prever:", 4, 24, 12)
    with col2:
        show_confidence = st.checkbox("Mostrar intervalos de confiança", value=True)
    
    # Prepare forecast data
    with st.spinner("Preparando dados para previsão de performance..."):
        forecast_data = aa.performance_forecaster.prepare_forecast_data(chamados_df, bombas_df)
    
    if forecast_data and 'weekly_performance' in forecast_data:
        weekly_data = forecast_data['weekly_performance']
        
        if len(weekly_data) > 0:
            # Generate forecasts
            with st.spinner("Gerando previsões com Machine Learning..."):
                forecasts = aa.performance_forecaster.forecast_performance_metrics(weekly_data, forecast_weeks)
            
            # Performance insights
            insights = aa.performance_forecaster.performance_insights(weekly_data, forecasts)
            
            # Current performance summary
            st.subheader("Performance Atual")
            recent_data = weekly_data.tail(4)  # Last 4 weeks
            
            perf_cols = st.columns(4)
            
            if len(recent_data) > 0:
                perf_cols[0].metric(
                    "📞 Chamados/Semana",
                    f"{recent_data['TOTAL_CHAMADOS'].mean():.0f}",
                    f"{insights.get('TOTAL_CHAMADOS', {}).get('pct_change', 0):+.1f}%" if insights.get('TOTAL_CHAMADOS') else ""
                )
                perf_cols[1].metric(
                    "🛡️ Taxa Garantia",
                    f"{recent_data['TAXA_GARANTIA'].mean():.1f}%",
                    f"{insights.get('TAXA_GARANTIA', {}).get('pct_change', 0):+.1f}%" if insights.get('TAXA_GARANTIA') else ""
                )
                perf_cols[2].metric(
                    "📡 Taxa RTM",
                    f"{recent_data['TAXA_RTM'].mean():.1f}%",
                    f"{insights.get('TAXA_RTM', {}).get('pct_change', 0):+.1f}%" if insights.get('TAXA_RTM') else ""
                )
                perf_cols[3].metric(
                    "⚡ Chamados/Bomba",
                    f"{recent_data['CHAMADOS_POR_BOMBA'].mean():.2f}",
                    f"{insights.get('CHAMADOS_POR_BOMBA', {}).get('pct_change', 0):+.1f}%" if insights.get('CHAMADOS_POR_BOMBA') else ""
                )
            
            # Forecast charts
            if len(forecasts) > 0:
                charts = aa.performance_forecaster.create_performance_dashboard(weekly_data, forecasts)
                
                # Display forecast charts
                for metric, chart in charts.items():
                    if not show_confidence:
                        # Remove confidence interval traces
                        chart.data = [trace for trace in chart.data if 'Confiança' not in trace.name]
                    
                    st.plotly_chart(chart, use_container_width=True)
                
                # Forecast insights
                st.subheader("Insights das Previsões")
                
                if 'forecasts' in insights:
                    insight_cols = st.columns(2)
                    
                    with insight_cols[0]:
                        st.markdown("**🎯 Previsões de Tendência**")
                        for metric, forecast_data in insights['forecasts'].items():
                            trend_icon = "📈" if forecast_data['forecast_trend'] == 'Crescente' else "📉"
                            metric_name = {
                                'TOTAL_CHAMADOS': 'Total de Chamados',
                                'TAXA_GARANTIA': 'Taxa de Garantia',
                                'TAXA_RTM': 'Taxa RTM',
                                'CHAMADOS_POR_BOMBA': 'Chamados por Bomba'
                            }.get(metric, metric)
                            
                            st.info(f"{trend_icon} **{metric_name}**: {forecast_data['forecast_trend']} (Média prevista: {forecast_data['forecast_avg']:.1f})")
                    
                    with insight_cols[1]:
                        st.markdown("**⚠️ Alertas de Performance**")
                        
                        # Generate alerts based on forecasts
                        alerts = []
                        for metric, forecast_data in insights['forecasts'].items():
                            if metric == 'TOTAL_CHAMADOS' and forecast_data['forecast_avg'] > weekly_data['TOTAL_CHAMADOS'].mean() * 1.2:
                                alerts.append("🔴 Volume de chamados pode aumentar significativamente")
                            elif metric == 'TAXA_GARANTIA' and forecast_data['forecast_avg'] > 40:
                                alerts.append("🟡 Taxa de garantia pode subir acima do normal")
                            elif metric == 'CHAMADOS_POR_BOMBA' and forecast_data['forecast_avg'] > 0.5:
                                alerts.append("🟠 Eficiência pode diminuir (mais chamados por bomba)")
                        
                        if alerts:
                            for alert in alerts:
                                st.warning(alert)
                        else:
                            st.success("✅ Performance dentro do esperado")
                
                # Export forecasts
                st.subheader("📥 Exportar Previsões")
                
                # Format forecast data for export
                export_forecasts = forecasts.copy()
                export_forecasts['DATA'] = export_forecasts['DATA'].dt.strftime('%Y-%m-%d')
                export_forecasts['VALOR_PREVISTO'] = export_forecasts['VALOR_PREVISTO'].round(2)
                
                csv_forecasts = export_forecasts.to_csv(index=False)
                st.download_button(
                    label="Baixar Previsões (CSV)",
                    data=csv_forecasts,
                    file_name=f"previsoes_performance_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("⚠️ Não foi possível gerar previsões com os dados disponíveis.")
        else:
            st.warning("⚠️ Dados semanais insuficientes para previsão.")
    else:
        st.warning("⚠️ Erro ao preparar dados para previsão de performance.")

elif analysis_type == "Dashboard Personalizado":
    st.header("Dashboard Personalizado")
    st.markdown("**Configure seu próprio dashboard com métricas customizadas**")
    
    # Dashboard configuration
    st.subheader("⚙️ Configuração do Dashboard")
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_metrics = st.multiselect(
            "Selecione as métricas:",
            [
                "Volume de Chamados",
                "Taxa de Garantia",
                "Taxa RTM", 
                "Distribuição por Estado",
                "Top Serviços",
                "Performance por Mês",
                "Status dos Chamados"
            ],
            default=["Volume de Chamados", "Taxa de Garantia", "Distribuição por Estado"]
        )
    
    with col2:
        time_period = st.selectbox(
            "Período de análise:",
            ["Último mês", "Últimos 3 meses", "Últimos 6 meses", "Último ano", "Todos os dados"]
        )
        
        chart_type = st.selectbox(
            "Tipo de gráfico preferido:",
            ["Automático", "Barras", "Linhas", "Pizza", "Área"]
        )
    
    # Filter data based on time period
    if time_period != "Todos os dados":
        days_map = {
            "Último mês": 30,
            "Últimos 3 meses": 90,
            "Últimos 6 meses": 180,
            "Último ano": 365
        }
        days = days_map[time_period]
        cutoff_date = datetime.now() - timedelta(days=days)
        
        chamados_filtered = chamados_df[
            pd.to_datetime(chamados_df['DATA'], errors='coerce') >= cutoff_date
        ]
    else:
        chamados_filtered = chamados_df
    
    # Generate custom dashboard
    if selected_metrics:
        st.subheader("🎯 Seu Dashboard Personalizado")
        
        # Create dynamic layout based on number of metrics
        if len(selected_metrics) == 1:
            cols = st.columns(1)
        elif len(selected_metrics) <= 2:
            cols = st.columns(2)
        elif len(selected_metrics) <= 4:
            cols = st.columns(2)
        else:
            cols = st.columns(3)
        
        col_idx = 0
        
        for metric in selected_metrics:
            with cols[col_idx % len(cols)]:
                
                if metric == "Volume de Chamados":
                    total_chamados = len(chamados_filtered)
                    st.metric("Volume de Chamados", f"{total_chamados:,}")
                    
                    if chart_type in ["Automático", "Barras"]:
                        daily_counts = chamados_filtered.groupby(
                            pd.to_datetime(chamados_filtered['DATA'], errors='coerce').dt.date
                        ).size().reset_index()
                        daily_counts.columns = ['Data', 'Chamados']
                        
                        if len(daily_counts) > 0:
                            fig = px.bar(daily_counts.tail(30), x='Data', y='Chamados', 
                                       title="Volume Diário (Últimos 30 dias)")
                            st.plotly_chart(fig, use_container_width=True)
                
                elif metric == "Taxa de Garantia":
                    garantia_count = chamados_filtered['SERVIÇO'].str.contains('GARANTIA', na=False).sum()
                    taxa_garantia = garantia_count / len(chamados_filtered) * 100 if len(chamados_filtered) > 0 else 0
                    st.metric("Taxa de Garantia", f"{taxa_garantia:.1f}%")
                
                elif metric == "Taxa RTM":
                    rtm_count = (chamados_filtered['RTM'] == 'SIM').sum()
                    taxa_rtm = rtm_count / len(chamados_filtered) * 100 if len(chamados_filtered) > 0 else 0
                    st.metric("Taxa RTM", f"{taxa_rtm:.1f}%")
                
                elif metric == "Distribuição por Estado":
                    if 'UF' in bombas_df.columns:
                        estado_counts = bombas_df['UF'].value_counts().head(10)
                        fig = px.pie(values=estado_counts.values, names=estado_counts.index, 
                                   title="Top 10 Estados")
                        st.plotly_chart(fig, use_container_width=True)
                
                elif metric == "Top Serviços":
                    top_services = chamados_filtered['SERVIÇO'].value_counts().head(5)
                    fig = px.bar(x=top_services.values, y=top_services.index, 
                               orientation='h', title="Top 5 Tipos de Serviço")
                    st.plotly_chart(fig, use_container_width=True)
                
                elif metric == "Performance por Mês":
                    chamados_filtered['DATA'] = pd.to_datetime(chamados_filtered['DATA'], errors='coerce')
                    monthly = chamados_filtered.groupby(
                        chamados_filtered['DATA'].dt.to_period('M')
                    ).size().reset_index()
                    monthly.columns = ['Mês', 'Chamados']
                    monthly['Mês'] = monthly['Mês'].astype(str)
                    
                    if len(monthly) > 0:
                        fig = px.line(monthly, x='Mês', y='Chamados', 
                                    title="Evolução Mensal")
                        st.plotly_chart(fig, use_container_width=True)
                
                elif metric == "Status dos Chamados":
                    status_counts = chamados_filtered['STATUS'].value_counts()
                    fig = px.pie(values=status_counts.values, names=status_counts.index, 
                               title="Status dos Chamados")
                    st.plotly_chart(fig, use_container_width=True)
            
            col_idx += 1
    else:
        st.info("Selecione pelo menos uma métrica para exibir no dashboard.")