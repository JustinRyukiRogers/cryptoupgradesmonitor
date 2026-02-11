import feedparser
import requests
from bs4 import BeautifulSoup

BLOG_URL = "blog.ethereum.org"
Base = "https://blog.ethereum.org"

def test_rss():
    urls = [
        f"{Base}/feed",
        f"{Base}/rss",
        f"{Base}/rss.xml",
        f"{Base}/feed.xml",
        f"{Base}/index.xml",
        Base
    ]
    
    print("--- Testing RSS ---")
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    
    for url in urls:
        print(f"Checking {url}...")
        try:
            # Test simple request first
            resp = requests.get(url, headers=headers, timeout=5)
            print(f"  Status: {resp.status_code}")
            
            # Test feedparser
            # Feedparser can fetch URL directly or parse string
            f = feedparser.parse(url) # uses its own user agent usually
            print(f"  Bozo: {f.bozo}")
            if f.bozo:
                print(f"  Bozo exception: {f.bozo_exception}")
            print(f"  Entries: {len(f.entries)}")
            if len(f.entries) > 0:
                print(f"  First entry title: {f.entries[0].title}")
                
            # Try parsing content directly if requests worked
            if resp.status_code == 200:
                 f2 = feedparser.parse(resp.content)
                 print(f"  [Direct Content Parse] Entries: {len(f2.entries)}")

        except Exception as e:
            print(f"  Error: {e}")

def test_html():
    print("\n--- Testing HTML Scraping ---")
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        resp = requests.get(Base, headers=headers, timeout=10)
        print(f"HTML Status: {resp.status_code}")
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Test my heuristic
        articles = soup.find_all('article')
        print(f"Found {len(articles)} <article> tags")
        
        divs = soup.find_all('div', class_=lambda x: x and any(c in x for c in ['post', 'entry', 'item', 'article']))
        print(f"Found {len(divs)} divs with post-like classes")
        
        roles = soup.find_all(attrs={"role": "article"})
        print(f"Found {len(roles)} elements with role='article'")
        
    except Exception as e:
        print(f"HTML Error: {e}")

if __name__ == "__main__":
    test_rss()
    test_html()
