"""
🚌 Entur Punctuality Insights Dashboard
Advanced analytics for Norwegian public transport service quality and performance optimization.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import warnings
from pathlib import Path
warnings.filterwarnings('ignore')

# Configuration
st.set_page_config(
    page_title="🚌 Entur Punctuality Insights",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2E86AB;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 3px solid #A23B72;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .insight-box {
        background: #f8f9fa;
        padding: 1rem;
        border-left: 4px solid #2E86AB;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #2E86AB 0%, #A23B72 100%);
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Load processed punctuality data"""
    try:
        # Try multiple path configurations for local and Streamlit Cloud environments
        base_paths = [
            Path(__file__).parent.parent.parent,  # Local development 
            Path("."),  # Streamlit Cloud root
            Path(__file__).resolve().parents[2],  # Alternative path
        ]
        
        for base_path in base_paths:
            data_path = base_path / "data" / "processed" / "punctuality_insights_processed.csv"
            if data_path.exists():
                df = pd.read_csv(data_path)
                df['date'] = pd.to_datetime(df['date'])
                st.success(f"✅ Data loaded from: {data_path}")
                return df
        
        # If no data file found, show error
        st.error("❌ Data file not found. Please run the data processing pipeline first.")
        st.info("Run: `python -m src.analysis.prepare` from the project root")
        return None
        
    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")
        st.info("💡 Please ensure data processing is complete: python -m src.analysis.prepare")
        return None

def create_performance_overview(df):
    """Create overall performance metrics"""
    current_data = df[df['date'] >= '2024-01-01']
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_punctuality = df['punctuality_rate_mean'].mean()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{avg_punctuality:.1f}%</div>
            <div class="metric-label">Overall Punctuality</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_trips = df['scheduled_trips_total'].sum()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_trips:,}</div>
            <div class="metric-label">Total Trips Tracked</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        best_operator = df.groupby('operator')['punctuality_rate_mean'].mean().idxmax()
        best_score = df.groupby('operator')['punctuality_rate_mean'].mean().max()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{best_operator}</div>
            <div class="metric-label">Best Operator ({best_score:.1f}%)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        operators_count = df['operator'].nunique()
        regions_count = df['region'].nunique()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{operators_count}/{regions_count}</div>
            <div class="metric-label">Operators/Regions</div>
        </div>
        """, unsafe_allow_html=True)

def create_punctuality_trends(df):
    """Create punctuality trends over time"""
    st.subheader("📈 Punctuality Trends Over Time")
    
    # Monthly trends by operator
    fig = px.line(df, x='date', y='punctuality_rate_mean', 
                  color='operator', facet_col='region',
                  title="Monthly Punctuality Rates by Operator and Region",
                  labels={'punctuality_rate_mean': 'Punctuality Rate (%)',
                          'date': 'Date'})
    
    fig.update_layout(height=400, showlegend=True)
    fig.update_traces(line=dict(width=3))
    st.plotly_chart(fig, use_container_width=True)
    
    # Smoothed trends
    st.subheader("🎯 Smoothed Punctuality Trends (3-Month Average)")
    
    fig2 = px.line(df.dropna(subset=['punctuality_trend']), 
                   x='date', y='punctuality_trend',
                   color='operator', facet_col='region',
                   title="Smoothed Punctuality Trends (3-Month Rolling Average)",
                   labels={'punctuality_trend': 'Smoothed Punctuality Rate (%)',
                           'date': 'Date'})
    
    fig2.update_layout(height=400, showlegend=True)
    fig2.update_traces(line=dict(width=3))
    st.plotly_chart(fig2, use_container_width=True)

def create_operator_comparison(df):
    """Create operator performance comparison"""
    st.subheader("🚌 Operator Performance Comparison")
    
    # Average performance by operator
    operator_performance = df.groupby('operator').agg({
        'punctuality_rate_mean': ['mean', 'std'],
        'scheduled_trips_total': 'sum',
        'date': 'count'
    }).round(2)
    
    operator_performance.columns = ['Avg_Punctuality', 'Punctuality_StdDev', 'Total_Trips', 'Months_Active']
    operator_performance = operator_performance.sort_values('Avg_Punctuality', ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.bar(operator_performance.reset_index(), 
                     x='operator', y='Avg_Punctuality',
                     title="Average Punctuality by Operator",
                     color='Avg_Punctuality',
                     color_continuous_scale='RdYlGn',
                     text='Avg_Punctuality')
        
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.scatter(operator_performance.reset_index(),
                         x='Total_Trips', y='Avg_Punctuality',
                         size='Months_Active', color='operator',
                         title="Punctuality vs. Trip Volume",
                         labels={'Total_Trips': 'Total Trips', 
                                'Avg_Punctuality': 'Average Punctuality (%)'})
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

def create_seasonal_analysis(df):
    """Create seasonal performance analysis"""
    st.subheader("🌸 Seasonal Performance Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Monthly patterns
        monthly_avg = df.groupby('month')['punctuality_rate_mean'].mean().reset_index()
        
        fig = px.line(monthly_avg, x='month', y='punctuality_rate_mean',
                      title="Average Punctuality by Month",
                      markers=True,
                      labels={'month': 'Month', 'punctuality_rate_mean': 'Punctuality Rate (%)'})
        
        fig.update_traces(line=dict(width=4, color='#2E86AB'), 
                         marker=dict(size=8, color='#A23B72'))
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Seasonal patterns
        seasonal_avg = df.groupby('season')['punctuality_rate_mean'].mean().reset_index()
        
        fig = px.bar(seasonal_avg, x='season', y='punctuality_rate_mean',
                     title="Average Punctuality by Season",
                     color='punctuality_rate_mean',
                     color_continuous_scale='RdYlGn',
                     text='punctuality_rate_mean')
        
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

def create_regional_analysis(df):
    """Create regional performance analysis"""
    st.subheader("🏙️ Regional Performance Analysis")
    
    # Regional comparison
    regional_performance = df.groupby('region').agg({
        'punctuality_rate_mean': ['mean', 'std'],
        'scheduled_trips_total': 'sum'
    }).round(2)
    
    regional_performance.columns = ['Avg_Punctuality', 'Punctuality_StdDev', 'Total_Trips']
    regional_performance = regional_performance.sort_values('Avg_Punctuality', ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.bar(regional_performance.reset_index(),
                     x='region', y='Avg_Punctuality',
                     title="Average Punctuality by Region",
                     color='Avg_Punctuality',
                     color_continuous_scale='RdYlGn',
                     text='Avg_Punctuality')
        
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.box(df, x='region', y='punctuality_rate_mean',
                     title="Punctuality Distribution by Region",
                     color='region')
        
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

def create_insights_summary(df):
    """Create insights and recommendations"""
    st.subheader("💡 Key Insights & Recommendations")
    
    # Calculate insights
    best_operator = df.groupby('operator')['punctuality_rate_mean'].mean().idxmax()
    worst_operator = df.groupby('operator')['punctuality_rate_mean'].mean().idxmin()
    
    best_region = df.groupby('region')['punctuality_rate_mean'].mean().idxmax()
    worst_region = df.groupby('region')['punctuality_rate_mean'].mean().idxmin()
    
    best_month = df.groupby('month')['punctuality_rate_mean'].mean().idxmax()
    worst_month = df.groupby('month')['punctuality_rate_mean'].mean().idxmin()
    
    recent_trend = df[df['date'] >= '2024-01-01']['punctuality_rate_mean'].mean()
    historical_avg = df[df['date'] < '2024-01-01']['punctuality_rate_mean'].mean()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="insight-box">
        <h4>🏆 Performance Leaders</h4>
        <ul>
            <li><strong>Best Operator:</strong> {best_operator} - Most consistent punctuality</li>
            <li><strong>Best Region:</strong> {best_region} - Highest regional performance</li>
            <li><strong>Peak Month:</strong> Month {best_month} - Optimal conditions</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="insight-box">
        <h4>⚠️ Improvement Areas</h4>
        <ul>
            <li><strong>Focus Operator:</strong> {worst_operator} - Needs improvement strategies</li>
            <li><strong>Challenge Region:</strong> {worst_region} - Infrastructure investment needed</li>
            <li><strong>Difficult Month:</strong> Month {worst_month} - Weather/seasonal impacts</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Trend analysis
    trend_direction = "improving" if recent_trend > historical_avg else "declining"
    trend_change = abs(recent_trend - historical_avg)
    
    st.markdown(f"""
    <div class="insight-box">
    <h4>📊 Recent Trends (2024)</h4>
    <p>Punctuality is currently <strong>{trend_direction}</strong> compared to historical averages, 
    with a {trend_change:.1f} percentage point change. Current average: <strong>{recent_trend:.1f}%</strong> 
    vs. historical: <strong>{historical_avg:.1f}%</strong></p>
    </div>
    """, unsafe_allow_html=True)

def main():
    """Main application"""
    # Header
    st.markdown('<h1 class="main-header">🚌 Entur Punctuality Insights</h1>', 
                unsafe_allow_html=True)
    
    st.markdown("""
    **Advanced analytics for Norwegian public transport service quality and performance optimization**
    
    This dashboard analyzes punctuality data from major Norwegian transport operators, providing insights 
    into service quality trends, seasonal patterns, and regional performance differences.
    """)
    
    # Load data
    df = load_data()
    if df is None:
        return
    
    # Sidebar filters
    st.sidebar.header("📊 Dashboard Filters")
    
    # Date range filter
    date_range = st.sidebar.date_input(
        "Select Date Range",
        value=(df['date'].min(), df['date'].max()),
        min_value=df['date'].min(),
        max_value=df['date'].max()
    )
    
    # Filter data
    if len(date_range) == 2:
        filtered_df = df[
            (df['date'] >= pd.Timestamp(date_range[0])) & 
            (df['date'] <= pd.Timestamp(date_range[1]))
        ]
    else:
        filtered_df = df
    
    # Operator filter
    selected_operators = st.sidebar.multiselect(
        "Select Operators",
        options=df['operator'].unique(),
        default=df['operator'].unique()
    )
    
    # Region filter
    selected_regions = st.sidebar.multiselect(
        "Select Regions",
        options=df['region'].unique(),
        default=df['region'].unique()
    )
    
    # Apply filters
    filtered_df = filtered_df[
        (filtered_df['operator'].isin(selected_operators)) &
        (filtered_df['region'].isin(selected_regions))
    ]
    
    if filtered_df.empty:
        st.warning("⚠️ No data available for the selected filters.")
        return
    
    # Display metrics and charts
    create_performance_overview(filtered_df)
    
    st.markdown("---")
    
    # Main analysis tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Trends", "🚌 Operators", "🌸 Seasonal", "🏙️ Regional", "💡 Insights"
    ])
    
    with tab1:
        create_punctuality_trends(filtered_df)
    
    with tab2:
        create_operator_comparison(filtered_df)
    
    with tab3:
        create_seasonal_analysis(filtered_df)
    
    with tab4:
        create_regional_analysis(filtered_df)
    
    with tab5:
        create_insights_summary(filtered_df)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        <p>🚌 <strong>Entur Punctuality Insights</strong> | 
        Data-driven public transport optimization | 
        Built with Streamlit & Python</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()