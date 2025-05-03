import streamlit as st
import pandas as pd
import os
import sys

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import load_json_file, save_json_file, analyze_article, analyze_all, keep_article, keep_all_articles, get_articles_df

# Initialize session state variables
if 'analyze_process_started' not in st.session_state:
    st.session_state.analyze_process_started = False
if 'analyze_process_complete' not in st.session_state:
    st.session_state.analyze_process_complete = False
if 'keep_process_started' not in st.session_state:
    st.session_state.keep_process_started = False
if 'keep_process_complete' not in st.session_state:
    st.session_state.keep_process_complete = False
if 'analyzed_articles_count' not in st.session_state:
    st.session_state.analyzed_articles_count = 0
if 'kept_articles_count' not in st.session_state:
    st.session_state.kept_articles_count = 0

# Define callback functions
def start_analyze_processing():
    st.session_state.analyze_process_started = True
    
def start_keep_processing():
    st.session_state.keep_process_started = True
    
def reset_processing():
    st.session_state.analyze_process_started = False
    st.session_state.analyze_process_complete = False
    st.session_state.keep_process_started = False
    st.session_state.keep_process_complete = False
    st.rerun()

# Page configuration
st.set_page_config(
    page_title="prospectorAIDE - Prospecting",
    page_icon="🔍",
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
        st.title("🔍 Prospecting")
    
    with col2:
        # Company logo
        if os.path.exists("assets/CtiPath-logo.png"):
            st.image("assets/CtiPath-logo.png", width=150)

st.markdown("Review and analyze potential articles for your sales pipeline.")

# File paths
PROSPECTS_FILE = "data/prospects-new.json"
KEPT_PROSPECTS_FILE = "data/prospects-kept.json"

# Load data
@st.cache_data(ttl=10)  # Cache with a short time-to-live to allow refreshing
def load_data():
    try:
        articles = load_json_file(PROSPECTS_FILE)
        # If articles is a list of dictionaries, convert to list and extract 'articleID'
        if articles and isinstance(articles, list) and 'articleID' in articles[0]:
            # Make sure each article has an index based on its position
            for i, article in enumerate(articles):
                article['index'] = i
            return articles
        return []
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return []

articles = load_data()

# Display message if no articles loaded
if not articles:
    st.warning(f"No prosepcts found to analyze found. Please Survey prospects first, or check that the file exists and contains valid data.")
else:
    # Display statistics
    st.subheader("📊 Prospecting Statistics", anchor=False)
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Prospects", len(articles))

    with col2:
        # Count articles with confidence > 40
        confidence_40_count = sum(1 for a in articles if a.get('confidence', 0) >= 40 and a.get('confidence', 0) < 60)
        st.metric("🟡 Confidence >40", f"{confidence_40_count}/{len(articles)}")

    with col3:
        # Count articles with confidence > 60
        confidence_60_count = sum(1 for a in articles if a.get('confidence', 0) >= 60 and a.get('confidence', 0) < 80)
        st.metric("🔵 Confidence >60", f"{confidence_60_count}/{len(articles)}")

    with col4:
        # Count articles with confidence > 80
        confidence_80_count = sum(1 for a in articles if a.get('confidence', 0) >= 80)
        st.metric("🟢 Confidence >80", f"{confidence_80_count}/{len(articles)}")

    with col5:
        # Count analyzed articles based on presence of 'analysis' key
        analyzed_count = sum(1 for a in articles if 'analysis' in a)
        st.metric("Analyzed Prospects", f"{analyzed_count}/{len(articles)}")

# Convert to DataFrame
df = get_articles_df(articles)

# Filtering and sorting options
st.subheader("Filter and Sort Prospects", anchor=False)
col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

with col1:
    # Filter by confidence score (moved to first position)
    min_confidence = st.slider("Minimum Confidence", 0, 100, 0)

with col2:
    # Filter by date (moved to second position)
    if 'date' in df.columns and not df.empty:
        date_options = ['All', 'Today', 'Yesterday', 'Last 7 days']
        date_filter = st.selectbox("Date", date_options)
    else:
        date_filter = "All"

with col3:
    # Filter by company (moved to third position)
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
    # Sorting options (now in the fifth column)
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
                'analysis' in next((a for a in articles if a.get('articleID') == row.get('articleID')), {}), axis=1)]
        elif analyzed_filter == "Not Analyzed":
            # Keep only articles that don't have 'analysis' key
            filtered_df = filtered_df[filtered_df.apply(lambda row: 
                'analysis' not in next((a for a in articles if a.get('articleID') == row.get('articleID')), {}), axis=1)]
    
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

filtered_count = len(filtered_df) if not filtered_df.empty else 0

# Buttons for "Analyze All" and "Keep All"
col1, col2 = st.columns(2)

# Only show the buttons if not currently processing
if not st.session_state.analyze_process_started and not st.session_state.keep_process_started:
    with col1:
        st.button(f"Analyze All ({filtered_count})", type="primary", use_container_width=True, 
                  on_click=start_analyze_processing)

    with col2:
        st.button(f"Keep All ({filtered_count})", type="secondary", use_container_width=True, 
                  on_click=start_keep_processing)

# Processing logic for Analyze All
if st.session_state.analyze_process_started and not st.session_state.analyze_process_complete:
    # Create a container for progress indicators
    progress_container = st.container()
    
    with progress_container:
        with st.spinner("Analyzing all filtered articles..."):
            # Get the list of article IDs from the filtered DataFrame
            filtered_article_ids = filtered_df['articleID'].tolist() if not filtered_df.empty else []
            
            if filtered_article_ids:
                # Only analyze articles that match the filter
                filtered_articles = [a for a in articles if a.get('articleID') in filtered_article_ids]
                # Run analysis on filtered articles
                analyzed_articles = analyze_all(filtered_articles)
                
                # Update the main articles list with the analyzed articles
                for analyzed_article in analyzed_articles:
                    for i, article in enumerate(articles):
                        if article.get('articleID') == analyzed_article.get('articleID'):
                            articles[i] = analyzed_article
                            break
                
                # Save back to file
                save_json_file(articles, PROSPECTS_FILE)
                # Store count for success message
                st.session_state.analyzed_articles_count = len(analyzed_articles)
            else:
                st.session_state.analyzed_articles_count = 0
            
            # Mark as complete
            st.session_state.analyze_process_complete = True
            # Clear cache to reload data
            st.cache_data.clear()
    
    # Force a rerun to refresh the page and show the success message
    st.rerun()

# Processing logic for Keep All
if st.session_state.keep_process_started and not st.session_state.keep_process_complete:
    # Create a container for progress indicators
    progress_container = st.container()
    
    with progress_container:
        with st.spinner("Keeping all articles..."):
            # Keep all articles

            # Get the list of article IDs from the filtered DataFrame
            filtered_article_ids = filtered_df['articleID'].tolist() if not filtered_df.empty else []
            
            if filtered_article_ids:
                # Only analyze articles that match the filter
                filtered_articles = [a for a in articles if a.get('articleID') in filtered_article_ids]
                # Run analysis on filtered articles
                kept_count = keep_all_articles(filtered_articles, KEPT_PROSPECTS_FILE)
                # Store count for success message
                st.session_state.kept_articles_count = kept_count
                # Mark as complete
                st.session_state.keep_process_complete = True
    
    # Force a rerun to refresh the page and show the success message
    st.rerun()

# Show success message after analyze processing is complete
if st.session_state.analyze_process_complete:
    if st.session_state.analyzed_articles_count > 0:
        st.success(f"Successfully analyzed {st.session_state.analyzed_articles_count} articles.")
    else:
        st.warning("No articles match your current filters.")
    # Add a button to reset the process state
    reset_processing()

# Show success message after keep processing is complete
if st.session_state.keep_process_complete:
    if st.session_state.kept_articles_count > 0:
        st.success(f"Successfully kept {st.session_state.kept_articles_count} articles.")
    else:
        st.warning("No articles were kept.")
    # Add a button to reset the process state
    reset_processing()

# Display data
if not filtered_df.empty:
    st.markdown(f"<div class='article-header'><strong>Prospect List</strong> ({len(filtered_df)} matching)</div>", unsafe_allow_html=True)

    # Create a compact list of articles with minimal spacing
    for idx, row in filtered_df.iterrows():
        article_id = row.get('articleID')
        article = next((a for a in articles if a.get('articleID') == article_id), None)
        
        if article:
            # Use a 2-column layout: Article Content | Action Buttons
            cols = st.columns([6, 1])
            
            with cols[0]:
                # Title
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
                # Stack buttons vertically to make them wider
                # Only show buttons if not in the middle of a process
                if not st.session_state.analyze_process_started and not st.session_state.keep_process_started:
                    if 'analysis' in article:
                        analyze_button_text = "Re-Analyze"
                    else:
                        analyze_button_text = "Analyze"
                    analyze_button = st.button(analyze_button_text, key=f"analyze_{article_id}", type="primary", use_container_width=True)
                    keep_button = st.button("Keep", key=f"keep_{article_id}", type="secondary", use_container_width=True)
                    
                    # Handle button clicks
                    if analyze_button:
                        with st.spinner("Analyzing..."):
                            # Analyze the article
                            analyzed_article = analyze_article(article)
                            
                            # Update the article in the list
                            for i, a in enumerate(articles):
                                if a.get('articleID') == analyzed_article.get('articleID'):
                                    articles[i] = analyzed_article
                                    break
                            
                            # Save back to file
                            save_json_file(articles, PROSPECTS_FILE)
                            
                            # Show success message
                            st.success(f"Article analyzed!")
                            
                            # Clear cache to reload data
                            st.cache_data.clear()
                            
                            # Rerun to update UI
                            st.rerun()
                    
                    if keep_button:
                        with st.spinner("Keeping..."):
                            if keep_article(article, KEPT_PROSPECTS_FILE):
                                st.success(f"Article kept!")
                            else:
                                st.error(f"Failed to keep article.")

            # Much thinner separator line using the CSS class
            st.markdown("<hr class='article-separator'>", unsafe_allow_html=True)
        else:
            st.info("No articles found matching your filters.")

# Footer
st.markdown("**Next Step:** After identifying potential articles, proceed to Mining stage.")