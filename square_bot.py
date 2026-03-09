import requests
import feedparser
import random
import time
import hashlib
import hmac
import os
from datetime import datetime

# === SECURE API KEYS ===
API_KEY = os.getenv("BINANCE_API_KEY")
SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
BINANCE_REF_CODE = os.getenv("BINANCE_REF_CODE")

POSTED_FILE = "posted_articles.txt"

# === CRYPTO NEWS SOURCES ===
RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cryptoslate.com/feed/",
    "https://bitcoinmagazine.com/.rss/full/",
    "https://news.bitcoin.com/feed"
]

def rephrase_news(title, description):
    templates = [
        "🚨 JUST IN: {title}\n\n{summary}",
        "⚠️ MARKET ALERT: {title}\n\n{summary}",
        "📰 BREAKING: {title}\n\n{summary}",
        "⚡ DEVELOPING: {title}\n\n{summary}",
        "📊 CRYPTO UPDATE: {title}\n\n{summary}"
    ]

    summary = description[:220] + "..." if len(description) > 220 else description
    template = random.choice(templates)
    ref_link = f"https://www.binance.com/en/join?ref={BINANCE_REF_CODE}"

    post = template.format(title=title, summary=summary)
    full_post = f"{post}\n\nTrade crypto on Binance: {ref_link}"

    return full_post[:1800]

def already_posted(title):
    if not os.path.exists(POSTED_FILE):
        return False
    with open(POSTED_FILE, "r", encoding="utf-8") as f:
        posted = f.read().splitlines()
        return title in posted

def create_signature(query_string, secret):
    return hmac.new(
        secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

def post_to_square(content):
    base_url = "https://www.binance.com/bapi/square/v1/public/square/post/create"
    
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    signature = create_signature(query_string, SECRET_KEY)

    headers = {
        "X-MBX-APIKEY": API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "content": content,
        "contentType": "text",
        "language": "en"
    }

    url = f"{base_url}?{query_string}&signature={signature}"
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def fetch_rss_news(feed_url):
    feed = feedparser.parse(feed_url)
    articles = []
    for entry in feed.entries[:5]:
        articles.append({
            "title": entry.get("title", ""),
            "summary": entry.get("summary", ""),
            "link": entry.get("link", "")
        })
    return articles

def get_all_news():
    all_articles = []
    for feed in RSS_FEEDS:
        try:
            articles = fetch_rss_news(feed)
            all_articles.extend(articles)
            time.sleep(0.5)
        except Exception:
            continue
    return all_articles

def run_bot():
    print(f"[{datetime.now()}] Fetching news...")
    articles = get_all_news()

    if not articles:
        print("No news found.")
        return

    new_article = None
    for a in articles:
        if not already_posted(a["title"]):
            new_article = a
            break

    if not new_article:
        print("No new articles to post.")
        return

    post_content = rephrase_news(new_article["title"], new_article["summary"])
    print(f"Posting: {new_article['title']}")

    result = post_to_square(post_content)
    print(f"Response: {result}")

    # Log the title only if the post was successful or attempted
    with open(POSTED_FILE, "a", encoding="utf-8") as f:
        f.write(new_article["title"] + "\n")

if name == "__main__":
    run_bot()
