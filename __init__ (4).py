"""
Trend Detection Service - Reddit Source
SRS Reference: Part 1 Sec 8 (Trend Collector), Part 3 Sec 25 (Trend Sources), Part 3 Sec 31 (Trend Detection Pipeline)

Fetches trending/hot posts from Reddit's public JSON endpoints.
No API key required for read-only access to public listings.
"""

import requests
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import List


@dataclass
class TrendItem:
    """Mirrors SRS Part 4 Sec 35.4 'Trends Table' schema."""
    source: str
    title: str
    description: str
    url: str
    category: str
    popularity_score: float   # derived from upvotes
    velocity_score: float     # derived from upvotes / age
    detected_language: str = "en"
    country: str = "global"
    created_at: str = ""

    def to_dict(self):
        return asdict(self)


# Subreddits to monitor. Mix of general + current-events + meme-adjacent.
# SRS Part 1 Sec 9.2: "Monitor Reddit" is an explicit Trend Intelligence Agent responsibility.
DEFAULT_SUBREDDITS = [
    "all",          # general site-wide trending
    "soccer",       # World Cup / football specific
    "worldnews",    # breaking events with meme potential
    "memes",        # what's already resonating format-wise
    "popculturechat",
]

USER_AGENT = "MemePulseAI-TrendBot/0.1 (contact: founder@memepulseai.local)"


def fetch_subreddit_hot(subreddit: str, limit: int = 15) -> List[TrendItem]:
    """
    Pulls the 'hot' listing for a subreddit via Reddit's public JSON API.
    This endpoint requires no authentication for public subreddits.
    """
    url = f"https://www.reddit.com/r/{subreddit}/hot.json"
    params = {"limit": limit}
    headers = {"User-Agent": USER_AGENT}

    items: List[TrendItem] = []

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        # SRS Part 3 Sec 33: Error Handling - every module must implement retry/graceful degradation.
        # For MVP: log and return empty list rather than crashing the whole pipeline.
        print(f"[trend_collector] Failed to fetch r/{subreddit}: {e}")
        return items

    posts = data.get("data", {}).get("children", [])

    for post in posts:
        p = post.get("data", {})

        # Skip stickied/mod posts - rarely meme-worthy, usually rules/announcements
        if p.get("stickied"):
            continue

        ups = p.get("ups", 0)
        created_utc = p.get("created_utc", 0)
        age_hours = max(
            (datetime.now(timezone.utc).timestamp() - created_utc) / 3600.0, 0.1
        )

        velocity = round(ups / age_hours, 2)

        items.append(
            TrendItem(
                source=f"reddit/r/{subreddit}",
                title=p.get("title", "").strip(),
                description=p.get("selftext", "")[:280].strip(),
                url=f"https://reddit.com{p.get('permalink', '')}",
                category=subreddit,
                popularity_score=float(ups),
                velocity_score=velocity,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        )

    return items


def collect_trends(subreddits: List[str] = None, limit_per_sub: int = 15) -> List[TrendItem]:
    """
    Main entry point for the Trend Collector.
    SRS Part 1 Sec 8: "Trend Collector downloads current trends."
    """
    subreddits = subreddits or DEFAULT_SUBREDDITS
    all_items: List[TrendItem] = []

    for sub in subreddits:
        all_items.extend(fetch_subreddit_hot(sub, limit=limit_per_sub))

    return all_items


def deduplicate_trends(items: List[TrendItem]) -> List[TrendItem]:
    """
    SRS Part 1 Sec 8: "Duplicate detector removes repeated topics."
    Simple title-based dedup for MVP. Future: semantic similarity (Part 7 Sec 79).
    """
    seen_titles = set()
    deduped = []

    for item in items:
        normalized = item.title.lower().strip()
        if normalized and normalized not in seen_titles:
            seen_titles.add(normalized)
            deduped.append(item)

    return deduped


if __name__ == "__main__":
    # Quick manual test
    trends = collect_trends()
    trends = deduplicate_trends(trends)
    trends.sort(key=lambda t: t.velocity_score, reverse=True)

    print(f"\nFetched {len(trends)} unique trending items.\n")
    for t in trends[:10]:
        print(f"[{t.category}] (vel={t.velocity_score}) {t.title}")
