import re
from src.models import RawEvent, UpgradeStatus

class UpgradeStatusAgent:
    def __init__(self):
        self.deployed_keywords = ["live", "activated", "executed", "deployed", "mainnet", "on-chain", "successful"]
        self.approved_keywords = ["approved", "passed", "governance pass", "scheduled"]
        
    def determine_status(self, event: RawEvent) -> UpgradeStatus:
        text_lower = event.text.lower()

        # Check for deployed/live signals first (highest priority)
        if any(k in text_lower for k in self.deployed_keywords):
            # Must check if it says "now live" or "is live" vs "will be live"
            # MVP: simple keyword match. "will be live" might trigger false positive.
            # Improvement: Check for future tense.
            if "will be" in text_lower or "planning" in text_lower or "proposal" in text_lower:
                 # Ambiguous. If it has explicit "live" it might be "X is live, Y will be live".
                 pass
            else:
                 return UpgradeStatus.DEPLOYED_MAINNET
        
        # Check for approved signals
        if any(k in text_lower for k in self.approved_keywords):
             return UpgradeStatus.APPROVED_NOT_DEPLOYED
             
        return UpgradeStatus.PROPOSAL_ONLY
