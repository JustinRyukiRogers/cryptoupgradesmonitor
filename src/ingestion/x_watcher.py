import os
import tweepy
from typing import List
from datetime import datetime, timezone
from src.models import RawEvent, ProjectConfig, SourceType
from src.ingestion.base import BaseWatcher

class XWatcherAgent(BaseWatcher):
    def __init__(self, project_name: str, config: ProjectConfig):
        super().__init__(project_name, config)
        
        # Authentication
        # Using OAuth 2.0 Bearer Token (App-only) is usually sufficient for reading public tweets 
        # but X API v2 access levels vary. Assuming Basic/Pro access.
        self.bearer_token = os.getenv("X_BEARER_TOKEN")
        self.client = None
        
        if self.bearer_token:
            self.client = tweepy.Client(bearer_token=self.bearer_token)
        else:
             # Fallback to consumer keys if needed, or just warn
             pass

    def poll(self) -> List[RawEvent]:
        if not self.client:
            print(f"XWatcherAgent for {self.project_name}: No valid credentials.")
            return []

        events = []
        # X API v2 limits are strict.
        # We need to look up User IDs from usernames first (can be cached), then get timeline.
        # For efficiency in MVP, we might only poll the first few accounts.
        
        for handle in self.config.x_accounts:
            username = handle.lstrip('@')
            try:
                # 1. Get User ID (Cache this in production!)
                user = self.client.get_user(username=username)
                if not user.data:
                    print(f"User {username} not found")
                    continue
                user_id = user.data.id

                # 2. Get User Tweets
                # exclude=['retweets', 'replies'] might be good to reduce noise, but sometimes upgrades are in threads.
                # Let's include everything but filter later? Or just exclude replies.
                # start_time needs to be RFC3339 string.
                
                start_time = None
                if self.last_seen_cursor:
                    start_time = self.last_seen_cursor.isoformat()

                tweets = self.client.get_users_tweets(
                    id=user_id,
                    max_results=5, # Minimal for polling
                    exclude=['replies'],
                    tweet_fields=['created_at', 'author_id', 'text']
                )

                if not tweets.data:
                    continue

                for tweet in tweets.data:
                    created_at = tweet.created_at # Tweepy returns datetime (aware)
                    
                    if self.last_seen_cursor and created_at <= self.last_seen_cursor:
                        continue
                        
                    raw_event = RawEvent(
                        project=self.project_name,
                        source_type=SourceType.X,
                        author=handle,
                        text=tweet.text,
                        url=f"https://x.com/{username}/status/{tweet.id}",
                        timestamp=created_at,
                        raw_data=tweet.data
                    )
                    events.append(raw_event)

            except Exception as e:
                print(f"Error polling X for {username}: {e}")
                continue

        events.sort(key=lambda x: x.timestamp)
        return events
