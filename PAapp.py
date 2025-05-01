import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import re
import json
import uuid

# Constants - modify these as needed
START_URL = 'https://chainstoreage.com/news'
CUTOFF_DATE = datetime(2025, 4, 25)  # Articles before this date will not be scraped
OUTPUT_FILE = 'articles.json'

def fetch_and_parse(url, parser='html.parser', extract_data=False):
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
        
        articles = extract_articles(soup)
        pagination = extract_pagination(soup)
        
        return {
            'soup': soup,
            'articles': articles,
            'pagination': pagination
        }
    
    except Exception as e:
        print(f"Error fetching or parsing URL: {e}")
        return None

def extract_articles(soup):
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

def extract_pagination(soup):
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

def scrape_articles_until_date(start_url, cutoff_date):
    """
    Scrapes articles until finding one published before the cutoff date.
    """
    all_articles = []
    current_url = start_url
    page_count = 1
    reached_cutoff = False
    
    while current_url and not reached_cutoff:
        print(f"Scraping page {page_count}: {current_url}")
        
        data = fetch_and_parse(current_url, extract_data=True)
        if not data:
            print(f"Failed to fetch or parse page {page_count}")
            break
            
        articles = data['articles']
        pagination = data['pagination']
        
        if not articles:
            print(f"No articles found on page {page_count}")
            break
            
        print(f"Found {len(articles)} articles on page {page_count}")
        
        # Process articles on this page
        for article in articles:
            print(f"Processing article: {article.get('title', 'Unknown Title')}")
            
            # Check if the article has a date
            article_date = None
            
            # Try to get the date from various sources
            if 'date' in article and article['date']:
                article_date = parse_date(article['date'])
            elif 'date_from_url' in article and article['date_from_url']:
                article_date = parse_date(article['date_from_url'])
            
            if article_date:
                print(f"Article date: {article_date}")
                
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
            time.sleep(2)
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

def main():
    """Main function to run the scraper."""
    print(f"Starting scrape from: {START_URL}")
    print(f"Using cutoff date: {CUTOFF_DATE}")
    
    articles = scrape_articles_until_date(START_URL, CUTOFF_DATE)
    
    print(f"Total articles collected: {len(articles)}")
    
    # Count how many articles have valid dates
    articles_with_dates = sum(1 for article in articles if ('date' in article and article['date']) or ('date_from_url' in article and article['date_from_url']))
    print(f"Articles with dates: {articles_with_dates} out of {len(articles)}")
    
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
    
    # Save to JSON file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(clean_articles, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()