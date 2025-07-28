import os
import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import hashlib
from collections import deque
import logging
from dotenv import load_dotenv
import feedparser

# === Load environment variables from .env ===
load_dotenv()

# === Configuration ===
KEYWORDS = ["thailand", "cambodia", "border", "clash", "military", "attack", "conflict", "war"]
EXCLUDE = ["israel", "russia", "ukraine", "palestinians", "gaza"]

NEWS_SITES = [
    "https://www.reuters.com/world/asia-pacific/",
    "https://www.bbc.com/news/world/asia",
    "https://www.aljazeera.com/news/asia-pacific/",
    "https://www.cnn.com/asia",
    "https://www.nytimes.com/section/world/asia",
    "https://www.dw.com/en/asia/s-12502",
    "https://www.abc.net.au/news/world/asia-pacific/",
    "https://asia.nikkei.com/",
    "https://www.thaipbsworld.com/",
    "https://www.khmertimeskh.com/category/national/",
    "https://www.phnompenhpost.com/national",
    "https://www.phnompenhpost.com/international",
    "https://www.bangkokpost.com/thailand",
    "https://www.voanews.com/asia",
    "https://thethaiger.com/news",
    "https://tna.mcot.net/english-news",
    "https://www.manilatimes.net/news/world",
    "https://www.channelnewsasia.com/asia",
    "https://www.asahi.com/ajw/asia/",
    "https://japantoday.com/category/world",
    "https://www.irrawaddy.com/news",
    "https://vietnamnews.vn/world",
    "https://www.bangkokpost.com/world"
]

RSS_FEEDS = [
    "https://feeds.reuters.com/reuters/AsiaPacificNews",
    "http://feeds.bbci.co.uk/news/world/asia/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://rss.cnn.com/rss/edition_asia.rss",
    "https://rss.nytimes.com/services/xml/rss/nyt/AsiaPacific.xml",
    "https://rss.dw.com/rdf/rss-en-asia",
    "https://www.thaipbsworld.com/feed/",
    "https://www.khmertimeskh.com/feed/",
    "https://www.abc.net.au/news/feed/51120/rss.xml",
    "https://www.voanews.com/api/epiqqe$eqq",
    "https://thethaiger.com/feed",
    "https://www.channelnewsasia.com/rssfeeds/8395986",
    "https://www.asahi.com/rss/asahi/english.rdf",
    "https://japantoday.com/rss",
    "https://www.irrawaddy.com/feed",
    "https://vietnamnews.vn/rss/world.rss",
    "https://www.bangkokpost.com/rss/data/world.xml",
    "https://www.straitstimes.com/news/asia/rss.xml",
    "https://www.manilatimes.net/rss/221"
]

sent_articles = deque(maxlen=60)

# === Logging Setup ===
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

# === Relevance Filter ===
def is_relevant(title: str) -> bool:
    lower = title.lower()
    if any(ex in lower for ex in EXCLUDE):
        return False
    return sum(1 for k in KEYWORDS if k in lower) >= 1

# === Telegram Sender ===
def send_telegram_message(message: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        logging.error("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}

    try:
        response = requests.post(url, data=data, timeout=5)
        if response.status_code != 200:
            logging.error(f"Telegram error {response.status_code}: {response.text}")
    except Exception as e:
        logging.error(f"Telegram exception: {e}")

# === HTML Site Fetcher ===
async def fetch_site(session, url):
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
            )
        }

        async with session.get(url, timeout=15, headers=headers, ssl=False, allow_redirects=True) as response:
            if response.status != 200:
                logging.warning(f"⚠️ Skipped {url} with status code: {response.status}")
                return []

            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            articles = soup.find_all('a')

            messages = []
            for a in articles:
                title = a.get_text().strip()
                if not title or not is_relevant(title):
                    continue

                href = a.get('href')
                if not href or len(href) < 5:
                    continue

                link = urljoin(url, href)
                uid = hashlib.md5(f"{title}|{link}".encode()).hexdigest()

                if uid in sent_articles:
                    continue

                sent_articles.append(uid)
                msg = f"🛑 *War News*\n\n*{title}*\n🔗 {link}"
                messages.append(msg)

            return messages

    except asyncio.TimeoutError:
        logging.error(f"❌ Timeout while fetching {url}")
    except aiohttp.ClientError as e:
        logging.error(f"❌ Client error fetching {url}: {e}")
    except Exception as e:
        logging.error(f"❌ Unexpected error fetching {url}: {type(e).__name__}: {e}")
    return []

# === RSS Feed Fetcher ===
async def fetch_rss_feed(url):
    try:
        feed = feedparser.parse(url)
        messages = []

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link or not is_relevant(title):
                continue

            uid = hashlib.md5(f"{title}|{link}".encode()).hexdigest()
            if uid in sent_articles:
                continue

            sent_articles.append(uid)
            msg = f"🛑 *War News*\n\n*{title}*\n🔗 {link}"
            messages.append(msg)

        return messages

    except Exception as e:
        logging.error(f"❌ RSS error for {url}: {e}")
        return []

# === Run All News Checks ===
async def check_all_sites():
    async with aiohttp.ClientSession() as session:
        html_tasks = [fetch_site(session, url) for url in NEWS_SITES]
        rss_tasks = [fetch_rss_feed(url) for url in RSS_FEEDS]

        all_results = await asyncio.gather(*html_tasks, *rss_tasks)

        messages = [msg for result in all_results for msg in result]
        count = len(messages)

        if messages:
            for msg in messages:
                send_telegram_message(msg)
            logging.info(f"✅ Total messages sent: {count}")
        else:
            logging.info("No relevant news found.\n✅ Total messages sent: 0")

# === Main Periodic Runner ===
async def periodic_check(sleep_seconds: int):
    while True:
        logging.info("🔍 Checking all news sites...")
        await check_all_sites()
        logging.info(f"⏱ Waiting {sleep_seconds // 60} minutes for next run...\n")
        await asyncio.sleep(sleep_seconds)

# === Script Entry Point ===
if __name__ == "__main__":
    try:
        asyncio.run(periodic_check(900))  # 15 minutes
    except KeyboardInterrupt:
        logging.info("🛑 Exiting gracefully...")
