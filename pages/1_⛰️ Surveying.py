import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import load_json_file, save_json_file, find_articles_chainstoreage, review_articles, get_articles_df

# Initialize session state variables
if 'process_started' not in st.session_state:
    st.session_state.process_started = False
if 'process_complete' not in st.session_state:
    st.session_state.process_complete = False
if 'loaded_articles_count' not in st.session_state:
    st.session_state.loaded_articles_count = 0

# Define callback functions
def start_processing():
    st.session_state.process_started = True
    
def reset_processing():
    st.session_state.process_started = False
    st.session_state.process_complete = False
    st.rerun()

# Page configuration
st.set_page_config(
    page_title="prospectorAIDE - Surveying",
    page_icon="⛰️",
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
        st.title("⛰️ Surveying", anchor=False)
    
    with col2:
        # Company logo
        if os.path.exists("assets/CtiPath-logo.png"):
            st.image("assets/CtiPath-logo.png", width=150)

st.markdown("Gather and initial review of potential prospects.")

# Constants
PROSPECTS_FILE = "data/prospects-new.json"
START_URL = 'https://chainstoreage.com/news'

# Calculate yesterday's date
yesterday = datetime.now() - timedelta(days=1)
if 'default_cutoff_date' not in st.session_state:
    st.default_cutoff_date = yesterday.date()  

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
    st.warning(f"No prospects data found. Please Load/Review Prospects, or check that the file exists and contains valid data.")
else:
    # Display statistics
    st.subheader("📊 Surveying Statistics", anchor=False)
    col1, col2, col3, col4 = st.columns(4)

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

# Convert to DataFrame
df = get_articles_df(articles)

# Single column declaration
col1, col2 = st.columns(2)

with col2:
    st.markdown(" ")

with col1:
    # Date input field for Cutoff Date
    selected_cutoff_date = st.date_input(
        "Cutoff Date (articles before this date will not be selected)",
        value=st.default_cutoff_date,
        format="MM/DD/YYYY",
        disabled=st.session_state.process_started  # Disable during processing
    )
    # Convert the selected date to datetime at midnight
    cutoff_datetime = datetime.combine(selected_cutoff_date, datetime.min.time())

    st.markdown(" ")
    
    # Only show the button if not currently processing
    if not st.session_state.process_started:
        st.button("Load/Review Prospects", type="primary", use_container_width=True, 
                on_click=start_processing)  # Use callback instead of if condition

# Processing logic in a separate section
if st.session_state.process_started and not st.session_state.process_complete:
    # Create a container for progress indicators
    progress_container = st.container()
    
    with progress_container:
        with st.spinner("Loading prospects from ChainStoreAge..."):
            loaded_articles = find_articles_chainstoreage(START_URL, cutoff_datetime)
        
        with st.spinner("Reviewing new prospects..."):
            reviewed_articles = review_articles(loaded_articles)

        with st.spinner("Saving prospects to file..."):
            # Save back to file
            save_json_file(reviewed_articles, PROSPECTS_FILE)
            # Store count for success message
            st.session_state.loaded_articles_count = len(loaded_articles)
            # Mark as complete
            st.session_state.process_complete = True
            # Clear cache to reload data
            st.cache_data.clear()
    
    # Force a rerun to refresh the page and show the success message
    st.rerun()
    
# Show success message after processing is complete
if st.session_state.process_complete:
    #st.success(f"Successfully loaded/reviewed {st.session_state.loaded_articles_count} articles.")
    # Add a button to reset the process state
    reset_processing()

# Filtering and sorting options
st.subheader("Filter and Sort Prospects", anchor=False)
col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

with col1:
    # Filter by company
    if 'company' in df.columns and not df.empty:
        companies = ['All'] + sorted(df['company'].unique().tolist())
        selected_company = st.selectbox("Company", companies)
    else:
        selected_company = "All"

with col2:
    # Filter by confidence score
    min_confidence = st.slider("Minimum Confidence", 0, 100, 0)

with col3:
    # Filter by date
    if 'date' in df.columns and not df.empty:
        date_options = ['All', 'Today', 'Yesterday', 'Last 7 days']
        date_filter = st.selectbox("Date", date_options)
    else:
        date_filter = "All"

with col4:
    # Sorting options
    sort_options = ['Date (newest first)', 'Date (oldest first)', 
                   'Confidence (highest first)', 'Confidence (lowest first)']
    sort_selection = st.selectbox("Sort By", sort_options)

# Apply filters
if not df.empty:
    filtered_df = df.copy()
    
    # Company filter
    if selected_company != "All" and 'company' in df.columns:
        filtered_df = filtered_df[filtered_df['company'] == selected_company]
    
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
else:
    filtered_df = pd.DataFrame()

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
                    metadata_parts.append(f"<strong>Confidence: {article['confidence']}%</strong>")
                
                # Date
                if 'date' in article:
                    formatted_date = article['date'].split('T')[0] if 'T' in article['date'] else article['date']
                    metadata_parts.append(f"Date: {formatted_date}")
                
                # Company
                if 'company' in article and article['company']:
                    metadata_parts.append(f"Company: {article['company']}")
                
                # Location
                if 'location' in article and article['location']:
                    metadata_parts.append(f"Location: {article['location']}")
                
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

            # Much thinner separator line using the CSS class
            st.markdown("<hr class='article-separator'>", unsafe_allow_html=True)
        else:
            st.info("No articles found matching your filters.")

# Footer
st.markdown("**Next Step:** After loading prospects, proceed to the Prospecting step to analyze them.")