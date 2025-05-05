import json
import os
from datetime import datetime
import time
import pandas as pd
import boto3
import streamlit as st
import requests
import uuid
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def load_json_file(file_path):
    """Load data from a JSON file, return empty list if file doesn't exist or is empty."""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()
            if not content:  # File is empty
                return []
            try:
                data = json.loads(content)
                # If loading from the main data file, make sure we have indexes
                if file_path.endswith('prospects-new.json'):
                    # Make sure each article has an index for proper dataframe creation
                    for i, article in enumerate(data):
                        article['index_pos'] = i
                return data
            except json.JSONDecodeError:
                print(f"JSON decode error in {file_path}, returning empty list")
                return []
    return []

def save_json_file(data, file_path):
    """Save data to a JSON file."""
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def log_debug_info(message, data=None, log_file="debug_log.txt"):
    """
    Log debug information to a file for troubleshooting.
    
    Args:
        message (str): Debug message
        data (any, optional): Data to log with the message
        log_file (str, optional): Path to log file
    """
    #try:
    #    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #    with open(log_file, "a") as f:
    #        f.write(f"\n[{timestamp}] {message}\n")
    #        if data is not None:
    #            if isinstance(data, (dict, list)):
    #                f.write(json.dumps(data, indent=2))
    #            else:
    #                f.write(str(data))
    #            f.write("\n")
    #        f.write("-" * 80 + "\n")
    #except Exception as e:
    #    print(f"Error writing to debug log: {e}")
    return

def extract_url_content(url, article_title=None):
    """
    Advanced extraction of article content from a URL.
    
    Args:
        url (str): The URL to extract content from
        article_title (str, optional): The title of the article to help identify the correct content
        
    Returns:
        str: The extracted article text
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Get the domain for site-specific handling
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Fetch the page
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')

#        print("---")
#        print(soup)
#        print("---")

        # Remove non-content elements
        for tag in soup(['script', 'style', 'header', 'nav', 'footer', 'aside', 'form']):
            tag.decompose()
            
        # Site-specific handlers
        if 'chainstoreage.com' in domain:
            return extract_chainstoreage(soup, article_title)
        # Add more site-specific handlers as needed
            
        # General extraction strategies
        
        # 1. Try to find the article by its title
        if article_title:
            article_content = find_article_by_title(soup, article_title)
            if article_content:
                return article_content
        
        # 2. Look for article or main content containers
        article_content = find_main_content(soup)
        if article_content:
            return article_content
            
        # 3. Use text density analysis as a last resort
        return extract_by_text_density(soup)
        
    except Exception as e:
        log_debug_info("URL extraction error", f"Error extracting content from {url}: {str(e)}")
        return f"Error extracting content: {str(e)}"

def extract_chainstoreage(soup, article_title=None):
    """Extract content from Chain Store Age website
    
    If there are multiple news-brief articles on a page, this function will extract only
    the first article. For standalone article pages, it extracts the main article content.
    
    Args:
        soup: BeautifulSoup object of the page
        article_title: Optional title to help identify the article
        
    Returns:
        Cleaned text content of the article
    """
    
    # APPROACH 1: For pages with multiple "news-brief" sections, always extract the first one
    news_briefs = soup.find_all('section', class_='news-brief')
    if news_briefs:
        # Get the first news brief section
        first_section = news_briefs[0]
        body_div = first_section.find('div', class_='body')
        if body_div:
            # Find the text div inside the body
            text_div = body_div.find('div', class_='text')
            if text_div:
                return clean_text(text_div.get_text(separator=' ', strip=True))
            return clean_text(body_div.get_text(separator=' ', strip=True))
    
    # APPROACH 2: For single-article pages, extract from schema.org metadata
    schema_article = soup.find('meta', attrs={'name': 'articleBody'})
    if schema_article and schema_article.get('content'):
        return clean_text(schema_article.get('content'))
    
    # APPROACH 3: Look for main article content in the article element
    article = soup.find('article')
    if article:
        # Look for article content in eiq-paragraph divs
        eiq_paragraphs = article.find_all('div', class_='eiq-paragraph')
        if eiq_paragraphs:
            content = []
            for para in eiq_paragraphs:
                # Extract content from wysiwyg divs if present
                wysiwyg = para.find(class_='wysiwyg')
                if wysiwyg:
                    content.append(wysiwyg.get_text(separator=' ', strip=True))
                # Otherwise get the full paragraph content
                elif not para.find(class_='ad-slot') and not para.find('nav'):
                    content.append(para.get_text(separator=' ', strip=True))
            
            if content:
                return clean_text(' '.join(content))
        
        # If no eiq-paragraphs or they were empty, try the article-body class
        article_body = article.find(class_='article-body')
        if article_body:
            return clean_text(article_body.get_text(separator=' ', strip=True))
        
        # If no specific article-body, get all the article content
        return clean_text(article.get_text(separator=' ', strip=True))
    
    # APPROACH 4: Look for content in the main element
    main_content = soup.find('main')
    if main_content:
        # Try to find eiq-paragraph divs in main content
        eiq_paragraphs = main_content.find_all('div', class_='eiq-paragraph')
        if eiq_paragraphs:
            content = []
            for para in eiq_paragraphs:
                # Only include text content, not navigation or ads
                if not para.find('nav') and not para.find(class_='ad-slot'):
                    wysiwyg = para.find(class_='wysiwyg')
                    if wysiwyg:
                        content.append(wysiwyg.get_text(separator=' ', strip=True))
                    else:
                        content.append(para.get_text(separator=' ', strip=True))
            return clean_text(' '.join(content))
    
    # APPROACH 5: Find the article content div
    content_div = soup.find('div', class_='content')
    if content_div:
        # Try to find paragraph elements
        paragraphs = content_div.find_all('p')
        if paragraphs:
            content = []
            for p in paragraphs:
                content.append(p.get_text(separator=' ', strip=True))
            return clean_text(' '.join(content))
        
        # If no paragraphs found, use the whole content div
        return clean_text(content_div.get_text(separator=' ', strip=True))
    
    # If nothing else worked, return cleaned body text
    return clean_text(soup.body.get_text(separator=' ', strip=True))

def find_article_by_title(soup, article_title):
    """Find article content by matching title"""
    if not article_title:
        return None
        
    # Clean the article title for comparison
    clean_title = article_title.lower().strip()
    
    # Look for headers that contain the article title
    headers = soup.find_all(['h1', 'h2', 'h3'])
    for header in headers:
        header_text = header.get_text().lower().strip()
        
        # Check if the header text matches or contains the article title
        if clean_title in header_text or header_text in clean_title:
            # Found a matching header, try to find the article container
            current = header
            for _ in range(4):  # Try up to 4 levels up
                current = current.parent
                if not current:
                    break
                    
                # Check if this is an article container
                if current.name in ['article', 'div', 'section'] and (
                    'article' in current.get('class', []) or 
                    'content' in current.get('class', []) or
                    'post' in current.get('class', [])
                ):
                    return clean_text(current.get_text(separator=' ', strip=True))
            
            # If we didn't find an article container, collect paragraphs after the header
            content = []
            next_element = header.find_next(['p', 'div'])
            while next_element and next_element.name in ['p', 'div']:
                text = next_element.get_text(strip=True)
                if text and len(text) > 100:  # Only include substantial paragraphs
                    content.append(text)
                next_element = next_element.find_next_sibling(['p', 'div'])
            
            if content:
                return clean_text(' '.join(content))
    
    return None

def find_main_content(soup):
    """Find the main content container using common patterns"""
    # Try article tag first
    article = soup.find('article')
    if article:
        return clean_text(article.get_text(separator=' ', strip=True))
    
    # Look for common content container classes
    content_selectors = [
        '.article-content', '.post-content', '.entry-content', 
        '.article-body', '.story-body', '.main-content',
        '#article-content', '#post-content', '#main-content',
        'main', '[role="main"]'
    ]
    
    for selector in content_selectors:
        content = soup.select_one(selector)
        if content:
            return clean_text(content.get_text(separator=' ', strip=True))
    
    return None

def extract_by_text_density(soup):
    """Extract content by analyzing text density"""
    # Get all paragraph elements
    paragraphs = soup.find_all('p')
    
    if not paragraphs:
        return clean_text(soup.get_text(separator=' ', strip=True))
    
    # Collect substantial paragraphs (more than 100 chars)
    content_paragraphs = []
    for p in paragraphs:
        text = p.get_text(strip=True)
        if len(text) > 100:
            content_paragraphs.append(text)
    
    if content_paragraphs:
        return clean_text(' '.join(content_paragraphs))
    
    # If no substantial paragraphs found, return body text
    return clean_text(soup.body.get_text(separator=' ', strip=True))

def clean_text(text):
    """Clean extracted text"""
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove empty lines
    text = re.sub(r'\n\s*\n', '\n', text)
    
    # Trim the text
    text = text.strip()
    
    # Limit text length
    if len(text) > 10000:
        text = text[:10000] + "... [content truncated for length]"
    
    return text

def analyze_article(article):
    """
    Analyze an article and add analysis information.
    Extracts URL content, creates a prompt for Bedrock LLM, and parses the response.
    """
    # Make a copy of the article to avoid modifying the original
    analyzed_article = article.copy()
    
    # Extract content from URL if available
    url_content = ""
    if 'url' in article and article['url']:
        # Pass the article title to help with extraction
        url_content = extract_url_content(
            article['url'], 
            article_title=article.get('title', '')
        )
        # Log debug information
        log_debug_info("Article URL", article.get('url'))
        log_debug_info("Article title", article.get('title', ''))
        log_debug_info("Extracted URL content (preview)", url_content[:500] + "..." if len(url_content) > 500 else url_content)
    
#    print("---")
#    print(url_content)
#    print("---")

    # Load criteria from criteria.json
    CRITERIA_FILE = "data/criteria.json"
    try:
        existing_criteria = load_json_file(CRITERIA_FILE)
        
        # Format criteria with bullet points for the prompt
        criteria_list = "\n".join([f"* {item['criteria']}" for item in existing_criteria])
        
        # Log debug information
        log_debug_info("Existing criteria loaded", existing_criteria)
    except Exception as e:
        # If there's an error loading the criteria file, create a default list
        log_debug_info("Error loading criteria file", str(e))
        criteria_list = "* No existing criteria found"

    # Create prompt for LLM
    prompt = f"""Examine the article contents provided. Determine how well the information in the article matches the following criteria:

Criteria:
{criteria_list}

Create a criteria compatiblity score of 0-100 based on how well the information in the article matches the criteria. [analysis_compatibility]

Create a 1 sentence explanation of your compatibility score based on the criteria. [analysis_explanation]
Determine which company the article is about, if applicable. [analysis_company]
Determine the location or locations the article is about, if applicable. [analysis_location]
Determine any company contacts mentioned by the article, if applicable. [analysis_contact]

Create a brief 1-2 sentence summary of any building, opening, or remodeling projects mentioned in the article. [analysis_summary]

Output only json with the fields listed above. Return your response in JSON format only, with no additional text.

Article content:
{url_content}"""

    # Log debug information
    log_debug_info("LLM prompt", prompt[:500] + "..." if len(prompt) > 500 else prompt)
    
    try:
        # Call Bedrock LLM
        llm_response = call_bedrock_llm(prompt)
        
        # Debug log
        log_debug_info("LLM raw response", llm_response)
        
        # Check if response is empty or not valid JSON
        if not llm_response or not llm_response.strip():
            raise ValueError("Received empty response from LLM")
        
        # Try to parse the response as JSON
        try:
            analysis_data = json.loads(llm_response)
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON from the response
            # Try to find JSON content between code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                analysis_data = json.loads(json_match.group(1))
            else:
                # Try to find just a JSON object anywhere in the text
                json_match = re.search(r'(\{.*\})', llm_response, re.DOTALL)
                if json_match:
                    analysis_data = json.loads(json_match.group(1))
                else:
                    # If we still can't find valid JSON, create a simple structure
                    analysis_data = {
                        "analysis_explanation": "Could not parse LLM response as JSON.",
                        "error": "Invalid JSON format in LLM response"
                    }
        
        # Add analysis date and ID
        analysis_data['analysis_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        analysis_data['analysis_id'] = str(uuid.uuid4())
        analysis_data['original_compatibility'] = article['compatibility']
        
        # Log debug information
        log_debug_info("Parsed analysis data", analysis_data)
        
        # Add analysis data to article
        analyzed_article['analysis'] = analysis_data
        
        # Update the compatibility score based on the analysis
        if 'analysis_compatibility' in analysis_data:
            try:
                compatibility_value = int(analysis_data['analysis_compatibility'])
                analyzed_article['compatibility'] = compatibility_value
            except (ValueError, TypeError):
                # If conversion fails, keep the existing compatibility or set to 0
                if 'compatibility' not in analyzed_article:
                    analyzed_article['compatibility'] = 0
        
        # Update company and location if available from analysis
        if 'analysis_company' in analysis_data and analysis_data['analysis_company']:
            analyzed_article['company'] = analysis_data['analysis_company']
        
        if 'analysis_location' in analysis_data and analysis_data['analysis_location']:
            analyzed_article['location'] = analysis_data['analysis_location']
    
    except Exception as e:
        # Log the error
        log_debug_info("Error in analyze_article", str(e))
        
        # Add error information to the article
        analyzed_article['analysis'] = {
            'error': str(e),
            'analysis_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'analysis_id': str(uuid.uuid4())
        }
        
    return analyzed_article

def analyze_all(articles):
    """
    Analyze all articles in the list.
    """
    analyzed_articles = []
    for article in articles:
        analyzed_article = analyze_article(article)
        analyzed_articles.append(analyzed_article)
    return analyzed_articles

def get_articles_df(articles):
    """Convert articles list to a pandas DataFrame with proper types."""
    if not articles:
        return pd.DataFrame()
    
    # Create a copy of the articles to avoid modifying the original
    articles_copy = [article.copy() for article in articles]
    
    # Create the DataFrame
    df = pd.DataFrame(articles_copy)
    
    # Set articleID as index if it exists
    if 'articleID' in df.columns:
        df.set_index('articleID', inplace=True, drop=False)
    
    # Convert date strings to datetime objects
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    if 'analyze_date' in df.columns:
        df['analyze_date'] = pd.to_datetime(df['analyze_date'], errors='coerce')
    
    # Ensure compatibility is numeric
    if 'compatibility' in df.columns:
        df['compatibility'] = pd.to_numeric(df['compatibility'], errors='coerce')
        # Fill NaN values with 0
        df['compatibility'] = df['compatibility'].fillna(0)
    
    return df

def keep_article(article, kept_file):
    """
    Save the article to the kept file.
    Returns True if successful, False otherwise.
    """
    try:
        # Ensure the data directory exists
        os.makedirs(os.path.dirname(kept_file), exist_ok=True)
        
        # Load existing kept articles or initialize with empty list if file doesn't exist or is empty
        if os.path.exists(kept_file):
            with open(kept_file, 'r') as file:
                content = file.read().strip()
                if content:
                    kept_articles = json.loads(content)
                else:
                    kept_articles = []
        else:
            kept_articles = []
            
        # Check if article is already in kept articles
        article_ids = [a.get('articleID') for a in kept_articles]
        if article.get('articleID') in article_ids:
            # Article already exists, update it
            for i, kept_article in enumerate(kept_articles):
                if kept_article.get('articleID') == article.get('articleID'):
                    kept_articles[i] = article
                    break
        else:
            # Add new article
            kept_articles.append(article)
        
        # Save back to file
        with open(kept_file, 'w') as file:
            json.dump(kept_articles, file, indent=4)
        return True
    except Exception as e:
        print(f"Error keeping article: {e}")
        return False
    
def keep_all_articles(articles, kept_file):
    """
    Save all articles to the kept file.
    Returns the number of successfully kept articles.
    """
    successfully_kept = 0
    try:
        print(f"Attempting to keep {len(articles)} articles")
        # Ensure the data directory exists
        os.makedirs(os.path.dirname(kept_file), exist_ok=True)
        
        # Initialize the file with an empty list if it doesn't exist
        if not os.path.exists(kept_file):
            with open(kept_file, 'w') as f:
                f.write('[]')
                
        for article in articles:
            if keep_article(article, kept_file):
                successfully_kept += 1
            else:
                print(f"Failed to keep article: {article.get('title', 'Unknown')}")
        
        print(f"Successfully kept {successfully_kept} articles")
        return successfully_kept
    except Exception as e:
        print(f"Error in keep_all_articles: {str(e)}")
        return 0
    
def call_bedrock_llm(
    prompt: str,
    model_name: str = "us.amazon.nova-lite-v1:0",
    ) -> str:
    """
    Call Amazon Bedrock LLM with improved JSON handling.
    Ensures the prompt explicitly requests JSON output format.
    """
    # Enhance prompt to ensure JSON output
    json_prompt = prompt
    if "Output only json" not in prompt:
        json_prompt = prompt + "\n\nReturn your response in JSON format only, with no additional text."

    client = boto3.client(
        service_name="bedrock-runtime",
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY"],
        aws_secret_access_key=st.secrets["AWS_SECRET_KEY"],
        region_name=st.secrets["AWS_REGION"]
    )

    messages = [
        {"role": "user", "content": [{"text": json_prompt}]}
    ]

    try:
        model_response = client.converse(
            modelId=model_name,
            messages=messages
        )
        response_text = model_response["output"]["message"]["content"][0]["text"]
        
        # Clean up the response to extract just the JSON part
        # Try to find JSON content between code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # Try to find just a JSON object anywhere in the text
        json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # If we couldn't find JSON formatting, return the raw response
        return response_text
        
    except Exception as e:
        print(f"Error calling Bedrock LLM: {str(e)}")
        return f"{{\"error\": \"{str(e)}\"}}"

def remove_article(article_id, kept_file):
    """
    Remove an article from the kept file by its articleID.
    Returns True if successful, False otherwise.
    """
    try:
        # Load existing kept articles
        kept_articles = load_json_file(kept_file)
        
        # Find the article to remove
        original_length = len(kept_articles)
        kept_articles = [article for article in kept_articles if article.get('articleID') != article_id]
        
        # Check if any article was removed
        if len(kept_articles) < original_length:
            # Save back to file
            save_json_file(kept_articles, kept_file)
            return True
        else:
            # No article was removed
            return False
    except Exception as e:
        print(f"Error removing article: {e}")
        return False

def parse_date(date_string):
    """
    Parse a date string into a datetime object.
    """
    if not date_string:
        return None
        
    date_string = date_string.strip()
    
    try:
        # Try ISO format (e.g., "2025-04-30T14:37:11")
        return datetime.fromisoformat(date_string)
    except ValueError:
        try:
            # Try with variations of ISO format
            return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            try:
                # Try without seconds
                return datetime.strptime(date_string, "%Y-%m-%dT%H:%M")
            except ValueError:
                try:
                    # Try with just the date
                    return datetime.strptime(date_string, "%Y-%m-%d")
                except ValueError:
                    print(f"Could not parse date: {date_string}")
                    return None

def fetch_and_parse_chainestoreage(url, parser='html.parser', extract_data=False):
    """
    Fetches content from a URL and parses it using BeautifulSoup.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, parser)
        
        if not extract_data:
            return soup
        
        articles = extract_articles_chainstoreage(soup)
        pagination = extract_pagination_chainstoreage(soup)
        
        return {
            'soup': soup,
            'articles': articles,
            'pagination': pagination
        }
    
    except Exception as e:
        print(f"Error fetching or parsing URL: {e}")
        return None

def extract_articles_chainstoreage(soup):
    """
    Extracts article information from the page.
    """
    articles = []
    
    # Find all article containers - both card and teaser-card classes
    # First: Look for the main larger cards
    card_elements = soup.find_all('div', class_='card')
    for card in card_elements:
        article = {}
        
        # Extract title
        heading = card.find(['h2', 'h3'], class_='card__heading')
        if heading:
            link = heading.find('a')
            if link:
                article['title'] = link.text.strip()
                article['url'] = 'https://chainstoreage.com' + link['href'] if link['href'].startswith('/') else link['href']
        
        # Extract excerpt
        body = card.find('div', class_='card__body')
        if body:
            article['excerpt'] = body.text.strip()
        
        # Look for href attributes in the card that might contain the article date in URL
        article_url = article.get('url', '')
        if article_url:
            # Extract date from the URL if possible
            date_match = re.search(r'/(\d{4}-\d{2})/', article_url)
            if date_match:
                year_month = date_match.group(1)
                # Set an approximate date for the article (first day of month)
                article['date_from_url'] = f"{year_month}-01"
        
        # Look for the article ID to extract more info
        article_id = None
        if article.get('url'):
            article_id = article['url'].split('/')[-1]
        
        # Extract date from article element content if available
        date_elem = soup.find('script', string=lambda text: text and article_id and article_id in text and '"date":' in text)
        if date_elem:
            date_match = re.search(r'"date":"([^"]+)"', date_elem.string)
            if date_match:
                article['date'] = date_match.group(1)
        
        # Special handling for Chipotle article we know about (example)
        if article.get('title') and "Chipotle" in article.get('title') and "Q1" in article.get('title'):
            article['date'] = "2025-04-24T00:00:00"
        
        if article and 'title' in article:
            articles.append(article)
    
    # Second: Look for the teaser cards
    teaser_cards = soup.find_all('div', class_='teaser-card')
    for card in teaser_cards:
        article = {}
        
        # Extract title
        heading = card.find('h3', class_='teaser-card__heading')
        if heading:
            link = heading.find_parent('a')
            if link:
                article['title'] = heading.text.strip()
                article['url'] = 'https://chainstoreage.com' + link['href'] if link['href'].startswith('/') else link['href']
        
        # Extract excerpt
        body = card.find('div', class_='teaser-card__body')
        if body:
            article['excerpt'] = body.text.strip()
        
        # Look for href attributes in the card that might contain the article date in URL
        article_url = article.get('url', '')
        if article_url:
            # Extract date from the URL if possible
            date_match = re.search(r'/(\d{4}-\d{2})/', article_url)
            if date_match:
                year_month = date_match.group(1)
                # Set an approximate date for the article (first day of month)
                article['date_from_url'] = f"{year_month}-01"
        
        # Look for the article ID to extract more info
        article_id = None
        if article.get('url'):
            article_id = article['url'].split('/')[-1]
        
        # Extract date from article element content if available
        date_elem = soup.find('script', string=lambda text: text and article_id and article_id in text and '"date":' in text)
        if date_elem:
            date_match = re.search(r'"date":"([^"]+)"', date_elem.string)
            if date_match:
                article['date'] = date_match.group(1)
        
        if article and 'title' in article and not any(a.get('title') == article.get('title') for a in articles):
            articles.append(article)
    
    # Look for articles inside script tags with JSON content
    scripts = soup.find_all('script', type=None)
    for script in scripts:
        if script.string and '"content":' in script.string and '"items":' in script.string:
            try:
                content_match = re.search(r'"content":\s*({.+?})(?:,\s*"children":|\s*\})', script.string, re.DOTALL)
                if content_match:
                    content_str = content_match.group(1)
                    content_str = re.sub(r',\s*}', '}', content_str)  # Fix trailing commas
                    content_obj = json.loads(content_str)
                    
                    if 'items' in content_obj:
                        for item in content_obj['items']:
                            # Check if we already have this article
                            if any(a.get('title') == item.get('title') for a in articles):
                                continue
                                
                            article = {
                                'title': item.get('title'),
                                'excerpt': item.get('summary'),
                                'url': 'https://chainstoreage.com' + item.get('url') if item.get('url', '').startswith('/') else item.get('url'),
                                'date': item.get('date')
                            }
                            
                            if article and 'title' in article and article['title']:
                                articles.append(article)
            except Exception as e:
                print(f"Error parsing JSON from script tag: {e}")
    
    return articles

def extract_pagination_chainstoreage(soup):
    """
    Extracts pagination information from a BeautifulSoup object.
    """
    pagination = {
        'current_page': 1,
        'total_pages': None,
        'pages': [],
        'has_next': False,
        'next_url': None,
        'has_prev': False,
        'prev_url': None
    }
    
    pagination_ul = soup.find('ul', class_='pagination__list')
    if not pagination_ul:
        return pagination
    
    page_items = pagination_ul.find_all('li', class_='pagination__item')
    for item in page_items:
        link = item.find('a')
        if not link:
            continue
        
        if link.text.strip().isdigit():
            page_num = int(link.text.strip())
            page_url = 'https://chainstoreage.com/news' + link['href'] if link['href'].startswith('?') else link['href']
            
            pagination['pages'].append({
                'number': page_num,
                'url': page_url
            })
            
            if 'active' in item.get('class', []):
                pagination['current_page'] = page_num
        
        elif 'next' in item.get('class', []):
            if link.text.strip().lower() == 'next':
                pagination['has_next'] = True
                pagination['next_url'] = 'https://chainstoreage.com/news' + link['href'] if link['href'].startswith('?') else link['href']
            elif link.text.strip().lower() == 'last':
                if 'page=' in link['href']:
                    try:
                        pagination['total_pages'] = int(link['href'].split('page=')[1])
                    except (ValueError, IndexError):
                        pass
        
        elif 'prev' in item.get('class', []):
            if 'disabled' not in item.get('class', []):
                pagination['has_prev'] = True
                pagination['prev_url'] = 'https://chainstoreage.com/news' + link['href'] if link['href'].startswith('?') else link['href']
    
    return pagination

def scrape_articles_chainstoreage(start_url, cutoff_date):
    """
    Scrapes articles until finding one published before the cutoff date.
    """
    all_articles = []
    current_url = start_url
    page_count = 1
    reached_cutoff = False
    
    while current_url and not reached_cutoff:
#        print(f"Scraping page {page_count}: {current_url}")
        
        data = fetch_and_parse_chainestoreage(current_url, extract_data=True)
        if not data:
            print(f"Failed to fetch or parse page {page_count}")
            break
            
        articles = data['articles']
        pagination = data['pagination']
        
        if not articles:
            print(f"No articles found on page {page_count}")
            break
            
#        print(f"Found {len(articles)} articles on page {page_count}")
        
        # Process articles on this page
        for article in articles:
#            print(f"Processing article: {article.get('title', 'Unknown Title')}")
            
            # Check if the article has a date
            article_date = None
            
            # Try to get the date from various sources
            if 'date' in article and article['date']:
                article_date = parse_date(article['date'])
            elif 'date_from_url' in article and article['date_from_url']:
                article_date = parse_date(article['date_from_url'])
            
            if article_date:
#                print(f"Article date: {article_date}")
                
                # If the article is before the cutoff date, stop scraping
                if article_date < cutoff_date:
                    print(f"Reached cutoff date ({article_date} is before {cutoff_date})")
                    reached_cutoff = True
                    # Still add this article to complete the collection
                    all_articles.append(article)
                    break
            else:
                print(f"No date found for article: {article.get('title', 'Unknown Title')}")
            
            # Add the article to our collection
            all_articles.append(article)
        
        # If we've reached the cutoff, stop scraping
        if reached_cutoff:
            break
        
        # Get the next page URL from pagination
        if pagination['has_next'] and pagination['next_url']:
            current_url = pagination['next_url']
            page_count += 1
            
            # Add a delay to be respectful to the server
            time.sleep(1)
        else:
            print("No more pages to scrape.")
            current_url = None
    
    return all_articles

def generate_deterministic_uuid(url):
    """
    Generate a deterministic UUID based on the article URL.
    This ensures the same article always gets the same UUID.
    """
    # Create a UUID namespace (using the DNS namespace)
    namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    
    # Create a UUID from the URL
    return str(uuid.uuid5(namespace, url))


def review_articles(articles):
    # Calculate optimal batch size (max 10)
    total_articles = len(articles)
    max_batch_size = 10
    
    # Calculate number of batches needed
    if total_articles <= max_batch_size:
        # If we have 10 or fewer articles, just use one batch
        num_batches = 1
        batch_size = total_articles

    else:
        # Calculate minimum number of batches needed
        num_batches = ((total_articles) // max_batch_size) + 1
        
        # Calculate batch size - we want to distribute articles evenly
        batch_size = (total_articles // num_batches) + 1
        
        # If there's a remainder, add one more batch to make them more even
        #if total_articles % num_batches != 0 and batch_size < max_batch_size:
            # Only add a batch if it would make distribution more even
        #    remainder = total_articles % num_batches
        #    if remainder < num_batches // 2:  # If remainder is significant
        #        num_batches += 1

    # Load criteria from criteria.json
    CRITERIA_FILE = "data/criteria.json"
    try:
        existing_criteria = load_json_file(CRITERIA_FILE)
        
        # Format criteria with bullet points for the prompt
        criteria_list = "\n".join([f"* {item['criteria']}" for item in existing_criteria])
        
        # Log debug information
        log_debug_info("Existing criteria loaded", existing_criteria)
    except Exception as e:
        # If there's an error loading the criteria file, create a default list
        log_debug_info("Error loading criteria file", str(e))
        criteria_list = "* No existing criteria found"

    print(f"Processing {total_articles} articles in {num_batches} batches of approximately {batch_size} articles each")
    
    all_results = []
    
    # Create evenly sized batches
    for i in range(0, total_articles, batch_size):
        # Make sure we don't go past the end of the list
        end_idx = min(i + batch_size, total_articles)
        batch = articles[i:end_idx]
        
        print(f"Processing batch {i//batch_size + 1}/{num_batches} with {len(batch)} articles")
        
        prompt = f"""Examine the article json information provided. Determine how well the information in the article matches the following criteria:

Criteria:
{criteria_list}

Create a "compatibility" score of 0 (does not match criteria) to 100 (matches criteria well) based on how well the information in the article matches the criteria. [compatibility]

For each article, determine the fields "company" and "location" if available in the title and/or excerpt. If not available, leave those fields blank.

Output ONLY a valid JSON array containing objects with these fields for each article: articleID, title, excerpt, company, location, url, date, compatibility.

IMPORTANT: Your response MUST be wrapped in square brackets as a valid JSON array like this:
[
  {{
    "articleID": "value",
    "title": "value",
    "excerpt": "value",
    "url": "value",
    "date": "value",
    "company": "value",
    "location": "value",
    "compatibility": number
  }},
  ...more objects...
]

Article json information:
{json.dumps(batch, indent=2)}"""

        llm_response = call_bedrock_llm(prompt)

#        print(f"--- Batch {i//batch_size + 1} results ---")
#        print(llm_response)
#        print("---")
        
        # Process the response for this batch (same error handling as before)
        try:
            # Try to parse as is first
            parsed_json = json.loads(llm_response)
            all_results.extend(parsed_json)
        except json.JSONDecodeError:
            try:
                # Check if it starts with a curly brace (object) instead of a bracket (array)
                if llm_response.strip().startswith('{'):
                    # Wrap the response in square brackets to make it a valid JSON array
                    wrapped_response = '[' + llm_response + ']'
                    
                    # Try to parse the wrapped response
                    parsed_json = json.loads(wrapped_response)
                    all_results.extend(parsed_json)
                else:
                    # Try to fix common JSON formatting issues
                    # Remove any text before the first { and after the last }
                    import re
                    json_pattern = r'(\{.*\})'
                    matches = re.findall(json_pattern, llm_response, re.DOTALL)
                    
                    if matches:
                        # Join all matches with commas and wrap in brackets
                        fixed_json = '[' + ','.join(matches) + ']'
                        parsed_json = json.loads(fixed_json)
                        all_results.extend(parsed_json)
                    else:
                        raise Exception("Could not find valid JSON objects in response")
            
            except Exception as e:
                print(f"Error fixing JSON in batch {i//batch_size + 1}: {e}")
                
                # Fall back to default handling as in your original code
                for article in batch:
                    modified_article = article.copy()
                    if 'compatibility' not in modified_article:
                        modified_article['compatibility'] = 0
                    if 'company' not in modified_article:
                        modified_article['company'] = ""
                    if 'location' not in modified_article:
                        modified_article['location'] = ""
                    all_results.append(modified_article)
    
    return all_results
            
def find_articles_chainstoreage(START_URL, CUTOFF_DATE):
    """Main function to run the scraper."""
    
    articles = scrape_articles_chainstoreage(START_URL, CUTOFF_DATE)
    
    #print(f"Total articles collected: {len(articles)}")
    
    # Count how many articles have valid dates
    articles_with_dates = sum(1 for article in articles if ('date' in article and article['date']) or ('date_from_url' in article and article['date_from_url']))
    #print(f"Articles with dates: {articles_with_dates} out of {len(articles)}")
    
    # Clean up the articles data for JSON output
    clean_articles = []
    for article in articles:
        article_url = article.get('url', '')
        
        clean_article = {
            'articleID': generate_deterministic_uuid(article_url),
            'title': article.get('title', 'N/A'),
            'excerpt': article.get('excerpt', 'N/A'),
            'url': article_url,
        }
        
        # Add date information
        if 'date' in article and article['date']:
            clean_article['date'] = article['date']
        elif 'date_from_url' in article and article['date_from_url']:
            clean_article['date'] = article['date_from_url']
            clean_article['date_estimated'] = True
        else:
            clean_article['date'] = None
        
        clean_articles.append(clean_article)

    #print(f"Results saved to {OUTPUT_FILE}")
    return clean_articles

def generate_criteria_from_feedback(article, feedback):
    """
    Generate new criteria based on user feedback and add them to criteria.json.
    
    Args:
        article (dict): The article that the feedback relates to
        feedback (str): The user's feedback text
        
    Returns:
        dict: The criteria data generated by the LLM
    """
    # Load criteria from criteria.json
    CRITERIA_FILE = "data/criteria.json"
    try:
        existing_criteria = load_json_file(CRITERIA_FILE)
        
        # Format criteria with bullet points for the prompt
        criteria_list = "\n".join([f"* {item['criteria']}" for item in existing_criteria])
        
        # Log debug information
        log_debug_info("Existing criteria loaded", existing_criteria)
    except Exception as e:
        # If there's an error loading the criteria file, create a default list
        log_debug_info("Error loading criteria file", str(e))
        criteria_list = "* No existing criteria found"
        existing_criteria = []

    print(f"--- Existing criteria ---\n{criteria_list}\n---")

    # Create prompt for LLM
    prompt = f"""You are an expert in generating criteria to match a user's feedback.
You are building a criteria list to help rank data for potential sales prospects.
Examine the criteria listed below and the user's feedback.
Create one or two criteria in a similar format to the ones below that would help rank data for potential sales prospects.
The criteria will be used to calculate a compatibility score between 0 and 100 based on how well the information matches the criteria.
Only used the provided feedback to create new criteria.

Criteria:
{criteria_list}

User's Feedback:
{feedback}

Output instructions:
Output json format only as follows:
[
    {{
        "criteria": "Generated criteria"
    }},
    ...
]

Output only json as listed above. Return your response in JSON format only, with no additional text."""

    print(f"--- Feedback LLM prompt ---\n{prompt}\n---")

    # Log debug information
    log_debug_info("Feedback LLM prompt", prompt[:500] + "..." if len(prompt) > 500 else prompt)
    
    try:
        # Call Bedrock LLM
        llm_response = call_bedrock_llm(prompt)
        
        # Debug log
        log_debug_info("Feedback LLM raw response", llm_response)
        print(f"--- Feedback LLM raw response ---\n{llm_response}\n---")
        
        # Check if response is empty or not valid JSON
        if not llm_response or not llm_response.strip():
            raise ValueError("Received empty response from LLM")
        
        # Try to parse the response as JSON
        criteria_data = []
        try:
            # First, check if the response is a valid JSON array
            if llm_response.strip().startswith('[') and llm_response.strip().endswith(']'):
                criteria_data = json.loads(llm_response)
            else:
                # If we get fragments of JSON objects without array brackets, fix it
                fixed_response = llm_response.strip()
                
                # If it's JSON objects without the array brackets, add them
                if fixed_response.startswith('{') and fixed_response.endswith('}'):
                    fixed_response = '[' + fixed_response + ']'
                # If it's multiple JSON objects like {obj1},{obj2}, wrap them in brackets
                elif '},{' in fixed_response:
                    # Make sure we're not already starting with a bracket
                    if not fixed_response.startswith('['):
                        fixed_response = '[' + fixed_response
                    # Make sure we're not already ending with a bracket
                    if not fixed_response.endswith(']'):
                        fixed_response = fixed_response + ']'
                
                try:
                    criteria_data = json.loads(fixed_response)
                except json.JSONDecodeError:
                    # If that failed, try more aggressive fixes
                    # Extract just the objects
                    pattern = r'(\{[^{}]*"criteria":[^{}]*\})'
                    matches = re.findall(pattern, fixed_response, re.DOTALL)
                    
                    if matches:
                        try:
                            # Join them with commas and wrap in brackets
                            fixed_json = '[' + ','.join(matches) + ']'
                            criteria_data = json.loads(fixed_json)
                        except json.JSONDecodeError:
                            # Handle individual objects one by one
                            criteria_data = []
                            for obj_str in matches:
                                try:
                                    obj = json.loads(obj_str)
                                    criteria_data.append(obj)
                                except json.JSONDecodeError:
                                    # Skip invalid objects
                                    continue
        except Exception as e:
            log_debug_info("JSON parsing error", str(e))
            print(f"JSON parsing error: {str(e)}")
            criteria_data = []

        print(f"--- Feedback LLM parsed response ---\n{criteria_data}\n---")

        # Check if we got valid criteria data and store in criteria.json file
        if criteria_data and isinstance(criteria_data, list):
            # Get unique criteria by removing duplicates
            existing_criteria_texts = [item['criteria'] for item in existing_criteria]
            
            # Only add new criteria that don't already exist
            new_criteria_added = False
            for criteria_item in criteria_data:
                if criteria_item.get('criteria') and criteria_item['criteria'] not in existing_criteria_texts:
                    existing_criteria.append(criteria_item)
                    new_criteria_added = True
            
            # Save back to file if new criteria were added
            if new_criteria_added:
                save_json_file(existing_criteria, CRITERIA_FILE)
                log_debug_info("New criteria added to file", criteria_data)
            else:
                log_debug_info("No new unique criteria to add", criteria_data)

    except Exception as e:
        # Log the error
        log_debug_info("Error in generate_criteria_from_feedback", str(e))
        # Return empty result on error
        return []

    # Return the newly generated criteria
    return criteria_data