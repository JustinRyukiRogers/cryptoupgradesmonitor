import os
import json
from google import genai
from typing import List, Optional
from src.models import RawEvent, RelevanceSignal, UpgradeConfirmation, Evidence, SourceType

class GeminiAgent:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        # New SDK initialization
        self.client = genai.Client(api_key=api_key)
        # Using gemini-2.0-flash
        self.model_name = 'gemini-2.0-flash'

    def generate_json(self, prompt: str) -> dict:
        try:
            # New SDK usage
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    'response_mime_type': 'application/json'
                }
            )
            
            # response.text is widely supported property, but new SDK might use response.text or response.candidates[0].content.parts[0].text
            # Checking documentation: response.text is usually available helper.
            
            data = json.loads(response.text)
            if isinstance(data, list):
                if data and isinstance(data[0], dict):
                    return data[0]
                return {}
            if isinstance(data, dict):
                return data
            return {}
        except Exception as e:
            print(f"Error generating JSON from Gemini ({self.model_name}): {e}")
            return {}

class LLMRelevanceAgent(GeminiAgent):
    def classify(self, event: RawEvent) -> RelevanceSignal:
        prompt = f"""
        Analyze the following text from a crypto project source ({event.source_type.value}).
        Determine if it discusses a technical or cryptoeconomic upgrade, proposition, or execution.
        Ignore general market news, price discussion, or vague marketing.
        
        Focus on:
        - Fee changes
        - Staking / Slashing logic updates
        - Emission / Inflation changes
        - Governance proposals acting on the above
        - Protocol version upgrades (v2, v3, etc.)

        Text: "{event.text}"
        Source: {event.url}

        Return JSON:
        {{
            "is_relevant": bool,
            "is_economic": bool,
            "is_upgrade_related": bool,
            "reason": "short explanation",
            "signals": ["list", "of", "keywords", "found"]
        }}
        """
        
        data = self.generate_json(prompt)
        
        return RelevanceSignal(
            is_crypto=True, 
            is_economic=data.get("is_economic", False),
            is_upgrade_related=data.get("is_upgrade_related", False),
            signals=data.get("signals", [])
        )

class LLMVerificationAgent(GeminiAgent):
    def verify(self, events: List[RawEvent]) -> UpgradeConfirmation:
        context_text = "\n\n".join([f"Source ({e.source_type.value}): {e.text} (URL: {e.url})" for e in events])
        
        prompt = f"""
        Analyze the provided evidence to determine if a specific cryptocurrency upgrade has been successfully deployed to MAINNET.

        ### Verification Protocol:
        1. **Check Environment:** Is this discussing Mainnet, Testnet (Sepolia, Goerli, etc.), or a Devnet?
        2. **Check Status:** Look for "Success" markers (e.g., "Activated," "Live," "Height reached") vs. "Intent" markers (e.g., "Proposed," "Upcoming," "Roadmap").
        3. **Look for Anchors:** Identify specific block numbers, transaction hashes, or official protocol announcements.

        ### Scoring Rubric:
        - **1.0 (Confirmed):** Explicitly live on Mainnet. Phrases: "Successfully deployed," "Post-upgrade report," "Now active at block X."
        - **0.7 (Imminent/Certain):** Governance passed and scheduled, but no confirmation of execution yet.
        - **0.4 (In Progress):** Voting is currently open or it is live on TESTNET only.
        - **0.1 (Speculative):** Proposals, forum discussions, or roadmap mentions.
        - **0.0 (Irrelevant):** The text does not mention an upgrade.

        Evidence:
        {context_text}

        Return JSON:
        {{
            "is_confirmed": bool, // ONLY true if score is 1.0
            "confidence": float,
            "status_detected": "string", // e.g., "Mainnet Live", "Testnet Only", "Proposal"
            "supporting_evidence": "quote the specific line confirming status",
            "reasoning": "brief explanation"
        }}
        """
        
        data = self.generate_json(prompt)
        
        evidence_list = [
            Evidence(type=e.source_type.value, url=e.url, description=e.text[:50])
            for e in events
        ]
        
        return UpgradeConfirmation(
            is_confirmed=data.get("is_confirmed", False),
            confidence=float(data.get("confidence", 0.0)),
            status_detected=data.get("status_detected"),
            supporting_evidence=data.get("supporting_evidence"),
            evidence=evidence_list,
            reasoning=data.get("reasoning", "No reasoning provided by LLM")
        )
