import requests
import feedparser
import random
import hashlib
import hmac
import os
import re
import time
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# === API KEYS ===
API_KEY = os.getenv("BINANCE_API_KEY")
SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
POSTED_FILE = "posted_articles.txt"

# === 3 SOURCES ONLY ===
FEEDS = [
    "https://rss.app/feeds/tuwQqmiiJgd3fkN2.xml",  # WatcherGuru (X)
    "https://cointelegraph.com/rss",                 # CoinTelegraph
    "https://www.coinbureau.com/feed/",              # CoinBureau
]

# === YOUR STYLE — reframes news like a real person who follows crypto ===
def reframe(title, summary):
    title = title.strip()
    summary = clean_html(summary).strip()
    summary = summary[:280] + "..." if len(summary) > 280 else summary

    openers = [
        "Okay this is big —",
        "Worth knowing about this:",
        "Just caught this one:",
        "Keep an eye on this:",
        "This one matters:",
        "Not gonna lie, this is interesting:",
        "If you haven't seen this yet —",
        "This is developing fast:",
        "Crypto never sleeps —",
        "In case you missed it:",
    ]

    closers = [
        "What do you think?",
        "Thoughts?",
        "This space moves fast.",
        "Stay sharp out there.",
        "Always something happening in crypto.",
        "Do your own research, but this looks significant.",
        "The market will react — watch closely.",
        "",
        "",
        "",  # empty closers weighted higher so not every post ends with one
    ]

    opener = random.choice(openers)
    closer = random.choice(closers)

    if summary and summary.lower() not in title.lower():
        body = f"{opener}\n\n{title}\n\n{summary}"
    else:
        body = f"{opener}\n\n{title}"

    if closer:
        body += f"\n\n{closer}"

    return body[:1800]

def clean_html(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_fresh(entry, max_days=14):
    for field in ["published", "updated"]:
        raw = entry.get(field, "")
        if not raw:
            continue
        try:
            pub = parsedate_to_datetime(raw)
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            return pub >= datetime.now(timezone.utc) - timedelta(days=max_days)
        except Exception:
            continue
    return True  # no date = include it

def already_posted(title):
    if not os.path.exists(POSTED_FILE):
        return False
    with open(POSTED_FILE, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    normalize = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())
    return normalize(title) in {normalize(l) for l in lines}

def mark_posted(title):
    # Keep file trim — last 300 entries only
    lines = []
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    lines.append(title)
    lines = lines[-300:]
    with open(POSTED_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

def create_signature(query_string, secret):
    return hmac.new(
        secret.encode("utf-8"),
        query_string.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()

def post_to_square(content):
    base_url = "https://www.binance.com/bapi/square/v1/public/square/post/create"
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    signature = create_signature(query_string, SECRET_KEY)
    headers = {"X-MBX-APIKEY": API_KEY, "Content-Type": "application/json"}
    payload = {"content": content, "contentType": "text", "language": "en"}
    url = f"{base_url}?{query_string}&signature={signature}"
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def run_bot():
    print(f"[{datetime.now()}] Bot starting...")

    all_articles = []
    for feed_url in FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:
                if not is_fresh(entry):
                    continue
                title = entry.get("title", "").strip()
                if not title:
                    continue
                all_articles.append({
                    "title": title,
                    "summary": entry.get("summary", entry.get("description", "")),
                })
            print(f"  ✓ Fetched: {feed_url.split('/')[2]}")
        except Exception as e:
            print(f"  ✗ Failed: {feed_url.split('/')[2]} — {e}")

    print(f"Total fresh articles found: {len(all_articles)}")

    # Shuffle so we don't always post from the same source
    random.shuffle(all_articles)

    new_article = None
    for a in all_articles:
        if not already_posted(a["title"]):
            new_article = a
            break

    if not new_article:
        print("Nothing new to post — all recent articles already posted.")
        return

    content = reframe(new_article["title"], new_article["summary"])
    print(f"\nPosting:\n{content}\n")

    result = post_to_square(content)
    print(f"Binance response: {result}")

    if "error" not in str(result).lower():
        mark_posted(new_article["title"])
        print("Done.")
    else:
        print("Post failed — not marking as posted so it retries next run.")

if __name__ == "__main__":
    run_bot()
