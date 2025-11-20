from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import feedparser
import requests
from dateutil import parser as date_parser
import re
import os
from dotenv import load_dotenv

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
    category = db.Column(db.String(50))
    published_date = db.Column(db.DateTime, nullable=False)
    fetched_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'link': self.link,
            'description': self.description,
            'source': self.source,
            'category': self.category,
            'published_date': self.published_date.isoformat() if self.published_date else None,
            'fetched_date': self.fetched_date.isoformat() if self.fetched_date else None
        }

def clean_html(text):
    """Remove HTML tags from text"""
    if not text:
        return ""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def parse_date(date_str):
    """Parse various date formats"""
    if not date_str:
        return datetime.utcnow()
    try:
        if isinstance(date_str, tuple):
            date_str = date_str[0]
        return date_parser.parse(date_str)
    except:
        return datetime.utcnow()

def fetch_rss_feed(feed_config):
    """Fetch and parse a single RSS feed"""
    articles = []
    try:
        # Set user agent to avoid being blocked
        feedparser.USER_AGENT = 'CyberNewsHub/1.0 +https://github.com/cybernewshub'
        
        # Fetch with timeout
        try:
            response = requests.get(feed_config['url'], timeout=10, headers={
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
        
        for entry in feed.entries[:50]:  # Limit to 50 most recent
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
                
                articles.append({
                    'title': title,
                    'link': link,
                    'description': description[:500] if description else '',  # Limit description length
                    'source': feed_config['name'],
                    'category': feed_config['category'],
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
    all_articles = []
    successful_feeds = 0
    failed_feeds = 0
    
    try:
        # Fetch from all feed categories
        total_feeds = sum(len(feeds) for feeds in RSS_FEEDS.values())
        current_feed = 0
        
        for category, feeds in RSS_FEEDS.items():
            for feed_config in feeds:
                current_feed += 1
                print(f"Fetching {feed_config['name']} ({current_feed}/{total_feeds})...")
                try:
                    articles = fetch_rss_feed(feed_config)
                    if articles:
                        all_articles.extend(articles)
                        successful_feeds += 1
                        print(f"  ✓ {feed_config['name']}: {len(articles)} articles")
                    else:
                        failed_feeds += 1
                        print(f"  ✗ {feed_config['name']}: No articles")
                except Exception as e:
                    failed_feeds += 1
                    print(f"  ✗ {feed_config['name']}: {str(e)}")
        
        # Store in database
        new_count = 0
        errors = []
        for article_data in all_articles:
            try:
                # Check if article already exists
                existing = Article.query.filter_by(link=article_data['link']).first()
                if not existing:
                    article = Article(**article_data)
                    db.session.add(article)
                    new_count += 1
            except Exception as e:
                errors.append(str(e))
                continue
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'total_fetched': len(all_articles),
            'new_articles': new_count,
            'successful_feeds': successful_feeds,
            'failed_feeds': failed_feeds,
            'errors': errors[:5] if errors else []  # Return first 5 errors if any
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
    category = request.args.get('category', None)
    source = request.args.get('source', None)
    search = request.args.get('search', None)
    days = request.args.get('days', None, type=int)
    
    query = Article.query
    
    # Apply filters
    if category:
        query = query.filter(Article.category == category)
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
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(Article.published_date >= cutoff_date)
    
    # Order by published date (newest first)
    query = query.order_by(Article.published_date.desc())
    
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
    """Get list of all categories"""
    categories = db.session.query(Article.category).distinct().all()
    return jsonify({'categories': [c[0] for c in categories if c[0]]})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics about articles"""
    total = Article.query.count()
    by_category = db.session.query(
        Article.category,
        db.func.count(Article.id)
    ).group_by(Article.category).all()
    
    recent = Article.query.filter(
        Article.published_date >= datetime.utcnow() - timedelta(days=7)
    ).count()
    
    return jsonify({
        'total_articles': total,
        'recent_articles_7d': recent,
        'by_category': {cat: count for cat, count in by_category if cat}
    })

# Initialize database
with app.app_context():
    db.create_all()

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

