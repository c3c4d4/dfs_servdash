"""
Performance Monitor for DFS ServiceWatch

This module provides performance monitoring and optimization tracking
for the DFS ServiceWatch application.
"""

import time
import psutil
import pandas as pd
import streamlit as st
from typing import Dict, Any, Callable
from functools import wraps
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Monitor and track performance metrics."""
    
    def __init__(self):
        self.metrics = {}
        self.start_time = None
    
    def start_timer(self, operation_name: str):
        """Start timing an operation."""
        self.start_time = time.time()
        logger.info(f"Starting operation: {operation_name}")
    
    def end_timer(self, operation_name: str) -> float:
        """End timing an operation and return duration."""
        if self.start_time is None:
            return 0.0
        
        duration = time.time() - self.start_time
        self.metrics[operation_name] = duration
        logger.info(f"Operation {operation_name} completed in {duration:.2f}s")
        return duration
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage."""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size in MB
            'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size in MB
            'percent': process.memory_percent()
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        return {
            'cpu_count': psutil.cpu_count(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
            'memory_available_gb': psutil.virtual_memory().available / 1024 / 1024 / 1024,
            'memory_percent': psutil.virtual_memory().percent
        }
    
    def display_metrics(self):
        """Display performance metrics in Streamlit."""
        st.sidebar.header("📊 Performance Metrics")
        
        # Operation timings
        if self.metrics:
            st.sidebar.subheader("Operation Timings")
            for operation, duration in self.metrics.items():
                st.sidebar.metric(operation, f"{duration:.2f}s")
        
        # Memory usage
        memory_usage = self.get_memory_usage()
        st.sidebar.subheader("Memory Usage")
        st.sidebar.metric("RSS", f"{memory_usage['rss_mb']:.1f} MB")
        st.sidebar.metric("VMS", f"{memory_usage['vms_mb']:.1f} MB")
        st.sidebar.metric("Percent", f"{memory_usage['percent']:.1f}%")
        
        # System info
        system_info = self.get_system_info()
        st.sidebar.subheader("System Info")
        st.sidebar.metric("CPU Usage", f"{system_info['cpu_percent']:.1f}%")
        st.sidebar.metric("Memory Available", f"{system_info['memory_available_gb']:.1f} GB")

def monitor_performance(operation_name: str = None):
    """Decorator to monitor function performance."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            
            # Get initial memory
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024
            
            # Time the operation
            start_time = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Get final memory
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_delta = final_memory - initial_memory
            
            # Log performance
            logger.info(f"{name}: {duration:.2f}s, Memory: {memory_delta:+.1f}MB")
            
            return result
        return wrapper
    return decorator

@st.cache_data(ttl=300, show_spinner=False)
def get_dataframe_info(df: pd.DataFrame) -> Dict[str, Any]:
    """Get comprehensive information about a DataFrame."""
    return {
        'shape': df.shape,
        'memory_usage_mb': df.memory_usage(deep=True).sum() / 1024 / 1024,
        'dtypes': df.dtypes.to_dict(),
        'null_counts': df.isnull().sum().to_dict(),
        'unique_counts': {col: df[col].nunique() for col in df.columns},
        'sample_values': {col: df[col].dropna().head(3).tolist() for col in df.columns}
    }

def display_dataframe_info(df: pd.DataFrame, title: str = "DataFrame Info"):
    """Display DataFrame information in Streamlit."""
    st.subheader(title)
    
    info = get_dataframe_info(df)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Shape", f"{info['shape'][0]:,} rows × {info['shape'][1]} cols")
        st.metric("Memory Usage", f"{info['memory_usage_mb']:.1f} MB")
    
    with col2:
        st.metric("Null Values", sum(info['null_counts'].values()))
        st.metric("Total Unique Values", sum(info['unique_counts'].values()))
    
    # Show data types
    st.write("**Data Types:**")
    dtype_df = pd.DataFrame(list(info['dtypes'].items()), columns=['Column', 'Type'])
    st.dataframe(dtype_df, use_container_width=True, hide_index=True)

def optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply optimizations to DataFrame."""
    df_opt = df.copy()
    
    # Optimize dtypes
    for col in df_opt.columns:
        if df_opt[col].dtype == 'object':
            # Try to convert to category if low cardinality
            if df_opt[col].nunique() / len(df_opt) < 0.5:
                df_opt[col] = df_opt[col].astype('category')
        
        # Optimize numeric columns
        elif df_opt[col].dtype in ['int64', 'float64']:
            if df_opt[col].dtype == 'int64':
                # Downcast integers
                df_opt[col] = pd.to_numeric(df_opt[col], downcast='integer')
            else:
                # Downcast floats
                df_opt[col] = pd.to_numeric(df_opt[col], downcast='float')
    
    return df_opt

def compare_performance(before_df: pd.DataFrame, after_df: pd.DataFrame, operation_name: str):
    """Compare performance before and after optimization."""
    before_info = get_dataframe_info(before_df)
    after_info = get_dataframe_info(after_df)
    
    st.subheader(f"Performance Comparison: {operation_name}")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Memory Reduction", 
                 f"{before_info['memory_usage_mb'] - after_info['memory_usage_mb']:.1f} MB",
                 f"{((before_info['memory_usage_mb'] - after_info['memory_usage_mb']) / before_info['memory_usage_mb'] * 100):.1f}%")
    
    with col2:
        st.metric("Rows", f"{before_info['shape'][0]:,}", f"{after_info['shape'][0]:,}")
    
    with col3:
        st.metric("Columns", f"{before_info['shape'][1]}", f"{after_info['shape'][1]}")

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

def show_performance_dashboard():
    """Show comprehensive performance dashboard."""
    st.header("🚀 Performance Dashboard")
    
    # System overview
    st.subheader("System Overview")
    system_info = performance_monitor.get_system_info()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("CPU Cores", system_info['cpu_count'])
    col2.metric("CPU Usage", f"{system_info['cpu_percent']:.1f}%")
    col3.metric("Total Memory", f"{system_info['memory_total_gb']:.1f} GB")
    col4.metric("Available Memory", f"{system_info['memory_available_gb']:.1f} GB")
    
    # Memory usage chart
    st.subheader("Memory Usage")
    memory_usage = performance_monitor.get_memory_usage()
    
    import plotly.graph_objects as go
    fig = go.Figure(data=[
        go.Bar(name='Memory Usage', x=['RSS', 'VMS'], y=[memory_usage['rss_mb'], memory_usage['vms_mb']])
    ])
    fig.update_layout(title="Memory Usage (MB)", height=300)
    st.plotly_chart(fig, use_container_width=True)
    
    # Performance tips
    st.subheader("💡 Performance Tips")
    st.markdown("""
    - **Use caching**: Functions decorated with `@st.cache_data` are cached
    - **Optimize data types**: Use appropriate dtypes (category for strings, downcast numbers)
    - **Vectorize operations**: Use pandas vectorized operations instead of loops
    - **Limit data**: Only load necessary columns and rows
    - **Use efficient filters**: Pre-compute filter options when possible
    """)

if __name__ == "__main__":
    # Example usage
    monitor = PerformanceMonitor()
    monitor.start_timer("test_operation")
    time.sleep(1)  # Simulate work
    monitor.end_timer("test_operation")
    
    print("Performance monitoring ready!") 