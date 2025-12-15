"""
Groq-based article categorization using LLM.
Fast, free, and accurate.
Get your free API key at: https://console.groq.com
"""

import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Cache for efficiency
_cache = {}

# Reusable session for better performance
_session = None

def get_session():
    """Get or create a reusable requests session with connection pooling."""
    global _session
    if _session is None:
        _session = requests.Session()
        # Configure retry strategy
        retry_strategy = Retry(
            total=2,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        _session.mount("http://", adapter)
        _session.mount("https://", adapter)
    return _session


def categorize_with_groq(title, description):
    """
    Categorize article using Groq LLM API.

    Returns:
        tuple: (category, confidence) or (None, 0) if unavailable
    """
    if not GROQ_API_KEY:
        return None, 0

    # Check cache
    cache_key = f"{title}|{description}"
    if cache_key in _cache:
        return _cache[cache_key]

    text = f"{title}. {description or ''}"[:500]

    prompt = f"""Categorize this cybersecurity article into exactly ONE category.

Categories:
- News: Incident reports, breaches, attacks, hacks, ransomware events
- Alert: Security advisories, CVE disclosures, vulnerability warnings, patches
- Research: Security research, technical analysis, whitepapers, studies
- Event: Conferences, webinars, summits, workshops, training

Article: {text}

Respond with ONLY the category name (News, Alert, Research, or Event), nothing else."""

    try:
        session = get_session()
        response = session.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 10
            },
            timeout=3  # Reduced from 10s to 3s for faster fallback
        )

        if response.status_code == 200:
            result = response.json()
            category_raw = result['choices'][0]['message']['content'].strip()

            # Normalize the response
            category_lower = category_raw.lower()
            if 'news' in category_lower:
                category = 'News'
            elif 'alert' in category_lower:
                category = 'Alert'
            elif 'research' in category_lower:
                category = 'Research'
            elif 'event' in category_lower:
                category = 'Event'
            else:
                category = 'News'  # Default

            # Cache result
            _cache[cache_key] = (category, 0.9)
            return category, 0.9
        else:
            print(f"Groq API error: {response.status_code}")
            return None, 0

    except Exception as e:
        print(f"Groq categorization error: {e}")
        return None, 0


def is_available():
    """Check if Groq API is configured."""
    return bool(GROQ_API_KEY)
