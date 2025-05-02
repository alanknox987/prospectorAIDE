import streamlit as st
import os
import sys

# Add pages directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "pages"))

# Set page config
st.set_page_config(
    page_title="prospectorAIDE",
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
        st.title("Lead Prospecting Tool", anchor=False)
    
    with col2:
        # Company logo
        if os.path.exists("assets/CtiPath-logo.png"):
            st.image("assets/CtiPath-logo.png", width=150)

# Main page content
st.markdown("""
This application helps sales associates process articles through a 4-step workflow:

1. **Surveying**: Load potential prospects from various sources
2. **Prospecting**: Review prospects and analyze their potential
3. **Mining**: Augment prospects with valuable information
4. **Collecting**: Finalize and organize information for prospects to contact

### How to use this application:
- Navigate between the workflow steps using the sidebar menu
- Each step offers specific tools to help process the prospects
- Prospects saved in one step will be available in the next step

Click on **Surveying** in the sidebar to begin the workflow.
""")

# Display some stats if available
try:
    import json
    import os.path
    
    # Function to count articles in a file
    def count_articles(file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
                return len(data)
        return 0
    
    # Get counts
    all_articles = count_articles('article-confidence.json')
    kept_articles = count_articles('articles-kept.json')
    
    # Show stats
    st.subheader("Statistics")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Articles", all_articles)
    
    with col2:
        st.metric("Kept Articles", kept_articles)
        
except Exception as e:
    st.info("Statistics will be available once you start processing articles.")