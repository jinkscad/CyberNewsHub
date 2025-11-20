from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
import feedparser
import requests
from dateutil import parser as date_parser
import re
import os
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

load_dotenv()

app = Flask(__name__)
# Use absolute path for database
db_path = os.path.join(os.path.dirname(__file__), 'cybernews.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)

db = SQLAlchemy(app)

# RSS Feed Sources Configuration
RSS_FEEDS = {
    'industry': [
        {'name': 'The Hacker News', 'url': 'https://feeds.feedburner.com/TheHackersNews', 'category': 'Industry'},
        {'name': 'BleepingComputer', 'url': 'https://www.bleepingcomputer.com/feed/', 'category': 'Industry'},
        {'name': 'Krebs on Security', 'url': 'https://krebsonsecurity.com/feed/', 'category': 'Industry'},
        {'name': 'Dark Reading', 'url': 'https://www.darkreading.com/rss.xml', 'category': 'Industry'},
        {'name': 'SC Magazine', 'url': 'https://www.scmagazine.com/home/feed/', 'category': 'Industry'},
        {'name': 'SecurityWeek', 'url': 'https://feeds.securityweek.com/securityweek/', 'category': 'Industry'},
    ],
    'government': [
        {'name': 'CISA', 'url': 'https://www.cisa.gov/news.xml', 'category': 'Government'},
        {'name': 'US-CERT Alerts', 'url': 'https://www.us-cert.gov/ncas/alerts.xml', 'category': 'Government'},
        {'name': 'ENISA', 'url': 'https://www.enisa.europa.eu/news/enisa-news/RSS', 'category': 'Government'},
        {'name': 'NCSC UK', 'url': 'https://www.ncsc.gov.uk/api/1/services/v1/news-rss-feed.xml', 'category': 'Government'},
        {'name': 'CERT-EU', 'url': 'https://cert.europa.eu/public/news.rss', 'category': 'Government'},
        {'name': 'CSA Singapore', 'url': 'https://www.csa.gov.sg/rss', 'category': 'Government'},
        {'name': 'CCCS Advisories', 'url': 'https://cyber.gc.ca/en/rss/advisories.xml', 'category': 'Government'},
        {'name': 'CCCS Alerts', 'url': 'https://cyber.gc.ca/en/rss/alerts.xml', 'category': 'Government'},
        {'name': 'CCCS News', 'url': 'https://cyber.gc.ca/en/rss/news.xml', 'category': 'Government'},
    ],
    'vendors': [
        {'name': 'Microsoft Security', 'url': 'https://www.microsoft.com/en-us/security/blog/feed/', 'category': 'Vendor'},
        {'name': 'Google Security', 'url': 'https://security.googleblog.com/feeds/posts/default', 'category': 'Vendor'},
        {'name': 'Cisco Talos', 'url': 'https://blog.talosintelligence.com/feed/', 'category': 'Vendor'},
        {'name': 'Cloudflare Blog', 'url': 'https://blog.cloudflare.com/rss/', 'category': 'Vendor'},
        {'name': 'Palo Alto Unit42', 'url': 'https://unit42.paloaltonetworks.com/feed/', 'category': 'Vendor'},
        {'name': 'CrowdStrike', 'url': 'https://www.crowdstrike.com/blog/feed/', 'category': 'Vendor'},
        {'name': 'FireEye', 'url': 'https://www.fireeye.com/blog/feed', 'category': 'Vendor'},
        {'name': 'Sophos', 'url': 'https://news.sophos.com/en-us/feed/', 'category': 'Vendor'},
        {'name': 'Kaspersky SecureList', 'url': 'https://securelist.com/feed/', 'category': 'Vendor'},
    ],
    'research': [
        {'name': 'Citizen Lab', 'url': 'https://citizenlab.ca/feed/', 'category': 'Research'},
        {'name': 'Check Point Research', 'url': 'https://research.checkpoint.com/feed/', 'category': 'Research'},
        {'name': 'Recorded Future', 'url': 'https://www.recordedfuture.com/feed', 'category': 'Research'},
        {'name': 'SANS ISC', 'url': 'https://isc.sans.edu/rssfeed.xml', 'category': 'Research'},
        {'name': 'Rapid7', 'url': 'https://www.rapid7.com/blog/feed/', 'category': 'Research'},
    ]
}

# Database Models
class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    link = db.Column(db.Text, unique=True, nullable=False)
    description = db.Column(db.Text)
    source = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))  # Keep for backward compatibility (maps to content_type)
    publisher_type = db.Column(db.String(50))  # Industry, Government, Vendor, Research
    content_type = db.Column(db.String(50))  # News, Research, Event, Alert, Vulnerability, etc.
    country_region = db.Column(db.String(20))  # US, UK, EU, CA, SG, Global, etc.
    published_date = db.Column(db.DateTime, nullable=False)
    fetched_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'link': self.link,
            'description': self.description,
            'source': self.source,
            'publisher_type': self.publisher_type,
            'category': self.content_type,  # Keep 'category' for backward compatibility with frontend
            'content_type': self.content_type,
            'country_region': self.country_region or 'Global',
            'published_date': self.published_date.isoformat() if self.published_date else None,
            'fetched_date': self.fetched_date.isoformat() if self.fetched_date else None
        }

def clean_html(text):
    """Remove HTML tags from text"""
    if not text:
        return ""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def get_country_region(source_name, url):
    """Determine country/region from source name or URL"""
    source_lower = source_name.lower()
    url_lower = url.lower() if url else ''
    
    # Government sources by country
    if 'cisa' in source_lower or 'us-cert' in source_lower or '.gov' in url_lower:
        return 'United States'
    elif 'ncsc' in source_lower or ('uk' in source_lower and 'ncsc' in source_lower):
        return 'United Kingdom'
    elif 'enisa' in source_lower or 'cert-eu' in source_lower or 'europa.eu' in url_lower:
        return 'European Union'
    elif 'csa' in source_lower and 'singapore' in source_lower:
        return 'Singapore'
    elif 'cyber.gc.ca' in url_lower or 'cccs' in source_lower:
        return 'Canada'
    elif 'citizenlab' in source_lower or 'citizenlab.ca' in url_lower:
        return 'Canada'
    
    # Vendor/Company locations (common ones)
    elif 'microsoft' in source_lower:
        return 'United States'
    elif 'google' in source_lower:
        return 'United States'
    elif 'cisco' in source_lower:
        return 'United States'
    elif 'palo alto' in source_lower:
        return 'United States'
    elif 'crowdstrike' in source_lower:
        return 'United States'
    elif 'cloudflare' in source_lower:
        return 'United States'
    elif 'kaspersky' in source_lower:
        return 'Russia'
    elif 'sophos' in source_lower:
        return 'United Kingdom'
    
    # Research labs
    elif 'check point' in source_lower:
        return 'Israel'
    
    # Default to Global if unknown
    return 'Global'

def categorize_content(title, description, source):
    """Automatically categorize article content based on keywords"""
    if not title:
        return 'News'
    
    text = (title + ' ' + (description or '')).lower()
    
    # Event indicators (check first as events are very specific)
    event_keywords = ['event', 'conference', 'summit', 'webinar', 'workshop', 'meetup', 'expo',
                     'virtual event', 'register', 'agenda', 'speaker', 'rsvp', 'tickets',
                     'keynote', 'session', 'presentation', 'training', 'bootcamp', 'symposium']
    if any(keyword in text for keyword in event_keywords):
        return 'Event'
    
    # Research indicators
    research_keywords = ['research', 'study', 'findings', 'discovered', 'investigation', 
                        'research paper', 'whitepaper', 'technical research', 'academic',
                        'published research', 'research findings', 'scientific study',
                        'threat research', 'security research', 'cyber research', 'analysis',
                        'deep dive', 'technical analysis']
    if any(keyword in text for keyword in research_keywords):
        return 'Research'
    
    # Alert indicators (urgent warnings, advisories, vulnerabilities)
    alert_keywords = ['alert', 'advisory', 'warning', 'urgent', 'critical alert', 'security alert',
                     'threat alert', 'immediate action', 'emergency', 'breaking', 'cisa',
                     'ncsc', 'cert', 'enisa', 'vulnerability', 'cve-', 'exploit', 'patch',
                     'security update', 'zero-day', '0-day', 'unpatched', 'critical']
    if any(keyword in text for keyword in alert_keywords):
        return 'Alert'
    
    # Default to News
    return 'News'

def parse_date(date_str):
    """Parse various date formats and convert to UTC timezone-naive datetime"""
    if not date_str:
        return datetime.now(timezone.utc).replace(tzinfo=None)  # Return timezone-naive UTC
    try:
        if isinstance(date_str, tuple):
            date_str = date_str[0]
        parsed = date_parser.parse(date_str)
        
        # Always convert to UTC, then make timezone-naive for consistent storage
        if parsed.tzinfo is not None:
            # Convert to UTC
            parsed = parsed.astimezone(timezone.utc)
        else:
            # If no timezone info, assume it's already in UTC (or local time - we'll treat as UTC)
            # For safety, we could assume local time, but RSS feeds usually provide UTC
            pass
        
        # Return as timezone-naive UTC datetime
        return parsed.replace(tzinfo=None)
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
        return datetime.now(timezone.utc).replace(tzinfo=None)  # Return timezone-naive UTC

def fetch_rss_feed(feed_config):
    """Fetch and parse a single RSS feed"""
    articles = []
    try:
        # Set user agent to avoid being blocked
        feedparser.USER_AGENT = 'CyberNewsHub/1.0 +https://github.com/cybernewshub'
        
        # Fetch with timeout
        try:
            # Reduced timeout for faster overall fetching
            response = requests.get(feed_config['url'], timeout=5, headers={
                'User-Agent': 'CyberNewsHub/1.0'
            })
            response.raise_for_status()
            feed = feedparser.parse(response.content)
        except requests.RequestException as e:
            print(f"Network error fetching {feed_config['name']}: {e}")
            return articles
        except Exception as e:
            print(f"Error fetching {feed_config['name']}: {e}")
            return articles
        
        if feed.bozo and feed.bozo_exception:
            print(f"Error parsing {feed_config['name']}: {feed.bozo_exception}")
            return articles
        
        if not hasattr(feed, 'entries') or not feed.entries:
            print(f"No entries found in {feed_config['name']}")
            return articles
        
        # Limit to 20 most recent articles per feed (reduces total fetch time)
        max_articles_per_feed = int(os.environ.get('MAX_ARTICLES_PER_FEED', 20))
        for entry in feed.entries[:max_articles_per_feed]:
            try:
                title = entry.get('title', 'No Title')
                link = entry.get('link', '')
                
                # Skip if no link
                if not link:
                    continue
                
                # Get description
                description = ''
                if 'description' in entry:
                    description = clean_html(entry.description)
                elif 'summary' in entry:
                    description = clean_html(entry.summary)
                
                # Parse date
                published_date = parse_date(entry.get('published', entry.get('updated', entry.get('date'))))
                
                # Categorize content
                content_type = categorize_content(title, description, feed_config['name'])
                
                # Get country/region
                country_region = get_country_region(feed_config['name'], link)
                
                articles.append({
                    'title': title,
                    'link': link,
                    'description': description[:500] if description else '',  # Limit description length
                    'source': feed_config['name'],
                    'publisher_type': feed_config['category'],  # Industry, Government, Vendor, Research
                    'content_type': content_type,  # News, Research, Event, Alert, etc.
                    'country_region': country_region,
                    'published_date': published_date
                })
            except Exception as e:
                print(f"Error processing entry from {feed_config['name']}: {e}")
                continue
                
    except Exception as e:
        print(f"Error fetching {feed_config['name']}: {e}")
    
    return articles

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/feeds/fetch', methods=['POST'])
def fetch_all_feeds():
    """Fetch all RSS feeds and store in database"""
    # Get optional parameters
    max_workers = int(request.json.get('max_workers', 10)) if request.json else 10
    only_recent = request.json.get('only_recent', False) if request.json else False
    recent_days = int(request.json.get('recent_days', 1)) if request.json else 1  # Default to 1 day (24 hours)
    
    all_articles = []
    successful_feeds = 0
    failed_feeds = 0
    
    # Collect all feeds
    all_feed_configs = []
    for category, feeds in RSS_FEEDS.items():
        all_feed_configs.extend(feeds)
    
    total_feeds = len(all_feed_configs)
    
    try:
        # Fetch feeds in parallel for much faster performance
        print(f"Fetching {total_feeds} feeds in parallel (max {max_workers} workers)...")
        
        def fetch_single_feed(feed_config):
            """Fetch a single feed and return results"""
            try:
                articles = fetch_rss_feed(feed_config)
                if only_recent:
                    # Filter to only recent articles (last 24 hours)
                    # Use timezone-naive UTC datetime for comparison
                    cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
                    articles = [a for a in articles if a['published_date'] >= cutoff_date]
                
                if articles:
                    return {'success': True, 'feed': feed_config['name'], 'articles': articles, 'count': len(articles)}
                else:
                    return {'success': False, 'feed': feed_config['name'], 'articles': [], 'count': 0, 'error': 'No articles'}
            except Exception as e:
                return {'success': False, 'feed': feed_config['name'], 'articles': [], 'count': 0, 'error': str(e)}
        
        # Use ThreadPoolExecutor for parallel fetching
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_feed = {executor.submit(fetch_single_feed, feed): feed for feed in all_feed_configs}
            
            for future in as_completed(future_to_feed):
                result = future.result()
                if result['success']:
                    all_articles.extend(result['articles'])
                    successful_feeds += 1
                    print(f"  ✓ {result['feed']}: {result['count']} articles")
                else:
                    failed_feeds += 1
                    print(f"  ✗ {result['feed']}: {result.get('error', 'No articles')}")
        
        # Batch database operations for better performance
        print(f"\nProcessing {len(all_articles)} articles...")
        
        # Get all existing links in one query (much faster than individual checks)
        existing_links = set(
            db.session.query(Article.link)
            .filter(Article.link.in_([a['link'] for a in all_articles]))
            .all()
        )
        existing_links = {link[0] for link in existing_links}
        
        # Add only new articles
        new_articles = []
        for article_data in all_articles:
            if article_data['link'] not in existing_links:
                new_articles.append(Article(**article_data))
                existing_links.add(article_data['link'])  # Prevent duplicates in same batch
        
        # Batch insert
        db.session.add_all(new_articles)
        db.session.commit()
        new_count = len(new_articles)
        
        # Clean up old articles (keep only last 90 days by default)
        # This prevents the database from growing indefinitely
        retention_days = int(os.environ.get('ARTICLE_RETENTION_DAYS', 90))
        cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=retention_days)
        deleted_count = Article.query.filter(Article.published_date < cutoff_date).delete()
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'total_fetched': len(all_articles),
            'new_articles': new_count,
            'successful_feeds': successful_feeds,
            'failed_feeds': failed_feeds,
            'old_articles_deleted': deleted_count,
            'retention_days': retention_days
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/articles', methods=['GET'])
def get_articles():
    """Get articles with filtering and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    category = request.args.get('category', None)  # Content type (News, Research, etc.)
    publisher_type = request.args.get('publisher_type', None)  # Publisher type (Industry, Government, etc.)
    source = request.args.get('source', None)
    search = request.args.get('search', None)
    days = request.args.get('days', None, type=int)
    
    query = Article.query
    
    # Apply filters
    if category:
        query = query.filter(Article.content_type == category)
    if publisher_type:
        query = query.filter(Article.publisher_type == publisher_type)
    if source:
        query = query.filter(Article.source == source)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                Article.title.like(search_term),
                Article.description.like(search_term)
            )
        )
    if days:
        cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        query = query.filter(Article.published_date >= cutoff_date)
    
    # Filter out articles with future dates (likely timezone/parsing errors)
    # Only show articles published up to 1 hour in the future (to account for timezone differences)
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    max_future_date = now_utc + timedelta(hours=1)
    query = query.filter(Article.published_date <= max_future_date)
    
    # Order by published date descending (newest first)
    # Use fetched_date as secondary sort for articles with identical published_date
    # This ensures consistent ordering
    query = query.order_by(Article.published_date.desc(), Article.fetched_date.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    articles = [article.to_dict() for article in pagination.items]
    
    return jsonify({
        'articles': articles,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })

@app.route('/api/articles/sources', methods=['GET'])
def get_sources():
    """Get list of all sources"""
    sources = db.session.query(Article.source).distinct().all()
    return jsonify({'sources': [s[0] for s in sources]})

@app.route('/api/articles/categories', methods=['GET'])
def get_categories():
    """Get list of all content type categories"""
    categories = db.session.query(Article.content_type).distinct().all()
    return jsonify({'categories': [c[0] for c in categories if c[0]]})

@app.route('/api/articles/publisher-types', methods=['GET'])
def get_publisher_types():
    """Get list of all publisher types"""
    publisher_types = db.session.query(Article.publisher_type).distinct().all()
    return jsonify({'publisher_types': [pt[0] for pt in publisher_types if pt[0]]})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics about articles"""
    total = Article.query.count()
    by_publisher_type = db.session.query(
        Article.publisher_type,
        db.func.count(Article.id)
    ).group_by(Article.publisher_type).all()
    
    by_content_type = db.session.query(
        Article.content_type,
        db.func.count(Article.id)
    ).group_by(Article.content_type).all()
    
    recent = Article.query.filter(
        Article.published_date >= datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
    ).count()
    
    # Get database size info
    retention_days = int(os.environ.get('ARTICLE_RETENTION_DAYS', 90))
    oldest_article = Article.query.order_by(Article.published_date.asc()).first()
    oldest_date = oldest_article.published_date if oldest_article else None
    
    return jsonify({
        'total_articles': total,
        'recent_articles_24h': recent,
        'by_publisher_type': {pt: count for pt, count in by_publisher_type if pt},
        'by_content_type': {ct: count for ct, count in by_content_type if ct},
        'retention_days': retention_days,
        'oldest_article_date': oldest_date.isoformat() if oldest_date else None
    })

@app.route('/api/cleanup', methods=['POST'])
def cleanup_old_articles():
    """Manually clean up old articles"""
    try:
        retention_days = request.json.get('days', 90) if request.json else 90
        cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=retention_days)
        deleted_count = Article.query.filter(Article.published_date < cutoff_date).delete()
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'deleted_count': deleted_count,
            'retention_days': retention_days
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/articles/re-categorize', methods=['POST'])
def re_categorize_all():
    """Re-categorize all articles based on current categorization rules"""
    try:
        all_articles = Article.query.all()
        category_updated = 0
        region_updated = 0
        
        # Map of abbreviations to full names
        abbreviation_map = {
            'CA': 'Canada',
            'US': 'United States',
            'UK': 'United Kingdom',
            'EU': 'European Union',
            'SG': 'Singapore',
            'RU': 'Russia',
            'IL': 'Israel'
        }
        
        for article in all_articles:
            # Update content type
            new_category = categorize_content(article.title, article.description, article.source)
            if article.content_type != new_category:
                article.content_type = new_category
                category_updated += 1
            
            # Update country/region (convert abbreviations to full names)
            new_region = get_country_region(article.source, article.link)
            # Also check if it's an abbreviation that needs conversion
            if article.country_region in abbreviation_map:
                new_region = abbreviation_map[article.country_region]
            
            if article.country_region != new_region:
                article.country_region = new_region
                region_updated += 1
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'total_articles': len(all_articles),
            'categories_updated': category_updated,
            'regions_updated': region_updated
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Initialize database
with app.app_context():
    db.create_all()
    
    # Migration: Add new columns if they don't exist
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('article')]
        
        # Add publisher_type column if it doesn't exist
        if 'publisher_type' not in columns:
            print("Migrating: Adding publisher_type column...")
            db.session.execute(text('ALTER TABLE article ADD COLUMN publisher_type VARCHAR(50)'))
            # Migrate existing category data to publisher_type if category column exists
            if 'category' in columns:
                db.session.execute(text('UPDATE article SET publisher_type = category WHERE category IS NOT NULL'))
            db.session.commit()
            print("✓ Migration complete: publisher_type added")
        
        # Add content_type column if it doesn't exist
        if 'content_type' not in columns:
            print("Migrating: Adding content_type column...")
            db.session.execute(text('ALTER TABLE article ADD COLUMN content_type VARCHAR(50)'))
            # Set default content_type for existing articles
            db.session.execute(text("UPDATE article SET content_type = 'News' WHERE content_type IS NULL"))
            db.session.commit()
            print("✓ Migration complete: content_type added")
        
        # Add country_region column if it doesn't exist
        if 'country_region' not in columns:
            print("Migrating: Adding country_region column...")
            db.session.execute(text('ALTER TABLE article ADD COLUMN country_region VARCHAR(20)'))
            # Set default country_region for existing articles
            db.session.execute(text("UPDATE article SET country_region = 'Global' WHERE country_region IS NULL"))
            db.session.commit()
            print("✓ Migration complete: country_region added")
            
            # Re-categorize existing articles to get country_region (convert abbreviations to full names)
            try:
                all_articles = Article.query.all()
                if all_articles:
                    print(f"Setting country_region for {len(all_articles)} existing articles...")
                    updated_count = 0
                    for article in all_articles:
                        new_region = get_country_region(article.source, article.link)
                        if article.country_region != new_region:
                            article.country_region = new_region
                            updated_count += 1
                    db.session.commit()
                    print(f"✓ Updated country_region for {updated_count} articles")
            except Exception as e:
                print(f"Note: Could not set country_region for existing articles: {e}")
                db.session.rollback()
        
        # Also update any existing articles with abbreviations to full names
        if 'country_region' in columns:
            try:
                # Map of abbreviations to full names
                abbreviation_map = {
                    'CA': 'Canada',
                    'US': 'United States',
                    'UK': 'United Kingdom',
                    'EU': 'European Union',
                    'SG': 'Singapore',
                    'RU': 'Russia',
                    'IL': 'Israel'
                }
                
                for abbrev, full_name in abbreviation_map.items():
                    updated = Article.query.filter_by(country_region=abbrev).update({'country_region': full_name})
                    if updated > 0:
                        print(f"  Updated {updated} articles from '{abbrev}' to '{full_name}'")
                
                db.session.commit()
            except Exception as e:
                print(f"Note: Could not update abbreviations: {e}")
                db.session.rollback()
        
        # Re-categorize ALL existing articles to use the 4 allowed categories
        # This ensures all articles are properly categorized
        if 'content_type' in columns:
            try:
                all_articles = Article.query.all()
                if all_articles:
                    print(f"Re-categorizing {len(all_articles)} existing articles...")
                    updated_count = 0
                    for article in all_articles:
                        new_category = categorize_content(article.title, article.description, article.source)
                        if article.content_type != new_category:
                            article.content_type = new_category
                            updated_count += 1
                    db.session.commit()
                    print(f"✓ Re-categorized {updated_count} articles")
            except Exception as e:
                print(f"Note: Could not re-categorize existing articles: {e}")
                db.session.rollback()
        
        # Keep old category column for backward compatibility if it exists
        # We'll populate it from content_type for frontend compatibility
        if 'category' in columns and 'content_type' in columns:
            db.session.execute(text("UPDATE article SET category = content_type WHERE category IS NULL OR category = ''"))
            db.session.commit()
        
        # Rename old category column if it still exists (keep for backward compatibility)
        # We'll keep both for now to avoid breaking existing code
    except Exception as e:
        print(f"Migration note: {e}")
        # If migration fails, it's okay - might be first run

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))  # Use 8000 to avoid common port conflicts
    print(f"Starting CyberNewsHub backend on http://127.0.0.1:{port}")
    try:
        app.run(debug=True, port=port, host='127.0.0.1')
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\n❌ ERROR: Port {port} is already in use!")
            print(f"   Please stop the other process or set PORT environment variable:")
            print(f"   PORT=8001 python app.py")
            raise
        else:
            raise

