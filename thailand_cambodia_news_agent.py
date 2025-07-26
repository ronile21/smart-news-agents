import os
import requests
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from newspaper import Article
import hashlib

KEYWORDS = ["military", "attack", "clash", "border", "conflict", "war"]
COUNTRIES = ["thailand", "cambodia"]

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
    "https://www.khmertimeskh.com/category/national/"
]

sent_hashes = set()

def is_relevant(title: str) -> bool:
    lower = title.lower()
    return (
        any(c in lower for c in COUNTRIES) and
        any(k in lower for k in KEYWORDS)
    )

async def fetch_site(session, url):
    try:
        async with session.get(url, timeout=10) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            articles = soup.find_all('a')

            results = []
            for a in articles:
                title = a.get_text().strip()
                if not title or not is_relevant(title):
                    continue

                link = a.get('href')
                if link and not link.startswith("http"):
                    link = f"{url.rstrip('/')}/{link.lstrip('/')}"

                uid = hashlib.md5(f"{title}|{link}".encode()).hexdigest()
                if uid in sent_hashes:
                    continue
                sent_hashes.add(uid)

                summary = extract_summary(link)
                if summary:
                    msg = f"🛑 *War Update Found*\n\n*{title}*\n\n📄 {summary}\n\n🔗 {link}"
                    results.append(msg)
            return results
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
        return []

def extract_summary(url: str) -> str:
    try:
        article = Article(url)
        article.download()
        article.parse()
        article.nlp()
        return article.summary
    except Exception:
        return ""

async def check_all_sites():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_site(session, url) for url in NEWS_SITES]
        all_results = await asyncio.gather(*tasks)

        messages = sum(all_results, [])
        if messages:
            for msg in messages:
                print(msg)
                send_telegram_message(msg)
        else:
            print("No relevant news found.")

def send_telegram_message(message: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Telegram error: {e}")

if __name__ == "__main__":
    asyncio.run(check_all_sites())
