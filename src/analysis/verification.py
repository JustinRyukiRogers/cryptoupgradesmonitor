from typing import List
from src.models import RawEvent, UpgradeConfirmation, Evidence, SourceType

class VerificationAgent:
    def __init__(self):
        # Weights from plan
        self.weights = {
            SourceType.BLOG: 0.4,
            SourceType.GITHUB: 0.35, # Executed tx/release
            SourceType.X: 0.25
        }
        self.multi_source_bonus = 0.1
        self.confirmed_threshold = 0.75
        self.tentative_threshold = 0.6

    def verify(self, events: List[RawEvent]) -> UpgradeConfirmation:
        """
        Takes a list of related events (grouped by potential upgrade) and calculates confidence.
        For MVP pipeline, we might be verifying a single event initially or a cluster.
        Let's assume we are scoring a SINGLE event independently first, 
        but the canonicalizer will aggregate scores.
        
        Wait, the plan says "Multiple independent confirmations: +0.1". 
        So this agent should ideally look at a cluster of events.
        
        However, if we are processing stream-wise:
        We can score each event's *contribution* to confidence.
        
        But the Output Model `CanonicalUpgrade` has a single `confidence`.
        So `VerificationAgent` likely runs AFTER aggregation or on the aggregate.
        
        Let's design `verify(events: List[RawEvent])` which assumes these events are for the SAME upgrade.
        """
        
        score = 0.0
        sources_seen = set()
        evidence_list = []
        
        # Reason building
        reasons = []

        for event in events:
            w = self.weights.get(event.source_type, 0.1)
            
            # Contextual modifiers
            # If X account is "official" keys (registry check needed? passed in event?)
            # Assuming ingestion only pulls from registry, so all are "official" enough to get base weight.
            
            # Explicit language bonus?
            if "live" in event.text.lower() or "activated" in event.text.lower():
                 w += 0.1
            
            # Add to score if source type not saturated? 
            # Or just sum weights? Summing weights can go > 1.0.
            # Plan: "Official blog confirmation: +0.4", "GitHub release: +0.35".
            # If we have both: 0.4 + 0.35 = 0.75 (Confirmed).
            
            if event.source_type not in sources_seen:
                score += w
                sources_seen.add(event.source_type)
            else:
                # Diminishing returns for same source type?
                score += (w * 0.5)

            evidence_list.append(Evidence(
                type=event.source_type.value,
                url=event.url,
                description=event.text[:100] + "..."
            ))
            reasons.append(f"{event.source_type.value}: {event.author}")

        # Multiple independent confirmations bonus
        if len(sources_seen) >= 2:
            score += self.multi_source_bonus

        # Cap at 1.0
        score = min(score, 1.0)
        
        confirmed = score >= self.confirmed_threshold
        
        return UpgradeConfirmation(
            is_confirmed=confirmed,
            confidence=score,
            evidence=evidence_list,
            reasoning=f"Score {score:.2f} from sources: {', '.join(reasons)}"
        )
