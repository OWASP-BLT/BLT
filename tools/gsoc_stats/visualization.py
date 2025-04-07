import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def create_bar_chart(pr_counts_df):
    """
    Create a bar chart visualization for PR counts by year and repository.
    
    Args:
        pr_counts_df (pandas.DataFrame): DataFrame with columns 'year', 'repository', and 'count'
        
    Returns:
        plotly.graph_objects.Figure: Bar chart figure
    """
    if pr_counts_df.empty:
        # Return empty figure if no data
        return go.Figure()
    
    # Convert year to string for better display
    pr_counts_df = pr_counts_df.copy()
    pr_counts_df['year'] = pr_counts_df['year'].astype(str)
    
    # Create bar chart
    fig = px.bar(
        pr_counts_df,
        x='year',
        y='count',
        color='repository',
        title='Pull Requests by Year and Repository',
        labels={'count': 'Number of Pull Requests', 'year': 'Year', 'repository': 'Repository'},
        barmode='group'
    )
    
    # Update layout
    fig.update_layout(
        xaxis_title='Year',
        yaxis_title='Number of Pull Requests',
        legend_title='Repository',
        hovermode='closest'
    )
    
    return fig

def create_line_chart(pr_counts_df):
    """
    Create a line chart visualization for PR trends over years by repository.
    
    Args:
        pr_counts_df (pandas.DataFrame): DataFrame with columns 'year', 'repository', and 'count'
        
    Returns:
        plotly.graph_objects.Figure: Line chart figure
    """
    if pr_counts_df.empty:
        # Return empty figure if no data
        return go.Figure()
    
    # Convert year to string for better display
    pr_counts_df = pr_counts_df.copy()
    pr_counts_df['year'] = pr_counts_df['year'].astype(str)
    
    # Create line chart
    fig = px.line(
        pr_counts_df,
        x='year',
        y='count',
        color='repository',
        title='Pull Request Trends by Year and Repository',
        labels={'count': 'Number of Pull Requests', 'year': 'Year', 'repository': 'Repository'},
        markers=True
    )
    
    # Update layout
    fig.update_layout(
        xaxis_title='Year',
        yaxis_title='Number of Pull Requests',
        legend_title='Repository',
        hovermode='closest'
    )
    
    return fig

def create_heatmap(pr_counts_df):
    """
    Create a heatmap visualization for PR counts by year and repository.
    
    Args:
        pr_counts_df (pandas.DataFrame): DataFrame with columns 'year', 'repository', and 'count'
        
    Returns:
        plotly.graph_objects.Figure: Heatmap figure
    """
    if pr_counts_df.empty:
        # Return empty figure if no data
        return go.Figure()
    
    # Pivot data for heatmap
    pivot_df = pr_counts_df.pivot(index='repository', columns='year', values='count').fillna(0)
    
    # Create heatmap
    fig = px.imshow(
        pivot_df,
        title='Pull Request Heatmap by Year and Repository',
        labels=dict(x='Year', y='Repository', color='Number of PRs'),
        x=pivot_df.columns,
        y=pivot_df.index,
        color_continuous_scale='Viridis',
        aspect='auto'
    )
    
    # Update layout
    fig.update_layout(
        xaxis_title='Year',
        yaxis_title='Repository',
        coloraxis_colorbar_title='Number of PRs'
    )
    
    # Add text annotations
    for i, row in enumerate(pivot_df.index):
        for j, col in enumerate(pivot_df.columns):
            fig.add_annotation(
                x=col,
                y=row,
                text=str(int(pivot_df.iloc[i, j])),
                showarrow=False,
                font=dict(color='white' if pivot_df.iloc[i, j] > pivot_df.values.mean() else 'black')
            )
    
    return fig
