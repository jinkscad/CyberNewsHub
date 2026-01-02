"""
Google Sheets API Client for CyberNewsHub

This module provides a client to interact with the Google Apps Script API
that uses Google Spreadsheets as a database backend.
"""

import os
import requests
from datetime import datetime, timezone

# Google Apps Script Web App URL
# Set this via environment variable or directly here
SHEETS_API_URL = os.environ.get(
    'SHEETS_API_URL',
    'https://script.google.com/macros/s/AKfycbyummIyV5Mna2XzGWUT-9bZVoZuaUfx0KXkuPma7mMsmnRAI2Rct-SgDhRwFJCj_fwU/exec'
)

# Request timeout in seconds
REQUEST_TIMEOUT = 30


class SheetsClient:
    """Client for interacting with Google Sheets via Apps Script API"""

    def __init__(self, api_url=None):
        self.api_url = api_url or SHEETS_API_URL

    def _get(self, params):
        """Make a GET request to the API"""
        try:
            response = requests.get(
                self.api_url,
                params=params,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Sheets API GET error: {e}")
            raise

    def _post(self, data):
        """Make a POST request to the API"""
        try:
            response = requests.post(
                self.api_url,
                json=data,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Sheets API POST error: {e}")
            raise

    # ===== Health Check =====

    def health_check(self):
        """Check if the API is healthy"""
        return self._get({'action': 'health'})

    # ===== Article Operations =====

    def get_articles(self, page=1, per_page=50, category=None, publisher_type=None,
                     source=None, search=None, days=None, countries=None, sort='newest'):
        """Get articles with filtering and pagination"""
        params = {
            'action': 'articles',
            'page': page,
            'per_page': per_page,
            'sort': sort
        }

        if category:
            params['category'] = category
        if publisher_type:
            params['publisher_type'] = publisher_type
        if source:
            params['source'] = source
        if search:
            params['search'] = search
        if days:
            params['days'] = days
        if countries:
            params['countries'] = countries

        return self._get(params)

    def add_articles(self, articles):
        """Add multiple articles (with duplicate checking)"""
        return self._post({
            'action': 'add-articles',
            'articles': articles
        })

    def delete_article(self, link):
        """Delete a single article by its link"""
        return self._post({
            'action': 'delete-article',
            'link': link
        })

    def delete_by_source(self, source):
        """Delete all articles from a specific source"""
        return self._post({
            'action': 'delete-by-source',
            'source': source
        })

    # ===== Distinct Values =====

    def get_sources(self):
        """Get list of unique sources"""
        result = self._get({'action': 'sources'})
        return result.get('values', [])

    def get_categories(self):
        """Get list of unique content types"""
        result = self._get({'action': 'categories'})
        return result.get('values', [])

    def get_publisher_types(self):
        """Get list of unique publisher types"""
        result = self._get({'action': 'publisher-types'})
        return result.get('values', [])

    def get_countries(self):
        """Get list of unique countries"""
        result = self._get({'action': 'countries'})
        return result.get('values', [])

    # ===== Statistics =====

    def get_stats(self, days=None):
        """Get statistics about articles"""
        params = {'action': 'stats'}
        if days:
            params['days'] = days
        return self._get(params)

    # ===== Cleanup =====

    def cleanup_old_articles(self, days=90):
        """Delete articles older than specified days"""
        return self._post({
            'action': 'cleanup',
            'days': days
        })

    # ===== Feed Cache =====

    def get_feed_cache(self, feed_url):
        """Get cache entry for a feed URL"""
        result = self._get({
            'action': 'feed-cache',
            'feed_url': feed_url
        })
        return result.get('cache')

    def update_feed_cache(self, feed_url, etag=None, last_modified=None, content_hash=None):
        """Update or create cache entry for a feed URL"""
        return self._post({
            'action': 'update-feed-cache',
            'cache': {
                'feed_url': feed_url,
                'etag': etag or '',
                'last_modified': last_modified or '',
                'content_hash': content_hash or '',
                'last_fetched': datetime.now(timezone.utc).isoformat()
            }
        })


# Singleton instance
_client = None


def get_sheets_client():
    """Get the singleton SheetsClient instance"""
    global _client
    if _client is None:
        _client = SheetsClient()
    return _client
