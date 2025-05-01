import streamlit as st
import pandas as pd
import os
import sys
import datetime
import json

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import load_json_file, save_json_file, get_articles_df

# Page configuration
st.set_page_config(
    page_title="Collecting",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.logo("assets/prospectorAIDE-logo.png", size='large')

# Create a container for logos in the header
header = st.container()
with header:
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # App title
        st.title("💎 Collecting", anchor=False)
    
    with col2:
        # Company logo
        if os.path.exists("assets/CtiPath-logo.png"):
            st.image("assets/CtiPath-logo.png", width=150)

st.markdown("Organize and finalize the collection of valuable articles for your sales process.")

# File paths
KEPT_ARTICLES_FILE = "data/articles-kept.json"
FINAL_COLLECTION_FILE = "data/final-collection.json"

# Load data
@st.cache_data(ttl=10)  # Cache with a short time-to-live to allow refreshing
def load_kept_data():
    articles = load_json_file(KEPT_ARTICLES_FILE)
    return articles

@st.cache_data(ttl=10)
def load_final_collection():
    articles = load_json_file(FINAL_COLLECTION_FILE)
    return articles

kept_articles = load_kept_data()
final_collection = load_final_collection()

# Check if there are any kept articles
if not kept_articles:
    st.warning("No articles have been kept yet. Please go to the Prospecting page and keep some articles first.")
    st.stop()

# Convert to DataFrame
df = get_articles_df(kept_articles)
final_df = get_articles_df(final_collection)

# Tabs for different views
tab1, tab2 = st.tabs(["Articles Overview", "Collection Management"])

with tab1:
    # Display statistics
    st.subheader("Collection Statistics")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Kept Articles", len(kept_articles))
    
    with col2:
        st.metric("Final Collection", len(final_collection))
    
    with col3:
        if 'confidence' in df.columns and not df.empty:
            high_confidence = len(df[df['confidence'] >= 70])
            st.metric("High Confidence Articles", high_confidence)
        else:
            st.metric("High Confidence Articles", "0")
    
    # Company distribution
    if 'company' in df.columns and not df.empty:
        st.subheader("Company Distribution")
        company_counts = df['company'].value_counts().reset_index()
        company_counts.columns = ['Company', 'Count']
        company_counts = company_counts[company_counts['Company'] != '']  # Filter out empty company names
        
        if not company_counts.empty:
            st.bar_chart(company_counts.set_index('Company'))
        else:
            st.info("No company distribution data available.")
    
    # Confidence distribution
    if 'confidence' in df.columns and not df.empty:
        st.subheader("Confidence Score Distribution")
        
        # Create bins for confidence scores
        bins = [0, 20, 40, 60, 80, 100]
        labels = ['0-20', '21-40', '41-60', '61-80', '81-100']
        df['confidence_range'] = pd.cut(df['confidence'], bins=bins, labels=labels, right=False)
        
        confidence_counts = df['confidence_range'].value_counts().reset_index()
        confidence_counts.columns = ['Range', 'Count']
        confidence_counts = confidence_counts.sort_values('Range')
        
        st.bar_chart(confidence_counts.set_index('Range'))
    
    # Date distribution
    if 'date' in df.columns and not df.empty:
        st.subheader("Article Date Distribution")
        df['date_only'] = df['date'].dt.date
        date_counts = df.groupby('date_only').size().reset_index()
        date_counts.columns = ['Date', 'Count']
        date_counts = date_counts.sort_values('Date')
        
        st.line_chart(date_counts.set_index('Date'))

with tab2:
    st.subheader("Manage Your Collection")
    
    # Two columns layout for kept articles and final collection
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Kept Articles")
        
        # Filter options
        if 'company' in df.columns and not df.empty:
            companies = ['All'] + sorted(df['company'].unique().tolist())
            selected_company = st.selectbox("Filter by Company", companies, key="company_filter_kept")
        else:
            selected_company = "All"
        
        # Apply filter
        filtered_df = df.copy()
        if selected_company != "All" and 'company' in df.columns:
            filtered_df = filtered_df[filtered_df['company'] == selected_company]
        
        # Display kept articles
        if not filtered_df.empty:
            # Format dates for display
            display_df = filtered_df.copy()
            if 'date' in display_df.columns:
                display_df['date'] = display_df['date'].dt.strftime("%Y-%m-%d")
            
            # Define columns for display
            display_columns = ['title', 'company', 'confidence']
            
            # Display as selectable dataframe
            st.dataframe(
                display_df[display_columns],
                use_container_width=True,
                column_config={
                    "title": st.column_config.TextColumn("Title"),
                    "company": st.column_config.TextColumn("Company"),
                    "confidence": st.column_config.NumberColumn(
                        "Confidence",
                        format="%d%%"
                    ),
                },
                hide_index=True,
                height=300
            )
            
            # Select article to add to final collection
            selected_titles = filtered_df['title'].tolist()
            selected_title = st.selectbox(
                "Select article to add to collection", 
                options=selected_titles,
                key="kept_article_selector"
            )
            
            if selected_title:
                # Find the article
                selected_row = filtered_df[filtered_df['title'] == selected_title]
                if 'articleID' in selected_row.columns:
                    article_id = selected_row['articleID'].iloc[0]
                    selected_article = next((a for a in kept_articles if a.get('articleID') == article_id), None)
                else:
                    # Fallback to index if articleID not available
                    article_idx = selected_row.index[0]
                    selected_article = next((a for i, a in enumerate(kept_articles) if i == article_idx), None)
                
                if selected_article:
                    # Button to add to final collection
                    if st.button("Add to Final Collection", key="add_to_collection", type="primary"):
                        # Check if already in final collection
                        existing_ids = [a.get('articleID') for a in final_collection if 'articleID' in a]
                        
                        if 'articleID' in selected_article and selected_article['articleID'] in existing_ids:
                            st.warning("This article is already in the final collection.")
                        else:
                            # Add to final collection
                            final_collection.append(selected_article)
                            save_json_file(final_collection, FINAL_COLLECTION_FILE)
                            st.success("Article added to final collection!")
                            # Reload data
                            st.cache_data.clear()
                            st.rerun()
        else:
            st.info("No kept articles match your filter criteria.")
    
    with col2:
        st.markdown("### Final Collection")
        
        if not final_df.empty:
            # Format dates for display
            display_final_df = final_df.copy()
            if 'date' in display_final_df.columns:
                display_final_df['date'] = display_final_df['date'].dt.strftime("%Y-%m-%d")
            
            # Define columns for display
            display_columns = ['title', 'company', 'confidence']
            
            # Display as selectable dataframe
            st.dataframe(
                display_final_df[display_columns],
                use_container_width=True,
                column_config={
                    "title": st.column_config.TextColumn("Title"),
                    "company": st.column_config.TextColumn("Company"),
                    "confidence": st.column_config.NumberColumn(
                        "Confidence",
                        format="%d%%"
                    ),
                },
                hide_index=True,
                height=300
            )
            
            # Select article to remove from final collection
            final_titles = display_final_df['title'].tolist()
            if final_titles:
                selected_final_title = st.selectbox(
                    "Select article to remove from collection", 
                    options=final_titles,
                    key="final_article_selector"
                )
                
                if selected_final_title:
                    # Find the article
                    selected_row = final_df[final_df['title'] == selected_final_title]
                    if 'articleID' in selected_row.columns:
                        article_id = selected_row['articleID'].iloc[0]
                        
                        # Button to remove from final collection
                        if st.button("Remove from Final Collection", key="remove_from_collection", type="secondary"):
                            # Remove from final collection
                            final_collection = [a for a in final_collection if a.get('articleID') != article_id]
                            save_json_file(final_collection, FINAL_COLLECTION_FILE)
                            st.success("Article removed from final collection!")
                            # Reload data
                            st.cache_data.clear()
                            st.rerun()
            
            # Export options
            st.markdown("### Export Collection")
            export_format = st.radio(
                "Export Format",
                options=["JSON", "CSV", "Excel"],
                horizontal=True
            )
            
            if st.button("Export Collection", key="export_collection", type="primary"):
                if export_format == "JSON":
                    # Already in JSON format, just display a success message
                    st.success(f"Collection exported to {FINAL_COLLECTION_FILE}")
                elif export_format == "CSV":
                    # Export to CSV
                    csv_file = "data/final-collection.csv"
                    final_df.to_csv(csv_file, index=False)
                    st.success(f"Collection exported to {csv_file}")
                elif export_format == "Excel":
                    # Export to Excel
                    excel_file = "data/final-collection.xlsx"
                    final_df.to_excel(excel_file, index=False)
                    st.success(f"Collection exported to {excel_file}")
        else:
            st.info("No articles in final collection yet. Add some from the kept articles.")

# Footer
st.divider()
st.markdown("**Final Step:** Export your collection for use in your sales process.")