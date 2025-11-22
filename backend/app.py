from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
import feedparser
import requests
from dateutil import parser as date_parser
import re
import os
import hashlib
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

load_dotenv()

app = Flask(__name__)
# Database configuration: Use PostgreSQL if available (for production), otherwise SQLite (for local dev)
# Render provides DATABASE_URL environment variable for PostgreSQL
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Render provides DATABASE_URL in format: postgresql://user:pass@host:port/dbname
    # SQLAlchemy expects postgresql:// (not postgres://)
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    print("Using PostgreSQL database (production)")
else:
    # Local development: use SQLite
    db_path = os.path.join(os.path.dirname(__file__), 'cybernews.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    print(f"Using SQLite database (local): {db_path}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Enable CORS for all routes and origins
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

db = SQLAlchemy(app)

# RSS Feed Sources Configuration - Global Coverage
# Includes sources from all continents, G20 countries, and EU countries
# Focus on Industry news sites, Vendor blogs, and Research labs (not government CERT feeds)
RSS_FEEDS = {
    'industry': [
        # === NORTH AMERICA ===
        # USA - Major established sources
        {'name': 'The Hacker News', 'url': 'https://feeds.feedburner.com/TheHackersNews', 'category': 'Industry'},
        {'name': 'BleepingComputer', 'url': 'https://www.bleepingcomputer.com/feed/', 'category': 'Industry'},
        {'name': 'Krebs on Security', 'url': 'https://krebsonsecurity.com/feed/', 'category': 'Industry'},
        {'name': 'Dark Reading', 'url': 'https://www.darkreading.com/rss.xml', 'category': 'Industry'},
        {'name': 'SC Magazine', 'url': 'https://www.scmagazine.com/home/feed/', 'category': 'Industry'},
        {'name': 'SecurityWeek', 'url': 'https://www.securityweek.com/feed/', 'category': 'Industry'},
        {'name': 'Threatpost', 'url': 'https://threatpost.com/feed/', 'category': 'Industry'},
        {'name': 'CSO Online', 'url': 'https://www.csoonline.com/index.rss', 'category': 'Industry'},
        {'name': 'InfoSecurity Magazine', 'url': 'https://www.infosecurity-magazine.com/rss/news/', 'category': 'Industry'},
        {'name': 'Help Net Security', 'url': 'https://www.helpnetsecurity.com/feed/', 'category': 'Industry'},
        {'name': 'IT Security Guru', 'url': 'https://www.itsecurityguru.org/feed/', 'category': 'Industry'},
        {'name': 'Security Boulevard', 'url': 'https://securityboulevard.com/feed/', 'category': 'Industry'},
        {'name': 'CyberScoop', 'url': 'https://www.cyberscoop.com/feed/', 'category': 'Industry'},
        {'name': 'Security Affairs', 'url': 'https://securityaffairs.com/feed', 'category': 'Industry'},
        {'name': 'Schneier on Security', 'url': 'https://www.schneier.com/feed/atom/', 'category': 'Industry'},
        {'name': 'Graham Cluley', 'url': 'https://grahamcluley.com/feed/', 'category': 'Industry'},
        {'name': 'Ars Technica Security', 'url': 'https://feeds.arstechnica.com/arstechnica/security', 'category': 'Industry'},
        {'name': 'The Register Security', 'url': 'https://www.theregister.com/security/headlines.atom', 'category': 'Industry'},
        {'name': 'ZDNet Security', 'url': 'https://www.zdnet.com/topic/security/rss.xml', 'category': 'Industry'},
        {'name': 'Packet Storm Security', 'url': 'https://rss.packetstormsecurity.com/', 'category': 'Industry'},
        
        # === EUROPE ===
        # UK - Major established sources
        {'name': 'WeLiveSecurity', 'url': 'https://www.welivesecurity.com/feed/', 'category': 'Industry'},
        {'name': 'Naked Security', 'url': 'https://nakedsecurity.sophos.com/feed/', 'category': 'Industry'},
        {'name': 'Computer Weekly Security', 'url': 'https://www.computerweekly.com/rss/Security.xml', 'category': 'Industry'},
        # Germany
        {'name': 'Heise Security', 'url': 'https://www.heise.de/security/rss/news.rdf', 'category': 'Industry'},
        # Netherlands
        {'name': 'Security.nl', 'url': 'https://www.security.nl/rss', 'category': 'Industry'},
        # Poland
        {'name': 'Niebezpiecznik', 'url': 'https://niebezpiecznik.pl/feed/', 'category': 'Industry'},
        
        # === ASIA ===
        # India
        {'name': 'The Hacker News', 'url': 'https://thehackernews.com/feeds/posts/default', 'category': 'Industry'},
        # Japan - English sources only
        # Note: Removed ITmedia Security (Japanese-only) - using global sources that cover Japan
        
        # === OCEANIA ===
        # Australia
        {'name': 'CSO Australia', 'url': 'https://www.cso.com.au/index.rss', 'category': 'Industry'},
        {'name': 'IT News Australia', 'url': 'https://www.itnews.com.au/RSS/rss.ashx', 'category': 'Industry'},
        
        # === SOUTH AMERICA ===
        # Note: Most South American countries (Argentina, Brazil, Chile, Colombia, etc.) don't have 
        # dedicated English-language cybersecurity news sites. Articles from these countries will be 
        # detected from global sources (The Hacker News, SecurityWeek, etc.) when they mention 
        # these countries or use .ar, .br, .cl, .co TLDs
    ],
    'government': [
        # G20 Countries - North America (Verified Working)
        {'name': 'CISA', 'url': 'https://www.cisa.gov/news.xml', 'category': 'Government'},  # USA
        {'name': 'US-CERT Alerts', 'url': 'https://www.us-cert.gov/ncas/alerts.xml', 'category': 'Government'},  # USA
        {'name': 'US-CERT Bulletins', 'url': 'https://www.us-cert.gov/ncas/bulletins.xml', 'category': 'Government'},  # USA
        {'name': 'CCCS Advisories', 'url': 'https://cyber.gc.ca/en/rss/advisories.xml', 'category': 'Government'},  # Canada
        {'name': 'CCCS Alerts', 'url': 'https://cyber.gc.ca/en/rss/alerts.xml', 'category': 'Government'},  # Canada
        {'name': 'CCCS News', 'url': 'https://cyber.gc.ca/en/rss/news.xml', 'category': 'Government'},  # Canada
        
        # G20 Countries - Europe (Verified Working)
        {'name': 'ENISA', 'url': 'https://www.enisa.europa.eu/news/enisa-news/RSS', 'category': 'Government'},  # EU
        {'name': 'CERT-EU', 'url': 'https://cert.europa.eu/public/news.rss', 'category': 'Government'},  # EU
        {'name': 'NCSC UK', 'url': 'https://www.ncsc.gov.uk/api/1/services/v1/news-rss-feed.xml', 'category': 'Government'},  # UK
        {'name': 'BSI Germany', 'url': 'https://www.bsi.bund.de/SiteGlobals/Functions/RSSFeed/RSSNewsfeed/RSSNewsfeed.xml', 'category': 'Government'},  # Germany
        {'name': 'ANSSI France', 'url': 'https://www.ssi.gouv.fr/feed/', 'category': 'Government'},  # France
        {'name': 'NCSC Netherlands', 'url': 'https://www.ncsc.nl/rss', 'category': 'Government'},  # Netherlands
        
        # G20 Countries - Asia (Verified Working)
        {'name': 'CSA Singapore', 'url': 'https://www.csa.gov.sg/rss', 'category': 'Government'},  # Singapore
        {'name': 'JPCERT', 'url': 'https://www.jpcert.or.jp/english/rss/jpcert_en.rdf', 'category': 'Government'},  # Japan
        
        # G20 Countries - Oceania (Verified Working)
        {'name': 'ACSC Australia', 'url': 'https://www.cyber.gov.au/rss.xml', 'category': 'Government'},  # Australia
        {'name': 'CERT NZ', 'url': 'https://www.cert.govt.nz/rss.xml', 'category': 'Government'},  # New Zealand
    ],
    'vendors': [
        # === NORTH AMERICA ===
        # USA - Major established vendors
        {'name': 'Microsoft Security', 'url': 'https://www.microsoft.com/en-us/security/blog/feed/', 'category': 'Vendor'},
        {'name': 'Google Security', 'url': 'https://security.googleblog.com/feeds/posts/default', 'category': 'Vendor'},
        {'name': 'Cisco Talos', 'url': 'https://blog.talosintelligence.com/feed/', 'category': 'Vendor'},
        {'name': 'Cloudflare Blog', 'url': 'https://blog.cloudflare.com/rss/', 'category': 'Vendor'},
        {'name': 'Palo Alto Unit42', 'url': 'https://unit42.paloaltonetworks.com/feed/', 'category': 'Vendor'},
        {'name': 'CrowdStrike', 'url': 'https://www.crowdstrike.com/blog/feed/', 'category': 'Vendor'},
        {'name': 'Mandiant', 'url': 'https://www.mandiant.com/resources/blog/rss.xml', 'category': 'Vendor'},
        {'name': 'Proofpoint', 'url': 'https://www.proofpoint.com/us/rss.xml', 'category': 'Vendor'},
        {'name': 'Zscaler', 'url': 'https://www.zscaler.com/blogs/security-research/rss.xml', 'category': 'Vendor'},
        {'name': 'IBM Security', 'url': 'https://www.ibm.com/security/blog/feed', 'category': 'Vendor'},
        {'name': 'Rapid7', 'url': 'https://www.rapid7.com/blog/feed/', 'category': 'Vendor'},
        {'name': 'Tenable', 'url': 'https://www.tenable.com/blog/rss.xml', 'category': 'Vendor'},
        {'name': 'Qualys', 'url': 'https://blog.qualys.com/feed', 'category': 'Vendor'},
        {'name': 'Okta', 'url': 'https://www.okta.com/blog/feed/', 'category': 'Vendor'},
        {'name': 'SentinelOne', 'url': 'https://www.sentinelone.com/blog/feed/', 'category': 'Vendor'},
        {'name': 'Cybereason', 'url': 'https://www.cybereason.com/blog/feed', 'category': 'Vendor'},
        {'name': 'Varonis', 'url': 'https://www.varonis.com/blog/feed/', 'category': 'Vendor'},
        {'name': 'FireEye', 'url': 'https://www.fireeye.com/blog/feed', 'category': 'Vendor'},
        {'name': 'Symantec', 'url': 'https://symantec-enterprise-blogs.security.com/blogs/feed', 'category': 'Vendor'},
        {'name': 'McAfee', 'url': 'https://www.mcafee.com/blogs/feed/', 'category': 'Vendor'},
        {'name': 'Bitdefender', 'url': 'https://www.bitdefender.com/blog/feed/', 'category': 'Vendor'},
        {'name': 'Malwarebytes', 'url': 'https://www.malwarebytes.com/blog/feed/', 'category': 'Vendor'},
        {'name': 'Fortinet', 'url': 'https://www.fortinet.com/blog/rss.xml', 'category': 'Vendor'},
        {'name': 'AWS Security', 'url': 'https://aws.amazon.com/blogs/security/feed/', 'category': 'Vendor'},
        {'name': 'GitHub Security', 'url': 'https://github.blog/security/feed/', 'category': 'Vendor'},
        
        # === EUROPE ===
        # UK
        {'name': 'Sophos', 'url': 'https://news.sophos.com/en-us/feed/', 'category': 'Vendor'},
        {'name': 'Darktrace', 'url': 'https://www.darktrace.com/en/blog/feed/', 'category': 'Vendor'},
        # Russia
        {'name': 'Kaspersky SecureList', 'url': 'https://securelist.com/feed/', 'category': 'Vendor'},
        # Finland
        {'name': 'F-Secure', 'url': 'https://blog.f-secure.com/feed/', 'category': 'Vendor'},
        # Czech Republic
        {'name': 'Avast', 'url': 'https://blog.avast.com/rss.xml', 'category': 'Vendor'},
        # Slovakia
        {'name': 'ESET', 'url': 'https://www.welivesecurity.com/feed/', 'category': 'Vendor'},
        
        # === ASIA ===
        # Japan
        {'name': 'Trend Micro', 'url': 'https://www.trendmicro.com/en_us/research/rss.xml', 'category': 'Vendor'},
        # Israel
        {'name': 'Check Point', 'url': 'https://blog.checkpoint.com/feed/', 'category': 'Vendor'},
        {'name': 'CyberArk', 'url': 'https://www.cyberark.com/resources/blog/feed/', 'category': 'Vendor'},
    ],
    'research': [
        # === NORTH AMERICA ===
        # USA - Major established research labs
        {'name': 'SANS ISC', 'url': 'https://isc.sans.edu/rssfeed.xml', 'category': 'Research'},
        {'name': 'Mandiant Research', 'url': 'https://www.mandiant.com/resources/research/rss.xml', 'category': 'Research'},
        {'name': 'Secureworks Research', 'url': 'https://www.secureworks.com/rss?feed=research', 'category': 'Research'},
        {'name': 'Malwarebytes Labs', 'url': 'https://www.malwarebytes.com/blog/feed/', 'category': 'Research'},
        {'name': 'NIST Cybersecurity', 'url': 'https://www.nist.gov/blogs/cybersecurity-insights/rss.xml', 'category': 'Research'},
        # Canada
        {'name': 'Citizen Lab', 'url': 'https://citizenlab.ca/feed/', 'category': 'Research'},
        
        # === EUROPE ===
        # Israel
        {'name': 'Check Point Research', 'url': 'https://research.checkpoint.com/feed/', 'category': 'Research'},
        # Finland
        {'name': 'F-Secure Labs', 'url': 'https://labs.f-secure.com/feed/', 'category': 'Research'},
        # Czech Republic
        {'name': 'Avast Threat Labs', 'url': 'https://blog.avast.com/rss.xml', 'category': 'Research'},
        # Slovakia
        {'name': 'ESET Research', 'url': 'https://www.welivesecurity.com/feed/', 'category': 'Research'},
        # UK
        {'name': 'NCC Group Research', 'url': 'https://research.nccgroup.com/feed/', 'category': 'Research'},
        
        # === ASIA ===
        # Japan
        {'name': 'Trend Micro Research', 'url': 'https://www.trendmicro.com/en_us/research/rss.xml', 'category': 'Research'},
        # Russia
        {'name': 'Kaspersky Research', 'url': 'https://securelist.com/feed/', 'category': 'Research'},
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
    country_region = db.Column(db.String(200))  # Can store multiple countries: "Canada, United States", etc.
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
            'published_date': (self.published_date.isoformat() + 'Z') if self.published_date else None,
            'fetched_date': (self.fetched_date.isoformat() + 'Z') if self.fetched_date else None
        }

class FeedCache(db.Model):
    """Cache metadata for RSS feeds to enable HTTP caching"""
    id = db.Column(db.Integer, primary_key=True)
    feed_url = db.Column(db.String(500), unique=True, nullable=False)
    etag = db.Column(db.String(200))
    last_modified = db.Column(db.String(200))
    last_fetched = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    content_hash = db.Column(db.String(64))  # SHA-256 hash of content

def clean_html(text):
    """Remove HTML tags from text"""
    if not text:
        return ""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def capitalize_country_name(country):
    """Ensure country name is properly capitalized (title case)"""
    if not country:
        return country
    # Handle special cases like "United States", "United Kingdom", "European Union"
    special_cases = {
        'united states': 'United States',
        'united kingdom': 'United Kingdom',
        'european union': 'European Union',
        'south korea': 'South Korea',
        'new zealand': 'New Zealand',
        'south africa': 'South Africa',
        'united arab emirates': 'United Arab Emirates',
        'saudi arabia': 'Saudi Arabia'
    }
    country_lower = country.lower().strip()
    if country_lower in special_cases:
        return special_cases[country_lower]
    # Default: title case
    return country.title()

def get_country_region(source_name, url, title=None, description=None):
    """
    Determine country/region from source name, URL, TLD, and article content.
    Returns a comma-separated string of countries (e.g., "Canada, United States")
    """
    source_lower = (source_name or '').lower()
    url_lower = (url or '').lower()
    title_lower = (title or '').lower()
    desc_lower = (description or '').lower()
    content_lower = (title_lower + ' ' + desc_lower).strip()
    
    countries = set()  # Use set to avoid duplicates
    
    # === TLD-BASED DETECTION ===
    tld_to_country = {
        '.us': 'United States',
        '.uk': 'United Kingdom',
        '.ca': 'Canada',
        '.au': 'Australia',
        '.de': 'Germany',
        '.fr': 'France',
        '.it': 'Italy',
        '.es': 'Spain',
        '.nl': 'Netherlands',
        '.se': 'Sweden',
        '.no': 'Norway',
        '.fi': 'Finland',
        '.dk': 'Denmark',
        '.pl': 'Poland',
        '.jp': 'Japan',
        '.cn': 'China',
        '.kr': 'South Korea',
        '.in': 'India',
        '.sg': 'Singapore',
        '.nz': 'New Zealand',
        '.ie': 'Ireland',
        '.ch': 'Switzerland',
        '.at': 'Austria',
        '.be': 'Belgium',
        '.il': 'Israel',
        '.ru': 'Russia',
        '.br': 'Brazil',
        '.mx': 'Mexico',
        '.za': 'South Africa',
        '.ae': 'United Arab Emirates',
        '.sa': 'Saudi Arabia',
        '.ar': 'Argentina',
        '.cl': 'Chile',
        '.co': 'Colombia',
        '.pe': 'Peru',
        '.ve': 'Venezuela',
        '.uy': 'Uruguay',
        '.py': 'Paraguay',
        '.bo': 'Bolivia',
        '.ec': 'Ecuador',
        # G20 countries
        '.id': 'Indonesia',
        '.tr': 'Turkey',
        # EU countries
        '.bg': 'Bulgaria',
        '.hr': 'Croatia',
        '.cy': 'Cyprus',
        '.cz': 'Czech Republic',
        '.ee': 'Estonia',
        '.gr': 'Greece',
        '.hu': 'Hungary',
        '.lv': 'Latvia',
        '.lt': 'Lithuania',
        '.lu': 'Luxembourg',
        '.mt': 'Malta',
        '.pt': 'Portugal',
        '.ro': 'Romania',
        '.sk': 'Slovakia',
        '.si': 'Slovenia',
        # Other major countries
        '.th': 'Thailand',
        '.vn': 'Vietnam',
        '.ph': 'Philippines',
        '.my': 'Malaysia',
        '.tw': 'Taiwan',
        '.eg': 'Egypt',
        '.ng': 'Nigeria',
        '.ke': 'Kenya',
        '.ma': 'Morocco',
        '.tn': 'Tunisia',
        '.dz': 'Algeria',
        '.pk': 'Pakistan',
        '.bd': 'Bangladesh',
        '.lk': 'Sri Lanka',
        '.mm': 'Myanmar',
        '.kh': 'Cambodia',
        '.la': 'Laos',
    }
    
    # Check URL for TLD (be more precise to avoid false matches)
    # First check for source-specific patterns
    if 'itmedia' in source_lower or 'itmedia.co.jp' in url_lower:
        countries.add('Japan')
    
    # Then check TLDs - only match at end of domain or as proper TLD
    for tld, country in tld_to_country.items():
        # Match TLD at end of URL or after a dot (proper TLD)
        # Use word boundary to avoid matching .it inside "itmedia"
        if url_lower.endswith(tld) or re.search(r'\.' + re.escape(tld[1:]) + r'(/|$|\?|#)', url_lower):
            # Double-check: don't match .it if it's part of a longer domain like itmedia
            if tld == '.it' and 'itmedia' in url_lower:
                continue  # Skip Italy match for itmedia.co.jp
            countries.add(country)
    
    # === GOVERNMENT SOURCES ===
    if 'cisa' in source_lower or 'us-cert' in source_lower:
        countries.add('United States')
    if '.gov' in url_lower and '.gov.uk' not in url_lower and '.gov.au' not in url_lower and '.gc.ca' not in url_lower:
        countries.add('United States')
    
    if 'ncsc' in source_lower or '.gov.uk' in url_lower:
        countries.add('United Kingdom')
    
    if 'enisa' in source_lower or 'cert-eu' in source_lower or 'europa.eu' in url_lower:
        countries.add('European Union')
    
    if ('csa' in source_lower and 'singapore' in source_lower) or '.gov.sg' in url_lower:
        countries.add('Singapore')
    
    if 'cyber.gc.ca' in url_lower or 'cccs' in source_lower or '.gc.ca' in url_lower:
        countries.add('Canada')
    
    # === SOURCE-SPECIFIC DETECTION (before vendor detection) ===
    # Handle specific sources that might have ambiguous TLDs or need explicit country assignment
    if 'itmedia' in source_lower or 'itmedia.co.jp' in url_lower:
        countries.add('Japan')
        # Remove Italy if it was incorrectly added due to .it in itmedia
        countries.discard('Italy')
    
    # === VENDOR/COMPANY LOCATIONS (expanded) ===
    us_vendors = [
        'microsoft', 'google', 'cisco', 'palo alto', 'crowdstrike', 'cloudflare',
        'fireeye', 'mandiant', 'proofpoint', 'zscaler', 'okta', 'splunk',
        'rapid7', 'tenable', 'qualys', 'fortinet', 'trend micro', 'symantec',
        'mcafee', 'ibm security', 'oracle security', 'salesforce', 'aws',
        'azure', 'github security', 'twitter security', 'meta security', 'facebook security'
    ]
    
    uk_vendors = ['sophos', 'darktrace', 'bae systems']
    
    israel_vendors = ['check point', 'cyberark', 'sentinelone', 'cybereason']
    
    russia_vendors = ['kaspersky']
    
    japan_vendors = ['trend micro', 'jpcert']
    
    for vendor in us_vendors:
        if vendor in source_lower:
            countries.add('United States')
    
    for vendor in uk_vendors:
        if vendor in source_lower:
            countries.add('United Kingdom')
    
    for vendor in israel_vendors:
        if vendor in source_lower:
            countries.add('Israel')
    
    for vendor in russia_vendors:
        if vendor in source_lower:
            countries.add('Russia')
    
    for vendor in japan_vendors:
        if vendor in source_lower:
            countries.add('Japan')
    
    # === RESEARCH LABS ===
    if 'citizenlab' in source_lower or 'citizenlab.ca' in url_lower:
        countries.add('Canada')
    
    if 'check point research' in source_lower:
        countries.add('Israel')
    
    # === CONTENT-BASED DETECTION ===
    # Country name patterns in content (case-insensitive matching)
    # Map lowercase keys to proper country names
    country_patterns = {
        'United States': ['united states', 'usa', 'u.s.', 'u.s.a.', 'america', 'american', 'us government', 'fbi', 'cia', 'nsa', 'dhs'],
        'Canada': ['canada', 'canadian', 'canadian government', 'rcmp'],
        'United Kingdom': ['united kingdom', 'uk', 'u.k.', 'britain', 'british', 'uk government', 'gchq'],
        'Australia': ['australia', 'australian', 'australian government', 'acsc'],
        'Germany': ['germany', 'german', 'bsi'],
        'France': ['france', 'french', 'anssi'],
        'Japan': ['japan', 'japanese', 'japan government'],
        'China': ['china', 'chinese', 'beijing'],
        'Russia': ['russia', 'russian', 'moscow', 'kremlin'],
        'Israel': ['israel', 'israeli', 'tel aviv'],
        'Singapore': ['singapore', 'singaporean'],
        'South Korea': ['south korea', 'korean', 'seoul'],
        'India': ['india', 'indian', 'new delhi'],
        'Brazil': ['brazil', 'brazilian', 'brasil'],
        'Netherlands': ['netherlands', 'dutch', 'amsterdam'],
        'Sweden': ['sweden', 'swedish', 'stockholm'],
        'Norway': ['norway', 'norwegian', 'oslo'],
        'Finland': ['finland', 'finnish', 'helsinki'],
        'Denmark': ['denmark', 'danish', 'copenhagen'],
        'Poland': ['poland', 'polish', 'warsaw'],
        'Italy': ['italy', 'italian', 'rome'],
        'Spain': ['spain', 'spanish', 'madrid'],
        'Switzerland': ['switzerland', 'swiss', 'bern'],
        'New Zealand': ['new zealand', 'nz', 'wellington'],
        'Ireland': ['ireland', 'irish', 'dublin'],
        'South Africa': ['south africa', 'south african'],
        'European Union': ['european union', 'eu', 'europe', 'european commission', 'brussels'],
        'Argentina': ['argentina', 'argentine', 'argentinian', 'buenos aires'],
        'Brazil': ['brazil', 'brazilian', 'brasil', 'são paulo', 'rio de janeiro'],
        'Chile': ['chile', 'chilean', 'santiago'],
        'Colombia': ['colombia', 'colombian', 'bogota'],
        'Mexico': ['mexico', 'mexican', 'mexico city'],
        'Peru': ['peru', 'peruvian', 'lima'],
        # G20 countries
        'Indonesia': ['indonesia', 'indonesian', 'jakarta'],
        'Turkey': ['turkey', 'turkish', 'türkiye', 'ankara', 'istanbul'],
        # EU countries
        'Bulgaria': ['bulgaria', 'bulgarian', 'sofia'],
        'Croatia': ['croatia', 'croatian', 'zagreb'],
        'Cyprus': ['cyprus', 'cypriot', 'nicosia'],
        'Czech Republic': ['czech republic', 'czech', 'prague'],
        'Estonia': ['estonia', 'estonian', 'tallinn'],
        'Greece': ['greece', 'greek', 'athens'],
        'Hungary': ['hungary', 'hungarian', 'budapest'],
        'Latvia': ['latvia', 'latvian', 'riga'],
        'Lithuania': ['lithuania', 'lithuanian', 'vilnius'],
        'Luxembourg': ['luxembourg', 'luxembourgish', 'luxembourg city'],
        'Malta': ['malta', 'maltese', 'valletta'],
        'Portugal': ['portugal', 'portuguese', 'lisbon'],
        'Romania': ['romania', 'romanian', 'bucharest'],
        'Slovakia': ['slovakia', 'slovak', 'bratislava'],
        'Slovenia': ['slovenia', 'slovenian', 'ljubljana'],
        # Other major countries
        'Thailand': ['thailand', 'thai', 'bangkok'],
        'Vietnam': ['vietnam', 'vietnamese', 'hanoi', 'ho chi minh'],
        'Philippines': ['philippines', 'filipino', 'manila'],
        'Malaysia': ['malaysia', 'malaysian', 'kuala lumpur'],
        'Taiwan': ['taiwan', 'taiwanese', 'taipei'],
        'Egypt': ['egypt', 'egyptian', 'cairo'],
        'Nigeria': ['nigeria', 'nigerian', 'lagos', 'abuja'],
        'Kenya': ['kenya', 'kenyan', 'nairobi'],
        'Morocco': ['morocco', 'moroccan', 'rabat'],
        'Tunisia': ['tunisia', 'tunisian', 'tunis'],
        'Algeria': ['algeria', 'algerian', 'algiers'],
        'Pakistan': ['pakistan', 'pakistani', 'islamabad', 'karachi'],
        'Bangladesh': ['bangladesh', 'bangladeshi', 'dhaka'],
        'Sri Lanka': ['sri lanka', 'sri lankan', 'colombo'],
        'Myanmar': ['myanmar', 'burma', 'burmese', 'yangon'],
        'Cambodia': ['cambodia', 'cambodian', 'phnom penh'],
        'Laos': ['laos', 'laotian', 'vientiane'],
        'Venezuela': ['venezuela', 'venezuelan', 'caracas'],
        'Uruguay': ['uruguay', 'uruguayan', 'montevideo'],
        'Paraguay': ['paraguay', 'paraguayan', 'asuncion'],
        'Bolivia': ['bolivia', 'bolivian', 'la paz'],
        'Ecuador': ['ecuador', 'ecuadorian', 'quito'],
    }
    
    # Check content for country mentions (only if we haven't found many countries yet)
    if len(countries) < 3:  # Limit to avoid over-tagging
        for country, patterns in country_patterns.items():
            for pattern in patterns:
                # Only match whole words or common phrases to avoid false positives
                if pattern in content_lower:
                    # Additional context check: make sure it's actually about that country
                    # (not just mentioning it in passing)
                    context_words = ['government', 'authorities', 'officials', 'agency', 'ministry', 
                                   'targeted', 'attacked', 'breach', 'incident', 'cyber', 'security']
                    # If pattern found and context words nearby, it's likely relevant
                    pattern_pos = content_lower.find(pattern)
                    if pattern_pos >= 0:
                        # Check 50 chars before and after for context
                        context_start = max(0, pattern_pos - 50)
                        context_end = min(len(content_lower), pattern_pos + len(pattern) + 50)
                        context = content_lower[context_start:context_end]
                        if any(ctx_word in context for ctx_word in context_words):
                            countries.add(country)  # Add proper country name directly
                            break
    
    # === URL PATTERN MATCHING ===
    # More sophisticated URL pattern detection
    url_patterns = {
        'United States': ['.gov/', 'cisa.gov', 'us-cert.gov', 'fbi.gov', 'cia.gov', 'nsa.gov'],
        'United Kingdom': ['.gov.uk', 'ncsc.gov.uk', 'gchq.gov.uk'],
        'Canada': ['.gc.ca', 'cyber.gc.ca', 'canada.ca'],
        'Australia': ['.gov.au', 'cyber.gov.au', 'acsc.gov.au'],
        'Germany': ['.de/', 'bsi.bund.de'],
        'France': ['.fr/', 'ssi.gouv.fr'],
        'Japan': ['.go.jp', '.jp/'],
        'Singapore': ['.gov.sg', 'csa.gov.sg'],
        'Israel': ['.gov.il', '.il/'],
        'European Union': ['europa.eu', 'enisa.europa.eu']
    }
    
    for country, patterns in url_patterns.items():
        if any(pattern in url_lower for pattern in patterns):
            countries.add(country)
    
    # === RETURN RESULT ===
    if len(countries) == 0:
        return 'Global'
    elif len(countries) == 1:
        return capitalize_country_name(list(countries)[0])
    else:
        # Sort for consistency, ensure proper capitalization, and return comma-separated
        sorted_countries = sorted(countries)
        # Ensure each country is properly capitalized
        capitalized_countries = [capitalize_country_name(country) for country in sorted_countries]
        return ', '.join(capitalized_countries)

def categorize_content(title, description, source, url=None):
    """
    Categorize articles based on content:
    - News: Incident reports and latest news
    - Event: Events, meetups, announcements, conference reports
    - Alert: Newsletters/advisories that call attention to specific types of attacks
    - Research: Research papers and latest research findings
    """
    if not title:
        return 'News'
    
    text = (title + ' ' + (description or '')).lower()
    url_lower = (url or '').lower()
    source_lower = (source or '').lower()
    
    # Score-based categorization with weighted keywords
    scores = {'Event': 0, 'Research': 0, 'Alert': 0, 'News': 0}
    
    # === EVENT DETECTION ===
    # Events: meetups, announcements, conference reports
    strong_event_keywords = [
        'conference', 'summit', 'webinar', 'workshop', 'symposium', 'expo', 'exhibition',
        'rsvp', 'register now', 'register today', 'early bird', 'tickets', 'agenda',
        'keynote speaker', 'call for papers', 'cfp', 'submit abstract',
        'conference report', 'event report', 'conference coverage', 'event coverage'
    ]
    medium_event_keywords = [
        'event', 'meetup', 'training', 'bootcamp', 'session', 'presentation',
        'virtual event', 'online event', 'live event', 'networking',
        'announcement', 'announcing', 'upcoming event'
    ]
    event_phrases = [
        'save the date', 'join us', 'don\'t miss', 'coming soon',
        'speaker lineup', 'event schedule', 'conference program'
    ]
    
    for keyword in strong_event_keywords:
        if keyword in text:
            scores['Event'] += 3
    for keyword in medium_event_keywords:
        if keyword in text:
            scores['Event'] += 2
    for phrase in event_phrases:
        if phrase in text:
            scores['Event'] += 2
    
    # URL hints for events
    if any(term in url_lower for term in ['/event', '/conference', '/webinar', '/workshop', '/summit', '/training']):
        scores['Event'] += 3
    
    # === RESEARCH DETECTION ===
    # Research: research papers and latest research findings
    strong_research_keywords = [
        'research paper', 'whitepaper', 'technical research', 'academic paper',
        'published research', 'peer-reviewed', 'research findings', 'scientific study',
        'latest research', 'new research', 'research publication'
    ]
    medium_research_keywords = [
        'research', 'study', 'findings', 'discovered',
        'deep dive', 'technical analysis', 'threat analysis', 'malware analysis',
        'reverse engineering', 'vulnerability research', 'security research'
    ]
    research_phrases = [
        'our research shows', 'we discovered', 'we found that', 'analysis reveals',
        'according to our research', 'research indicates', 'study shows',
        'research reveals', 'findings show'
    ]
    
    for keyword in strong_research_keywords:
        if keyword in text:
            scores['Research'] += 3
    for keyword in medium_research_keywords:
        if keyword in text:
            scores['Research'] += 2
    for phrase in research_phrases:
        if phrase in text:
            scores['Research'] += 2
    
    # URL hints for research
    if any(term in url_lower for term in ['/research', '/study', '/whitepaper', '/paper']):
        scores['Research'] += 3
    
    # Source-based research hints (research labs are more likely to publish research)
    if any(term in source_lower for term in ['research', 'lab', 'citizen lab', 'check point research']):
        scores['Research'] += 1
    
    # === ALERT DETECTION ===
    # Alert: newsletters/advisories that call attention to specific types of attacks
    # Focus on attack-specific warnings and threat advisories
    strong_alert_keywords = [
        'threat alert', 'attack alert', 'threat advisory', 'attack advisory',
        'active attack', 'ongoing attack', 'attack campaign', 'threat campaign',
        'malware campaign', 'ransomware alert', 'phishing alert', 'apt alert',
        'threat actor', 'attack group', 'threat group', 'call attention',
        'be aware of', 'watch out for', 'new attack', 'emerging threat'
    ]
    medium_alert_keywords = [
        'alert', 'advisory', 'warning', 'threat warning', 'attack warning',
        'security alert', 'critical alert', 'urgent alert',
        'newsletter', 'threat intelligence', 'threat update'
    ]
    alert_phrases = [
        'calls attention', 'draws attention', 'highlights threat', 'warns about',
        'alert about', 'advisory about', 'threat targeting', 'attack targeting',
        'be on the lookout', 'be vigilant', 'exercise caution'
    ]
    
    for keyword in strong_alert_keywords:
        if keyword in text:
            scores['Alert'] += 4
    for keyword in medium_alert_keywords:
        if keyword in text:
            scores['Alert'] += 2
    for phrase in alert_phrases:
        if phrase in text:
            scores['Alert'] += 3
    
    # CVE/vulnerability alerts (these call attention to specific attack vectors)
    if re.search(r'cve-\d{4}-\d+', text):
        scores['Alert'] += 3
    if any(term in text for term in ['cve-', 'vulnerability', 'exploit', 'zero-day', '0-day']):
        scores['Alert'] += 2
    
    # URL hints for alerts/advisories
    if any(term in url_lower for term in ['/alert', '/advisory', '/warning', '/threat', '/newsletter']):
        scores['Alert'] += 3
    
    # Source-based alert hints (government agencies often issue threat alerts)
    if any(term in source_lower for term in ['cisa', 'us-cert', 'ncsc', 'cert', 'enisa', 'cccs']):
        scores['Alert'] += 2
    
    # === NEWS DETECTION ===
    # News: Incident reports and latest news
    # Boost News score for incident-related content that isn't an alert
    news_keywords = [
        'incident', 'breach', 'data breach', 'cyber attack', 'hacked', 'hacking',
        'compromised', 'leak', 'data leak', 'ransomware attack', 'malware attack',
        'latest news', 'breaking news', 'reported', 'announced', 'disclosed',
        'victim', 'affected', 'impacted', 'stolen', 'exposed'
    ]
    news_phrases = [
        'has been breached', 'has been hacked', 'was compromised', 'fell victim',
        'reported a breach', 'announced an incident', 'disclosed an attack'
    ]
    
    for keyword in news_keywords:
        if keyword in text:
            scores['News'] += 2
    for phrase in news_phrases:
        if phrase in text:
            scores['News'] += 3
    
    # URL hints for news
    if any(term in url_lower for term in ['/news', '/article', '/post', '/blog']):
        scores['News'] += 1
    
    # === NEGATIVE KEYWORDS (reduce false positives) ===
    # If it's about an incident but also has strong alert indicators, don't reduce Alert
    # But if it's just reporting news about an incident (not calling attention to attack type), boost News
    if 'incident' in text or 'breach' in text:
        if 'alert' not in text and 'advisory' not in text and 'threat' not in text:
            scores['News'] += 1
    
    # If it mentions "research" but in context of "research shows news" pattern, reduce Research
    if 'research' in text and ('news' in text or 'report' in text):
        if 'research paper' not in text and 'whitepaper' not in text and 'findings' not in text:
            scores['Research'] -= 1
            scores['News'] += 1
    
    # If it's about an event but also reporting on it (conference report), keep Event score
    # This is handled by the event keywords above
    
    # === DETERMINE CATEGORY ===
    # Find the category with the highest score
    max_score = max(scores.values())
    
    # If no category scored, default to News
    if max_score == 0:
        return 'News'
    
    # Get the category with the highest score
    # In case of ties, prioritize: Alert > Research > Event > News
    priority_order = ['Alert', 'Research', 'Event', 'News']
    for category in priority_order:
        if scores[category] == max_score:
            return category
    
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
    """Fetch and parse a single RSS feed with HTTP caching support
    Returns: (articles, error_message) tuple
    """
    articles = []
    error_message = None
    try:
        # Set user agent to avoid being blocked (more realistic user agent)
        feedparser.USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        # Get cached metadata for this feed (safely handle if table doesn't exist yet)
        # Use application context for database operations (needed for ThreadPoolExecutor)
        cache_etag = None
        cache_last_modified = None
        cache_content_hash = None
        try:
            with app.app_context():
                cache = FeedCache.query.filter_by(feed_url=feed_config['url']).first()
                if cache:
                    cache_etag = cache.etag
                    cache_last_modified = cache.last_modified
                    cache_content_hash = cache.content_hash
        except Exception:
            # FeedCache table might not exist yet, continue without caching
            pass
        
        # Prepare headers with caching support (more realistic headers)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        if cache_etag:
            headers['If-None-Match'] = cache_etag
        if cache_last_modified:
            headers['If-Modified-Since'] = cache_last_modified
        
        # Fetch with longer timeout and caching headers
        feed = None
        try:
            # Increase timeout to 15 seconds (some feeds are slow)
            # Allow redirects (max 5 redirects)
            response = requests.get(
                feed_config['url'], 
                timeout=15, 
                headers=headers,
                allow_redirects=True,
                verify=True,  # SSL verification (set to False if SSL issues)
                stream=False
            )
            
            # Handle 304 Not Modified (feed hasn't changed)
            if response.status_code == 304:
                print(f"  {feed_config['name']}: Not modified (cached)")
                return articles, None  # Return empty, feed hasn't changed
            
            # Check for non-200 status codes
            if response.status_code != 200:
                error_message = f"HTTP {response.status_code}: {response.reason}"
                print(f"  {feed_config['name']}: HTTP {response.status_code} - {response.reason}")
                return articles, error_message
            
            response.raise_for_status()
            
            # Check if response is actually RSS/XML
            content_type = response.headers.get('Content-Type', '').lower()
            if 'html' in content_type and 'xml' not in content_type and 'rss' not in content_type:
                # Might be an HTML error page instead of RSS
                if len(response.content) < 1000:  # Small response might be error page
                    error_message = "HTML response (not RSS)"
                    print(f"  {feed_config['name']}: Got HTML instead of RSS (might be error page)")
                    # Still try to parse it, feedparser might handle it
            
            # Calculate content hash to detect changes even without ETag
            content_hash = hashlib.sha256(response.content).hexdigest()
            if cache_content_hash and cache_content_hash == content_hash:
                # Content hash matches, no new articles
                print(f"  {feed_config['name']}: No changes (content hash match)")
                # Update last_fetched timestamp (safely)
                try:
                    with app.app_context():
                        cache = FeedCache.query.filter_by(feed_url=feed_config['url']).first()
                        if cache:
                            cache.last_fetched = datetime.now(timezone.utc).replace(tzinfo=None)
                            db.session.commit()
                except Exception:
                    with app.app_context():
                        db.session.rollback()
                return articles, None
            
            # Parse feed
            feed = feedparser.parse(response.content)
            
            # Update cache metadata (safely handle if table doesn't exist)
            # Use application context for database operations
            try:
                with app.app_context():
                    etag = response.headers.get('ETag')
                    last_modified = response.headers.get('Last-Modified')
                    
                    # Re-query cache in this context to avoid cross-context issues
                    cache = FeedCache.query.filter_by(feed_url=feed_config['url']).first()
                    if cache:
                        if etag:
                            cache.etag = etag
                        if last_modified:
                            cache.last_modified = last_modified
                        cache.content_hash = content_hash
                        cache.last_fetched = datetime.now(timezone.utc).replace(tzinfo=None)
                    else:
                        cache = FeedCache(
                            feed_url=feed_config['url'],
                            etag=etag,
                            last_modified=last_modified,
                            content_hash=content_hash,
                            last_fetched=datetime.now(timezone.utc).replace(tzinfo=None)
                        )
                        db.session.add(cache)
                    
                    db.session.commit()
            except Exception as e:
                # If FeedCache table doesn't exist or other DB error, just continue without caching
                try:
                    with app.app_context():
                        db.session.rollback()
                except:
                    pass
                pass
            
        except requests.Timeout as e:
            error_message = "Timeout (>15s)"
            print(f"  {feed_config['name']}: Timeout - {e}")
            return articles, error_message
        except requests.ConnectionError as e:
            error_message = f"Connection error: {str(e)[:100]}"
            print(f"  {feed_config['name']}: Connection error - {e}")
            return articles, error_message
        except requests.HTTPError as e:
            error_message = f"HTTP {response.status_code if 'response' in locals() else 'error'}: {str(e)[:100]}"
            print(f"  {feed_config['name']}: HTTP error - {e}")
            return articles, error_message
        except requests.RequestException as e:
            error_message = f"Request error: {str(e)[:100]}"
            print(f"  {feed_config['name']}: Request error - {e}")
            return articles, error_message
        except Exception as e:
            error_message = f"Unexpected error: {str(e)[:100]}"
            print(f"  {feed_config['name']}: Unexpected error - {e}")
            return articles, error_message
        
        # Check if feed was successfully parsed
        if not feed:
            error_message = "No feed object returned"
            return articles, error_message
        
        if feed.bozo and feed.bozo_exception:
            error_message = f"Parse error: {str(feed.bozo_exception)[:100]}"
            print(f"  {feed_config['name']}: Parse error - {feed.bozo_exception}")
            # Try to continue anyway - feedparser sometimes marks feeds as bozo but still parses them
            if not hasattr(feed, 'entries') or not feed.entries:
                return articles, error_message
        
        if not hasattr(feed, 'entries') or not feed.entries:
            error_message = "No entries in feed"
            print(f"  {feed_config['name']}: No entries found")
            return articles, error_message
        
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
                content_type = categorize_content(title, description, feed_config['name'], link)
                
                # Get country/region
                country_region = get_country_region(feed_config['name'], link, title, description)
                
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
        error_message = f"Exception: {str(e)[:100]}"
        print(f"Error fetching {feed_config['name']}: {e}")
        return articles, error_message
    
    return articles, None

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/feeds/schedule', methods=['GET'])
def get_schedule_info():
    """Get information about automatic feed fetching schedule"""
    global scheduler
    if scheduler and scheduler.running:
        job = scheduler.get_job('auto_fetch_feeds')
        if job:
            next_run = job.next_run_time
            return jsonify({
                'enabled': True,
                'interval_hours': 12,
                'next_run_time': next_run.isoformat() if next_run else None,
                'next_run_time_formatted': next_run.strftime('%Y-%m-%d %H:%M:%S') if next_run else None
            })
    
    return jsonify({
        'enabled': False,
        'interval_hours': 12,
        'next_run_time': None,
        'message': 'Automatic feed fetching is not enabled'
    })

def fetch_all_feeds_internal(max_workers=10, only_recent=False, recent_days=1):
    """Internal function to fetch all RSS feeds - can be called manually or by scheduler"""
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
            # Wrap entire function in app context for thread safety
            with app.app_context():
                try:
                    articles, error_message = fetch_rss_feed(feed_config)
                    if only_recent:
                        # Filter to only recent articles (last 24 hours)
                        # Use timezone-naive UTC datetime for comparison
                        cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
                        articles = [a for a in articles if a['published_date'] >= cutoff_date]
                    
                    if articles:
                        return {'success': True, 'feed': feed_config['name'], 'articles': articles, 'count': len(articles), 'url': feed_config['url']}
                    else:
                        # Use the error message from fetch_rss_feed, or default message
                        error = error_message if error_message else 'No articles'
                        return {'success': False, 'feed': feed_config['name'], 'articles': [], 'count': 0, 'error': error, 'url': feed_config['url']}
                except Exception as e:
                    return {'success': False, 'feed': feed_config['name'], 'articles': [], 'count': 0, 'error': str(e)[:200], 'url': feed_config['url']}
        
        # Use ThreadPoolExecutor for parallel fetching
        # Increase max_workers for better parallelism with more sources
        optimal_workers = min(max_workers, total_feeds, 20)  # Cap at 20 to avoid overwhelming
        with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
            future_to_feed = {executor.submit(fetch_single_feed, feed): feed for feed in all_feed_configs}
            
            failed_feed_details = []  # Track failed feeds with details
            for future in as_completed(future_to_feed):
                result = future.result()
                if result['success']:
                    all_articles.extend(result['articles'])
                    successful_feeds += 1
                    print(f"  ✓ {result['feed']}: {result['count']} articles")
                else:
                    failed_feeds += 1
                    error_msg = result.get('error', 'No articles')
                    print(f"  ✗ {result['feed']}: {error_msg}")
                    failed_feed_details.append({
                        'name': result['feed'],
                        'url': result.get('url', ''),
                        'error': error_msg
                    })
        
        # Batch database operations for better performance
        print(f"\nProcessing {len(all_articles)} articles...")
        
        # Get all existing links in one query (much faster than individual checks)
        with app.app_context():
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
        
        # Print summary of failed feeds (first 10) for debugging
        if failed_feed_details:
            print(f"\nFailed feeds summary (showing first 10 of {len(failed_feed_details)}):")
            for detail in failed_feed_details[:10]:
                print(f"  - {detail['name']}: {detail['error']}")
            if len(failed_feed_details) > 10:
                print(f"  ... and {len(failed_feed_details) - 10} more")
        
        return {
            'status': 'success',
            'total_fetched': len(all_articles),
            'new_articles': new_count,
            'successful_feeds': successful_feeds,
            'failed_feeds': failed_feeds,
            'failed_feed_details': failed_feed_details[:20],  # Return first 20 for frontend display
            'old_articles_deleted': deleted_count,
            'retention_days': retention_days
        }
    except Exception as e:
        with app.app_context():
            db.session.rollback()
        print(f"Error in fetch_all_feeds_internal: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }

def scheduled_fetch_feeds():
    """Scheduled task to fetch feeds automatically every 12 hours"""
    print(f"\n{'='*60}")
    print(f"AUTOMATIC FEED FETCH - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    result = fetch_all_feeds_internal(max_workers=10, only_recent=False, recent_days=1)
    print(f"Automatic fetch completed: {result.get('new_articles', 0)} new articles from {result.get('successful_feeds', 0)} feeds")
    print(f"{'='*60}\n")

@app.route('/api/feeds/fetch', methods=['POST'])
def fetch_all_feeds():
    """Manual endpoint to fetch all RSS feeds and store in database"""
    # Get optional parameters
    max_workers = int(request.json.get('max_workers', 10)) if request.json else 10
    only_recent = request.json.get('only_recent', False) if request.json else False
    recent_days = int(request.json.get('recent_days', 1)) if request.json else 1  # Default to 1 day (24 hours)
    
    result = fetch_all_feeds_internal(max_workers, only_recent, recent_days)
    
    if result['status'] == 'error':
        return jsonify(result), 500
    return jsonify(result)

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
    countries = request.args.get('countries', None)  # Comma-separated list of countries
    sort_by = request.args.get('sort_by', 'newest')  # Sort order: 'newest', 'oldest', 'relevance'
    
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
    
    # Country filter (multi-select, comma-separated)
    if countries:
        country_list = [c.strip() for c in countries.split(',') if c.strip()]
        if country_list:
            # Match articles where country_region contains any of the selected countries
            # Since country_region can be comma-separated, we need to check if any country matches
            country_filters = []
            for country in country_list:
                # Match exact country or country in comma-separated list
                country_filters.append(
                    db.or_(
                        Article.country_region == country,
                        Article.country_region.like(f'%{country}%')
                    )
                )
            if country_filters:
                query = query.filter(db.or_(*country_filters))
    
    # Filter out articles with future dates (likely timezone/parsing errors)
    # Only show articles published up to 24 hours in the future (to account for timezone differences and scheduling)
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    max_future_date = now_utc + timedelta(hours=24)
    query = query.filter(Article.published_date <= max_future_date)
    
    # Apply sorting
    if sort_by == 'oldest':
        # Oldest first
        query = query.order_by(Article.published_date.asc(), Article.fetched_date.asc())
    elif sort_by == 'relevance':
        # Relevance: prioritize recent articles but also consider fetched_date
        # This gives a mix but still favors newer content
        query = query.order_by(Article.published_date.desc(), Article.fetched_date.desc())
    else:
        # Default: newest first (newest to oldest)
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
    """Get list of all sources with their primary country"""
    from collections import Counter
    
    # Get all sources with their country_region
    source_countries = db.session.query(
        Article.source,
        Article.country_region
    ).filter(Article.country_region.isnot(None)).all()
    
    # Group by source and find the most common country for each
    source_country_map = {}
    for source, country_region in source_countries:
        if not country_region or country_region == 'Global':
            continue
        
        # Handle comma-separated countries - take the first one as primary
        primary_country = country_region.split(',')[0].strip()
        
        if source not in source_country_map:
            source_country_map[source] = []
        source_country_map[source].append(primary_country)
    
    # Get all distinct sources
    all_sources = db.session.query(Article.source).distinct().all()
    sources_list = []
    
    for source_tuple in all_sources:
        source = source_tuple[0]
        # Find most common country for this source
        if source in source_country_map:
            country_counter = Counter(source_country_map[source])
            primary_country = country_counter.most_common(1)[0][0]
        else:
            primary_country = None
        
        sources_list.append({
            'name': source,
            'country': primary_country
        })
    
    # Sort by source name
    sources_list.sort(key=lambda x: x['name'])
    
    return jsonify({'sources': sources_list})

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

@app.route('/api/articles/countries', methods=['GET'])
def get_countries():
    """Get list of all unique countries/regions"""
    # Get all country_region values from database
    country_regions = db.session.query(Article.country_region).distinct().all()
    
    # Extract all unique countries from database (handle comma-separated values)
    db_countries = set()
    for cr in country_regions:
        if cr[0]:
            # Split comma-separated countries and add each one
            countries = [c.strip() for c in cr[0].split(',')]
            db_countries.update(countries)
    
    # Define all supported countries (from TLD mapping and country patterns)
    # This ensures all countries appear in dropdown even if they have no articles yet
    all_supported_countries = {
        # G20 Countries
        'Argentina', 'Australia', 'Brazil', 'Canada', 'China', 'France', 'Germany',
        'India', 'Indonesia', 'Italy', 'Japan', 'Mexico', 'Russia', 'Saudi Arabia',
        'South Africa', 'South Korea', 'Turkey', 'United Kingdom', 'United States',
        'European Union',
        # EU Countries (all 27)
        'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czech Republic',
        'Denmark', 'Estonia', 'Finland', 'France', 'Germany', 'Greece', 'Hungary',
        'Ireland', 'Italy', 'Latvia', 'Lithuania', 'Luxembourg', 'Malta',
        'Netherlands', 'Poland', 'Portugal', 'Romania', 'Slovakia', 'Slovenia',
        'Spain', 'Sweden',
        # Other major countries
        'Chile', 'Colombia', 'Peru', 'Venezuela', 'Uruguay', 'Paraguay', 'Bolivia', 'Ecuador',
        'Thailand', 'Vietnam', 'Philippines', 'Malaysia', 'Taiwan', 'Singapore',
        'Egypt', 'Nigeria', 'Kenya', 'Morocco', 'Tunisia', 'Algeria',
        'Pakistan', 'Bangladesh', 'Sri Lanka', 'Myanmar', 'Cambodia', 'Laos',
        'Israel', 'United Arab Emirates', 'New Zealand', 'Switzerland', 'Norway'
    }
    
    # Combine database countries with all supported countries
    all_countries = db_countries.union(all_supported_countries)
    
    # Remove 'Global' if present
    all_countries.discard('Global')
    
    # Sort and return
    sorted_countries = sorted(all_countries)
    return jsonify({'countries': sorted_countries})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics about articles with optional filters"""
    # Get filter parameters (same as get_articles)
    category = request.args.get('category', None)  # Content type (News, Research, etc.)
    publisher_type = request.args.get('publisher_type', None)  # Publisher type (Industry, Government, etc.)
    source = request.args.get('source', None)
    search = request.args.get('search', None)
    days = request.args.get('days', None, type=int)
    countries = request.args.get('countries', None)  # Comma-separated list of countries
    
    # Build query with same filters as get_articles
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
    
    # Country filter (multi-select, comma-separated)
    if countries:
        country_list = [c.strip() for c in countries.split(',') if c.strip()]
        if country_list:
            # Match articles where country_region contains any of the selected countries
            country_filters = []
            for country in country_list:
                country_filters.append(
                    db.or_(
                        Article.country_region == country,
                        Article.country_region.like(f'%{country}%')
                    )
                )
            if country_filters:
                query = query.filter(db.or_(*country_filters))
    
    # Filter out articles with future dates (same as get_articles)
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    max_future_date = now_utc + timedelta(hours=1)
    query = query.filter(Article.published_date <= max_future_date)
    
    # Get filtered counts
    total = query.count()
    
    # Recent articles (last 24 hours) with filters applied
    recent_query = query.filter(
        Article.published_date >= datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
    )
    recent = recent_query.count()
    
    # Get breakdowns (only if no search filter, as search makes grouping less meaningful)
    by_publisher_type = {}
    by_content_type = {}
    
    if not search:  # Only show breakdowns when not searching
        # Use the same filtered query for breakdowns
        by_publisher_type_result = db.session.query(
            Article.publisher_type,
            db.func.count(Article.id)
        )
        # Apply same filters to breakdown query
        if category:
            by_publisher_type_result = by_publisher_type_result.filter(Article.content_type == category)
        if publisher_type:
            by_publisher_type_result = by_publisher_type_result.filter(Article.publisher_type == publisher_type)
        if source:
            by_publisher_type_result = by_publisher_type_result.filter(Article.source == source)
        if days:
            cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
            by_publisher_type_result = by_publisher_type_result.filter(Article.published_date >= cutoff_date)
        if countries:
            country_list = [c.strip() for c in countries.split(',') if c.strip()]
            if country_list:
                country_filters = []
                for country in country_list:
                    country_filters.append(
                        db.or_(
                            Article.country_region == country,
                            Article.country_region.like(f'%{country}%')
                        )
                    )
                if country_filters:
                    by_publisher_type_result = by_publisher_type_result.filter(db.or_(*country_filters))
        by_publisher_type_result = by_publisher_type_result.filter(Article.published_date <= max_future_date)
        by_publisher_type_result = by_publisher_type_result.group_by(Article.publisher_type).all()
        by_publisher_type = {pt: count for pt, count in by_publisher_type_result if pt}
        
        by_content_type_result = db.session.query(
            Article.content_type,
            db.func.count(Article.id)
        )
        # Apply same filters to breakdown query
        if category:
            by_content_type_result = by_content_type_result.filter(Article.content_type == category)
        if publisher_type:
            by_content_type_result = by_content_type_result.filter(Article.publisher_type == publisher_type)
        if source:
            by_content_type_result = by_content_type_result.filter(Article.source == source)
        if days:
            cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
            by_content_type_result = by_content_type_result.filter(Article.published_date >= cutoff_date)
        if countries:
            country_list = [c.strip() for c in countries.split(',') if c.strip()]
            if country_list:
                country_filters = []
                for country in country_list:
                    country_filters.append(
                        db.or_(
                            Article.country_region == country,
                            Article.country_region.like(f'%{country}%')
                        )
                    )
                if country_filters:
                    by_content_type_result = by_content_type_result.filter(db.or_(*country_filters))
        by_content_type_result = by_content_type_result.filter(Article.published_date <= max_future_date)
        by_content_type_result = by_content_type_result.group_by(Article.content_type).all()
        by_content_type = {ct: count for ct, count in by_content_type_result if ct}
    
    # Get database size info (unfiltered)
    retention_days = int(os.environ.get('ARTICLE_RETENTION_DAYS', 90))
    oldest_article = Article.query.order_by(Article.published_date.asc()).first()
    oldest_date = oldest_article.published_date if oldest_article else None
    
    return jsonify({
        'total_articles': total,
        'recent_articles_24h': recent,
        'by_publisher_type': by_publisher_type,
        'by_content_type': by_content_type,
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
            new_category = categorize_content(article.title, article.description, article.source, article.link)
            if article.content_type != new_category:
                article.content_type = new_category
                category_updated += 1
            
            # Update country/region (convert abbreviations to full names)
            new_region = get_country_region(article.source, article.link, article.title, article.description)
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

@app.route('/api/articles/delete-by-source', methods=['POST'])
def delete_articles_by_source():
    """Delete articles from a specific source (useful for removing unwanted sources)"""
    try:
        source_name = request.json.get('source') if request.json else None
        if not source_name:
            return jsonify({
                'status': 'error',
                'message': 'Source name is required'
            }), 400
        
        deleted_count = Article.query.filter_by(source=source_name).delete()
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'source': source_name,
            'deleted_count': deleted_count
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
            print("Migration complete: publisher_type added")
        
        # Add content_type column if it doesn't exist
        if 'content_type' not in columns:
            print("Migrating: Adding content_type column...")
            db.session.execute(text('ALTER TABLE article ADD COLUMN content_type VARCHAR(50)'))
            # Set default content_type for existing articles
            db.session.execute(text("UPDATE article SET content_type = 'News' WHERE content_type IS NULL"))
            db.session.commit()
            print("Migration complete: content_type added")
        
        # Add country_region column if it doesn't exist
        if 'country_region' not in columns:
            print("Migrating: Adding country_region column...")
            db.session.execute(text('ALTER TABLE article ADD COLUMN country_region VARCHAR(200)'))
            # Set default country_region for existing articles
            db.session.execute(text("UPDATE article SET country_region = 'Global' WHERE country_region IS NULL"))
            db.session.commit()
            print("Migration complete: country_region added")
            
            # Re-categorize existing articles to get country_region (convert abbreviations to full names)
            try:
                all_articles = Article.query.all()
                if all_articles:
                    print(f"Setting country_region for {len(all_articles)} existing articles...")
                    updated_count = 0
                    for article in all_articles:
                        new_region = get_country_region(article.source, article.link, article.title, article.description)
                        if article.country_region != new_region:
                            article.country_region = new_region
                            updated_count += 1
                    db.session.commit()
                    print(f"Updated country_region for {updated_count} articles")
            except Exception as e:
                print(f"Note: Could not set country_region for existing articles: {e}")
                db.session.rollback()
        
        # Update country_region column size if it's too small (for existing databases)
        # Note: SQLite doesn't support ALTER COLUMN, but VARCHAR in SQLite is flexible
        # We'll just ensure new data uses the larger size. Existing data will work fine.
        if 'country_region' in columns:
            try:
                # Re-run country detection on all articles to get multi-country support
                all_articles = Article.query.all()
                if all_articles:
                    print(f"Updating country_region with enhanced detection for {len(all_articles)} articles...")
                    updated_count = 0
                    for article in all_articles:
                        new_region = get_country_region(article.source, article.link, article.title, article.description)
                        if article.country_region != new_region:
                            article.country_region = new_region
                            updated_count += 1
                    db.session.commit()
                    if updated_count > 0:
                        print(f"Updated country_region for {updated_count} articles with multi-country support")
            except Exception as e:
                print(f"Note: Could not update country_region with enhanced detection: {e}")
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
        
        # Update country_region with enhanced multi-country detection (run once on startup)
        # This will add content-based detection and TLD detection to existing articles
        if 'country_region' in columns:
            try:
                # Only run this migration once - check if we have any single-country entries that could benefit
                # We'll skip this on every startup to avoid performance issues
                # Instead, users can use the re-categorize button to update countries
                pass  # Migration handled by re-categorize endpoint
            except Exception as e:
                print(f"Note: Could not update country_region with enhanced detection: {e}")
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
                        new_category = categorize_content(article.title, article.description, article.source, article.link)
                        if article.content_type != new_category:
                            article.content_type = new_category
                            updated_count += 1
                    db.session.commit()
                    print(f"Re-categorized {updated_count} articles")
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

# Initialize scheduler for automatic feed fetching
scheduler = None

def start_scheduler():
    """Start the background scheduler for automatic feed fetching"""
    global scheduler
    if scheduler and scheduler.running:
        return  # Already running
    
    try:
        scheduler = BackgroundScheduler(daemon=True)
        # Schedule feed fetching every 12 hours
        scheduler.add_job(
            func=scheduled_fetch_feeds,
            trigger=IntervalTrigger(hours=12),
            id='auto_fetch_feeds',
            name='Automatic Feed Fetch (every 12 hours)',
            replace_existing=True
        )
        scheduler.start()
        next_run = scheduler.get_job('auto_fetch_feeds')
        if next_run and next_run.next_run_time:
            print(f"✓ Automatic feed scheduler started (every 12 hours)")
            print(f"  Next automatic fetch: {next_run.next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"✓ Automatic feed scheduler started (every 12 hours)")
    except Exception as e:
        print(f"Warning: Could not start scheduler: {e}")
        print("  Automatic feed fetching will not be available, but manual fetching will still work.")

# Start scheduler - only in the actual Flask process (not in reloader parent)
# Flask's reloader: parent process has no WERKZEUG_RUN_MAIN, child process has WERKZEUG_RUN_MAIN='true'
# We want to start scheduler in the child process (actual Flask app)
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    # This is the actual Flask process (child of reloader)
    start_scheduler()
elif not os.environ.get('WERKZEUG_RUN_MAIN'):
    # No reloader (production mode or debug=False), start scheduler
    start_scheduler()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))  # Use 8000 to avoid common port conflicts
    host = os.environ.get('HOST', '127.0.0.1')  # Use 0.0.0.0 for production (Render sets this)
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    print(f"Starting CyberNewsHub backend on http://{host}:{port}")
    print(f"Automatic feed fetching: Every 12 hours")
    print(f"Manual feed fetching: Available via API endpoint")
    try:
        app.run(debug=debug, port=port, host=host)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\nERROR: Port {port} is already in use!")
            print(f"   Please stop the other process or set PORT environment variable:")
            print(f"   PORT=8001 python app.py")
            raise
        else:
            raise
    finally:
        # Shutdown scheduler when app stops
        if scheduler and scheduler.running:
            scheduler.shutdown()

