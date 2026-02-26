from typing import List, Dict
from uuid import uuid4
from src.models import RawEvent, CanonicalUpgrade, UpgradeConfirmation, UpgradeStatus, AffectedSubtype

class UpgradeCanonicalizerAgent:
    def canonicalize(self, events: List[RawEvent], confirmation: UpgradeConfirmation, status: UpgradeStatus, event_subtypes: Dict[str, List[AffectedSubtype]] = None) -> CanonicalUpgrade:
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

        # Construct Headline
        # Text usually starts with "Title: Desc\n\n[Body]". We split by \n\n to isolate the title block
        first_segment = earliest_event.text.split('\n\n')[0].strip()
        
        if len(first_segment) > 120:
            headline = first_segment[:117] + "..."
        else:
            headline = first_segment

        # Aggregate affected subtypes
        aggregated_subtypes = []
        seen_subtypes = set()
        if event_subtypes:
            for e in events:
                subtypes = event_subtypes.get(str(e.event_id), [])
                for st in subtypes:
                    key = f"{st.subtype_code}_{st.impact_type}"
                    if key not in seen_subtypes:
                        seen_subtypes.add(key)
                        aggregated_subtypes.append(st)

        return CanonicalUpgrade(
            canonical_id=uuid4(),
            headline=headline,
            project=primary_event.project,
            network="ethereum", # TODO: Resolve network from registry/event
            status=status,
            primary_source=primary_source,
            supporting_sources=supporting,
            timestamp=earliest_event.timestamp,
            confidence=confirmation.confidence,
            reasoning=confirmation.reasoning,
            affected_subtypes=aggregated_subtypes
        )
