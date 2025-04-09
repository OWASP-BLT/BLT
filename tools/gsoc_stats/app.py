import streamlit as st
import pandas as pd
import datetime
import os
from github_api import fetch_repositories, fetch_pull_requests
from data_processing import process_pull_requests, filter_gsoc_prs
from visualization import create_bar_chart, create_line_chart, create_heatmap
from utils import get_gsoc_dates, setup_page_config

# Set page configuration
setup_page_config()

# App title and description
st.title("OWASP BLT GSoC Pull Request Statistics")
st.markdown("""
This application visualizes the pull request statistics for OWASP BLT repositories 
during Google Summer of Code (GSoC) over the past 10 years.
""")

# GitHub API token
github_token = os.environ.get("GITHUB_TOKEN", "")

# Sidebar for filters
st.sidebar.title("Data Filters")

# Initialize session state if not already done
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
    st.session_state.repositories = []
    st.session_state.all_prs = pd.DataFrame()
    st.session_state.gsoc_prs = pd.DataFrame()

# Load data button
if st.sidebar.button("Load Data") or st.session_state.data_loaded:
    if not st.session_state.data_loaded:
        with st.spinner('Fetching repositories...'):
            try:
                # Fetch OWASP BLT repositories
                repositories = fetch_repositories(github_token, "OWASP-BLT")
                
                if not repositories:
                    st.error("No repositories found for OWASP BLT. Please check the organization name or your GitHub token.")
                else:
                    st.session_state.repositories = repositories
                    
                    # Fetch pull requests for each repository
                    all_prs = []
                    progress_bar = st.progress(0)
                    for i, repo in enumerate(repositories):
                        progress_text = f"Fetching pull requests for {repo}..."
                        st.text(progress_text)
                        
                        repo_prs = fetch_pull_requests(github_token, "OWASP-BLT", repo)
                        all_prs.extend(repo_prs)
                        
                        # Update progress
                        progress_bar.progress((i + 1) / len(repositories))
                    
                    # Process pull requests data
                    if all_prs:
                        df_all_prs = process_pull_requests(all_prs)
                        
                        # Get GSoC dates for filtering
                        gsoc_dates = get_gsoc_dates(10)  # Last 10 years
                        
                        # Filter PRs for GSoC periods
                        df_gsoc_prs = filter_gsoc_prs(df_all_prs, gsoc_dates)
                        
                        # Store in session state
                        st.session_state.all_prs = df_all_prs
                        st.session_state.gsoc_prs = df_gsoc_prs
                        st.session_state.data_loaded = True
                        
                        st.success("Data loaded successfully!")
                    else:
                        st.warning("No pull requests found for the selected repositories.")
            except Exception as e:
                st.error(f"Error loading data: {str(e)}")
    
    # If data is loaded, display filters and visualizations
    if st.session_state.data_loaded and not st.session_state.gsoc_prs.empty:
        # Year filter
        available_years = sorted(st.session_state.gsoc_prs['year'].unique().tolist())
        selected_years = st.sidebar.multiselect(
            "Filter by Year",
            available_years,
            default=available_years
        )
        
        # Repository filter
        available_repos = sorted(st.session_state.gsoc_prs['repository'].unique().tolist())
        selected_repos = st.sidebar.multiselect(
            "Filter by Repository",
            available_repos,
            default=available_repos
        )
        
        # Apply filters
        filtered_df = st.session_state.gsoc_prs[
            (st.session_state.gsoc_prs['year'].isin(selected_years)) &
            (st.session_state.gsoc_prs['repository'].isin(selected_repos))
        ]
        
        # Display stats
        st.header("Pull Request Statistics")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total PRs", len(filtered_df))
        with col2:
            st.metric("Repositories", len(selected_repos))
        with col3:
            st.metric("Years", len(selected_years))
        
        # Visualization options
        viz_type = st.selectbox(
            "Select Visualization",
            ["Bar Chart", "Line Chart", "Heatmap"]
        )
        
        # Group data for visualization
        if not filtered_df.empty:
            # Aggregate data by year and repository
            pr_counts = filtered_df.groupby(['year', 'repository']).size().reset_index(name='count')
            
            # Display the appropriate visualization
            if viz_type == "Bar Chart":
                st.plotly_chart(create_bar_chart(pr_counts), use_container_width=True)
            elif viz_type == "Line Chart":
                st.plotly_chart(create_line_chart(pr_counts), use_container_width=True)
            else:  # Heatmap
                st.plotly_chart(create_heatmap(pr_counts), use_container_width=True)
            
            # Display data table
            st.subheader("Data Table")
            st.dataframe(pr_counts, use_container_width=True)
        else:
            st.warning("No data available for the selected filters.")
    
    elif st.session_state.data_loaded and st.session_state.gsoc_prs.empty:
        st.warning("No GSoC pull requests found in the last 10 years.")
else:
    st.info("Click 'Load Data' to fetch OWASP BLT repository pull request statistics.")

# About section
with st.expander("About this application"):
    st.markdown("""
    This application fetches and displays GitHub pull request data for OWASP BLT repositories
    during Google Summer of Code periods over the past 10 years.
    
    Data is sourced directly from the GitHub API and is automatically filtered to include
    only pull requests that occurred during official GSoC timeframes.
    
    **How to use:**
    1. Click the "Load Data" button to fetch repositories and pull requests
    2. Use the filters in the sidebar to explore data by year and repository
    3. Choose different visualization types to view the data
    
    **Note:** GitHub API has rate limits. If you encounter errors, please wait a few minutes before retrying.
    """)
