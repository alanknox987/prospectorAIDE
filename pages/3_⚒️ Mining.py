import streamlit as st
import pandas as pd
import os
import sys
import datetime

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import load_json_file, save_json_file, get_articles_df, remove_article

# Initialize session state variables
if 'selected_mining_article_index' not in st.session_state:
    st.session_state.selected_mining_article_index = None

# Page configuration
st.set_page_config(
    page_title="prospectorAIDE - Mining",
    page_icon="⚒️",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.logo("assets/prospectorAIDE-logo.png", size='large')

# Load external CSS file
def load_css(css_file):
    if os.path.exists(css_file):
        with open(css_file, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"CSS file not found: {css_file}")

# Load the CSS
load_css("styles.css")

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

st.markdown("Extract valuable information for prospects that passed the prospecting stage.")

# File paths
KEPT_ARTICLES_FILE = "data/prospects-kept.json"

# Load data
@st.cache_data(ttl=10)  # Cache with a short time-to-live to allow refreshing
def load_kept_data():
    articles = load_json_file(KEPT_ARTICLES_FILE)
    # If articles is a list of dictionaries, convert to list and extract 'articleID'
    if articles and isinstance(articles, list) and 'articleID' in articles[0]:
        # Make sure each article has an index based on its position
        for i, article in enumerate(articles):
            article['index'] = i
    return articles

kept_articles = load_kept_data()

# Check if there are any kept articles
if not kept_articles:
    st.warning("No prospects have been kept yet. Please go to the Prospecting page and keep some prospects first.")
    st.stop()

# Convert to DataFrame
df = get_articles_df(kept_articles)

# Display statistics
st.subheader("📊 Statistics", anchor=False)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Prospects", len(kept_articles))

with col2:
    if 'confidence' in df.columns:
        avg_confidence = df['confidence'].mean()
        st.metric("Average Confidence", f"{avg_confidence:.0f}%")
    else:
        st.metric("Average Confidence", "N/A")

with col3:
    # Count analyzed articles based on presence of 'analysis' key instead of analyze_date
    analyzed_count = sum(1 for a in kept_articles if 'analysis' in a)
    st.metric("Analyzed Prospects", f"{analyzed_count}/{len(kept_articles)}")

with col4:
    # Count mined articles based on presence of 'mined' key
    mined_count = sum(1 for a in kept_articles if 'mined' in a)
    st.metric("Mined Prospects", f"{mined_count}/{len(kept_articles)}")

# Filtering and sorting options (matching Prospecting page)
st.subheader("Filter and Sort Prospects", anchor=False)
col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

with col1:
    # Filter by confidence score
    min_confidence = st.slider("Minimum Confidence", 0, 100, 0)

with col2:
    # Filter by date
    if 'date' in df.columns and not df.empty:
        date_options = ['All', 'Today', 'Yesterday', 'Last 7 days']
        date_filter = st.selectbox("Date", date_options)
    else:
        date_filter = "All"

with col3:
    # Filter by company
    if 'company' in df.columns and not df.empty:
        companies = ['All'] + sorted(df['company'].unique().tolist())
        selected_company = st.selectbox("Company", companies)
    else:
        selected_company = "All"

with col4:
    # New filter for analyzed status
    analyzed_options = ['All', 'Analyzed', 'Not Analyzed']
    analyzed_filter = st.selectbox("Analyzed", analyzed_options)

with col5:
    # Sorting options
    sort_options = ['Date (newest first)', 'Date (oldest first)', 
                   'Confidence (highest first)', 'Confidence (lowest first)']
    sort_selection = st.selectbox("Sort By", sort_options)

# Apply filters
filtered_df = pd.DataFrame()  # Initialize with an empty DataFrame
if not df.empty:
    filtered_df = df.copy()
    
    # Confidence filter
    if 'confidence' in df.columns:
        filtered_df = filtered_df[filtered_df['confidence'] >= min_confidence]
    
    # Date filter
    if date_filter != "All" and 'date' in df.columns:
        today = pd.Timestamp.now().floor('D')
        if date_filter == "Today":
            filtered_df = filtered_df[filtered_df['date'].dt.date == today.date()]
        elif date_filter == "Yesterday":
            yesterday = today - pd.Timedelta(days=1)
            filtered_df = filtered_df[filtered_df['date'].dt.date == yesterday.date()]
        elif date_filter == "Last 7 days":
            last_week = today - pd.Timedelta(days=7)
            filtered_df = filtered_df[filtered_df['date'] >= last_week]
    
    # Company filter
    if selected_company != "All" and 'company' in df.columns:
        filtered_df = filtered_df[filtered_df['company'] == selected_company]
    
    # Analyzed filter
    if analyzed_filter != "All":
        if analyzed_filter == "Analyzed":
            # Keep only articles that have 'analysis' key
            filtered_df = filtered_df[filtered_df.apply(lambda row: 
                'analysis' in next((a for a in kept_articles if a.get('articleID') == row.get('articleID')), {}), axis=1)]
        elif analyzed_filter == "Not Analyzed":
            # Keep only articles that don't have 'analysis' key
            filtered_df = filtered_df[filtered_df.apply(lambda row: 
                'analysis' not in next((a for a in kept_articles if a.get('articleID') == row.get('articleID')), {}), axis=1)]
    
    # Apply sorting
    if 'date' in filtered_df.columns and 'confidence' in filtered_df.columns:
        if sort_selection == 'Date (newest first)':
            filtered_df = filtered_df.sort_values('date', ascending=False)
        elif sort_selection == 'Date (oldest first)':
            filtered_df = filtered_df.sort_values('date', ascending=True)
        elif sort_selection == 'Confidence (highest first)':
            filtered_df = filtered_df.sort_values('confidence', ascending=False)
        elif sort_selection == 'Confidence (lowest first)':
            filtered_df = filtered_df.sort_values('confidence', ascending=True)

# Display data in the same format as the Prospecting page
if not filtered_df.empty:
    st.markdown(f"<div class='article-header'><strong>Prospect List</strong> ({len(filtered_df)} matching)</div>", unsafe_allow_html=True)

    # Create a compact list of articles with minimal spacing
    for idx, row in filtered_df.iterrows():
        article_id = row.get('articleID')
        article = next((a for a in kept_articles if a.get('articleID') == article_id), None)
        
        if article:
            # Use a 2-column layout: Article Content | Action Buttons
            cols = st.columns([6, 1])
            
            with cols[0]:
                # Title with confidence emoji
                if article['confidence'] >= 80:
                    confidence_emoji = "🟢"
                elif article['confidence'] >= 60:
                    confidence_emoji = "🔵"
                elif article['confidence'] >= 40:
                    confidence_emoji = "🟡"
                elif article['confidence'] >= 20:
                    confidence_emoji = "🔴"
                else:
                    confidence_emoji = "⚫"

                st.markdown(f"<div class='article-title'><strong>{confidence_emoji} {article['title']}</strong></div>", unsafe_allow_html=True)
                
                # Excerpt
                if 'excerpt' in article:
                    st.markdown(f"<div class='article-excerpt'>{article['excerpt']}</div>", unsafe_allow_html=True)
                
                # Metadata in specified order: confidence, date, company, location
                metadata_parts = []
                
                # Confidence (bold)
                if 'confidence' in article:
                    metadata_parts.append(f"<strong>Confidence: {article['confidence']}</strong>")
                
                # Date
                if 'date' in article:
                    formatted_date = article['date'].split('T')[0] if 'T' in article['date'] else article['date']
                    metadata_parts.append(f"<strong>Date:</strong> {formatted_date}")
                
                # Company
                if 'company' in article and article['company']:
                    metadata_parts.append(f"<strong>Company:</strong> {article['company']}")
                
                # Location
                if 'location' in article and article['location']:
                    metadata_parts.append(f"<strong>Location:</strong> {article['location']}")
                
                # Join metadata with pipe separators
                if metadata_parts:
                    metadata_html = "<div class='article-metadata'>" + " | ".join(metadata_parts) + "</div>"
                    st.markdown(metadata_html, unsafe_allow_html=True)

                # Show analyze_date if available
                if 'analyze_date' in article:
                    st.markdown(f"<div class='article-metadata'>Analyzed: {article['analyze_date']}</div>", unsafe_allow_html=True)

                # URL as a link that opens in a new tab
                if 'url' in article and article['url']:
                    url_html = f"<div class='article-url'><a href='{article['url']}' target='_blank'>{article['url']}</a></div>"
                    st.markdown(url_html, unsafe_allow_html=True)

                # Display analysis information if available
                if 'analysis' in article:
                    analysis = article['analysis']
                    expander_title = f"Show Analysis from {analysis['analysis_date']}" if 'analysis_date' in analysis else "Show Analysis"
                    
                    with st.expander(expander_title):
                        # Display analysis information in a clean format
                        if 'analysis_confidence' in analysis:
                            st.markdown(f"<div class='analysis-item'><strong class='analysis-label'>Confidence:</strong> {analysis['analysis_confidence']}</div>", unsafe_allow_html=True)

                        if 'original_confidence' in analysis:
                            st.markdown(f"<div class='analysis-item'><strong class='analysis-label'>Original Confidence:</strong> {analysis['original_confidence']}</div>", unsafe_allow_html=True)                        

                        if 'analysis_explanation' in analysis:
                            st.markdown(f"<div class='analysis-item'><strong class='analysis-label'>Explanation:</strong> {analysis['analysis_explanation']}</div>", unsafe_allow_html=True)
                        
                        if 'analysis_company' in analysis and analysis['analysis_company']:
                            st.markdown(f"<div class='analysis-item'><strong class='analysis-label'>Company:</strong> {analysis['analysis_company']}</div>", unsafe_allow_html=True)
                        
                        if 'analysis_location' in analysis and analysis['analysis_location']:
                            st.markdown(f"<div class='analysis-item'><strong class='analysis-label'>Location:</strong> {analysis['analysis_location']}</div>", unsafe_allow_html=True)
                        
                        if 'analysis_contact' in analysis and analysis['analysis_contact']:
                            st.markdown(f"<div class='analysis-item'><strong class='analysis-label'>Contact:</strong> {analysis['analysis_contact']}</div>", unsafe_allow_html=True)
                        
                        if 'analysis_summary' in analysis and analysis['analysis_summary']:
                            st.markdown(f"<div class='analysis-item'><strong class='analysis-label'>Project Summary:</strong> {analysis['analysis_summary']}</div>", unsafe_allow_html=True)

            with cols[1]:
                # Mine button
                if st.button("Mine", key=f"mine_{article_id}", type="primary", use_container_width=True):
                    st.session_state.selected_mining_article_index = idx
                    # Use rerun to update the UI with the selected article
                    st.rerun()
                
                # Remove button
                if st.button("Remove", key=f"remove_{article_id}", type="secondary", use_container_width=True):
                    # Call the remove_article function
                    if remove_article(article_id, KEPT_ARTICLES_FILE):
                        st.success(f"Article '{article['title']}' removed successfully.")
                        # Clear the cache to force data reload
                        st.cache_data.clear()
                        # Reload the page to reflect the changes
                        st.rerun()
                    else:
                        st.error("Failed to remove the article.")

            # Much thinner separator line using the CSS class
            st.markdown("<hr class='article-separator'>", unsafe_allow_html=True)
        else:
            st.info("No articles found matching your filters.")
else:
    st.info("No articles found matching your filters.")

# Footer
st.markdown("**Next Step:** After mining valuable information, proceed to the Collecting stage.")