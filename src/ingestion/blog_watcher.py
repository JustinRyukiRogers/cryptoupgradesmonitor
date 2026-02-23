import feedparser
import requests
import json
from bs4 import BeautifulSoup
from typing import List, Optional, Set
from datetime import datetime, timezone
from src.models import RawEvent, ProjectConfig, SourceType
from src.ingestion.base import BaseWatcher

class BlogRSSAgent(BaseWatcher):
    def poll(self) -> List[RawEvent]:
        all_events = []
        seen_urls = set()

        for blog_url in self.config.blogs:
            print(f"Polling blog: {blog_url}")
            
            # 1. Try RSS/Atom Feeds
            feed_events = self._poll_rss(blog_url)
            if feed_events:
                print(f"  Found {len(feed_events)} events via RSS")
                for e in feed_events:
                    if e.url not in seen_urls:
                        all_events.append(e)
                        seen_urls.add(e.url)
                continue # If RSS works, we might skip scraping to be polite, or check others? 
                         # Usually RSS is best. Let's stop if RSS works well.
            
            # 2. Try Sitemap
            print(f"  RSS failed or empty. Trying Sitemap...")
            sitemap_events = self._poll_sitemap(blog_url)
            if sitemap_events:
                print(f"  Found {len(sitemap_events)} events via Sitemap")
                for e in sitemap_events:
                    if e.url not in seen_urls:
                        all_events.append(e)
                        seen_urls.add(e.url)
                continue

            # 3. Try HTML Fallback (Listing Page)
            print(f"  Sitemap failed. Trying HTML scraping...")
            html_events = self._poll_html(blog_url)
            if html_events:
                print(f"  Found {len(html_events)} events via HTML scraping")
                for e in html_events:
                    if e.url not in seen_urls:
                        all_events.append(e)
                        seen_urls.add(e.url)

        all_events.sort(key=lambda x: x.timestamp)
        
        # Ingestion logic handles finding events newer than last_seen_cursor
        # Limit initial fetch to avoid overwhelming the pipeline
        if not self.last_seen_cursor:
            # Sort and take latest N to avoid processing entire history on first run
            if len(all_events) > 20:
                print(f"  [Limit] Returning latest 20 events for initial poll")
                all_events = all_events[-20:]
            
        return all_events

    def _poll_rss(self, blog_url: str) -> List[RawEvent]:
        # ... (Existing RSS logic with minor refactor) ...
        # Common feed paths
        base = blog_url if blog_url.startswith("http") else f"https://{blog_url}"
        feed_urls = [
            f"{base.rstrip('/')}/feed",
            f"{base.rstrip('/')}/rss",
            f"{base.rstrip('/')}/rss.xml",
            f"{base.rstrip('/')}/feed.xml", # Common for Jekyll/GitHub Pages (like Ethereum blog)
            f"{base.rstrip('/')}/index.xml",
            base # Sometimes base URL is the feed
        ]
        
        for url in feed_urls:
            try:
                # Use requests first to handle SSL/User-Agent better than feedparser's internal fetcher
                # The debug script showed feedparser failing SSL while requests succeeded.
                headers = {"User-Agent": "CryptoUpgradeMonitor/1.0"}
                resp = requests.get(url, headers=headers, timeout=10)
                
                if resp.status_code == 200:
                    # Parse the content directly
                    f = feedparser.parse(resp.content)
                    
                    if len(f.entries) > 0:
                        events = []
                        for entry in f.entries:
                            events.append(self._parse_feed_entry(entry))
                        return [e for e in events if e is not None]
                else:
                    # Fallback to standard feedparser if requests fails (unlikely given debug results)
                    f = feedparser.parse(url)
                    if not f.bozo and len(f.entries) > 0:
                        events = []
                        for entry in f.entries:
                            events.append(self._parse_feed_entry(entry))
                        return [e for e in events if e is not None]

            except Exception as e:
                # print(f"Error fetching RSS {url}: {e}")
                continue
        return []

    def _parse_feed_entry(self, entry) -> Optional[RawEvent]:
        # Helper to parse feedparser entry
        published_time = None
        if hasattr(entry, 'published_parsed'):
             published_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        elif hasattr(entry, 'updated_parsed'):
             published_time = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
        
        if not published_time:
            return None
            
        if self.last_seen_cursor and published_time <= self.last_seen_cursor:
            return None

        return RawEvent(
            project=self.project_name,
            source_type=SourceType.BLOG,
            author=entry.get('author', 'unknown'),
            text=f"{entry.get('title', '')}: {entry.get('summary', '')}",
            url=entry.get('link', ''),
            timestamp=published_time,
            raw_data=dict(entry)
        )

    def _poll_sitemap(self, blog_url: str) -> List[RawEvent]:
        base = blog_url if blog_url.startswith("http") else f"https://{blog_url}"
        sitemap_url = f"{base.rstrip('/')}/sitemap.xml"
        
        try:
            resp = requests.get(sitemap_url, timeout=10)
            if resp.status_code != 200:
                return []
            
            soup = BeautifulSoup(resp.content, 'xml')
            urls = soup.find_all('url')
            
            # We will process all sitemap URLs and rely on the sorting and limit in `poll()`
            # to return the correct top 20 latest events.
            events = []
            for url_tag in urls:
                loc = url_tag.find('loc').text if url_tag.find('loc') else None
                lastmod = url_tag.find('lastmod').text if url_tag.find('lastmod') else None
                
                if not loc or not lastmod:
                    continue
                
                # Filter for blog post patterns if possible?
                # Or just ingest everything and let Relevance agent filter.
                
                try:
                    # ISO 8601 parsing
                    # lastmod might be YYYY-MM-DD or full datetime
                    if 'T' in lastmod:
                        dt = datetime.fromisoformat(lastmod.replace('Z', '+00:00'))
                    else:
                        dt = datetime.fromisoformat(lastmod)
                    
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
                    
                if self.last_seen_cursor and dt <= self.last_seen_cursor:
                    continue
                
                # Note: Sitemap doesn't have title/text usually. 
                # We might need to fetch the page to get title, or just return URL.
                # User wants "Text" for relevance checking.
                # MVP: Fetch page title? Or just return URL as text?
                # Let's try to fetch page title efficiently? No, too slow for sitemap.
                # Let's use URL as headline and hope RelevanceAgent can fetch or infer?
                # Actually, `RawEvent` expects `text`. 
                # Improving robustness: Let's fetch the page content for the *new* items only.
                
                events.append(self._fetch_page_metadata(loc, dt))
                
            return [e for e in events if e is not None]
        except Exception as e:
            print(f"Sitemap error: {e}")
            return []

    def _poll_html(self, blog_url: str) -> List[RawEvent]:
        base = blog_url if blog_url.startswith("http") else f"https://{blog_url}"
        
        try:
            headers = {"User-Agent": "CryptoUpgradeMonitor/1.0"}
            resp = requests.get(base, headers=headers, timeout=10)
            if resp.status_code != 200:
                print(f"HTML fetch failed: {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            events = []
            
            # Heuristic: Look for <article> tags or divs with 'post' class
            articles = soup.find_all('article')
            if not articles:
                 # Check for common blog patterns
                 # expanded to include 'entry', 'item', and role='article'
                 articles = soup.find_all('div', class_=lambda x: x and any(c in x for c in ['post', 'entry', 'item', 'article']))
            
            if not articles:
                 # Try finding elements with role="article"
                 articles = soup.find_all(attrs={"role": "article"})
            
            if not articles:
                # Fallback: Look for <a> tags
                # This leads to too much noise.
                return []
                
            for article in articles:
                # Extract Link
                a_tag = article.find('a')
                if not a_tag: continue
                link = a_tag.get('href')
                if not link: continue
                
                # Resolve relative link
                if link.startswith('/'):
                    link = f"{base.rstrip('/')}{link}"
                elif not link.startswith('http'):
                    link = f"{base.rstrip('/')}/{link}"
                
                # Extract Title
                title = article.get_text().strip()[:200]
                if a_tag.get_text():
                    title = a_tag.get_text().strip()
                
                # Extract Date logic is hard in generic HTML.
                # Try <time> tag
                dt = datetime.now(timezone.utc) # Default to now if not found? Risk of dupes.
                time_tag = article.find('time')
                if time_tag and time_tag.get('datetime'):
                    try:
                        dt_str = time_tag.get('datetime').replace('Z', '+00:00')
                        dt = datetime.fromisoformat(dt_str)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                    except: pass
                
                if self.last_seen_cursor and dt <= self.last_seen_cursor:
                    continue
                
                events.append(RawEvent(
                    project=self.project_name,
                    source_type=SourceType.BLOG,
                    author="unknown",
                    text=title,
                    url=link,
                    timestamp=dt,
                    raw_data={"html_snippet": str(article)[:500]}
                ))
                
            return events

        except Exception as e:
            print(f"HTML scraping error: {e}")
            return []

    def _fetch_page_metadata(self, url: str, timestamp: datetime) -> Optional[RawEvent]:
        try:
            resp = requests.get(url, timeout=5, headers={"User-Agent": "CryptoUpgradeMonitor/1.0"})
            if resp.status_code != 200: return None
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            title = soup.title.string if soup.title else url
            
            # Description from meta
            desc = ""
            meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
            if meta_desc:
                desc = meta_desc.get('content', '')
            
            text = f"{title}: {desc}"
            
            # Extract true published timestamp
            published_time = timestamp
            
            # First try regex on ALL body text to find the earliest mentioned date
            import re
            body_text = soup.get_text() 
            # We want to find all dates and take the earliest one that makes sense
            matches = re.finditer(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, \d{4}', body_text)
            
            found_dates = []
            for match in matches:
                try:
                    dt = datetime.strptime(match.group(0).replace("Sept", "Sep")[:12]+match.group(0)[-5:], '%b %d, %Y').replace(tzinfo=timezone.utc)
                    found_dates.append(dt)
                except:
                    try:
                        dt = datetime.strptime(match.group(0), '%B %d, %Y').replace(tzinfo=timezone.utc)
                        found_dates.append(dt)
                    except: pass
            
            # If we found dates, take the very first one (which corresponds to the article header before the body)
            if found_dates:
                published_time = found_dates[0]
            
            # Fallback to metadata ONLY if regex found absolutely nothing
            if published_time == timestamp:
                meta_date = soup.find('meta', attrs={'property': 'article:published_time'})
                if meta_date:
                    try:
                        dt_str = meta_date.get('content', '').replace('Z', '+00:00')
                        dt = datetime.fromisoformat(dt_str)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        published_time = dt
                    except: pass

            return RawEvent(
                project=self.project_name,
                source_type=SourceType.BLOG,
                author="unknown",
                text=text,
                url=url,
                timestamp=published_time,
                raw_data={"scraped": True}
            )
        except Exception as e:
            print(f"Error fetching metadata for {url}: {e}")
            return None
