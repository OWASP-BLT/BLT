import pandas as pd
import streamlit as st
from datetime import datetime

def process_pull_requests(pull_requests):
    """
    Process the raw pull request data into a pandas DataFrame.
    
    Args:
        pull_requests (list): List of pull request dictionaries
        
    Returns:
        pandas.DataFrame: Processed pull request data
    """
    if not pull_requests:
        return pd.DataFrame()
        
    # Convert to DataFrame
    df = pd.DataFrame(pull_requests)
    
    # Convert datetime columns
    for col in ['created_at', 'closed_at', 'merged_at']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    
    # Extract year from created_at
    df['year'] = df['created_at'].dt.year
    
    # Calculate PR duration in days (if closed)
    df['duration_days'] = None
    mask = df['closed_at'].notna()
    df.loc[mask, 'duration_days'] = (df.loc[mask, 'closed_at'] - df.loc[mask, 'created_at']).dt.total_seconds() / 86400
    
    # Add merged flag
    df['merged'] = df['merged_at'].notna()
    
    return df

def filter_gsoc_prs(df, gsoc_dates):
    """
    Filter pull requests to only include those created during GSoC periods.
    
    Args:
        df (pandas.DataFrame): DataFrame containing all pull requests
        gsoc_dates (dict): Dictionary mapping years to (start_date, end_date) tuples
        
    Returns:
        pandas.DataFrame: Filtered DataFrame with only GSoC pull requests
    """
    if df.empty:
        return df
        
    # Create an empty DataFrame with the same columns
    gsoc_df = pd.DataFrame(columns=df.columns)
    
    # Filter for each GSoC period
    for year, (start_date, end_date) in gsoc_dates.items():
        year_prs = df[(df['created_at'] >= start_date) & (df['created_at'] <= end_date)]
        
        # Set the year to the GSoC year (since PRs might be created in a different calendar year)
        if not year_prs.empty:
            year_prs = year_prs.copy()
            year_prs['year'] = year
            
        gsoc_df = pd.concat([gsoc_df, year_prs])
    
    return gsoc_df

def aggregate_pr_data(df, group_by):
    """
    Aggregate pull request data by specified grouping.
    
    Args:
        df (pandas.DataFrame): DataFrame containing pull request data
        group_by (list): List of columns to group by
        
    Returns:
        pandas.DataFrame: Aggregated data
    """
    if df.empty:
        return df
        
    # Group by specified columns and count PRs
    grouped = df.groupby(group_by).size().reset_index(name='count')
    
    return grouped
