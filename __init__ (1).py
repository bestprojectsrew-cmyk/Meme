"""
Caption AI / Humor Engine
SRS Reference: Part 2 Sec 9.2 (Humor Engine, Caption AI), Part 3 Sec 25 (AI Providers - Gemini priority 1),
Part 6 Sec 71-72 (Prompt Structure, Brand Personality Engine)

Uses Google Gemini's free tier (gemini-1.5-flash or gemini-2.0-flash) as primary provider,
matching SRS provider priority order: Gemini -> Groq -> OpenRouter -> HuggingFace.

Get a free API key: https://aistudio.google.com/app/apikey
"""

import os
import json
import re
from dataclasses import dataclass
from typing import List, Optional

import requests

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


@dataclass
class MemeIdea:
    """Mirrors SRS Part 4 Sec 35.5 'Meme Ideas' table schema."""
    caption_top: str
    caption_bottom: str
    humor_style: str
    confidence_score: float
    originality_score: float


# SRS Part 6 Sec 71.2: Every prompt should contain System Role, Objective, Business Context,
# Brand Personality, Audience, Platform, Output Format, Restrictions, Safety Rules.
SYSTEM_PROMPT = """You are the Caption AI for an Instagram meme account targeting Gen Z (ages 16-26).

BRAND PERSONALITY: Gen Z humor - ironic, self-aware, relatable, fast-paced. Use current internet
vocabulary naturally (not forced). Absurdist or deadpan delivery often lands better than explaining the joke.

AUDIENCE: Gen Z social media users who scroll fast. Captions must land in under 2 seconds of reading.

PLATFORM: Instagram meme post, classic top-text/bottom-text format.

OBJECTIVE: Given a trending topic, generate {n} distinct meme caption concepts.

OUTPUT FORMAT: Return ONLY valid JSON, no markdown, no commentary. Format:
[
  {{
    "caption_top": "short punchy setup, ALL CAPS not required in your output, max 60 chars",
    "caption_bottom": "punchline or reaction, max 60 chars, can be empty string if one-liner",
    "humor_style": "one of: relatable, ironic, absurd, deadpan, self-deprecating, wordplay",
    "confidence_score": 0.0-1.0 (how funny/likely to land you think this is),
    "originality_score": 0.0-1.0 (how non-generic this is)
  }}
]

SAFETY RULES (non-negotiable):
- No hate speech, slurs, or targeting protected groups
- No real named private individuals
- No graphic violence references
- No NSFW/sexual content
- Keep it brand-safe for a general Instagram audience
- If the trend topic itself is a tragedy, serious crime, or death, do not joke about victims - skip dark angles entirely and return an empty list

TREND TOPIC: "{trend_title}"
TREND CATEGORY: {trend_category}
"""


def _build_prompt(trend_title: str, trend_category: str, n: int = 5) -> str:
    return SYSTEM_PROMPT.format(n=n, trend_title=trend_title, trend_category=trend_category)


def _call_gemini(prompt: str) -> Optional[str]:
    """
    Raw call to Gemini's generateContent endpoint.
    SRS Part 4 Sec 43: AI Provider Abstraction - this is the Gemini-specific implementation
    behind the generic AIProvider.GenerateText() interface.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY environment variable not set. "
            "Get a free key at https://aistudio.google.com/app/apikey"
        )

    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.9,  # higher creativity for humor generation
            "maxOutputTokens": 1024,
        },
    }

    try:
        resp = requests.post(GEMINI_URL, headers=headers, params=params, json=body, timeout=20.0)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except requests.exceptions.HTTPError as e:
        # SRS Part 3 Sec 33: Circuit breaker for repeated API failures - for MVP we log and
        # surface None so the caller can fall back / skip this trend rather than crash.
        print(f"[caption_ai] Gemini API error: {e} | Response: {getattr(e.response, 'text', '')[:300]}")
        return None
    except Exception as e:
        print(f"[caption_ai] Gemini call failed: {e}")
        return None


def _parse_ideas(raw_text: str) -> List[MemeIdea]:
    """
    Parses the model's JSON output into MemeIdea objects.
    Defensive parsing since LLMs sometimes wrap JSON in markdown fences despite instructions.
    """
    if not raw_text:
        return []

    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw_text.strip(), flags=re.MULTILINE)

    try:
        items = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"[caption_ai] Failed to parse JSON from model output: {e}")
        return []

    ideas = []
    for item in items:
        try:
            ideas.append(
                MemeIdea(
                    caption_top=item.get("caption_top", "").strip(),
                    caption_bottom=item.get("caption_bottom", "").strip(),
                    humor_style=item.get("humor_style", "relatable"),
                    confidence_score=float(item.get("confidence_score", 0.5)),
                    originality_score=float(item.get("originality_score", 0.5)),
                )
            )
        except (ValueError, TypeError):
            continue

    return ideas


def generate_meme_ideas(trend_title: str, trend_category: str = "general", n: int = 5) -> List[MemeIdea]:
    """
    Main entry point - SRS Part 1 Sec 8: 'Caption Generator creates multiple joke candidates.'
    """
    prompt = _build_prompt(trend_title, trend_category, n)
    raw_output = _call_gemini(prompt)
    ideas = _parse_ideas(raw_output)

    # SRS Part 1 Sec 8: 'Humor Evaluator ranks captions.' - simple MVP ranking by combined score.
    ideas.sort(key=lambda i: (i.confidence_score + i.originality_score), reverse=True)

    return ideas


if __name__ == "__main__":
    # Manual test - requires GEMINI_API_KEY env var set
    ideas = generate_meme_ideas(
        trend_title="Messi scores last-minute winner in World Cup 2026 group stage",
        trend_category="soccer",
    )

    if not ideas:
        print("No ideas generated. Check GEMINI_API_KEY is set and valid.")
    else:
        for idea in ideas:
            print(f"\n[{idea.humor_style}] conf={idea.confidence_score} orig={idea.originality_score}")
            print(f"  TOP: {idea.caption_top}")
            print(f"  BOTTOM: {idea.caption_bottom}")
