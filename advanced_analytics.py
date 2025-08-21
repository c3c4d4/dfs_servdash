"""
Advanced Analytics Module for DFS ServiceWatch
Provides predictive analytics, ML models, and advanced business intelligence features.
"""

import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple, Optional, Any
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler, LabelEncoder
import warnings
warnings.filterwarnings('ignore')

class PumpFailurePrediction:
    """Predictive model for pump failure analysis."""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_importance = None
        
    @st.cache_data(ttl=3600, show_spinner=False)
    def prepare_features(_self, df_bombas: pd.DataFrame, df_chamados: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for failure prediction model."""
        try:
            # Base features from pump data
            features = df_bombas.copy()
            
            # Age features
            if 'DT_NUM_NF' in features.columns:
                features['DT_NUM_NF'] = pd.to_datetime(features['DT_NUM_NF'], errors='coerce')
                today = pd.Timestamp.now()
                features['IDADE_BOMBA_DIAS'] = (today - features['DT_NUM_NF']).dt.days
                features['IDADE_BOMBA_ANOS'] = features['IDADE_BOMBA_DIAS'] / 365.25
            
            # Chamados-based features (aggregated by chassis)
            chamados_agg = df_chamados.groupby('CHASSI').agg({
                'SS': ['count', 'nunique'],
                'SERVIÇO': lambda x: (x.str.contains('GARANTIA', na=False)).sum(),
                'STATUS': lambda x: (x == 'ABERTO').sum(),
                'DATA': ['min', 'max']  # First and last service dates
            }).reset_index()
            
            # Flatten column names
            chamados_agg.columns = ['CHASSI', 'TOTAL_CHAMADOS', 'CHAMADOS_UNICOS', 
                                  'CHAMADOS_GARANTIA', 'CHAMADOS_ABERTOS',
                                  'PRIMEIRO_CHAMADO', 'ULTIMO_CHAMADO']
            
            # Calculate service frequency
            chamados_agg['PRIMEIRO_CHAMADO'] = pd.to_datetime(chamados_agg['PRIMEIRO_CHAMADO'], errors='coerce')
            chamados_agg['ULTIMO_CHAMADO'] = pd.to_datetime(chamados_agg['ULTIMO_CHAMADO'], errors='coerce')
            
            service_duration = (chamados_agg['ULTIMO_CHAMADO'] - chamados_agg['PRIMEIRO_CHAMADO']).dt.days
            chamados_agg['FREQUENCIA_SERVICO'] = chamados_agg['TOTAL_CHAMADOS'] / (service_duration + 1)
            
            # Merge with main features
            features = features.merge(chamados_agg, left_on='NUM_SERIAL', right_on='CHASSI', how='left')
            
            # Fill missing values
            numeric_cols = features.select_dtypes(include=[np.number]).columns
            features[numeric_cols] = features[numeric_cols].fillna(0)
            
            categorical_cols = features.select_dtypes(include=['object', 'category']).columns
            features[categorical_cols] = features[categorical_cols].fillna('UNKNOWN')
            
            # Create risk score (target variable for prediction)
            features['RISK_SCORE'] = (
                features['TOTAL_CHAMADOS'] * 0.3 +
                features['CHAMADOS_GARANTIA'] * 0.2 +
                features['CHAMADOS_ABERTOS'] * 0.4 +
                features['FREQUENCIA_SERVICO'] * 100 * 0.1
            )
            
            return features
            
        except Exception as e:
            st.error(f"Erro ao preparar features: {str(e)}")
            return pd.DataFrame()
    
    @st.cache_data(ttl=3600, show_spinner=False)
    def train_model(_self, features_df: pd.DataFrame) -> Dict[str, Any]:
        """Train failure prediction model."""
        try:
            if len(features_df) == 0:
                return {'error': 'No data available for training'}
            
            # Select features for training
            feature_cols = [
                'IDADE_BOMBA_ANOS', 'TOTAL_CHAMADOS', 'CHAMADOS_GARANTIA', 
                'CHAMADOS_ABERTOS', 'FREQUENCIA_SERVICO', 'GARANTIA'
            ]
            
            # Filter available columns
            available_cols = [col for col in feature_cols if col in features_df.columns]
            
            if len(available_cols) < 2:
                return {'error': 'Not enough features available for training'}
            
            X = features_df[available_cols].copy()
            y = features_df['RISK_SCORE'].copy()
            
            # Handle missing values
            X = X.fillna(0)
            y = y.fillna(0)
            
            # Train-test split
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Train model
            model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
            model.fit(X_train, y_train)
            
            # Predictions and metrics
            y_pred = model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            
            # Feature importance
            feature_importance = pd.DataFrame({
                'feature': available_cols,
                'importance': model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            return {
                'model': model,
                'features': available_cols,
                'mae': mae,
                'rmse': rmse,
                'feature_importance': feature_importance,
                'predictions': y_pred,
                'actual': y_test.values
            }
            
        except Exception as e:
            st.error(f"Erro ao treinar modelo: {str(e)}")
            return {'error': str(e)}
    
    def predict_failures(self, features_df: pd.DataFrame, model_results: Dict[str, Any]) -> pd.DataFrame:
        """Predict failure risk for pumps."""
        try:
            if 'error' in model_results:
                return pd.DataFrame()
            
            model = model_results['model']
            feature_cols = model_results['features']
            
            X = features_df[feature_cols].fillna(0)
            predictions = model.predict(X)
            
            # Create risk categories
            risk_df = features_df[['NUM_SERIAL', 'UF', 'CIDADE']].copy()
            risk_df['RISK_SCORE'] = predictions
            risk_df['RISK_CATEGORY'] = pd.cut(
                predictions, 
                bins=[0, 1, 3, 5, float('inf')], 
                labels=['Baixo', 'Médio', 'Alto', 'Crítico']
            )
            
            return risk_df.sort_values('RISK_SCORE', ascending=False)
            
        except Exception as e:
            st.error(f"Erro ao predizer falhas: {str(e)}")
            return pd.DataFrame()

class TimeSeriesAnalyzer:
    """Advanced time series analysis for service data."""
    
    @st.cache_data(ttl=1800, show_spinner=False)
    def prepare_time_series(_self, df_chamados: pd.DataFrame) -> pd.DataFrame:
        """Prepare time series data from chamados."""
        try:
            df = df_chamados.copy()
            df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce')
            df = df.dropna(subset=['DATA'])
            
            # Create monthly aggregations
            df['ANO_MES'] = df['DATA'].dt.to_period('M')
            
            monthly_stats = df.groupby('ANO_MES').agg({
                'SS': 'count',
                'CHASSI': 'nunique',
                'SERVIÇO': lambda x: (x.str.contains('GARANTIA', na=False)).sum(),
                'STATUS': lambda x: (x == 'ABERTO').sum(),
                'RTM': lambda x: (x == 'SIM').sum()
            }).reset_index()
            
            monthly_stats.columns = ['ANO_MES', 'TOTAL_CHAMADOS', 'BOMBAS_UNICAS', 
                                   'CHAMADOS_GARANTIA', 'CHAMADOS_ABERTOS', 'CHAMADOS_RTM']
            
            # Calculate additional metrics
            monthly_stats['TAXA_GARANTIA'] = monthly_stats['CHAMADOS_GARANTIA'] / monthly_stats['TOTAL_CHAMADOS'] * 100
            monthly_stats['TAXA_RTM'] = monthly_stats['CHAMADOS_RTM'] / monthly_stats['TOTAL_CHAMADOS'] * 100
            monthly_stats['TAXA_ABERTURA'] = monthly_stats['CHAMADOS_ABERTOS'] / monthly_stats['TOTAL_CHAMADOS'] * 100
            monthly_stats['CHAMADOS_POR_BOMBA'] = monthly_stats['TOTAL_CHAMADOS'] / monthly_stats['BOMBAS_UNICAS']
            
            # Convert period back to datetime for plotting
            monthly_stats['DATA'] = monthly_stats['ANO_MES'].dt.to_timestamp()
            
            return monthly_stats
            
        except Exception as e:
            st.error(f"Erro ao preparar série temporal: {str(e)}")
            return pd.DataFrame()
    
    def create_trend_analysis(self, time_series_df: pd.DataFrame) -> Dict[str, Any]:
        """Perform trend analysis on time series data."""
        try:
            if time_series_df.empty:
                return {}
                
            results = {}
            
            # Analyze trends for key metrics
            metrics = ['TOTAL_CHAMADOS', 'TAXA_GARANTIA', 'TAXA_RTM', 'CHAMADOS_POR_BOMBA']
            
            for metric in metrics:
                if metric in time_series_df.columns:
                    values = time_series_df[metric].values
                    
                    # Linear regression for trend
                    from sklearn.linear_model import LinearRegression
                    x = np.arange(len(values)).reshape(-1, 1)
                    model = LinearRegression().fit(x, values)
                    
                    trend_slope = model.coef_[0]
                    r_squared = model.score(x, values)
                    
                    # Categorize trend
                    if abs(trend_slope) < 0.01:
                        trend_direction = "Estável"
                    elif trend_slope > 0:
                        trend_direction = "Crescente"
                    else:
                        trend_direction = "Decrescente"
                    
                    results[metric] = {
                        'trend_slope': trend_slope,
                        'trend_direction': trend_direction,
                        'r_squared': r_squared,
                        'current_value': values[-1] if len(values) > 0 else 0,
                        'avg_value': np.mean(values),
                        'volatility': np.std(values)
                    }
            
            return results
            
        except Exception as e:
            st.error(f"Erro na análise de tendência: {str(e)}")
            return {}
    
    def detect_seasonality(self, time_series_df: pd.DataFrame, metric: str) -> Dict[str, Any]:
        """Detect seasonal patterns in the data."""
        try:
            if time_series_df.empty or metric not in time_series_df.columns:
                return {}
                
            # Extract month from date
            time_series_df['MES'] = pd.to_datetime(time_series_df['DATA']).dt.month
            
            # Monthly averages
            monthly_avg = time_series_df.groupby('MES')[metric].mean()
            
            # Calculate seasonality strength (coefficient of variation)
            seasonality_strength = monthly_avg.std() / monthly_avg.mean() if monthly_avg.mean() > 0 else 0
            
            # Find peak and trough months
            peak_month = monthly_avg.idxmax()
            trough_month = monthly_avg.idxmin()
            
            month_names = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                          7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
            
            return {
                'seasonality_strength': seasonality_strength,
                'peak_month': month_names.get(peak_month, peak_month),
                'trough_month': month_names.get(trough_month, trough_month),
                'monthly_averages': monthly_avg.to_dict(),
                'has_seasonality': seasonality_strength > 0.1
            }
            
        except Exception as e:
            st.error(f"Erro na detecção de sazonalidade: {str(e)}")
            return {}
    
    def forecast_metric(self, time_series_df: pd.DataFrame, metric: str, periods: int = 6) -> pd.DataFrame:
        """Simple forecast using linear regression."""
        try:
            if time_series_df.empty or metric not in time_series_df.columns:
                return pd.DataFrame()
                
            # Prepare data for forecasting
            df_forecast = time_series_df[['DATA', metric]].copy()
            df_forecast = df_forecast.dropna()
            
            if len(df_forecast) < 3:
                return pd.DataFrame()
            
            # Create time index
            df_forecast['TIME_INDEX'] = range(len(df_forecast))
            
            # Fit linear regression
            from sklearn.linear_model import LinearRegression
            model = LinearRegression()
            X = df_forecast[['TIME_INDEX']]
            y = df_forecast[metric]
            model.fit(X, y)
            
            # Generate future dates
            last_date = df_forecast['DATA'].max()
            future_dates = pd.date_range(
                start=last_date + pd.DateOffset(months=1),
                periods=periods,
                freq='MS'
            )
            
            # Predict future values
            future_indices = range(len(df_forecast), len(df_forecast) + periods)
            future_predictions = model.predict([[i] for i in future_indices])
            
            # Create forecast dataframe
            forecast_df = pd.DataFrame({
                'DATA': future_dates,
                'VALOR_PREVISTO': future_predictions,
                'TIPO': 'Previsão'
            })
            
            # Add historical data
            historical_df = df_forecast[['DATA', metric]].copy()
            historical_df.columns = ['DATA', 'VALOR_PREVISTO']
            historical_df['TIPO'] = 'Histórico'
            
            # Combine
            result_df = pd.concat([historical_df, forecast_df], ignore_index=True)
            result_df['METRICA'] = metric
            
            return result_df
            
        except Exception as e:
            st.error(f"Erro na previsão: {str(e)}")
            return pd.DataFrame()
    
    def create_time_series_charts(self, ts_data: pd.DataFrame) -> Dict[str, go.Figure]:
        """Create comprehensive time series visualizations."""
        charts = {}
        
        if len(ts_data) == 0:
            return charts
        
        # 1. Volume de chamados over time
        fig_volume = go.Figure()
        fig_volume.add_trace(go.Scatter(
            x=ts_data['DATA'],
            y=ts_data['TOTAL_CHAMADOS'],
            mode='lines+markers',
            name='Total de Chamados',
            line=dict(color='#1f77b4', width=3)
        ))
        
        fig_volume.update_layout(
            title='Evolução do Volume de Chamados',
            xaxis_title='Período',
            yaxis_title='Número de Chamados',
            hovermode='x unified'
        )
        charts['volume'] = fig_volume
        
        # 2. Multi-metric dashboard
        fig_multi = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Chamados vs Bombas Únicas', 'Taxa de Garantia (%)', 
                          'Taxa RTM (%)', 'Chamados por Bomba'),
            specs=[[{"secondary_y": True}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Chamados vs Bombas
        fig_multi.add_trace(
            go.Scatter(x=ts_data['DATA'], y=ts_data['TOTAL_CHAMADOS'], 
                      name='Total Chamados', line=dict(color='blue')),
            row=1, col=1
        )
        fig_multi.add_trace(
            go.Scatter(x=ts_data['DATA'], y=ts_data['BOMBAS_UNICAS'], 
                      name='Bombas Únicas', line=dict(color='red')),
            row=1, col=1, secondary_y=True
        )
        
        # Taxa de Garantia
        fig_multi.add_trace(
            go.Scatter(x=ts_data['DATA'], y=ts_data['TAXA_GARANTIA'], 
                      name='Taxa Garantia (%)', line=dict(color='green')),
            row=1, col=2
        )
        
        # Taxa RTM
        fig_multi.add_trace(
            go.Scatter(x=ts_data['DATA'], y=ts_data['TAXA_RTM'], 
                      name='Taxa RTM (%)', line=dict(color='orange')),
            row=2, col=1
        )
        
        # Chamados por Bomba
        fig_multi.add_trace(
            go.Scatter(x=ts_data['DATA'], y=ts_data['CHAMADOS_POR_BOMBA'], 
                      name='Chamados/Bomba', line=dict(color='purple')),
            row=2, col=2
        )
        
        fig_multi.update_layout(
            title_text="Dashboard de Métricas Temporais",
            showlegend=False,
            height=600
        )
        charts['dashboard'] = fig_multi
        
        # 3. Seasonal analysis (if enough data)
        if len(ts_data) >= 12:
            ts_data['MES'] = pd.to_datetime(ts_data['DATA']).dt.month
            seasonal_data = ts_data.groupby('MES').agg({
                'TOTAL_CHAMADOS': 'mean',
                'TAXA_GARANTIA': 'mean',
                'CHAMADOS_POR_BOMBA': 'mean'
            }).reset_index()
            
            months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                     'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
            seasonal_data['MES_NOME'] = seasonal_data['MES'].map(lambda x: months[x-1])
            
            fig_seasonal = go.Figure()
            fig_seasonal.add_trace(go.Bar(
                x=seasonal_data['MES_NOME'],
                y=seasonal_data['TOTAL_CHAMADOS'],
                name='Média de Chamados',
                marker_color='lightblue'
            ))
            
            fig_seasonal.update_layout(
                title='Análise Sazonal - Média de Chamados por Mês',
                xaxis_title='Mês',
                yaxis_title='Média de Chamados'
            )
            charts['seasonal'] = fig_seasonal
        
        return charts

class CorrelationAnalyzer:
    """Advanced correlation and relationship analysis."""
    
    @st.cache_data(ttl=1800, show_spinner=False)
    def calculate_correlations(_self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate correlation matrix for numeric variables."""
        try:
            # Select only numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            
            if len(numeric_cols) < 2:
                return pd.DataFrame()
            
            correlation_matrix = df[numeric_cols].corr()
            return correlation_matrix
            
        except Exception as e:
            st.error(f"Erro ao calcular correlações: {str(e)}")
            return pd.DataFrame()
    
    def create_correlation_heatmap(self, corr_matrix: pd.DataFrame) -> go.Figure:
        """Create interactive correlation heatmap."""
        if len(corr_matrix) == 0:
            return go.Figure()
        
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.columns,
            colorscale='RdBu_r',
            zmid=0,
            text=np.round(corr_matrix.values, 2),
            texttemplate="%{text}",
            textfont={"size": 10},
            hovertemplate='<b>%{x} vs %{y}</b><br>Correlação: %{z:.3f}<extra></extra>'
        ))
        
        fig.update_layout(
            title='Matriz de Correlação - Variáveis Numéricas',
            xaxis_title='Variáveis',
            yaxis_title='Variáveis',
            height=600,
            width=600
        )
        
        return fig
    
    def find_strong_correlations(self, corr_matrix: pd.DataFrame, threshold: float = 0.5) -> pd.DataFrame:
        """Find strong correlations above threshold."""
        if len(corr_matrix) == 0:
            return pd.DataFrame()
        
        # Create list of correlations
        correlations = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                corr_value = corr_matrix.iloc[i, j]
                if abs(corr_value) >= threshold:
                    correlations.append({
                        'Variável 1': corr_matrix.columns[i],
                        'Variável 2': corr_matrix.columns[j],
                        'Correlação': corr_value,
                        'Força': 'Forte' if abs(corr_value) >= 0.7 else 'Moderada'
                    })
        
        return pd.DataFrame(correlations).sort_values('Correlação', key=abs, ascending=False)

class MaintenanceOptimizer:
    """Optimization algorithms for maintenance scheduling."""
    
    @st.cache_data(ttl=1800, show_spinner=False)
    def analyze_maintenance_patterns(_self, df_chamados: pd.DataFrame) -> Dict[str, Any]:
        """Analyze maintenance patterns and suggest optimizations."""
        try:
            df = df_chamados.copy()
            df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce')
            
            # Analyze by service type
            service_analysis = df.groupby('SERVIÇO').agg({
                'SS': 'count',
                'CHASSI': 'nunique',
                'DATA': ['min', 'max']
            }).reset_index()
            
            service_analysis.columns = ['SERVIÇO', 'TOTAL_CHAMADOS', 'BOMBAS_AFETADAS', 'PRIMEIRO', 'ULTIMO']
            service_analysis['FREQUENCIA_MEDIA'] = service_analysis['TOTAL_CHAMADOS'] / service_analysis['BOMBAS_AFETADAS']
            
            # Identify preventive vs reactive patterns
            preventive_services = df[df['SERVIÇO'].str.contains('PREVENTIVA|INSPEÇÃO|MANUTENÇÃO PROGRAMADA', na=False, case=False)]
            reactive_services = df[df['SERVIÇO'].str.contains('CORRETIVA|EMERGÊNCIA|FALHA', na=False, case=False)]
            
            maintenance_summary = {
                'total_services': len(df),
                'preventive_count': len(preventive_services),
                'reactive_count': len(reactive_services),
                'preventive_ratio': len(preventive_services) / len(df) * 100 if len(df) > 0 else 0,
                'service_analysis': service_analysis.sort_values('FREQUENCIA_MEDIA', ascending=False)
            }
            
            return maintenance_summary
            
        except Exception as e:
            st.error(f"Erro na análise de manutenção: {str(e)}")
            return {}
    
    def recommend_maintenance_schedule(self, analysis: Dict[str, Any]) -> pd.DataFrame:
        """Generate maintenance schedule recommendations."""
        try:
            if not analysis or 'service_analysis' not in analysis:
                return pd.DataFrame()
            
            service_df = analysis['service_analysis']
            
            # Create recommendations based on frequency and patterns
            recommendations = []
            for _, row in service_df.iterrows():
                service = row['SERVIÇO']
                freq = row['FREQUENCIA_MEDIA']
                total_calls = row['TOTAL_CHAMADOS']
                pumps_affected = row['BOMBAS_AFETADAS']
                
                # Calculate impact score
                impact_score = (freq * total_calls) / pumps_affected if pumps_affected > 0 else 0
                
                # Determine priority and recommendations
                if impact_score > 10:
                    priority = 'Crítica'
                    suggestion = 'Implementar manutenção preventiva imediatamente'
                    interval_suggestion = 'Mensal'
                elif impact_score > 5:
                    priority = 'Alta'
                    suggestion = 'Aumentar frequência de manutenção preventiva'
                    interval_suggestion = 'Bimestral'
                elif impact_score > 2:
                    priority = 'Média'
                    suggestion = 'Monitorar e ajustar cronograma conforme necessário'
                    interval_suggestion = 'Trimestral'
                else:
                    priority = 'Baixa'
                    suggestion = 'Manter cronograma atual de manutenção'
                    interval_suggestion = 'Semestral'
                
                # Cost-benefit analysis
                if 'preventiva' in service.lower() or 'inspeção' in service.lower():
                    cost_benefit = 'Positivo - Preventiva'
                elif 'corretiva' in service.lower() or 'emergência' in service.lower():
                    cost_benefit = 'Negativo - Reativa'
                else:
                    cost_benefit = 'Neutro'
                
                recommendations.append({
                    'Serviço': service,
                    'Frequência Atual': freq,
                    'Total Chamados': total_calls,
                    'Bombas Afetadas': pumps_affected,
                    'Score de Impacto': impact_score,
                    'Prioridade': priority,
                    'Intervalo Sugerido': interval_suggestion,
                    'Custo-Benefício': cost_benefit,
                    'Recomendação': suggestion
                })
            
            return pd.DataFrame(recommendations).sort_values('Score de Impacto', ascending=False)
            
        except Exception as e:
            st.error(f"Erro ao gerar recomendações: {str(e)}")
            return pd.DataFrame()
    
    def calculate_maintenance_roi(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate ROI estimates for maintenance optimization."""
        try:
            if not analysis:
                return {}
            
            total_services = analysis['total_services']
            preventive_count = analysis['preventive_count']
            reactive_count = analysis['reactive_count']
            
            # Estimated costs (these would be configurable in a real system)
            preventive_cost_per_service = 500  # R$
            reactive_cost_per_service = 1500   # R$ (typically 3x preventive)
            
            # Current costs
            current_preventive_cost = preventive_count * preventive_cost_per_service
            current_reactive_cost = reactive_count * reactive_cost_per_service
            current_total_cost = current_preventive_cost + current_reactive_cost
            
            # Optimized scenario (increase preventive by 30%, reduce reactive by 20%)
            optimized_preventive_count = preventive_count * 1.3
            optimized_reactive_count = reactive_count * 0.8
            
            optimized_preventive_cost = optimized_preventive_count * preventive_cost_per_service
            optimized_reactive_cost = optimized_reactive_count * reactive_cost_per_service
            optimized_total_cost = optimized_preventive_cost + optimized_reactive_cost
            
            # ROI calculation
            cost_savings = current_total_cost - optimized_total_cost
            roi_percentage = (cost_savings / current_total_cost * 100) if current_total_cost > 0 else 0
            
            return {
                'current_total_cost': current_total_cost,
                'current_preventive_cost': current_preventive_cost,
                'current_reactive_cost': current_reactive_cost,
                'optimized_total_cost': optimized_total_cost,
                'optimized_preventive_cost': optimized_preventive_cost,
                'optimized_reactive_cost': optimized_reactive_cost,
                'annual_savings': cost_savings,
                'roi_percentage': roi_percentage,
                'payback_period_months': 12 if roi_percentage > 0 else float('inf')
            }
            
        except Exception as e:
            st.error(f"Erro no cálculo de ROI: {str(e)}")
            return {}
    
    def create_maintenance_calendar(self, recommendations: pd.DataFrame) -> pd.DataFrame:
        """Create a maintenance calendar based on recommendations."""
        try:
            if len(recommendations) == 0:
                return pd.DataFrame()
            
            # Filter high and critical priority items
            priority_items = recommendations[
                recommendations['Prioridade'].isin(['Alta', 'Crítica'])
            ]
            
            calendar_items = []
            base_date = datetime.now()
            
            for _, row in priority_items.iterrows():
                service = row['Serviço']
                interval = row['Intervalo Sugerido']
                priority = row['Prioridade']
                
                # Calculate next maintenance dates based on interval
                if interval == 'Mensal':
                    intervals = [1, 2, 3, 4, 5, 6]
                elif interval == 'Bimestral':
                    intervals = [2, 4, 6]
                elif interval == 'Trimestral':
                    intervals = [3, 6]
                else:  # Semestral
                    intervals = [6]
                
                for months_ahead in intervals:
                    next_date = base_date + timedelta(days=months_ahead * 30)
                    
                    calendar_items.append({
                        'Data Planejada': next_date.strftime('%Y-%m-%d'),
                        'Serviço': service,
                        'Prioridade': priority,
                        'Tipo': 'Preventiva',
                        'Status': 'Planejado'
                    })
            
            return pd.DataFrame(calendar_items).sort_values('Data Planejada')
            
        except Exception as e:
            st.error(f"Erro ao criar calendário: {str(e)}")
            return pd.DataFrame()

class PerformanceForecaster:
    """Advanced performance forecasting and predictive analytics."""
    
    @st.cache_data(ttl=1800, show_spinner=False)
    def prepare_forecast_data(_self, chamados_df: pd.DataFrame, bombas_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Prepare comprehensive data for performance forecasting."""
        try:
            # Time series data
            chamados_df['DATA'] = pd.to_datetime(chamados_df['DATA'], errors='coerce')
            chamados_clean = chamados_df.dropna(subset=['DATA'])
            
            # Weekly aggregations for more granular forecasting
            chamados_clean['SEMANA'] = chamados_clean['DATA'].dt.to_period('W')
            
            weekly_data = chamados_clean.groupby('SEMANA').agg({
                'SS': 'count',
                'CHASSI': 'nunique',
                'SERVIÇO': lambda x: (x.str.contains('GARANTIA', na=False)).sum(),
                'STATUS': lambda x: (x == 'ABERTO').sum(),
                'RTM': lambda x: (x == 'SIM').sum()
            }).reset_index()
            
            weekly_data.columns = ['SEMANA', 'TOTAL_CHAMADOS', 'BOMBAS_UNICAS', 
                                 'CHAMADOS_GARANTIA', 'CHAMADOS_ABERTOS', 'CHAMADOS_RTM']
            
            # Convert back to datetime
            weekly_data['DATA'] = weekly_data['SEMANA'].dt.to_timestamp()
            
            # Calculate performance metrics
            weekly_data['TAXA_GARANTIA'] = weekly_data['CHAMADOS_GARANTIA'] / weekly_data['TOTAL_CHAMADOS'] * 100
            weekly_data['TAXA_RTM'] = weekly_data['CHAMADOS_RTM'] / weekly_data['TOTAL_CHAMADOS'] * 100
            weekly_data['TAXA_ABERTURA'] = weekly_data['CHAMADOS_ABERTOS'] / weekly_data['TOTAL_CHAMADOS'] * 100
            weekly_data['CHAMADOS_POR_BOMBA'] = weekly_data['TOTAL_CHAMADOS'] / weekly_data['BOMBAS_UNICAS']
            
            # Fleet performance data
            fleet_performance = bombas_df.groupby('UF').agg({
                'NUM_SERIAL': 'count',
                'RTM': lambda x: (x == 'SIM').sum(),
                'EM_GARANTIA': lambda x: (x == 'SIM').sum()
            }).reset_index()
            
            fleet_performance.columns = ['UF', 'TOTAL_BOMBAS', 'BOMBAS_RTM', 'BOMBAS_GARANTIA']
            fleet_performance['TAXA_RTM_FROTA'] = fleet_performance['BOMBAS_RTM'] / fleet_performance['TOTAL_BOMBAS'] * 100
            fleet_performance['TAXA_GARANTIA_FROTA'] = fleet_performance['BOMBAS_GARANTIA'] / fleet_performance['TOTAL_BOMBAS'] * 100
            
            return {
                'weekly_performance': weekly_data,
                'fleet_performance': fleet_performance
            }
            
        except Exception as e:
            st.error(f"Erro ao preparar dados para previsão: {str(e)}")
            return {}
    
    def forecast_performance_metrics(self, weekly_data: pd.DataFrame, periods: int = 12) -> pd.DataFrame:
        """Forecast key performance metrics using advanced time series methods."""
        try:
            if len(weekly_data) < 10:
                return pd.DataFrame()
            
            forecasts = []
            metrics = ['TOTAL_CHAMADOS', 'TAXA_GARANTIA', 'TAXA_RTM', 'CHAMADOS_POR_BOMBA']
            
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.preprocessing import StandardScaler
            
            for metric in metrics:
                if metric in weekly_data.columns:
                    # Prepare features (time-based features + lags)
                    df_metric = weekly_data[['DATA', metric]].copy().dropna()
                    df_metric = df_metric.sort_values('DATA')
                    
                    # Create time-based features
                    df_metric['WEEK_OF_YEAR'] = pd.to_datetime(df_metric['DATA']).dt.isocalendar().week
                    df_metric['MONTH'] = pd.to_datetime(df_metric['DATA']).dt.month
                    df_metric['QUARTER'] = pd.to_datetime(df_metric['DATA']).dt.quarter
                    df_metric['TIME_INDEX'] = range(len(df_metric))
                    
                    # Create lag features
                    for lag in [1, 2, 4]:
                        df_metric[f'{metric}_LAG_{lag}'] = df_metric[metric].shift(lag)
                    
                    # Rolling statistics
                    df_metric[f'{metric}_ROLL_MEAN'] = df_metric[metric].rolling(window=4).mean()
                    df_metric[f'{metric}_ROLL_STD'] = df_metric[metric].rolling(window=4).std()
                    
                    # Drop NaN rows
                    df_metric = df_metric.dropna()
                    
                    if len(df_metric) < 5:
                        continue
                    
                    # Prepare features and target
                    feature_cols = [col for col in df_metric.columns if col not in ['DATA', metric]]
                    X = df_metric[feature_cols]
                    y = df_metric[metric]
                    
                    # Train model
                    model = RandomForestRegressor(n_estimators=100, random_state=42)
                    model.fit(X, y)
                    
                    # Generate forecast
                    last_date = df_metric['DATA'].max()
                    future_dates = pd.date_range(
                        start=last_date + pd.Timedelta(weeks=1),
                        periods=periods,
                        freq='W'
                    )
                    
                    # Predict future values
                    future_predictions = []
                    for i, future_date in enumerate(future_dates):
                        # Create features for future date
                        future_features = {
                            'WEEK_OF_YEAR': future_date.isocalendar().week,
                            'MONTH': future_date.month,
                            'QUARTER': future_date.quarter,
                            'TIME_INDEX': len(df_metric) + i
                        }
                        
                        # Use last known values for lags and rolling stats
                        for lag in [1, 2, 4]:
                            if i == 0:
                                future_features[f'{metric}_LAG_{lag}'] = y.iloc[-lag] if lag < len(y) else y.iloc[-1]
                            else:
                                lag_idx = max(0, i - lag)
                                if lag_idx < len(future_predictions):
                                    future_features[f'{metric}_LAG_{lag}'] = future_predictions[lag_idx]
                                else:
                                    future_features[f'{metric}_LAG_{lag}'] = y.iloc[-1]
                        
                        future_features[f'{metric}_ROLL_MEAN'] = y.rolling(window=4).mean().iloc[-1]
                        future_features[f'{metric}_ROLL_STD'] = y.rolling(window=4).std().iloc[-1]
                        
                        # Create feature vector
                        feature_vector = pd.DataFrame([future_features])[feature_cols]
                        
                        # Predict
                        prediction = model.predict(feature_vector)[0]
                        future_predictions.append(prediction)
                    
                    # Create forecast dataframe
                    for i, (date, pred) in enumerate(zip(future_dates, future_predictions)):
                        forecasts.append({
                            'DATA': date,
                            'METRICA': metric,
                            'VALOR_PREVISTO': pred,
                            'TIPO': 'Previsão',
                            'CONFIDENCE_LOWER': pred * 0.9,
                            'CONFIDENCE_UPPER': pred * 1.1
                        })
            
            return pd.DataFrame(forecasts)
            
        except Exception as e:
            st.error(f"Erro na previsão de performance: {str(e)}")
            return pd.DataFrame()
    
    def create_performance_dashboard(self, weekly_data: pd.DataFrame, forecasts: pd.DataFrame) -> Dict[str, go.Figure]:
        """Create comprehensive performance forecasting visualizations."""
        charts = {}
        
        if len(weekly_data) == 0:
            return charts
        
        metrics_labels = {
            'TOTAL_CHAMADOS': 'Total de Chamados',
            'TAXA_GARANTIA': 'Taxa de Garantia (%)',
            'TAXA_RTM': 'Taxa RTM (%)',
            'CHAMADOS_POR_BOMBA': 'Chamados por Bomba'
        }
        
        # Create forecasting charts for each metric
        for metric, label in metrics_labels.items():
            if metric in weekly_data.columns:
                fig = go.Figure()
                
                # Historical data
                fig.add_trace(go.Scatter(
                    x=weekly_data['DATA'],
                    y=weekly_data[metric],
                    mode='lines+markers',
                    name='Histórico',
                    line=dict(color='#1f77b4', width=2),
                    marker=dict(size=4)
                ))
                
                # Forecast data
                if len(forecasts) > 0:
                    forecast_metric = forecasts[forecasts['METRICA'] == metric]
                    if len(forecast_metric) > 0:
                        fig.add_trace(go.Scatter(
                            x=forecast_metric['DATA'],
                            y=forecast_metric['VALOR_PREVISTO'],
                            mode='lines+markers',
                            name='Previsão',
                            line=dict(color='#ff7f0e', width=3, dash='dash'),
                            marker=dict(size=6)
                        ))
                        
                        # Confidence intervals
                        fig.add_trace(go.Scatter(
                            x=forecast_metric['DATA'],
                            y=forecast_metric['CONFIDENCE_UPPER'],
                            fill=None,
                            mode='lines',
                            line_color='rgba(255,127,14,0)',
                            showlegend=False
                        ))
                        
                        fig.add_trace(go.Scatter(
                            x=forecast_metric['DATA'],
                            y=forecast_metric['CONFIDENCE_LOWER'],
                            fill='tonexty',
                            mode='lines',
                            line_color='rgba(255,127,14,0)',
                            name='Intervalo de Confiança',
                            fillcolor='rgba(255,127,14,0.2)'
                        ))
                
                fig.update_layout(
                    title=f'Previsão de Performance - {label}',
                    xaxis_title='Data',
                    yaxis_title=label,
                    hovermode='x unified',
                    height=500
                )
                
                charts[metric] = fig
        
        return charts
    
    def performance_insights(self, weekly_data: pd.DataFrame, forecasts: pd.DataFrame) -> Dict[str, Any]:
        """Generate performance insights and recommendations."""
        try:
            insights = {}
            
            if len(weekly_data) == 0:
                return insights
            
            # Trend analysis
            recent_weeks = weekly_data.tail(8)  # Last 8 weeks
            
            for metric in ['TOTAL_CHAMADOS', 'TAXA_GARANTIA', 'TAXA_RTM', 'CHAMADOS_POR_BOMBA']:
                if metric in recent_weeks.columns:
                    values = recent_weeks[metric].values
                    if len(values) >= 2:
                        trend = 'Crescente' if values[-1] > values[0] else 'Decrescente'
                        pct_change = ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0
                        
                        insights[metric] = {
                            'trend': trend,
                            'pct_change': pct_change,
                            'current_value': values[-1],
                            'avg_last_8_weeks': np.mean(values),
                            'volatility': np.std(values)
                        }
            
            # Forecast insights
            if len(forecasts) > 0:
                forecast_insights = {}
                for metric in forecasts['METRICA'].unique():
                    metric_forecasts = forecasts[forecasts['METRICA'] == metric]
                    
                    if len(metric_forecasts) > 0:
                        forecast_insights[metric] = {
                            'forecast_avg': metric_forecasts['VALOR_PREVISTO'].mean(),
                            'forecast_trend': 'Crescente' if metric_forecasts['VALOR_PREVISTO'].iloc[-1] > metric_forecasts['VALOR_PREVISTO'].iloc[0] else 'Decrescente',
                            'forecast_range': [metric_forecasts['VALOR_PREVISTO'].min(), metric_forecasts['VALOR_PREVISTO'].max()]
                        }
                
                insights['forecasts'] = forecast_insights
            
            return insights
            
        except Exception as e:
            st.error(f"Erro ao gerar insights: {str(e)}")
            return {}

# Global instances
failure_predictor = PumpFailurePrediction()
time_series_analyzer = TimeSeriesAnalyzer()
correlation_analyzer = CorrelationAnalyzer()
maintenance_optimizer = MaintenanceOptimizer()
performance_forecaster = PerformanceForecaster()