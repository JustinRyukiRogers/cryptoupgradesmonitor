import os
from dotenv import load_dotenv
load_dotenv()
from src.models import RawEvent, SourceType, ProjectConfig
from src.analysis.llm_agents import LLMVerificationAgent
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def test_agent():
    print("Fetching article...")
    url = "https://blog.uniswap.org/unification"
    resp = requests.get(url, headers={"User-Agent": "CryptoUpgradeMonitor/1.0"})
    soup = BeautifulSoup(resp.content, 'html.parser')
    text = soup.get_text()[:4000]
    
    event = RawEvent(
        project="uniswap",
        source_type=SourceType.BLOG,
        author="unknown",
        text=text,
        url=url,
        timestamp=datetime.now()
    )
    
    agent = LLMVerificationAgent()
    print("Verifying event...")
    confirmation = agent.verify([event])
    print("Verification Signal:", confirmation.model_dump_json(indent=2))

if __name__ == "__main__":
    test_agent()
