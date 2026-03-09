import requests
import feedparser
import random
import time
import hashlib
import hmac
import os
import re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# === SECURE API KEYS ===
API_KEY = os.getenv("BINANCE_API_KEY")
SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
BINANCE_REF_CODE = os.getenv("BINANCE_REF_CODE")
POSTED_FILE = "posted_articles.txt"
MAX_AGE_DAYS = 14  # Only post articles from the last 2 weeks

# === RSS NEWS SOURCES ===
RSS_FEEDS = [
    # Major crypto news
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cryptoslate.com/feed/",
    "https://bitcoinmagazine.com/.rss/full/",
    "https://news.bitcoin.com/feed",
    "https://decrypt.co/feed",
    "https://cryptopotato.com/feed/",
    "https://ambcrypto.com/feed/",
    "https://cryptobriefing.com/feed/",
    "https://thedefiant.io/feed",
    "https://beincrypto.com/feed/",
    "https://cryptonews.com/news/feed/",
    "https://u.today/rss",
    "https://dailyhodl.com/feed/",
    "https://zycrypto.com/feed/",
    "https://bitcoinist.com/feed/",
    "https://insidebitcoins.com/feed",
    "https://crypto.news/feed/",
    "https://blockworks.co/feed",
    "https://www.theblock.co/rss.xml",

    # Bitcoin specific
    "https://bitcoinmagazine.com/feed",
    "https://bitcoinethereumnews.com/feed/",

    # Ethereum / DeFi / Altcoins
    "https://ethhub.substack.com/feed",
    "https://defipulse.com/blog/feed/",
    "https://www.coinbureau.com/feed/",

    # Market / Trading
    "https://www.financemagnates.com/cryptocurrency/feed/",
    "https://coinjournal.net/feed/",
    "https://coinpedia.org/feed/",
    "https://coingape.com/feed/",
    "https://cryptomode.com/feed/",
    "https://smartereum.com/feed/",
    "https://globalcryptopress.com/feed/",

    # On-chain / Analytics
    "https://glassnode.com/blog/feed.xml",
    "https://blog.chainalysis.com/feed/",

    # Broader finance with crypto coverage
    "https://www.reuters.com/finance/rss",
    "https://feeds.bloomberg.com/crypto/news.rss",
    "https://fortune.com/feed/",
    "https://www.nasdaq.com/feed/rssoutbound?category=Cryptocurrencies",
]

# === NITTER / X ACCOUNT RSS FEEDS ===
# These mirror crypto influencer X (Twitter) accounts via public Nitter RSS
# Falls back gracefully if any instance is down
NITTER_INSTANCES = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.1d4.us",
]

X_ACCOUNTS = [
    "saylor",           # Michael Saylor - Bitcoin maximalist
    "WatcherGuru",      # Breaking crypto/macro news
    "CryptoWhale",      # Market moves & sentiment
    "VitalikButerin",   # Ethereum founder
    "cz_binance",       # Binance founder
    "APompliano",       # Anthony Pompliano - Bitcoin bull
    "DocumentingBTC",   # Bitcoin price history & milestones
    "BitcoinMagazine",  # Bitcoin news
    "CoinDesk",         # Crypto news
    "Cointelegraph",    # Crypto news
    "whale_alert",      # Large on-chain transfers
    "ali_charts",       # Technical analysis & on-chain
    "RaoulGMI",         # Raoul Pal - macro & crypto
    "CryptoCapo_",      # Market analysis
    "lookonchain",      # On-chain tracking
    "IncomeSharks",     # Trading signals & commentary
    "CryptoCred",       # Technical analysis
    "PeterSchiff",      # Bitcoin skeptic (great for counter takes)
    "EleanorTerrett",   # Fox Business crypto reporter
    "EricBalchunas",    # Bloomberg ETF analyst
    "SBF_FTX",          # Historical — still referenced
    "Excellion",        # Samson Mow - Bitcoin
    "LayahHeilpern",    # Crypto journalist/presenter
    "cryptowendyo",     # Crypto educator
    "ScottMelker",      # The Wolf of All Streets
    "TheCryptoDog",     # Market commentary
    "Pentosh1",         # Trading analysis
    "CryptoTony__",     # Market analysis
    "TheRealPlanC",     # Bitcoin stock-to-flow
    "woonomic",         # Willy Woo - on-chain analytics
]

def get_nitter_feed(account):
    """Try each Nitter instance until one works."""
    for instance in NITTER_INSTANCES:
        try:
            url = f"{instance}/{account}/rss"
            feed = feedparser.parse(url)
            if feed.entries:
                return feed
        except Exception:
            continue
    return None

def is_within_timeframe(entry, max_days=MAX_AGE_DAYS):
    """Check if an article was published within the allowed timeframe."""
    for date_field in ["published", "updated"]:
        raw = entry.get(date_field, "")
        if not raw:
            continue
        try:
            pub_date = parsedate_to_datetime(raw)
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            cutoff = datetime.now(timezone.utc) - timedelta(days=max_days)
            return pub_date >= cutoff
        except Exception:
            continue
    # If no date found, include it anyway (better to post than skip)
    return True

def clean_html(text):
    """Strip HTML tags from summaries."""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def already_posted(title):
    if not os.path.exists(POSTED_FILE):
        return False
    with open(POSTED_FILE, "r", encoding="utf-8") as f:
        posted = f.read().splitlines()
    # Fuzzy match — strip punctuation and lowercase before comparing
    clean = lambda s: re.sub(r'[^a-z0-9 ]', '', s.lower()).strip()
    return clean(title) in [clean(p) for p in posted]

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

def rephrase_news(title, summary, source_type="rss"):
    """Rewrite news in a human, non-bot voice."""
    summary = clean_html(summary)
    summary = summary[:240] + "..." if len(summary) > 240 else summary

    if source_type == "x":
        # Social-style rephrasing for X/Twitter sourced content
        openers = [
            "This is making rounds right now —",
            "People are talking about this:",
            "Hard to ignore this one:",
            "Saw this and thought you should know:",
            "The crypto crowd is reacting to this:",
            "Worth a read if you haven't seen it:",
            "This one's getting a lot of attention:",
        ]
    else:
        openers = [
            "Just saw this drop —",
            "In case you missed it:",
            "This is developing:",
            "Keeping an eye on this one:",
            "Worth paying attention to:",
            "Markets are watching this closely:",
            "Something to keep on your radar:",
            "This just came through:",
        ]

    opener = random.choice(openers)
    ref_link = f"https://www.binance.com/en/join?ref={BINANCE_REF_CODE}"
    post = f"{opener}\n\n{title}\n\n{summary}\n\nTrade on Binance 👉 {ref_link}"
    return post[:1800]

def fetch_rss_articles():
    """Pull articles from all RSS feeds, filter by age."""
    all_articles = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                if not is_within_timeframe(entry):
                    continue
                all_articles.append({
                    "title": entry.get("title", "").strip(),
                    "summary": entry.get("summary", entry.get("description", "")),
                    "source": "rss"
                })
            time.sleep(0.3)
        except Exception:
            continue
    return all_articles

def fetch_x_articles():
    """Pull posts from X accounts via Nitter RSS, filter by age."""
    all_posts = []
    shuffled_accounts = X_ACCOUNTS.copy()
    random.shuffle(shuffled_accounts)  # Vary the source order each run
    for account in shuffled_accounts:
        try:
            feed = get_nitter_feed(account)
            if not feed:
                continue
            for entry in feed.entries[:3]:
                if not is_within_timeframe(entry):
                    continue
                title = entry.get("title", "").strip()
                # Skip retweets and replies — they sound odd out of context
                if title.startswith("RT @") or title.startswith("@"):
                    continue
                # Skip very short posts (less than 60 chars — not worth rephrasing)
                if len(title) < 60:
                    continue
                all_posts.append({
                    "title": title,
                    "summary": entry.get("summary", title),
                    "source": "x",
                    "account": account
                })
            time.sleep(0.3)
        except Exception:
            continue
    return all_posts

def get_all_articles():
    """Combine RSS and X sources, shuffle for variety."""
    print("Fetching RSS feeds...")
    rss_articles = fetch_rss_articles()
    print(f"  → {len(rss_articles)} RSS articles found")

    print("Fetching X/Twitter accounts via Nitter...")
    x_articles = fetch_x_articles()
    print(f"  → {len(x_articles)} X posts found")

    combined = rss_articles + x_articles
    random.shuffle(combined)
    return combined

def run_bot():
    print(f"[{datetime.now()}] Starting bot run...")
    articles = get_all_articles()

    if not articles:
        print("No articles fetched at all — check network/feeds.")
        return

    new_article = None
    for a in articles:
        if a["title"] and not already_posted(a["title"]):
            new_article = a
            break

    if not new_article:
        print("All recent articles already posted. Nothing new to post.")
        return

    source_label = f"@{new_article.get('account', '')}" if new_article["source"] == "x" else "RSS"
    print(f"Source: {source_label} | Title: {new_article['title'][:80]}")

    post_content = rephrase_news(new_article["title"], new_article["summary"], new_article["source"])
    result = post_to_square(post_content)
    print(f"Response: {result}")

    with open(POSTED_FILE, "a", encoding="utf-8") as f:
        f.write(new_article["title"] + "\n")

if __name__ == "__main__":
    run_bot()
