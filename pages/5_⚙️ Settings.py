import streamlit as st
import pandas as pd
import os
import sys
import json
from datetime import datetime

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import load_json_file, save_json_file

# Page configuration
st.set_page_config(
    page_title="prospectorAIDE - Settings",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load external CSS file
def load_css(css_file):
    if os.path.exists(css_file):
        with open(css_file, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"CSS file not found: {css_file}")

# Load the CSS
load_css("styles.css")

# Add custom CSS for our components
st.markdown("""
<style>
    .custom-criteria-container {
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 20px;
    }
    .criteria-header {
        display: flex;
        padding-bottom: 8px;
        margin-bottom: 10px;
        border-bottom: 1px solid #eee;
        font-weight: bold;
    }
    /* Make checkbox labels visually hidden but still accessible to screen readers */
    .visually-hidden {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border-width: 0;
    }
</style>
""", unsafe_allow_html=True)

# Create a container for logos in the header
header = st.container()
with header:
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # App title
        st.title("⚙️ Settings", anchor=False)
    
    with col2:
        # Company logo
        if os.path.exists("assets/CtiPath-logo.png"):
            st.image("assets/CtiPath-logo.png", width=150)
        
    # Add app logo if exists
    if os.path.exists("assets/prospectorAIDE-logo.png"):
        st.logo("assets/prospectorAIDE-logo.png", size='large')

st.markdown("Configure application settings and criteria for prospect evaluation.")

# Constants for file paths
CRITERIA_FILE = "data/criteria.json"
DEFAULT_CRITERIA_FILE = "data/default_criteria.json"

# Check for reset success/error messages from previous run
if 'reset_success' in st.session_state and st.session_state.reset_success:
    st.success("Criteria reset to defaults successfully!")
    st.session_state.reset_success = False  # Clear the flag
elif 'reset_error' in st.session_state and st.session_state.reset_error:
    st.error(f"Error resetting criteria: {st.session_state.reset_error}")
    st.session_state.reset_error = None  # Clear the error

# Function to reset criteria to defaults
def reset_criteria():
    try:
        default_criteria = load_json_file(DEFAULT_CRITERIA_FILE)
        save_json_file(default_criteria, CRITERIA_FILE)
        st.session_state.criteria = default_criteria
        st.session_state.reset_success = True  # Flag to display success message on next rerun
    except Exception as e:
        st.session_state.reset_error = str(e)  # Store error for display on next rerun

# Function to save criteria changes
def save_criteria_changes():
    save_json_file(st.session_state.criteria, CRITERIA_FILE)
    st.success("Criteria saved successfully!")

# Initialize session state for criteria management
if 'criteria' not in st.session_state:
    try:
        st.session_state.criteria = load_json_file(CRITERIA_FILE)
    except Exception as e:
        st.error(f"Error loading criteria: {e}")
        st.session_state.criteria = []

# Display criteria section
st.subheader("Prospect Evaluation Criteria", anchor=False)
st.markdown("""
The following criteria are used to evaluate and score prospects. 
Compatibility scores (0-100) are assigned based on how well a prospect matches these criteria.
""")

# Create a container for the criteria
criteria_container = st.container()

with criteria_container:
    # Add header for the criteria list
    header_col1, header_col2 = st.columns([1, 15])
    with header_col1:
        st.markdown("**Select**")
    with header_col2:
        st.markdown("**Criterion**")
    
    # Create a unique key prefix for the session state
    key_prefix = "criteria_"
    
    # Track selected criteria
    selected_indices = []
    
    # Display each criterion with a checkbox and text input
    for i, criterion in enumerate(st.session_state.criteria):
        # Create unique keys for this criterion
        select_key = f"{key_prefix}select_{i}"
        text_key = f"{key_prefix}text_{i}"
        
        # Create columns for checkbox and text input
        col1, col2 = st.columns([1, 15])
        
        # Checkbox for selection with accessible label
        with col1:
            selected = st.checkbox(
                f"Select criterion {i+1}", 
                key=select_key,
                label_visibility="collapsed"  # Visually hide label but keep it for screen readers
            )
            if selected:
                selected_indices.append(i)
        
        # Define a callback function to update the criterion when the text input changes
        def update_criterion(i=i):
            if text_key in st.session_state:
                new_text = st.session_state[text_key]
                if new_text != st.session_state.criteria[i]["criteria"]:
                    st.session_state.criteria[i]["criteria"] = new_text
                    # Save changes to file automatically
                    save_json_file(st.session_state.criteria, CRITERIA_FILE)
        
        # Text input for criterion with accessible label
        with col2:
            criterion_text = st.text_input(
                f"Criterion {i+1} text", 
                value=criterion["criteria"], 
                key=text_key,
                on_change=update_criterion,
                label_visibility="collapsed"  # Visually hide label but keep it for screen readers
            )

    # Display a visual separator
    st.markdown("---")

    # Add and Delete buttons side by side
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        # Add new criterion button
        if st.button("Add Criterion", type="primary", use_container_width=True):
            # Check if last row is already blank
            last_is_blank = False
            if st.session_state.criteria:
                if not st.session_state.criteria[-1]["criteria"].strip():
                    last_is_blank = True
            
            # Only add a new blank row if the last one isn't already blank
            if not last_is_blank:
                st.session_state.criteria.append({"criteria": ""})
                save_json_file(st.session_state.criteria, CRITERIA_FILE)
                st.rerun()  # This is fine outside a callback
    
    with col2:
        # Delete selected criteria button
        if st.button("Delete Selected", type="secondary", use_container_width=True):
            if selected_indices:
                # Remove from highest index to lowest to avoid shifting problems
                for index in sorted(selected_indices, reverse=True):
                    if index < len(st.session_state.criteria):
                        st.session_state.criteria.pop(index)
                
                # Save the updated criteria
                save_json_file(st.session_state.criteria, CRITERIA_FILE)
                st.rerun()  # This is fine outside a callback
            else:
                st.warning("No criteria selected for deletion")
    
    with col3:
        st.markdown(" ")

reset_col1, reset_col2 = st.columns([1, 3])
with reset_col1:
    # Reset button with on_click instead of direct action
    st.button(
        "Reset to Defaults",
        key="reset_button",
        on_click=reset_criteria,
        type="secondary",
        use_container_width=True
    )
    # Add a separate rerun button that appears after Reset is clicked
    if 'reset_success' in st.session_state and st.session_state.reset_success:
        st.button("Refresh Page", on_click=st.rerun, use_container_width=True)

# Footer
st.markdown("**Note:** Changes to criteria will affect how new prospects are evaluated in the system.")