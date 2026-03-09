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

# === ARENAR INTEL NEWS STYLE ===
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

   post = template.format(
    title=title,
    summary=summary
)

full_post = post

    return full_post[:1800]

# === DUPLICATE CHECK ===
def already_posted(title):
    try:
        with open(POSTED_FILE, "r") as f:
            posted = f.read().splitlines()
            return title in posted
    except:
        return False

# === SIGNATURE CREATION ===
def create_signature(query_string, secret):
    return hmac.new(
        secret.encode(),
        query_string.encode(),
        hashlib.sha256
    ).hexdigest()

# === POST TO BINANCE SQUARE ===
def post_to_square(content):

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

    response = requests.post(url, headers=headers, json=payload)

    return response.json()

# === FETCH NEWS ===
def fetch_rss_news(feed_url):

    feed = feedparser.parse(feed_url)

    articles = []

    for entry in feed.entries[:5]:

        articles.append({
            "title": entry.get("title",""),
            "summary": entry.get("summary",""),
            "link": entry.get("link","")
        })

    return articles

def get_all_news():

    all_articles = []

    for feed in RSS_FEEDS:

        try:
            articles = fetch_rss_news(feed)
            all_articles.extend(articles)
            time.sleep(1)
        except:
            pass

    return all_articles

# === MAIN BOT ===
def run_bot():

    print(f"[{datetime.now()}] Fetching news")

    articles = get_all_news()

    if not articles:
        print("No news found")
        return

    article = None

    for a in articles:
        if not already_posted(a["title"]):
            article = a
            break

    if article is None:
        print("No new articles")
        return

    post_content = rephrase_news(article["title"], article["summary"])

    print("Posting article...")

    result = post_to_square(post_content)

    print(result)

    with open(POSTED_FILE, "a") as f:
        f.write(article["title"] + "\n")

if __name == "__main__":
    run_bot()
