import streamlit as st
import pandas as pd
import os
import sys
import datetime

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import load_json_file, save_json_file, get_articles_df

# Page configuration
st.set_page_config(
    page_title="Mining",
    page_icon="⚒️",
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
        st.title("⚒️ Mining", anchor=False)
    
    with col2:
        # Company logo
        if os.path.exists("assets/CtiPath-logo.png"):
            st.image("assets/CtiPath-logo.png", width=150)

st.markdown("Extract valuable information from articles that passed the prospecting stage.")

# File paths
KEPT_ARTICLES_FILE = "articles-kept.json"

# Load data
@st.cache_data(ttl=10)  # Cache with a short time-to-live to allow refreshing
def load_kept_data():
    articles = load_json_file(KEPT_ARTICLES_FILE)
    return articles

kept_articles = load_kept_data()

# Check if there are any kept articles
if not kept_articles:
    st.warning("No articles have been kept yet. Please go to the Prospecting page and keep some articles first.")
    st.stop()

# Convert to DataFrame
df = get_articles_df(kept_articles)

# Display statistics
st.subheader("Mining Statistics")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Articles", len(kept_articles))

with col2:
    if 'confidence' in df.columns:
        avg_confidence = df['confidence'].mean()
        st.metric("Average Confidence", f"{avg_confidence:.1f}%")
    else:
        st.metric("Average Confidence", "N/A")

with col3:
    if 'analyze_date' in df.columns:
        analyzed_count = df['analyze_date'].notna().sum()
        st.metric("Analyzed Articles", f"{analyzed_count}/{len(kept_articles)}")
    else:
        st.metric("Analyzed Articles", "0/{len(kept_articles)}")

# Filtering options
st.subheader("Filter Articles")
col1, col2 = st.columns(2)

with col1:
    # Filter by company
    if 'company' in df.columns and not df.empty:
        companies = ['All'] + sorted(df['company'].unique().tolist())
        selected_company = st.selectbox("Company", companies)
    else:
        selected_company = "All"

with col2:
    # Filter by confidence score
    min_confidence = st.slider("Minimum Confidence Score", 0, 100, 0)

# Apply filters
filtered_df = df.copy()

# Company filter
if selected_company != "All" and 'company' in df.columns:
    filtered_df = filtered_df[filtered_df['company'] == selected_company]

# Confidence filter
if 'confidence' in df.columns:
    filtered_df = filtered_df[filtered_df['confidence'] >= min_confidence]

# Display data
st.subheader(f"Articles ({len(filtered_df)} matching)")

# Create a copy of filtered_df with format enhancements for display
display_df = filtered_df.copy()

# Format dates for display
if 'date' in display_df.columns and not display_df.empty:
    display_df['date'] = display_df['date'].dt.strftime("%Y-%m-%d")

if 'analyze_date' in display_df.columns and not display_df.empty:
    display_df['analyze_date'] = display_df['analyze_date'].dt.strftime("%Y-%m-%d %H:%M")

# Define columns for display
display_columns = ['title', 'company', 'location', 'confidence', 'date']
if 'analyze_date' in display_df.columns:
    display_columns.append('analyze_date')

# Create the table with selection
selected_indices = st.dataframe(
    display_df[display_columns] if not display_df.empty else pd.DataFrame(columns=display_columns),
    use_container_width=True,
    column_config={
        "title": st.column_config.TextColumn("Title"),
        "company": st.column_config.TextColumn("Company"),
        "location": st.column_config.TextColumn("Location"),
        "confidence": st.column_config.ProgressColumn(
            "Confidence",
            help="AI-generated confidence score",
            format="%d%%",
            min_value=0,
            max_value=100
        ),
        "date": st.column_config.TextColumn("Date"),
        "analyze_date": st.column_config.TextColumn("Analyzed"),
    },
    hide_index=True,
    height=400
)

# Article selection
if 'selected_mining_article_index' not in st.session_state:
    st.session_state.selected_mining_article_index = None

st.subheader("Article Mining")

# Select an article to view details
if not filtered_df.empty:
    selected_titles = filtered_df['title'].tolist()
    selected_title = st.selectbox(
        "Select an article to mine", 
        options=selected_titles,
        index=0 if selected_titles else None,
        key="mining_article_selector"
    )
    
    if selected_title:
        selected_article_index = filtered_df[filtered_df['title'] == selected_title].index[0]
        st.session_state.selected_mining_article_index = selected_article_index
        
        # Get the selected article
        article_id = filtered_df.loc[selected_article_index, 'articleID'] if 'articleID' in filtered_df.columns else filtered_df.index[selected_article_index]
        selected_article = next((a for a in kept_articles if a.get('articleID') == article_id), None)
        
        if selected_article:
            # Display article details
            with st.expander("Article Details", expanded=True):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"### {selected_article.get('title', 'Untitled')}")
                    st.markdown(f"**Excerpt:** {selected_article.get('excerpt', 'No excerpt available')}")
                    
                    if 'company' in selected_article and selected_article['company']:
                        st.markdown(f"**Company:** {selected_article['company']}")
                    
                    if 'location' in selected_article and selected_article['location']:
                        st.markdown(f"**Location:** {selected_article['location']}")
                    
                    if 'date' in selected_article:
                        formatted_date = selected_article['date'].split('T')[0] if 'T' in selected_article['date'] else selected_article['date']
                        st.markdown(f"**Date:** {formatted_date}")
                    
                    if 'url' in selected_article:
                        st.markdown(f"**URL:** [{selected_article['url']}]({selected_article['url']})")
                
                with col2:
                    if 'confidence' in selected_article:
                        st.metric("Confidence", f"{selected_article['confidence']}%")
                    
                    if 'analyze_date' in selected_article:
                        st.markdown(f"**Last Analyzed:** {selected_article['analyze_date']}")
            
            # Mining tools
            st.subheader("Mining Tools")
            
            # Add key entity extraction and information tagging functionality here
            # For this prototype, we'll just have some placeholder forms
            
            with st.form("mining_form"):
                st.markdown("### Extract Key Information")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    key_entities = st.text_area("Key Entities", 
                                              help="Enter entities mentioned in the article (companies, people, products)")
                    
                    topics = st.text_area("Topics", 
                                        help="Enter main topics discussed in the article")
                
                with col2:
                    sentiment = st.radio("Sentiment", 
                                       options=["Positive", "Neutral", "Negative", "Mixed"],
                                       index=1,
                                       help="Select the overall sentiment of the article")
                    
                    relevance = st.slider("Relevance Score", 
                                        min_value=0, 
                                        max_value=10, 
                                        value=5,
                                        help="Rate how relevant this article is to your needs")
                    
                    potential_value = st.slider("Potential Value", 
                                              min_value=0, 
                                              max_value=10, 
                                              value=5,
                                              help="Rate the potential value of this article")
                
                # Add notes
                notes = st.text_area("Notes", 
                                   help="Add any additional notes or observations about this article")
                
                # Submit button
                submitted = st.form_submit_button("Save Mining Results", type="primary")
                
                if submitted:
                    # In a real implementation, you would update the article with the mining results
                    st.success("Mining results saved successfully!")
                    
                    # Simulate updating the article
                    # In a real implementation, you would update the JSON file
                    st.info("In a real implementation, this would update the article with your mining results.")
else:
    st.info("No articles found matching your filters.")

# Footer
st.divider()
st.markdown("**Next Step:** After mining valuable information, proceed to the Collecting stage.")