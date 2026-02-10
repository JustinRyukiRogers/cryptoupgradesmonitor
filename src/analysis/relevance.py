from typing import List
from src.models import RawEvent, RelevanceSignal

class RelevanceClassifierAgent:
    def __init__(self):
        # Heuristics for MVP
        self.crypto_keywords = ["crypto", "blockchain", "ethereum", "bitcoin", "uniswap", "eigenlayer", "token", "defi", "l1", "l2", "rollup"]
        self.economic_keywords = ["fee", "staking", "slash", "emission", "inflation", "yield", "reward", "cost", "gas", "treasury", "revenue", "tax", "burn"]
        self.upgrade_keywords = ["upgrade", "hard fork", "migration", "v2", "v3", "v4", "activation", "deploy", "release", "update", "patch", "eip-", "proposal"]

    def classify(self, event: RawEvent) -> RelevanceSignal:
        text_lower = event.text.lower()
        
        is_crypto = any(k in text_lower for k in self.crypto_keywords)
        is_economic = any(k in text_lower for k in self.economic_keywords)
        is_upgrade = any(k in text_lower for k in self.upgrade_keywords)
        
        # Context-specific overrides
        # If it comes from a specific project source (e.g. Uniswap blog), is_crypto is implied true.
        # But we want to be explicit.
        if event.project in ["ethereum", "uniswap", "eigenlayer"]:
             is_crypto = True

        signals = []
        if is_crypto: signals.append("crypto_keyword")
        if is_economic: signals.append("economic_keyword")
        if is_upgrade: signals.append("upgrade_keyword")

        return RelevanceSignal(
            is_crypto=is_crypto,
            is_economic=is_economic,
            is_upgrade_related=is_upgrade,
            signals=signals
        )
