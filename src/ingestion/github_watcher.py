import os
import requests
from typing import List, Dict, Any
from datetime import datetime
from src.models import RawEvent, ProjectConfig, SourceType
from src.ingestion.base import BaseWatcher

class GitHubReleaseAgent(BaseWatcher):
    def __init__(self, project_name: str, config: ProjectConfig):
        super().__init__(project_name, config)
        self.token = os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def poll(self) -> List[RawEvent]:
        events = []
        for org in self.config.github_orgs:
            # Note: This is a simplification. To get all releases for an org, 
            # we'd need to list repos first, or use the search API, or config should list specific repos.
            # For MVP, assuming config might list "Owner/Repo" strings or we just check key repos.
            # The Registry schema says "github_orgs", so we might need to fetch repos for the org.
            # HOWEVER, for MVP efficiency, let's assume we search for releases in the org.
            # A better approach given the registry schema "github_orgs" is to search for recent releases in that org.
            
            # Using Search API to find recent releases in the org
            # query: "org:ORG_NAME is:public" but search API for releases is not direct.
            # Best MVP approach: List repos (sorted by pushed) and check releases for top N active repos?
            # Or asking user to be more specific in registry. 
            # Let's try listing repos for the org and checking releases for each.
            
            # Rate limit caution: Listing all repos and releases is expensive.
            # Optimization: User's registry schema is "github_orgs". 
            # Let's iterate repos.
            
            repos_url = f"https://api.github.com/orgs/{org}/repos?sort=pushed&direction=desc&per_page=5"
            try:
                response = requests.get(repos_url, headers=self.headers)
                response.raise_for_status()
                repos = response.json()
            except Exception as e:
                print(f"Error fetching repos for {org}: {e}")
                continue

            for repo in repos:
                repo_name = repo["name"]
                full_name = repo["full_name"]
                # Increased limit for better historical context
                releases_url = f"https://api.github.com/repos/{full_name}/releases?per_page=10"
                
                try:
                    r_resp = requests.get(releases_url, headers=self.headers)
                    r_resp.raise_for_status()
                    releases = r_resp.json()
                except Exception as e:
                    print(f"Error fetching releases for {full_name}: {e}")
                    continue

                for release in releases:
                    published_at_str = release.get("published_at")
                    if not published_at_str:
                        continue
                    
                    # Parse timestamp (ISO 8601)
                    # Python 3.11+ can use fromisoformat 
                    try:
                        published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
                    except ValueError:
                        continue

                    # Cursor check
                    if self.last_seen_cursor and published_at <= self.last_seen_cursor:
                        continue

                    raw_event = RawEvent(
                        project=self.project_name,
                        source_type=SourceType.GITHUB,
                        author=release.get("author", {}).get("login", "unknown"),
                        text=f"Release {release.get('name', release.get('tag_name'))}: {release.get('body', '')}",
                        url=release.get("html_url", ""),
                        timestamp=published_at,
                        raw_data=release
                    )
                    events.append(raw_event)
        
        # Sort by timestamp ascending to update cursor correctly later
        events.sort(key=lambda x: x.timestamp)
        return events
