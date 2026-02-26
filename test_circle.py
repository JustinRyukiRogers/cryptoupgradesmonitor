import urllib.parse
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timezone

def test_circle():
    base = "https://www.circle.com/topic/usdc"
    link = "/blog/native-usdc-and-cctp-are-coming-to-edge-chain-what-you-need-to-know"
    print(f"URLJoin test: {urllib.parse.urljoin(base, link)}")
    
    url = "https://www.circle.com/blog/native-usdc-and-cctp-are-coming-to-edge-chain-what-you-need-to-know"
    try:
        resp = requests.get(url, headers={"User-Agent": "CryptoUpgradeMonitor/1.0"}, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        body_text = soup.get_text(separator=' ') # Use space separator to avoid concatenating words
        body_text_clean = " ".join(body_text.split())
        
        print(f"Clean body text sample: {body_text_clean[:200]}...")
        
        matches = list(re.finditer(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, \d{4}', body_text))
        print(f"Matches found: {[m.group(0) for m in matches]}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_circle()
