from flask import Flask, jsonify, request
from flask_cors import CORS
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

# Google Sheets backend
from sheets_client import get_sheets_client

# LLM-based categorization using Groq (free API)
# Set GROQ_API_KEY environment variable to enable
def get_llm_categorizer():
    """Get the LLM categorizer if available."""
    try:
        from groq_categorizer import categorize_with_groq, is_available
        if is_available():
            return categorize_with_groq
    except ImportError:
        pass
    return None

# ML-based categorization using local transformer model
def get_ml_categorizer():
    """Get the ML categorizer if available."""
    try:
        from ml_categorizer import categorize_with_ml
        return categorize_with_ml
    except ImportError:
        pass
    except Exception as e:
        # Model might fail to load, that's okay
        pass
    return None

load_dotenv()

app = Flask(__name__)
# Enable CORS for all routes and origins
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# Using Google Sheets as database backend
print("Using Google Sheets database backend")

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

        # === EXPANDED G20/EU/NATO COVERAGE (English Sources) ===

        # G20 - Europe Additional
        {'name': 'CSIRT Italia', 'url': 'https://csirt.gov.it/data/indexer/rss', 'category': 'Government'},  # Italy

        # EU Members - Northern Europe
        {'name': 'NCSC-FI Finland', 'url': 'https://www.kyberturvallisuuskeskus.fi/feed/rss/en', 'category': 'Government'},  # Finland (English)
        {'name': 'CERT-SE Sweden', 'url': 'https://www.cert.se/feed.rss', 'category': 'Government'},  # Sweden
        {'name': 'CFCS Denmark', 'url': 'https://www.cert.dk/nyheder/rss', 'category': 'Government'},  # Denmark
        {'name': 'NSM Norway', 'url': 'https://nsm.no/fagomrader/digital-sikkerhet/nasjonalt-cybersikkerhetssenter/varsler-fra-ncsc/rss/', 'category': 'Government'},  # Norway (NATO)

        # EU Members - Central Europe
        {'name': 'CERT.at Austria', 'url': 'https://cert.at/cert-at.en.blog.rss_2.0.xml', 'category': 'Government'},  # Austria (English)
        {'name': 'CCB Belgium', 'url': 'https://cert.be/en/rss', 'category': 'Government'},  # Belgium (English)
        {'name': 'GovCERT Switzerland', 'url': 'https://www.govcert.ch/blog/rss.xml', 'category': 'Government'},  # Switzerland (English)
        {'name': 'NUKIB Czech', 'url': 'https://nukib.gov.cz/rss.xml', 'category': 'Government'},  # Czech Republic
        {'name': 'CERT.PL Poland', 'url': 'https://cert.pl/en/rss.xml', 'category': 'Government'},  # Poland (English)
        {'name': 'SK-CERT Slovakia', 'url': 'https://www.sk-cert.sk/index.html?feed=rss', 'category': 'Government'},  # Slovakia
        {'name': 'NCSC Hungary', 'url': 'https://nki.gov.hu/figyelmeztetesek/riasztas/feed/', 'category': 'Government'},  # Hungary

        # EU Members - Eastern Europe
        {'name': 'CERT.LV Latvia', 'url': 'https://cert.lv/en/feed/rss/all', 'category': 'Government'},  # Latvia (English)
        {'name': 'SI-CERT Slovenia', 'url': 'https://www.cert.si/en/category/news/feed/', 'category': 'Government'},  # Slovenia (English)
        {'name': 'CERT.hr Croatia', 'url': 'https://www.cert.hr/feed/', 'category': 'Government'},  # Croatia
        {'name': 'CERT-RO Romania', 'url': 'https://dnsc.ro/feed', 'category': 'Government'},  # Romania
        {'name': 'CERT-UA Ukraine', 'url': 'https://cert.gov.ua/api/articles/rss', 'category': 'Government'},  # Ukraine

        # EU Members - Southern Europe
        {'name': 'CCN-CERT Spain', 'url': 'https://www.ccn-cert.cni.es/component/obrss/rss-noticias.feed', 'category': 'Government'},  # Spain
        {'name': 'CNCS Portugal', 'url': 'https://www.cncs.gov.pt/docs/noticias/feed-rss/index.xml', 'category': 'Government'},  # Portugal
        {'name': 'GR-CERT Greece', 'url': 'https://cert.grnet.gr/feed/', 'category': 'Government'},  # Greece (Academic CERT)

        # Asia-Pacific Additional
        {'name': 'GovCERT.HK', 'url': 'https://www.govcert.gov.hk/en/rss_security_alerts.xml', 'category': 'Government'},  # Hong Kong (English)
        {'name': 'HKCERT', 'url': 'https://www.hkcert.org/getrss/security-bulletin', 'category': 'Government'},  # Hong Kong (English)
        {'name': 'BGD e-GOV CIRT', 'url': 'https://www.cirt.gov.bd/feed/', 'category': 'Government'},  # Bangladesh

        # Other Regions
        {'name': 'EG-CERT Egypt', 'url': 'https://www.egcert.eg/feed/', 'category': 'Government'},  # Egypt
        {'name': 'CERT-IL Israel', 'url': 'https://www.gov.il/he/api/PublicationApi/rss/4bcc13f5-fed6-4b8c-b8ee-7bf4a6bc81c8', 'category': 'Government'},  # Israel
        {'name': 'AusCERT', 'url': 'https://auscert.org.au/rss/bulletins/', 'category': 'Government'},  # Australia (Academic/Industry)
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

# Map each RSS feed to its country/region for filtered fetching
# Only countries with at least one source will be available for selection
FEED_COUNTRY_MAP = {
    # === INDUSTRY FEEDS ===
    # USA
    'The Hacker News': 'United States',
    'BleepingComputer': 'United States',
    'Krebs on Security': 'United States',
    'Dark Reading': 'United States',
    'SC Magazine': 'United States',
    'SecurityWeek': 'United States',
    'Threatpost': 'United States',
    'CSO Online': 'United States',
    'InfoSecurity Magazine': 'United States',
    'Help Net Security': 'United States',
    'IT Security Guru': 'United States',
    'Security Boulevard': 'United States',
    'CyberScoop': 'United States',
    'Security Affairs': 'United States',
    'Schneier on Security': 'United States',
    'Graham Cluley': 'United Kingdom',
    'Ars Technica Security': 'United States',
    'The Register Security': 'United Kingdom',
    'ZDNet Security': 'United States',
    'Packet Storm Security': 'United States',
    # UK/Europe Industry
    'WeLiveSecurity': 'Slovakia',  # ESET is Slovak
    'Naked Security': 'United Kingdom',
    'Computer Weekly Security': 'United Kingdom',
    'Heise Security': 'Germany',
    'Security.nl': 'Netherlands',
    'Niebezpiecznik': 'Poland',
    # Australia
    'CSO Australia': 'Australia',
    'IT News Australia': 'Australia',

    # === GOVERNMENT/CERT FEEDS ===
    # USA
    'CISA': 'United States',
    'US-CERT Alerts': 'United States',
    'US-CERT Bulletins': 'United States',
    # Canada
    'CCCS Advisories': 'Canada',
    'CCCS Alerts': 'Canada',
    'CCCS News': 'Canada',
    # EU
    'ENISA': 'European Union',
    'CERT-EU': 'European Union',
    # UK
    'NCSC UK': 'United Kingdom',
    # Germany
    'BSI Germany': 'Germany',
    # France
    'ANSSI France': 'France',
    # Netherlands
    'NCSC Netherlands': 'Netherlands',
    # Singapore
    'CSA Singapore': 'Singapore',
    # Japan
    'JPCERT': 'Japan',
    # Australia/NZ
    'ACSC Australia': 'Australia',
    'CERT NZ': 'New Zealand',
    'AusCERT': 'Australia',
    # Italy
    'CSIRT Italia': 'Italy',
    # Nordic
    'NCSC-FI Finland': 'Finland',
    'CERT-SE Sweden': 'Sweden',
    'CFCS Denmark': 'Denmark',
    'NSM Norway': 'Norway',
    # Central Europe
    'CERT.at Austria': 'Austria',
    'CCB Belgium': 'Belgium',
    'GovCERT Switzerland': 'Switzerland',
    'NUKIB Czech': 'Czech Republic',
    'CERT.PL Poland': 'Poland',
    'SK-CERT Slovakia': 'Slovakia',
    'NCSC Hungary': 'Hungary',
    # Eastern Europe
    'CERT.LV Latvia': 'Latvia',
    'SI-CERT Slovenia': 'Slovenia',
    'CERT.hr Croatia': 'Croatia',
    'CERT-RO Romania': 'Romania',
    'CERT-UA Ukraine': 'Ukraine',
    # Southern Europe
    'CCN-CERT Spain': 'Spain',
    'CNCS Portugal': 'Portugal',
    'GR-CERT Greece': 'Greece',
    # Asia-Pacific
    'GovCERT.HK': 'Hong Kong',
    'HKCERT': 'Hong Kong',
    'BGD e-GOV CIRT': 'Bangladesh',
    # Middle East/Africa
    'EG-CERT Egypt': 'Egypt',
    'CERT-IL Israel': 'Israel',

    # === VENDOR FEEDS ===
    # USA
    'Microsoft Security': 'United States',
    'Google Security': 'United States',
    'Cisco Talos': 'United States',
    'Cloudflare Blog': 'United States',
    'Palo Alto Unit42': 'United States',
    'CrowdStrike': 'United States',
    'Mandiant': 'United States',
    'Proofpoint': 'United States',
    'Zscaler': 'United States',
    'IBM Security': 'United States',
    'Rapid7': 'United States',
    'Tenable': 'United States',
    'Qualys': 'United States',
    'Okta': 'United States',
    'SentinelOne': 'United States',
    'Cybereason': 'United States',
    'Varonis': 'United States',
    'FireEye': 'United States',
    'Symantec': 'United States',
    'McAfee': 'United States',
    'Bitdefender': 'Romania',
    'Malwarebytes': 'United States',
    'Fortinet': 'United States',
    'AWS Security': 'United States',
    'GitHub Security': 'United States',
    # UK
    'Sophos': 'United Kingdom',
    'Darktrace': 'United Kingdom',
    # Russia
    'Kaspersky SecureList': 'Russia',
    # Finland
    'F-Secure': 'Finland',
    # Czech Republic
    'Avast': 'Czech Republic',
    # Slovakia
    'ESET': 'Slovakia',
    # Japan
    'Trend Micro': 'Japan',
    # Israel
    'Check Point': 'Israel',
    'CyberArk': 'Israel',

    # === RESEARCH FEEDS ===
    # USA
    'SANS ISC': 'United States',
    'Mandiant Research': 'United States',
    'Secureworks Research': 'United States',
    'Malwarebytes Labs': 'United States',
    'NIST Cybersecurity': 'United States',
    # Canada
    'Citizen Lab': 'Canada',
    # Israel
    'Check Point Research': 'Israel',
    # Finland
    'F-Secure Labs': 'Finland',
    # Czech Republic
    'Avast Threat Labs': 'Czech Republic',
    # Slovakia
    'ESET Research': 'Slovakia',
    # UK
    'NCC Group Research': 'United Kingdom',
    # Japan
    'Trend Micro Research': 'Japan',
    # Russia
    'Kaspersky Research': 'Russia',
}

def get_countries_with_sources():
    """Get list of countries that have at least one RSS source, with source count"""
    country_sources = {}
    for feed_name, country in FEED_COUNTRY_MAP.items():
        if country not in country_sources:
            country_sources[country] = []
        country_sources[country].append(feed_name)
    return {country: len(sources) for country, sources in sorted(country_sources.items())}

def get_feeds_for_countries(selected_countries):
    """Filter RSS feeds to only include those from selected countries"""
    if not selected_countries:
        return None  # Return None to indicate no filtering (fetch all)

    selected_set = set(selected_countries)
    selected_feeds = set()

    for feed_name, country in FEED_COUNTRY_MAP.items():
        if country in selected_set:
            selected_feeds.add(feed_name)

    return selected_feeds

# Article helper function for formatting
def format_article(article):
    """Format article dict for API response"""
    published_date = article.get('published_date', '')
    fetched_date = article.get('fetched_date', '')

    # Ensure dates end with 'Z' for ISO format
    if published_date and not published_date.endswith('Z'):
        published_date = published_date + 'Z' if 'T' in published_date else published_date
    if fetched_date and not fetched_date.endswith('Z'):
        fetched_date = fetched_date + 'Z' if 'T' in fetched_date else fetched_date

    return {
        'id': article.get('id'),
        'title': article.get('title', ''),
        'link': article.get('link', ''),
        'description': article.get('description', ''),
        'source': article.get('source', ''),
        'publisher_type': article.get('publisher_type', ''),
        'category': article.get('content_type', 'News'),  # Keep 'category' for backward compatibility
        'content_type': article.get('content_type', 'News'),
        'country_region': article.get('country_region') or 'Global',
        'published_date': published_date,
        'fetched_date': fetched_date
    }

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

    # === EXPANDED GOVERNMENT/CERT SOURCES ===
    # G20/EU/NATO CERTs
    if 'csirt italia' in source_lower or 'csirt.gov.it' in url_lower:
        countries.add('Italy')
    if 'ncsc-fi' in source_lower or 'kyberturvallisuuskeskus' in url_lower:
        countries.add('Finland')
    if 'cert-se' in source_lower or 'cert.se' in url_lower:
        countries.add('Sweden')
    if 'cfcs' in source_lower or 'cert.dk' in url_lower:
        countries.add('Denmark')
    if 'nsm norway' in source_lower or 'nsm.no' in url_lower:
        countries.add('Norway')
    if 'cert.at' in source_lower or 'cert.at' in url_lower:
        countries.add('Austria')
    if 'ccb belgium' in source_lower or 'cert.be' in url_lower:
        countries.add('Belgium')
    if 'govcert switzerland' in source_lower or 'govcert.ch' in url_lower:
        countries.add('Switzerland')
    if 'nukib' in source_lower or 'nukib.gov.cz' in url_lower:
        countries.add('Czech Republic')
    if 'cert.pl' in source_lower or 'cert.pl' in url_lower:
        countries.add('Poland')
    if 'sk-cert' in source_lower or 'sk-cert.sk' in url_lower:
        countries.add('Slovakia')
    if 'ncsc hungary' in source_lower or 'nki.gov.hu' in url_lower:
        countries.add('Hungary')
    if 'cert.lv' in source_lower or 'cert.lv' in url_lower:
        countries.add('Latvia')
    if 'si-cert' in source_lower or 'cert.si' in url_lower:
        countries.add('Slovenia')
    if 'cert.hr' in source_lower or 'cert.hr' in url_lower:
        countries.add('Croatia')
    if 'cert-ro' in source_lower or 'dnsc.ro' in url_lower:
        countries.add('Romania')
    if 'cert-ua' in source_lower or 'cert.gov.ua' in url_lower:
        countries.add('Ukraine')
    if 'ccn-cert' in source_lower or 'ccn-cert.cni.es' in url_lower:
        countries.add('Spain')
    if 'cncs portugal' in source_lower or 'cncs.gov.pt' in url_lower:
        countries.add('Portugal')
    if 'gr-cert' in source_lower or 'cert.grnet.gr' in url_lower:
        countries.add('Greece')
    if 'govcert.hk' in source_lower or 'govcert.gov.hk' in url_lower:
        countries.add('Hong Kong')
    if 'hkcert' in source_lower or 'hkcert.org' in url_lower:
        countries.add('Hong Kong')
    if 'bgd' in source_lower or 'cirt.gov.bd' in url_lower:
        countries.add('Bangladesh')
    if 'eg-cert' in source_lower or 'egcert.eg' in url_lower:
        countries.add('Egypt')
    if 'cert-il' in source_lower:
        countries.add('Israel')
    if 'auscert' in source_lower or 'auscert.org.au' in url_lower:
        countries.add('Australia')

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

def categorize_content(title, description, source, url=None, use_ml=True):
    """
    Categorize articles based on content:
    - News: Incident reports and latest news
    - Event: Events, meetups, announcements, conference reports
    - Alert: Newsletters/advisories that call attention to specific types of attacks
    - Research: Research papers and latest research findings

    Uses ML-based classification when available (more accurate), falls back to keywords.
    Priority: Groq LLM > Local ML Model > Keyword-based
    """
    if not title:
        return 'News'

    # Try Groq LLM-based categorization first (most accurate)
    if use_ml:
        try:
            categorize_fn = get_llm_categorizer()
            if categorize_fn:
                category, confidence = categorize_fn(title, description)
                if category and confidence > 0.4:
                    return category
        except Exception as e:
            pass  # Fall through to ML model

        # Try local ML model as fallback (good accuracy, no API needed)
        try:
            ml_categorize_fn = get_ml_categorizer()
            if ml_categorize_fn:
                category, confidence = ml_categorize_fn(title, description)
                if category and confidence > 0.4:
                    return category
        except Exception as e:
            pass  # Fall through to keyword-based

    # Fallback to keyword-based categorization
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
        
        # Get cached metadata for this feed from Google Sheets
        cache_etag = None
        cache_last_modified = None
        cache_content_hash = None
        try:
            sheets = get_sheets_client()
            cache = sheets.get_feed_cache(feed_config['url'])
            if cache:
                cache_etag = cache.get('etag')
                cache_last_modified = cache.get('last_modified')
                cache_content_hash = cache.get('content_hash')
        except Exception:
            # Continue without caching if Sheets API fails
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
                # Update last_fetched timestamp
                try:
                    sheets = get_sheets_client()
                    sheets.update_feed_cache(
                        feed_url=feed_config['url'],
                        etag=cache_etag,
                        last_modified=cache_last_modified,
                        content_hash=cache_content_hash
                    )
                except Exception:
                    pass
                return articles, None
            
            # Parse feed
            feed = feedparser.parse(response.content)
            
            # Update cache metadata in Google Sheets
            try:
                etag = response.headers.get('ETag')
                last_modified = response.headers.get('Last-Modified')
                sheets = get_sheets_client()
                sheets.update_feed_cache(
                    feed_url=feed_config['url'],
                    etag=etag,
                    last_modified=last_modified,
                    content_hash=content_hash
                )
            except Exception:
                # Continue without caching if update fails
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
                # Use fast mode (keywords only) during bulk fetches for speed
                # ML categorization can be done later via re-categorize endpoint
                use_ml_during_fetch = os.environ.get('USE_ML_DURING_FETCH', 'false').lower() == 'true'
                content_type = categorize_content(title, description, feed_config['name'], link, use_ml=use_ml_during_fetch)
                
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
                    'published_date': published_date.isoformat() if published_date else datetime.now(timezone.utc).isoformat()
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

@app.route('/api/feeds/sources-by-country', methods=['GET'])
def get_sources_by_country():
    """Get list of countries that have RSS sources configured"""
    country_sources = get_countries_with_sources()
    return jsonify({
        'countries': country_sources,
        'total_countries': len(country_sources),
        'total_sources': sum(country_sources.values())
    })

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

def fetch_all_feeds_internal(max_workers=10, only_recent=False, recent_days=1, countries=None):
    """Internal function to fetch all RSS feeds - can be called manually or by scheduler

    Args:
        max_workers: Number of parallel workers
        only_recent: Only fetch recent articles
        recent_days: Number of days to look back
        countries: List of countries to fetch from (None = all countries)
    """
    all_articles = []
    successful_feeds = 0
    failed_feeds = 0

    # Get feed names to include based on country filter
    allowed_feeds = get_feeds_for_countries(countries) if countries else None

    # Collect all feeds, optionally filtering by country
    all_feed_configs = []
    for category, feeds in RSS_FEEDS.items():
        for feed in feeds:
            # If we have a country filter, only include feeds from those countries
            if allowed_feeds is not None:
                if feed['name'] in allowed_feeds:
                    all_feed_configs.append(feed)
            else:
                all_feed_configs.append(feed)
    
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
                        cutoff_date = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
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
        
        # Batch add articles to Google Sheets
        print(f"\nProcessing {len(all_articles)} articles...")

        sheets = get_sheets_client()
        result = sheets.add_articles(all_articles)
        new_count = result.get('added', 0)
        deleted_for_capacity = result.get('deleted_for_capacity', 0)
        if deleted_for_capacity > 0:
            print(f"  Capacity limit reached: deleted {deleted_for_capacity} oldest articles (max: {result.get('max_articles', 5000)})")

        # Clean up old articles (keep only last 90 days by default)
        retention_days = int(os.environ.get('ARTICLE_RETENTION_DAYS', 90))
        cleanup_result = sheets.cleanup_old_articles(retention_days)
        deleted_count = cleanup_result.get('deleted', 0)
        
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
            'deleted_for_capacity': deleted_for_capacity,
            'max_articles': 5000,
            'retention_days': retention_days
        }
    except Exception as e:
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
    """Manual endpoint to fetch all RSS feeds and store in database

    Accepts JSON body with optional parameters:
    - max_workers: Number of parallel fetch workers (default: 10)
    - only_recent: Only fetch articles from last 24 hours (default: false)
    - recent_days: Days to look back (default: 1)
    - countries: List of country names to fetch from (default: null = all)
    """
    # Get optional parameters
    max_workers = int(request.json.get('max_workers', 10)) if request.json else 10
    only_recent = request.json.get('only_recent', False) if request.json else False
    recent_days = int(request.json.get('recent_days', 1)) if request.json else 1
    countries = request.json.get('countries', None) if request.json else None  # List of country names

    result = fetch_all_feeds_internal(max_workers, only_recent, recent_days, countries)
    
    if result['status'] == 'error':
        return jsonify(result), 500
    return jsonify(result)

@app.route('/api/articles', methods=['GET'])
def get_articles():
    """Get articles with filtering and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    category = request.args.get('category', None)
    publisher_type = request.args.get('publisher_type', None)
    source = request.args.get('source', None)
    search = request.args.get('search', None)
    days = request.args.get('days', None, type=int)
    countries = request.args.get('countries', None)
    sort_by = request.args.get('sort_by', 'newest')

    sheets = get_sheets_client()
    result = sheets.get_articles(
        page=page,
        per_page=per_page,
        category=category,
        publisher_type=publisher_type,
        source=source,
        search=search,
        days=days,
        countries=countries,
        sort=sort_by
    )

    # Format articles for response
    articles = [format_article(a) for a in result.get('articles', [])]

    return jsonify({
        'articles': articles,
        'total': result.get('total', 0),
        'page': result.get('page', page),
        'per_page': result.get('per_page', per_page),
        'pages': result.get('pages', 0)
    })

@app.route('/api/articles/sources', methods=['GET'])
def get_sources():
    """Get list of all sources"""
    sheets = get_sheets_client()
    sources = sheets.get_sources()
    # Return simple list format
    sources_list = [{'name': s, 'country': None} for s in sources]
    sources_list.sort(key=lambda x: x['name'])
    return jsonify({'sources': sources_list})

@app.route('/api/articles/categories', methods=['GET'])
def get_categories():
    """Get list of all content type categories"""
    sheets = get_sheets_client()
    categories = sheets.get_categories()
    return jsonify({'categories': categories})

@app.route('/api/articles/publisher-types', methods=['GET'])
def get_publisher_types():
    """Get list of all publisher types"""
    sheets = get_sheets_client()
    publisher_types = sheets.get_publisher_types()
    return jsonify({'publisher_types': publisher_types})

@app.route('/api/articles/countries', methods=['GET'])
def get_countries():
    """Get list of all unique countries/regions"""
    sheets = get_sheets_client()
    db_countries = set(sheets.get_countries())

    # Define all supported countries (G20, EU, NATO, and additional)
    all_supported_countries = {
        # G20 Countries
        'Argentina', 'Australia', 'Brazil', 'Canada', 'China', 'France', 'Germany',
        'India', 'Indonesia', 'Italy', 'Japan', 'Mexico', 'Russia', 'Saudi Arabia',
        'South Africa', 'South Korea', 'Turkey', 'United Kingdom', 'United States',
        # EU Countries
        'European Union', 'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus',
        'Czech Republic', 'Denmark', 'Estonia', 'Finland', 'Greece', 'Hungary',
        'Ireland', 'Latvia', 'Lithuania', 'Luxembourg', 'Malta', 'Netherlands',
        'Poland', 'Portugal', 'Romania', 'Slovakia', 'Slovenia', 'Spain', 'Sweden',
        # NATO Countries (additional)
        'Albania', 'Iceland', 'Montenegro', 'North Macedonia', 'Norway',
        # South America
        'Chile', 'Colombia', 'Peru', 'Venezuela', 'Uruguay', 'Paraguay', 'Bolivia', 'Ecuador',
        # Asia-Pacific
        'Thailand', 'Vietnam', 'Philippines', 'Malaysia', 'Taiwan', 'Singapore',
        'Hong Kong', 'Bangladesh', 'Sri Lanka', 'Myanmar', 'Cambodia', 'Laos',
        # Middle East & Africa
        'Egypt', 'Nigeria', 'Kenya', 'Morocco', 'Tunisia', 'Algeria',
        'Israel', 'United Arab Emirates',
        # Other
        'Pakistan', 'New Zealand', 'Switzerland', 'Ukraine'
    }

    all_countries = db_countries.union(all_supported_countries)
    all_countries.discard('Global')
    sorted_countries = sorted(all_countries)
    return jsonify({'countries': sorted_countries})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics about articles"""
    days = request.args.get('days', None, type=int)

    sheets = get_sheets_client()
    stats = sheets.get_stats(days=days)

    retention_days = int(os.environ.get('ARTICLE_RETENTION_DAYS', 90))

    return jsonify({
        'total_articles': stats.get('total_articles', 0),
        'recent_articles_24h': stats.get('recent_articles_24h', 0),
        'by_publisher_type': stats.get('by_publisher_type', {}),
        'by_content_type': stats.get('by_content_type', {}),
        'retention_days': retention_days,
        'max_articles': 5000,
        'oldest_article_date': stats.get('oldest_article_date')
    })

@app.route('/api/cleanup', methods=['POST'])
def cleanup_old_articles():
    """Manually clean up old articles"""
    try:
        retention_days = request.json.get('days', 90) if request.json else 90
        sheets = get_sheets_client()
        result = sheets.cleanup_old_articles(retention_days)

        return jsonify({
            'status': 'success',
            'deleted_count': result.get('deleted', 0),
            'retention_days': retention_days
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/articles/re-categorize', methods=['POST'])
def re_categorize_all():
    """Re-categorize all articles (not supported with Google Sheets backend)"""
    return jsonify({
        'status': 'info',
        'message': 'Re-categorization is not supported with Google Sheets backend. Articles are categorized when fetched.'
    })

@app.route('/api/articles/delete-by-source', methods=['POST'])
def delete_articles_by_source():
    """Delete articles from a specific source"""
    try:
        source_name = request.json.get('source') if request.json else None
        if not source_name:
            return jsonify({
                'status': 'error',
                'message': 'Source name is required'
            }), 400

        sheets = get_sheets_client()
        result = sheets.delete_by_source(source_name)

        return jsonify({
            'status': 'success',
            'source': source_name,
            'deleted_count': result.get('deleted', 0)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Google Sheets backend - no database initialization needed
# Test connection on startup
try:
    sheets = get_sheets_client()
    health = sheets.health_check()
    print(f"✓ Google Sheets backend connected: {health.get('status', 'unknown')}")
except Exception as e:
    print(f"Warning: Could not connect to Google Sheets backend: {e}")
    print("  Make sure SHEETS_API_URL is set correctly.")

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

