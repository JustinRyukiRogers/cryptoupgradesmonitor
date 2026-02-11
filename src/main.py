import os
import yaml
import time
from datetime import datetime, timedelta
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from src.models import SourceRegistry, RawEvent, ProjectConfig
from src.ingestion.github_watcher import GitHubReleaseAgent
from src.ingestion.blog_watcher import BlogRSSAgent
from src.ingestion.x_watcher import XWatcherAgent
from src.analysis.relevance import RelevanceClassifierAgent
from src.analysis.status import UpgradeStatusAgent
from src.analysis.verification import VerificationAgent
from src.synthesis.canonical import UpgradeCanonicalizerAgent
from src.data_manager import StateManager, OutputManager

# Load Config
def load_registry(path: str = "source_registry.yaml") -> SourceRegistry:
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    return SourceRegistry(**data)

def main():
    print("Starting Crypto Upgrade Monitor...")
    registry = load_registry()
    
    # Initialize Managers
    state_manager = StateManager()
    output_manager = OutputManager()
    
    # Initialize Agents
    watchers = []
    print("Initializing Watchers & Restoring State...")
    for project_name, config in registry.projects.items():
        # Create watchers
        project_watchers = []
        if config.github_orgs:
            project_watchers.append(GitHubReleaseAgent(project_name, config))
        if config.blogs:
            project_watchers.append(BlogRSSAgent(project_name, config))
        if config.x_accounts and os.getenv("X_BEARER_TOKEN"):
            project_watchers.append(XWatcherAgent(project_name, config))
            
        # Restore State
        for w in project_watchers:
            watcher_id = f"{w.project_name}_{w.__class__.__name__}"
            cursor = state_manager.get_cursor(watcher_id)
            if cursor:
                w.last_seen_cursor = cursor
                print(f"  [{watcher_id}] Restored cursor: {cursor}")
            watchers.append(w)
            
    # Initialize Analysis Agents
    if os.getenv("GOOGLE_API_KEY"):
        print("Initializing AI Agents (Gemini Pro)...")
        from src.analysis.llm_agents import LLMRelevanceAgent, LLMVerificationAgent
        relevance_agent = LLMRelevanceAgent()
        verification_agent = LLMVerificationAgent()
    else:
        print("Initializing Heuristic Agents...")
        relevance_agent = RelevanceClassifierAgent()
        verification_agent = VerificationAgent()

    status_agent = UpgradeStatusAgent()
    canonicalizer = UpgradeCanonicalizerAgent()

    # Polling Loop
    while True:
        print("\n--- Polling Cycle ---")
        all_events: List[RawEvent] = []
        
        # 1. Ingestion
        for watcher in watchers:
            try:
                new_events = watcher.poll()
                if new_events:
                    print(f"Found {len(new_events)} events from {watcher.__class__.__name__} for {watcher.project_name}")
                    all_events.extend(new_events)
                    
                    # Update State
                    sorted_events = sorted(new_events, key=lambda x: x.timestamp)
                    latest_ts = sorted_events[-1].timestamp
                    watcher.update_cursor(latest_ts)
                    
                    watcher_id = f"{watcher.project_name}_{watcher.__class__.__name__}"
                    state_manager.update_cursor(watcher_id, latest_ts)
            except Exception as e:
                print(f"Error polling {watcher.__class__.__name__}: {e}")

        # 2. Filtering & Analysis
        project_events: Dict[str, List[RawEvent]] = {}
        for event in all_events:
            try:
                # Check relevance
                signals = relevance_agent.classify(event)
                if not signals.is_upgrade_related and not signals.is_economic:
                    continue
                
                if event.project not in project_events:
                    project_events[event.project] = []
                project_events[event.project].append(event)
            except Exception as e:
                print(f"Analysis error: {e}")

        # 3. Clustering & Verification
        # Group by Project -> Clusters (Time-based sliding window)
        # Events for a project within 24 hours of each other are considered part of the same "Upgrade Candidates".
        
        for project, events in project_events.items():
            if not events:
                continue

            # Sort events by time
            events.sort(key=lambda x: x.timestamp)
            
            # Create clusters
            clusters: List[List[RawEvent]] = []
            if events:
                current_cluster = [events[0]]
                for i in range(1, len(events)):
                    prev_event = current_cluster[-1]
                    curr_event = events[i]
                    # 24 hour window
                    if (curr_event.timestamp - prev_event.timestamp) <= timedelta(hours=24):
                        current_cluster.append(curr_event)
                    else:
                        clusters.append(current_cluster)
                        current_cluster = [curr_event]
                clusters.append(current_cluster)

            print(f"Project {project}: Formed {len(clusters)} clusters from {len(events)} events")

            for cluster in clusters:
                # Verification
                confirmation = verification_agent.verify(cluster)
                
                if confirmation.confidence < 0.4:
                    print(f"Skipping low confidence candidate for {project} (Score: {confirmation.confidence}) based on {len(cluster)} events")
                    print(f"Reasoning: {confirmation.reasoning}")
                    continue
                
                # Status
                statuses = [status_agent.determine_status(e) for e in cluster]
                final_status = statuses[0] 
                
                # Canonicalization
                canonical = canonicalizer.canonicalize(cluster, confirmation, final_status)
                
                print(f"\n[NEW UPGRADE DETECTED] {project.upper()}")
                print(f"Headline: {canonical.headline}")
                print(f"Status: {canonical.status.value}")
                print(f"Confidence: {canonical.confidence}")
                print("-" * 30)
                
                # 4. Output
                output_manager.save_upgrade(canonical)

        print("Cycle complete. Sleeping for 60s...")
        time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopping Monitor...")
