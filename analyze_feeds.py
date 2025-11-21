#!/usr/bin/env python3
"""
Quick diagnostic script to test RSS feeds and see why they're failing
"""
import requests
import feedparser
from backend.app import RSS_FEEDS

def test_feed(name, url):
    """Test a single feed and return error details"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*'
        }
        
        response = requests.get(url, timeout=15, headers=headers, allow_redirects=True)
        
        if response.status_code != 200:
            return f"HTTP {response.status_code}: {response.reason}"
        
        content_type = response.headers.get('Content-Type', '').lower()
        if 'html' in content_type and 'xml' not in content_type and 'rss' not in content_type:
            return f"Wrong content type: {content_type} (got HTML instead of RSS?)"
        
        feed = feedparser.parse(response.content)
        
        if feed.bozo and feed.bozo_exception:
            return f"Parse error: {feed.bozo_exception}"
        
        if not hasattr(feed, 'entries') or not feed.entries:
            return "No entries in feed"
        
        return f"✓ OK ({len(feed.entries)} entries)"
        
    except requests.Timeout:
        return "Timeout (>15s)"
    except requests.ConnectionError as e:
        return f"Connection error: {str(e)[:80]}"
    except requests.HTTPError as e:
        return f"HTTP error: {e}"
    except Exception as e:
        return f"Error: {str(e)[:80]}"

def main():
    print("Testing RSS Feeds...")
    print("=" * 80)
    
    all_feeds = []
    for category, feeds in RSS_FEEDS.items():
        all_feeds.extend(feeds)
    
    print(f"\nTotal feeds to test: {len(all_feeds)}\n")
    
    # Test first 20 feeds as a sample
    print("Testing first 20 feeds (sample):")
    print("-" * 80)
    
    for i, feed in enumerate(all_feeds[:20], 1):
        result = test_feed(feed['name'], feed['url'])
        status = "✓" if result.startswith("✓") else "✗"
        print(f"{i:2d}. {status} {feed['name']}")
        print(f"    {result}")
        print(f"    URL: {feed['url']}")
        print()
    
    print("\n" + "=" * 80)
    print("\nTo test all feeds, run:")
    print("  python analyze_feeds.py --all")
    print("\nTo test a specific feed by name:")
    print("  python analyze_feeds.py --name 'Feed Name'")

if __name__ == '__main__':
    import sys
    if '--all' in sys.argv:
        all_feeds = []
        for category, feeds in RSS_FEEDS.items():
            all_feeds.extend(feeds)
        
        print(f"Testing all {len(all_feeds)} feeds...\n")
        results = {'ok': [], 'failed': []}
        
        for feed in all_feeds:
            result = test_feed(feed['name'], feed['url'])
            if result.startswith("✓"):
                results['ok'].append((feed['name'], feed['url']))
            else:
                results['failed'].append((feed['name'], feed['url'], result))
        
        print(f"\n✓ {len(results['ok'])} feeds working")
        print(f"✗ {len(results['failed'])} feeds failed\n")
        
        if results['failed']:
            print("Failed feeds:")
            print("-" * 80)
            for name, url, error in results['failed']:
                print(f"✗ {name}")
                print(f"  Error: {error}")
                print(f"  URL: {url}\n")
    
    elif '--name' in sys.argv:
        idx = sys.argv.index('--name')
        if idx + 1 < len(sys.argv):
            feed_name = sys.argv[idx + 1]
            all_feeds = []
            for category, feeds in RSS_FEEDS.items():
                all_feeds.extend(feeds)
            
            found = [f for f in all_feeds if feed_name.lower() in f['name'].lower()]
            if found:
                for feed in found:
                    print(f"Testing: {feed['name']}")
                    print(f"URL: {feed['url']}\n")
                    result = test_feed(feed['name'], feed['url'])
                    print(f"Result: {result}")
            else:
                print(f"Feed '{feed_name}' not found")
    else:
        main()

