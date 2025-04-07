import streamlit as st
from datetime import datetime, timedelta

def setup_page_config():
    """
    Set up Streamlit page configuration.
    """
    st.set_page_config(
        page_title="OWASP BLT GSoC PR Stats",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def get_gsoc_dates(years_back=10):
    """
    Get the start and end dates for GSoC for the specified number of years back.
    
    Args:
        years_back (int): Number of years to go back
        
    Returns:
        dict: Dictionary mapping years to (start_date, end_date) tuples
    """
    # Dictionary to store GSoC dates
    gsoc_dates = {}
    
    # Current year
    current_year = datetime.now().year
    
    # GSoC typically runs from April/May to August/September
    # These are approximate dates which can be adjusted if needed
    for year in range(current_year - years_back + 1, current_year + 1):
        # Approximate GSoC period for each year
        # Note: Actual dates may vary, these are estimates
        if year == 2023:
            start_date = datetime(year, 5, 1)
            end_date = datetime(year, 9, 15)
        elif year == 2022:
            start_date = datetime(year, 4, 19)
            end_date = datetime(year, 9, 12)
        elif year == 2021:
            start_date = datetime(year, 5, 17)
            end_date = datetime(year, 8, 23)
        elif year == 2020:
            start_date = datetime(year, 5, 4)
            end_date = datetime(year, 8, 31)
        elif year == 2019:
            start_date = datetime(year, 5, 6)
            end_date = datetime(year, 8, 26)
        elif year == 2018:
            start_date = datetime(year, 4, 23)
            end_date = datetime(year, 8, 14)
        elif year == 2017:
            start_date = datetime(year, 5, 4)
            end_date = datetime(year, 8, 29)
        elif year == 2016:
            start_date = datetime(year, 4, 22)
            end_date = datetime(year, 8, 23)
        elif year == 2015:
            start_date = datetime(year, 4, 27)
            end_date = datetime(year, 8, 21)
        elif year == 2014:
            start_date = datetime(year, 5, 19)
            end_date = datetime(year, 8, 18)
        elif year <= 2013:
            # Default dates for older years
            start_date = datetime(year, 5, 1)
            end_date = datetime(year, 8, 31)
        
        gsoc_dates[year] = (start_date, end_date)
    
    return gsoc_dates

def format_date(date_obj):
    """
    Format a datetime object as a string.
    
    Args:
        date_obj (datetime): The datetime object to format
        
    Returns:
        str: Formatted date string
    """
    if date_obj is None:
        return "N/A"
    return date_obj.strftime("%Y-%m-%d")

def calculate_pr_stats(df):
    """
    Calculate various statistics about pull requests.
    
    Args:
        df (pandas.DataFrame): DataFrame containing pull request data
        
    Returns:
        dict: Dictionary of statistics
    """
    if df.empty:
        return {
            'total_prs': 0,
            'open_prs': 0,
            'closed_prs': 0,
            'merged_prs': 0,
            'avg_duration': 0,
            'repositories': 0,
            'contributors': 0
        }
    
    stats = {
        'total_prs': len(df),
        'open_prs': len(df[df['state'] == 'open']),
        'closed_prs': len(df[df['state'] == 'closed']),
        'merged_prs': len(df[df['merged'] == True]),
        'avg_duration': df['duration_days'].dropna().mean() if 'duration_days' in df.columns else 0,
        'repositories': df['repository'].nunique(),
        'contributors': df['user'].nunique()
    }
    
    return stats
