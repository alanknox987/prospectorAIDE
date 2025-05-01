import streamlit as st
import json
import pandas as pd
import os
import time
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="prospectorAIDE - Article Confidence Review",
    page_icon="assets/pospectorAIDE-icon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load external CSS
def load_css(css_file):
    with open(css_file, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Load CSS
load_css("styles.css")

# Function to get confidence class based on confidence score
def get_confidence_class(confidence):
    if confidence >= 70:
        return "confidence-high"
    elif confidence >= 40:
        return "confidence-medium"
    elif confidence > 0:
        return "confidence-low"
    else:
        return "confidence-none"

# Function to analyze article
def analyze_article(article):
    # Display a progress indicator
    progress_placeholder = st.empty()
    progress_bar = progress_placeholder.progress(0)
    
    # Simulate backend processing with progress updates
    for i in range(101):
        # Update progress bar
        progress_bar.progress(i)
        if i < 100:
            time.sleep(0.01)  # Simulate processing time
    
    # In a real implementation, this would call your backend service
    # For example: response = requests.post('your-backend-url/analyze', json=article)
    new_excerpt = f"{article["excerpt"]} - AI analysis complete"
    # Simulate a successful analysis with updated data
    # In reality, this would be the response from your backend
    analysis_result = {
        "confidence": min(article["confidence"] + 15, 100),  # Increase confidence (max 100)
        "company": article["company"] if article["company"] else "Detected Company",
        "location": article["location"] if article["location"] else "Detected Location",
        "excerpt": new_excerpt
    }
    
    # Update the article with analysis results
    for key, value in analysis_result.items():
        article[key] = value
    
    # Update the article in the session state data
    for i, art in enumerate(st.session_state.data):
        if art["articleID"] == article["articleID"]:
            st.session_state.data[i] = article
            break
    
    # Clean up the progress bar
    progress_placeholder.empty()
    
    return True

# Function to load data
@st.cache_data
def load_data():
    try:
        with open('article-confidence.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        st.error("File 'article-confidence.json' not found.")
        return []

# Function to save data
def save_data(data):
    with open('article-confidence.json', 'w') as file:
        json.dump(data, file, indent=2)
    #st.success("Complete!")
    st.session_state.data = data
    return data

# Initialize session state variables
if 'data' not in st.session_state:
    st.session_state.data = load_data()
if 'filter_confidence' not in st.session_state:
    st.session_state.filter_confidence = "All"
if 'search_term' not in st.session_state:
    st.session_state.search_term = ""
if 'sort_by' not in st.session_state:
    st.session_state.sort_by = "confidence"
if 'sort_order' not in st.session_state:
    st.session_state.sort_order = "descending"
if 'analyzing' not in st.session_state:
    st.session_state.analyzing = False
if 'last_analyzed_id' not in st.session_state:
    st.session_state.last_analyzed_id = None

# Main application title
st.markdown("""
        <style>
            .block-container {
                    padding-top: 0.75rem;
                    padding-bottom: 0rem;
                    padding-left: 2rem;
                    padding-right: 2rem;
                }
        </style>
        """, unsafe_allow_html=True)
st.image("assets/prospectorAIDE-logo.png", width=300)
st.markdown('<div class="title">Article Confidence Review Tool</div>', unsafe_allow_html=True)

# Sidebar for filters and controls
with st.sidebar:
    st.header("Filters and Controls")
    
    # Search box
    st.session_state.search_term = st.text_input("Search articles", value=st.session_state.search_term)
    
    # Confidence filter
    st.session_state.filter_confidence = st.selectbox(
        "Filter by confidence",
        ["All", "High (70-100)", "Medium (40-69)", "Low (1-39)", "None (0)"],
        index=["All", "High (70-100)", "Medium (40-69)", "Low (1-39)", "None (0)"].index(st.session_state.filter_confidence)
    )
    
    # Sorting options
    st.session_state.sort_by = st.selectbox(
        "Sort by",
        ["confidence", "title", "company", "date"],
        index=["confidence", "title", "company", "date"].index(st.session_state.sort_by)
    )
    
    st.session_state.sort_order = st.selectbox(
        "Sort order",
        ["descending", "ascending"],
        index=["descending", "ascending"].index(st.session_state.sort_order)
    )
    
    # Actions
    st.subheader("Actions")
    if st.button("Save Changes"):
        save_data(st.session_state.data)
    
    if st.button("Reset Filters"):
        st.session_state.filter_confidence = "All"
        st.session_state.search_term = ""
        st.session_state.sort_by = "confidence"
        st.session_state.sort_order = "descending"
        st.rerun()

# Filter and sort data
filtered_data = st.session_state.data.copy()

# Apply search filter
if st.session_state.search_term:
    search_term = st.session_state.search_term.lower()
    filtered_data = [
        article for article in filtered_data
        if search_term in article["title"].lower() or 
           search_term in article["company"].lower() or
           search_term in article["location"].lower() or
           search_term in article["date"] or
           search_term in article["excerpt"].lower()
    ]

# Apply confidence filter
if st.session_state.filter_confidence != "All":
    if st.session_state.filter_confidence == "High (70-100)":
        filtered_data = [article for article in filtered_data if article["confidence"] >= 70]
    elif st.session_state.filter_confidence == "Medium (40-69)":
        filtered_data = [article for article in filtered_data if 40 <= article["confidence"] < 70]
    elif st.session_state.filter_confidence == "Low (1-39)":
        filtered_data = [article for article in filtered_data if 0 < article["confidence"] < 40]
    elif st.session_state.filter_confidence == "None (0)":
        filtered_data = [article for article in filtered_data if article["confidence"] == 0]

# Sort data
reverse_order = st.session_state.sort_order == "descending"
filtered_data = sorted(filtered_data, key=lambda x: x[st.session_state.sort_by] if x[st.session_state.sort_by] != "" else "zzz", reverse=reverse_order)

# Display filter summary
st.markdown(f"""
<div class="filter-section">
    <b>Current View:</b> {len(filtered_data)} articles 
</div>
""", unsafe_allow_html=True)

# Create a container for messages
message_container = st.container()

# Display articles
for idx, article in enumerate(filtered_data):
    confidence_class = get_confidence_class(article["confidence"])
    
    # Create a unique key for each article form
    form_key = f"article_form_{article['articleID']}"
    
    with st.form(key=form_key):
        # Display the title and excerpt (not editable)
        st.markdown(f"""
        <div class='article-card {confidence_class}'>
            <div class='article-title'>{article['title']}</div>
            <div class='article-excerpt'>{article['excerpt']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Row for company, location, confidence
        col1, col2, col3, col4, col5, btn_col = st.columns([2, 2, 2, 2, 1, 2], vertical_alignment="center")
        
        with col1:
            article["company"] = st.text_input("Company", article["company"], key=f"company_{idx}")
        
        with col2:
            article["location"] = st.text_input("Location", article["location"], key=f"location_{idx}")
        
        with col3:
            article["date"] = st.text_input("Date", article["date"], key=f"date_{idx}")
        
        with col4:
            article["confidence"] = st.number_input("Confidence", 0, 100, int(article["confidence"]), key=f"confidence_{idx}")
        
        with btn_col:
            st.write("")
            st.write("")
            
            analyze_button = st.form_submit_button("Analyze")
            
            if analyze_button:
                # Set the article as being analyzed and store its ID
                st.session_state.analyzing = True
                st.session_state.last_analyzed_id = article['articleID']
                
                # Perform the analysis (this will update the article in st.session_state.data)
                analyze_article(article)
                
                # Save the updated data to the JSON file
                save_data(st.session_state.data)
        
        st.markdown(f"""
            <a href="{article['url']}" target="_blank" class="url-link">{article['url']}</a>
            """, unsafe_allow_html=True)
    
    # Display a success message for the article that was just analyzed
    if st.session_state.last_analyzed_id == article['articleID'] and st.session_state.analyzing:
        with message_container:
#            st.success(f"Analysis completed for article: {article['title']}")
            # Reset the flags after showing the message
            st.session_state.analyzing = False
            st.session_state.last_analyzed_id = None

# Add a footer
st.markdown("""
---
""")