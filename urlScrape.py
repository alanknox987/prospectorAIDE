import requests
from bs4 import BeautifulSoup

# Constants - modify these as needed
START_URL = 'https://chainstoreage.com/news?page=6'

def fetch_and_parse(url):
    """
    Fetches content from a URL, parses it using BeautifulSoup,
    and optionally extracts structured data.
    
    Args:
        url (str): The URL to fetch content from.
        parser (str): The parser to use. Default is 'html.parser'.
        extract_data (bool): Whether to extract structured data from the content.
        
    Returns:
        If extract_data is True:
            dict: A dictionary containing:
                - soup: The BeautifulSoup object
                - articles: List of article dictionaries
                - pagination: Pagination information dictionary
        If extract_data is False:
            BeautifulSoup: The BeautifulSoup object containing the parsed HTML.
    """
    # Set a user agent to mimic a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Fetch the content from the URL
    response = requests.get(url, headers=headers, timeout=10)
        
    # Parse the content with BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    
    return soup

print(fetch_and_parse(START_URL))