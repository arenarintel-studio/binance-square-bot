import requests
import feedparser
import random
import time
import hashlib
import hmac
import json
from datetime import datetime
from typing import List, Dict

# === CONFIGURATION (Set these via Secrets) ===
API_KEY = "your-api-key-here"
SECRET_KEY = "your-secret-key-here"
BINANCE_REF_CODE = "your-ref-code"

# === NEWS SOURCES ===
RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cryptopotato.com/feed",
    "https://news.bitcoin.com/feed"
]

# === REPHRASING TEMPLATES ===
def rephrase_news(title: str, description: str) -> str:
    templates = [
        "🔥 JUST IN: {title}\n\n{summary}\n\nWhat's your take on this? 👇",
        "🚀 Big news in crypto! {title}\n\n{summary}\n\n{question}",
        "📰 Market update: {title}\n\n{summary}\n\nAre you bullish or bearish?",
        "💡 Here's what's happening: {title}\n\n{summary}\n\nTrade wisely!",
        "⚡️ Breaking: {title}\n\n{summary}\n\n{question}"
    ]
    
    questions = [
        "What do you think?",
        "Your thoughts?",
        "Is this bullish?",
        "Time to buy?",
        "Be careful out there!"
    ]
    
    summary = description[:200] + "..." if len(description) > 200 else description
    template = random.choice(templates)
    question = random.choice(questions)
    ref_link = f"https://www.binance.com/en/join?ref={BINANCE_REF_CODE}"
    
    post = template.format(
        title=title,
        summary=summary,
        question=question
    )
    
    full_post = f"{post}\n\nTrade on Binance: {ref_link}"
    return full_post[:1800]

# === BINANCE SQUARE API FUNCTIONS ===
def create_signature(query_string: str, secret: str) -> str:
    return hmac.new(
        secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def post_to_square(content: str) -> Dict:
    base_url = "https://www.binance.com/bapi/square/v1/public/square/post/create"
    
    payload = {
        "content": content,
        "contentType": "text",
        "language": "en"
    }
    
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    signature = create_signature(query_string, SECRET_KEY)
    
    headers = {
        "X-MBX-APIKEY": API_KEY,
        "Content-Type": "application/json"
    }
    
    url = f"{base_url}?{query_string}&signature={signature}"
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# === NEWS FETCHING ===
def fetch_rss_news(feed_url: str) -> List[Dict]:
    try:
        feed = feedparser.parse(feed_url)
        articles = []
        
        for entry in feed.entries[:5]:
            articles.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", "") or entry.get("description", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", "")
            })
        
        return articles
    except:
        return []

def get_all_news() -> List[Dict]:
    all_articles = []
    
    for feed_url in RSS_FEEDS:
        articles = fetch_rss_news(feed_url)
        all_articles.extend(articles)
        time.sleep(1)
    
    seen = set()
    unique = []
    for article in all_articles:
        if article["title"] not in seen:
            seen.add(article["title"])
            unique.append(article)
    
    return unique

# === MAIN LOOP ===
def run_bot():
    print(f"[{datetime.now()}] Fetching news...")
    
    articles = get_all_news()
    
    if not articles:
        print("No news found")
        return
    
    print(f"Found {len(articles)} articles")
    
    article = random.choice(articles)
    
    post_content = rephrase_news(article["title"], article["summary"])
    
    print(f"Posting: {post_content[:100]}...")
    
    result = post_to_square(post_content)
    
    if "error" in result:
        print(f"❌ Failed: {result['error']}")
    else:
        print(f"✅ Posted successfully!")
        print(f"Original: {article['title']}")
        print(f"Source: {article['link']}")
    
    with open("post_log.txt", "a") as f:
        f.write(f"{datetime.now()}: {article['title']} - Success: {'error' not in result}\n")

if __name__ == "__main__":
    run_bot()
