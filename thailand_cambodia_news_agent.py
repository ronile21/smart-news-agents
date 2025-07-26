import os
import requests
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import hashlib
from collections import deque

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
    "https://www.khmertimeskh.com/category/national/"
]

# A deque of 2 sets – memory of last 2 runs only
hash_history = deque(maxlen=2)

def is_relevant(title: str) -> bool:
    lower = title.lower()
    if any(ex in lower for ex in EXCLUDE):
        return False
    return sum(1 for k in KEYWORDS if k in lower) >= 2

async def fetch_site(session, url, current_run_hashes):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with session.get(url, timeout=10, headers=headers, ssl=False) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            articles = soup.find_all('a')

            results = []
            for a in articles:
                title = a.get_text().strip()
                if not title or not is_relevant(title):
                    continue

                link = a.get('href')
                if not link or len(link) < 5:
                    continue
                if not link.startswith("http"):
                    link = f"{url.rstrip('/')}/{link.lstrip('/')}"

                uid = hashlib.md5(f"{title}|{link}".encode()).hexdigest()

                # Check if UID is in any of the last 2 runs
                if any(uid in old_run for old_run in hash_history):
                    continue

                current_run_hashes.add(uid)
                msg = f"🛑 *War News*\n\n*{title}*\n🔗 {link}"
                results.append(msg)
            return results
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
        return []

async def check_all_sites():
    current_run_hashes = set()

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_site(session, url, current_run_hashes) for url in NEWS_SITES]
        all_results = await asyncio.gather(*tasks)

        messages = sum(all_results, [])
        count = len(messages)

        if messages:
            for msg in messages:
                print(msg)
                send_telegram_message(msg)
            print(f"✅ Total messages sent: {count}")
        else:
            print("No relevant news found.\n✅ Total messages sent: 0")

    # Push current hashes to the history queue
    hash_history.append(current_run_hashes)

def send_telegram_message(message: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}

    try:
        requests.post(url, data=data, timeout=5)
    except Exception as e:
        print(f"❌ Telegram error: {e}")

if __name__ == "__main__":
    asyncio.run(check_all_sites())
