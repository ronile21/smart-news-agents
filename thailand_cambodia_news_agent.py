import os
import requests
import asyncio
import aiohttp
from bs4 import BeautifulSoup

KEYWORDS = ["border", "conflict", "military", "attack", "clash", "war"]

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

async def fetch_summary(session, article_url):
    try:
        async with session.get(article_url, timeout=10) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')

            for p in soup.find_all('p'):
                text = p.get_text().strip()
                if len(text) > 40:
                    return text
            return "No summary found."
    except Exception as e:
        print(f"❌ Error fetching summary from {article_url}: {e}")
        return "Error loading summary."

async def fetch_site(session, url):
    try:
        async with session.get(url, timeout=10) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            articles = soup.find_all('a')

            matches = []
            for a in articles:
                title = a.get_text().strip()
                lower_title = title.lower()

                if (("thailand" in lower_title or "cambodia" in lower_title) and
                    any(k in lower_title for k in KEYWORDS)):

                    link = a.get('href')
                    if link and not link.startswith("http"):
                        link = f"{url.rstrip('/')}/{link.lstrip('/')}"

                    summary = await fetch_summary(session, link)
                    matches.append((title, summary, link))

            return matches
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
        return []

async def check_all_sites():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_site(session, url) for url in NEWS_SITES]
        results = await asyncio.gather(*tasks)

        total_matches = sum(results, [])  # flatten
        if total_matches:
            for title, summary, link in total_matches:
                msg = f"🛑 New war news!\n\n📰 {title}\n\n📄 {summary}\n👉 {link}"
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
        "text": message
    }

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Telegram error: {e}")

if __name__ == "__main__":
    asyncio.run(check_all_sites())
