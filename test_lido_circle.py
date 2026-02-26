import feedparser
import requests
from bs4 import BeautifulSoup

def test_lido():
    url = "https://blog.lido.fi/rss/"
    headers = {"User-Agent": "CryptoUpgradeMonitor/1.0"}
    resp = requests.get(url, headers=headers)
    print(f"Lido Status: {resp.status_code}")
    
    f = feedparser.parse(resp.content)
    print(f"Lido Entries: {len(f.entries)}")
    if len(f.entries) == 0:
        print("Why 0 entries? Let's check the content:")
        print(resp.content[:500])

def test_circle():
    url = "https://www.circle.com/blog-all"
    headers = {"User-Agent": "CryptoUpgradeMonitor/1.0"}
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.content, 'html.parser')
    articles = soup.find_all('div', class_=lambda x: x and any(c in x for c in ['post', 'entry', 'item', 'article']))
    print(f"Circle Found {len(articles)} articles!")

if __name__ == "__main__":
    test_lido()
    test_circle()
