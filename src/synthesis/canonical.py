from typing import List
from uuid import uuid4
from src.models import RawEvent, CanonicalUpgrade, UpgradeConfirmation, UpgradeStatus, UpgradeType

class UpgradeCanonicalizerAgent:
    def canonicalize(self, events: List[RawEvent], confirmation: UpgradeConfirmation, status: UpgradeStatus) -> CanonicalUpgrade:
        # Assumes events are already clustered and relate to the same upgrade
        
        if not events:
            raise ValueError("Cannot canonicalize empty event list")

        primary_event = events[0] # Earliest or most authoritative?
        # Sort by timestamp to find earliest
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        earliest_event = sorted_events[0]
        
        # Determine Source of Truth (Primary Source)
        # Ideally the one with highest weight? Or earliest?
        # Let's use the one that gave us the "verified" signal if possible, or just the first one.
        primary_source = earliest_event.url

        # Supporting sources
        supporting = [e.url for e in sorted_events if e.url != primary_source]

        # Determine Upgrade Type
        # Heuristic based on keywords in the aggregate text?
        # Or maybe the RelevanceClassifier already gave us signals.
        # For MVP, simple keyword match on the aggregate text of all events.
        
        full_text = " ".join([e.text for e in events]).lower()
        
        u_type = UpgradeType.OTHER_ECONOMIC
        if "fee" in full_text: u_type = UpgradeType.FEE_CHANGE
        elif "stake" in full_text or "slash" in full_text: u_type = UpgradeType.STAKING_SLASHING
        elif "emission" in full_text or "inflation" in full_text: u_type = UpgradeType.EMISSIONS_CHANGE
        elif "vote" in full_text or "proposal" in full_text: u_type = UpgradeType.GOVERNANCE_EXECUTION

        # Construct Headline
        # Use the text of the primary event, maybe truncated or summarized?
        # MVP: Use first event's text.
        headline = earliest_event.text[:100] + ("..." if len(earliest_event.text) > 100 else "")

        return CanonicalUpgrade(
            canonical_id=uuid4(),
            headline=headline,
            project=primary_event.project,
            network="ethereum", # TODO: Resolve network from registry/event
            upgrade_type=u_type,
            status=status,
            primary_source=primary_source,
            supporting_sources=supporting,
            timestamp=earliest_event.timestamp,
            confidence=confirmation.confidence,
            reasoning=confirmation.reasoning
        )
