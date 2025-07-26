# news_agent.py

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

KEYWORDS = ["Thailand", "Cambodia", "border", "conflict", "military", "attack", "clash", "war"]
NEWS_URL = "https://www.reuters.com/world/asia-pacific/"  # אפשר להחליף בעוד אתרים

def fetch_news():
    print(f"[{datetime.now()}] Checking news...")
    try:
        response = requests.get(NEWS_URL, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        articles = soup.find_all('a')
        new_items = []

        for a in articles:
            title = a.get_text().strip()
            if any(keyword.lower() in title.lower() for keyword in KEYWORDS):
                link = a.get('href')
                if link and not link.startswith("http"):
                    link = f"https://www.reuters.com{link}"
                new_items.append((title, link))

        if new_items:
            print("\n🛑 NEW NEWS DETECTED:")
            for title, link in new_items:
                print(f"- {title}\n  👉 {link}\n")
        else:
            print("No relevant news found.")

    except Exception as e:
        print(f"❌ Error fetching news: {e}")

# Main loop: every 15 minutes
if __name__ == "__main__":
    while True:
        fetch_news()
        time.sleep(15 * 60)
