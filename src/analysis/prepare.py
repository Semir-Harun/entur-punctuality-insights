"""
Entur Punctuality Insights - Data Processing Pipeline
Norwegian Public Transport Service Quality Analytics

This module processes Norwegian public transport punctuality data to generate
actionable insights about service quality, operator performance, and passenger experience.
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path


def load_raw(filename):
    """Load raw Entur punctuality data"""
    raw_path = Path(__file__).resolve().parents[2] / "data" / "raw" / filename
    print(f"🚌 Processing Entur punctuality data from {raw_path}")
    return pd.read_csv(raw_path)


def build_punctuality_metrics(df):
    """
    Build comprehensive public transport punctuality metrics
    
    Transforms raw Entur data into analytical metrics including:
    - Operator performance comparisons
    - Route-level service quality analysis
    - Regional punctuality patterns
    - Passenger impact assessment
    - Service improvement trends
    
    Args:
        df (pd.DataFrame): Raw Entur punctuality data
        
    Returns:
        pd.DataFrame: Processed monthly metrics with operator analysis
    """
    # Data preparation
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["season"] = df["month"].map({
        12: "Winter", 1: "Winter", 2: "Winter",
        3: "Spring", 4: "Spring", 5: "Spring", 
        6: "Summer", 7: "Summer", 8: "Summer",
        9: "Autumn", 10: "Autumn", 11: "Autumn"
    })
    
    # Group by date, region, and operator for comprehensive analysis
    monthly = df.groupby(["date", "region", "operator"]).agg({
        "scheduled_trips": ["sum", "mean"],
        "on_time_trips": ["sum", "mean"], 
        "delayed_trips": ["sum", "mean"],
        "avg_delay_minutes": ["mean", "max"],
        "punctuality_rate": ["mean", "min", "max"],
        "passenger_impact_score": ["mean", "sum"]
    }).round(1)
    
    # Flatten column names
    monthly.columns = [
        "scheduled_trips_total", "scheduled_trips_mean",
        "on_time_trips_total", "on_time_trips_mean",
        "delayed_trips_total", "delayed_trips_mean", 
        "avg_delay_mean", "avg_delay_max",
        "punctuality_rate_mean", "punctuality_rate_min", "punctuality_rate_max",
        "passenger_impact_mean", "passenger_impact_total"
    ]
    monthly = monthly.reset_index()
    
    # Calculate monthly improvements (month-over-month punctuality change)
    monthly["punctuality_improvement"] = monthly.groupby(["region", "operator"])["punctuality_rate_mean"].diff()
    monthly["punctuality_improvement"] = monthly["punctuality_improvement"].fillna(0).round(1)
    
    # Calculate reliability metrics
    monthly["service_reliability"] = (monthly["on_time_trips_total"] / monthly["scheduled_trips_total"] * 100).round(1)
    monthly["delay_consistency"] = (100 - (monthly["avg_delay_max"] - monthly["avg_delay_mean"]) * 10).clip(0, 100).round(1)
    
    # Add date components first
    monthly["year"] = monthly["date"].dt.year
    monthly["month"] = monthly["date"].dt.month
    
    # Rolling 3-month average for trend smoothing
    monthly["punctuality_trend"] = monthly.groupby(["region", "operator"])["punctuality_rate_mean"].transform(lambda x: x.rolling(window=3, center=True).mean()).round(1)
    
    # Year-over-year comparison
    monthly["yoy_punctuality_change"] = monthly.groupby(["region", "operator", "month"])["punctuality_rate_mean"].pct_change(periods=1) * 100
    monthly["yoy_punctuality_change"] = monthly["yoy_punctuality_change"].fillna(0).round(1)
    monthly["season"] = monthly["month"].map({
        12: "Winter", 1: "Winter", 2: "Winter",
        3: "Spring", 4: "Spring", 5: "Spring", 
        6: "Summer", 7: "Summer", 8: "Summer",
        9: "Autumn", 10: "Autumn", 11: "Autumn"
    })
    
    # Service quality classification
    monthly["service_grade"] = monthly["punctuality_rate_mean"].apply(lambda x:
        "Excellent" if x >= 95 else
        "Good" if x >= 85 else
        "Acceptable" if x >= 75 else
        "Needs Improvement" if x >= 65 else
        "Poor"
    )
    
    # Passenger impact classification
    monthly["impact_level"] = monthly["passenger_impact_mean"].apply(lambda x:
        "Low" if x < 1.0 else
        "Moderate" if x < 2.0 else
        "High" if x < 3.0 else
        "Critical"
    )
    
    # COVID-19 service adaptation indicator
    monthly["covid_adaptation"] = ((monthly["year"] == 2020) & 
                                  (monthly["month"].isin([3, 4, 5, 6]))).astype(int)
    
    return monthly


def calculate_operator_rankings(df):
    """Calculate comprehensive operator performance rankings"""
    operator_stats = df.groupby(["operator", "region"]).agg({
        "punctuality_rate_mean": ["mean", "std", "min", "max"],
        "passenger_impact_mean": ["mean", "std"],
        "scheduled_trips_total": ["sum", "mean"],
        "service_reliability": ["mean"],
        "delay_consistency": ["mean"]
    }).round(1)
    
    # Flatten column names
    operator_stats.columns = [
        "avg_punctuality", "punctuality_std", "worst_punctuality", "best_punctuality",
        "avg_impact", "impact_std", 
        "total_trips", "avg_monthly_trips",
        "avg_reliability", "avg_consistency"
    ]
    operator_stats = operator_stats.reset_index()
    
    # Calculate composite performance score
    # Higher punctuality + lower impact + higher consistency = better score
    operator_stats["performance_score"] = (
        operator_stats["avg_punctuality"] * 0.4 +
        (100 - operator_stats["avg_impact"] * 20) * 0.3 +  # Inverse impact (lower is better)
        operator_stats["avg_consistency"] * 0.3
    ).round(1)
    
    # Rank operators
    operator_stats["performance_rank"] = operator_stats["performance_score"].rank(ascending=False, method="dense").astype(int)
    
    return operator_stats.sort_values("performance_score", ascending=False)


def seasonal_analysis(df):
    """Analyze seasonal patterns in punctuality"""
    seasonal_stats = df.groupby(["season", "operator"]).agg({
        "punctuality_rate_mean": ["mean", "std"],
        "passenger_impact_mean": ["mean"],
        "avg_delay_mean": ["mean"]
    }).round(1)
    
    seasonal_stats.columns = ["punctuality", "punctuality_std", "impact", "delay"]
    seasonal_stats = seasonal_stats.reset_index()
    
    # Identify best and worst seasons for each operator
    best_seasons = seasonal_stats.loc[seasonal_stats.groupby("operator")["punctuality"].idxmax()]
    worst_seasons = seasonal_stats.loc[seasonal_stats.groupby("operator")["punctuality"].idxmin()]
    
    return seasonal_stats, best_seasons, worst_seasons


def covid_impact_analysis(df):
    """Analyze COVID-19 impact on public transport punctuality"""
    pre_covid = df[df["date"] < "2020-03-01"]["punctuality_rate_mean"].mean()
    covid_period = df[(df["date"] >= "2020-03-01") & (df["date"] < "2020-07-01")]["punctuality_rate_mean"].mean()
    post_covid = df[df["date"] >= "2021-01-01"]["punctuality_rate_mean"].mean()
    
    covid_analysis = {
        "pre_covid_punctuality": pre_covid,
        "covid_period_punctuality": covid_period,
        "post_covid_punctuality": post_covid,
        "covid_impact_pct": ((covid_period - pre_covid) / pre_covid * 100) if pre_covid > 0 else 0,
        "recovery_rate_pct": ((post_covid - covid_period) / covid_period * 100) if covid_period > 0 else 0,
        "service_improved": post_covid > pre_covid * 1.02  # 2% improvement threshold
    }
    
    return covid_analysis


def save_processed(df, filename):
    """Save processed punctuality data"""
    processed_path = Path(__file__).resolve().parents[2] / "data" / "processed" / filename
    df.to_csv(processed_path, index=False)
    print(f"✅ Processed punctuality data saved to {processed_path}")
    print(f"🚌 Dataset contains {len(df)} monthly records across {df['operator'].nunique()} operators")
    return processed_path


def main():
    """Main processing pipeline for Entur punctuality insights"""
    parser = argparse.ArgumentParser(description="Process Norwegian public transport punctuality data")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--analysis", "-a", action="store_true", help="Include detailed analysis")
    args = parser.parse_args()
    
    if args.verbose:
        print("🚌 Entur Punctuality Insights - Data Processing Pipeline")
        print("📊 Loading and processing Norwegian public transport data...")
    
    try:
        # Load raw data
        df_raw = load_raw("norwegian_entur_punctuality.csv")
        
        if args.verbose:
            print(f"📋 Raw data loaded: {len(df_raw)} records")
            print(f"📅 Date range: {df_raw['date'].min()} to {df_raw['date'].max()}")
            print(f"🏙️ Regions: {df_raw['region'].unique()}")
            print(f"🚌 Operators: {df_raw['operator'].unique()}")
            print(f"🚇 Routes tracked: {df_raw['route_id'].nunique() if 'route_id' in df_raw.columns else 'N/A'}")
        
        # Process data
        df_processed = build_punctuality_metrics(df_raw)
        
        # Save results
        output_path = save_processed(df_processed, "punctuality_insights_processed.csv")
        
        if args.verbose:
            print("\n📊 Processing Summary:")
            total_trips = df_processed["scheduled_trips_total"].sum()
            avg_punctuality = df_processed["punctuality_rate_mean"].mean()
            best_operator = df_processed.loc[df_processed["punctuality_rate_mean"].idxmax()]
            worst_month = df_processed.loc[df_processed["punctuality_rate_mean"].idxmin()]
            
            print(f"   • Total trips tracked: {total_trips:,.0f}")
            print(f"   • Average punctuality: {avg_punctuality:.1f}%")
            print(f"   • Best performance: {best_operator['operator']} ({best_operator['punctuality_rate_mean']:.1f}% in {best_operator['date'].strftime('%B %Y')})")
            print(f"   • Worst month: {worst_month['date'].strftime('%B %Y')} ({worst_month['punctuality_rate_mean']:.1f}%)")
        
        # Additional analysis if requested
        if args.analysis:
            print("\n🔍 Detailed Analysis:")
            
            # Operator rankings
            operator_rankings = calculate_operator_rankings(df_processed)
            print(f"\n🏆 Operator Performance Rankings:")
            for _, row in operator_rankings.head(3).iterrows():
                print(f"   {row.name + 1}. {row['operator']} ({row['region']}): {row['performance_score']:.1f} score, {row['avg_punctuality']:.1f}% punctuality")
            
            # Seasonal analysis
            seasonal_stats, best_seasons, worst_seasons = seasonal_analysis(df_processed)
            print(f"\n🌡️ Seasonal Performance:")
            overall_seasonal = seasonal_stats.groupby("season")["punctuality"].mean().sort_values(ascending=False)
            for season, punctuality in overall_seasonal.items():
                print(f"   • {season}: {punctuality:.1f}% average punctuality")
            
            # COVID impact analysis
            covid_analysis = covid_impact_analysis(df_processed)
            print(f"\n🦠 COVID-19 Impact Analysis:")
            print(f"   • Pre-COVID punctuality: {covid_analysis['pre_covid_punctuality']:.1f}%")
            print(f"   • COVID period impact: {covid_analysis['covid_impact_pct']:.1f}%")
            print(f"   • Post-COVID recovery: {covid_analysis['recovery_rate_pct']:.1f}%")
            print(f"   • Service improvement achieved: {'Yes' if covid_analysis['service_improved'] else 'No'}")
            
        print(f"\n🎯 Ready for dashboard analysis!")
        print(f"   Run: streamlit run src/app/streamlit_app.py")
        
    except FileNotFoundError as e:
        print(f"❌ Error: Could not find data file - {e}")
        print("💡 Ensure 'norwegian_entur_punctuality.csv' exists in data/raw/")
    except Exception as e:
        print(f"❌ Processing error: {e}")


if __name__ == "__main__":
    main()