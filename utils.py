import json
import os
import datetime
import pandas as pd
import boto3

def load_json_file(file_path):
    """Load data from a JSON file, return empty list if file doesn't exist."""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            # If loading from the main data file, make sure we have indexes
            if file_path.endswith('article-confidence.json'):
                # Make sure each article has an index for proper dataframe creation
                for i, article in enumerate(data):
                    article['index_pos'] = i
            return data
    return []

def save_json_file(data, file_path):
    """Save data to a JSON file."""
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def analyze_article(article):
    """
    Analyze an article and add analysis information.
    This is a placeholder for the actual analysis logic.
    """
    # Make a copy of the article to avoid modifying the original
    analyzed_article = article.copy()
    
    # Add analyze date
    analyzed_article['analyze_date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # In a real implementation, you would add more analysis here
    
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
    
    # Ensure confidence is numeric
    if 'confidence' in df.columns:
        df['confidence'] = pd.to_numeric(df['confidence'], errors='coerce')
        # Fill NaN values with 0
        df['confidence'] = df['confidence'].fillna(0)
    
    return df

def keep_article(article, kept_file='articles-kept.json'):
    """
    Save the article to the kept file.
    Returns True if successful, False otherwise.
    """
    try:
        # Load existing kept articles
        kept_articles = load_json_file(kept_file)
        
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
        save_json_file(kept_articles, kept_file)
        return True
    except Exception as e:
        print(f"Error keeping article: {e}")
        return False

def keep_all_articles(articles, kept_file='articles-kept.json'):
    """
    Save all articles to the kept file.
    Returns the number of successfully kept articles.
    """
    successfully_kept = 0
    for article in articles:
        if keep_article(article, kept_file):
            successfully_kept += 1
    return successfully_kept

def call_bedrock_llm(
    prompt: str,
    model_name: str = "us.amazon.nova-lite-v1:0",
    ) -> str:
    
    client = boto3.client(
        service_name="bedrock-runtime",
        aws_access_key_id=os.environ["AWS_ACCESS_KEY"],
        aws_secret_access_key=os.environ["AWS_SECRET_KEY"],
        region_name=os.environ["AWS_REGION"]
    )

    messages = [
        {"role": "user", "content": [{"text": prompt}]}
    ]

    model_response = client.converse(
        modelId=model_name,
        messages=messages
    )
    response_text = model_response["output"]["message"]["content"][0]["text"]
    return response_text
