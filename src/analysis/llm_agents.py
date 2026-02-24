import os
import json
from google import genai
from typing import List, Optional
from src.models import RawEvent, RelevanceSignal, UpgradeConfirmation, Evidence, SourceType, AffectedSubtype, ProjectConfig

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
    def classify(self, event: RawEvent, project_config: Optional[ProjectConfig] = None) -> RelevanceSignal:
        token_context_str = ""
        if project_config and project_config.relevant_tokens:
            tokens = ", ".join(project_config.relevant_tokens)
            token_context_str = f"Specifically, evaluate the impact against the native token(s) of this project: {tokens}. If the text describes general protocol enhancements but does NOT explicitly grant a new enforceable right, change supply, or directly impact the utility of {tokens}, it should NOT be considered relevant."

        prompt = f"""
        Analyze the following text from a crypto project source ({event.source_type.value}).
        Determine if it impacts the EXISTENCE or STRENGTH of a Token Functionality Subtype.
        
        CRITICAL NEGATIVE CONSTRAINTS:
        - Do NOT classify general market news, price discussions, or vague marketing as relevant.
        - Do NOT classify frontend UI updates (e.g. "We added a new button to our web app"), wallet integrations, exchange listings, or third-party partnerships as relevant.
        - The upgrade MUST be at the protocol or smart contract level, directly affecting the network's core features or token economics.
        - Be extremely conservative. When in doubt, it is NOT relevant.

        Use the following exact Subtype definitions to evaluate the text:

        **SERVICE PROVISION (SV-*)**
        SV-01 Sequencing/Execution: Right to execute state transitions/ordering.
        SV-02 Data Availability: Right to make payload available under guarantees.
        SV-03 Off-Chain Computation: Verifiable off-chain compute attested on-chain.
        SV-04 Crypto Proofs: Generate/verify ZK/validity proofs.
        SV-05 Oracle: Emit verifiable statements as truth.
        SV-06 Identity: Issue verifiable identity claims.
        SV-07 Indexing: Supply on-demand data access.
        SV-08 Storage: Long-term storage capacity allocation.
        SV-09 Interoperability Relay: Route messages/assets across domains.
        SV-10 Confidentiality Relay: Route data preserving privacy.
        SV-11 Physical Infrastructure (DePIN): Operate verifiable physical hardware.
        SV-12 Dispute Resolution: Adjudicate disputes.
        SV-13 State Attestation: Attest to block/state validity (e.g. standard PoS).

        **GOVERNANCE (G-*)** *(Scales: None / Signal / Partial / Unilateral)*
        G-01 Economic: Change fees, emissions, slashing.
        G-02 Technical: Codebase or architecture changes.
        G-03 Meta: Change decision-making rules.
        G-04 Treasury: Direct or burn on-chain treasury.
        G-05 Actor Set: Appoint/remove validators or councils.
        G-06 Product: Launch/retire markets or services.

        **VALUE DISTRIBUTION (VD-*)** *(Scales: One-off / Discretionary / Algorithmic)*
        VD-01 Direct Entitlement: Pro rata claim on surplus/revenue.
        VD-02 Burn Entitlement: Permanent token removal.
        VD-03 Buyback Entitlement: Redistribution of acquired tokens.
        VD-04 Inflation Entitlement: Receive newly minted units (without service risk).
        VD-05 Third-Party Rewards: Airdrops/rewards conditional on locking.

        **MEMBERSHIP (M-*)**
        M-01 Access Privilege: Gated venue/feature access.
        M-02 Preferential Pricing: Lower fees based on holding.
        M-03 Usage Quota Uplift: Higher usage allowance.

        **PAYMENTS (P-*)**
        P-01 Native Resource Fee: Mandatory internal resource fee (gas).
        P-02 General MoE: Widespread external payment acceptance.
        P-03 Prepaid Credit: Redeem token for future closed-loop service.
        P-04 Token-Settled Discount: Reduced price if paid in native token.

        **COLLATERAL & ASSET OWNERSHIP**
        C-01 Financial Collateral: Pledged for DeFi leverage (Exogenous).
        C-02 Stablecoin Reserve: Backing for a pegged currency.
        C-03 Risk Underwriting: Stake absorbs protocol/contract risk for premium.
        C-04 Performance Bond: Surety posted to guarantee delegated actor behavior.
        AO-01 On-Chain Asset: Claim on contract-controlled liquidity/assets.
        AO-02 Off-Chain Asset: Claim on RWA.

        Ultimately, if it impacts one of these functionalities for a relevant token, then it's relevant.
        {token_context_str}

        Text: "{event.text}"
        Source: {event.url}

        Return JSON:
        {{
            "is_relevant": bool,
            "affected_subtypes": [
                {{
                    "subtype_code": "The exact code from the cheat sheet (e.g., G-01, VD-02, SV-01)",
                    "impact_type": "Creation | Removal | Strength Change | Parameter Tweak",
                    "reason": "CRITICAL: You MUST explicitly quote the text that proves this. Then, explain the causal link of how that exact quote changes the enforceable rights or utility specifically for the token symbol listed in token_context. Do NOT hallucinate governance votes if the text does not explicitly mention them.",
                    "confidence": float (0.0 to 1.0 indicating your certainty),
                    "token_context": "The specific native token symbol affected (e.g., ETH, UNI)"
                }}
            ]
        }}
        """
        
        data = self.generate_json(prompt)
        
        affected_subtypes_data = data.get("affected_subtypes", [])
        
        parsed_subtypes = []
        for subtype in affected_subtypes_data:
            try:
                parsed_subtypes.append(AffectedSubtype(**subtype))
            except Exception as e:
                print(f"Error parsing subtype: {{e}}")
                continue
                
        is_relevant = data.get("is_relevant", len(parsed_subtypes) > 0)

        return RelevanceSignal(
            is_relevant=is_relevant,
            affected_subtypes=parsed_subtypes
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
        - **0.2 (Speculative):** Proposals, forum discussions, or roadmap mentions.
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
