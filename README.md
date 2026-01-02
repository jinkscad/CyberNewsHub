# CyberNewsHub

A modern web application that aggregates cybersecurity news from leading sources around the world, including industry news sites, government agencies, security vendors, and research labs. Features global coverage of G20 countries, EU member states, and sources from all continents.

## Features

- **Comprehensive News Aggregation**: Fetches news from 117+ authoritative cybersecurity sources across 36 countries
- **Global Coverage**: Sources from all continents, G20 countries, EU member states, and NATO countries
- **Automatic Updates**: Automatically fetches feeds every 12 hours in the background
- **Manual Updates**: Fetch the latest news on-demand with a single click
- **Advanced Filtering**: 
  - Filter by content category (News, Research, Event, Alert, etc.)
  - Filter by source (with country tags)
  - Filter by country/region (with searchable dropdown and country flags)
  - Filter by time range (24 hours, 7 days, 30 days, 90 days, or all time)
  - Full-text search across titles and descriptions
- **Smart Sorting**: Sort articles by newest first or oldest first
- **AI-Powered Content Categorization**: Automatically categorizes articles using ML/AI with three-tier approach:
  - Groq LLM (primary) - Most accurate, uses large language model
  - Local ML Model (fallback) - Good accuracy, runs locally without API
  - Keyword-based (last resort) - Reliable rule-based fallback
- **Country Detection**: Automatically detects and tags articles with their country/region
- **Publisher Classification**: Identifies sources as Industry, Government, Vendor, or Research
- **Beautiful UI**: Modern, responsive design with smooth animations and dark theme
- **Statistics Dashboard**: View total articles, recent activity, category breakdowns, and publisher type statistics
- **Fast Mode**: Option to show only articles from the last 24 hours for faster loading
- **Advanced Fetch Settings**: Select specific countries to fetch news from (36 countries available)
- **Pagination**: Navigate through large collections of articles efficiently
- **Google Sheets Backend**: Uses Google Sheets as a serverless database via Google Apps Script API
- **Automatic Cleanup**: Automatically removes articles older than 90 days to keep the database lean
- **Capacity Management**: Auto-deletes oldest articles when approaching 5,000 article limit
- **HTTP Caching**: Intelligent caching to reduce redundant feed fetches and improve performance

## News Sources

The application aggregates news from **117+ sources** across **36 countries** in four categories:

### Industry News Sites (29 sources)
- The Hacker News, BleepingComputer, Krebs on Security
- Dark Reading, SecurityWeek, InfoSecurity Magazine
- Security Boulevard, CyberScoop, Security Affairs
- The Register Security, ZDNet Security
- And many more...

### Government CERTs (40+ sources from 36 countries)
**North America:**
- CISA, US-CERT (United States)
- Canadian Centre for Cyber Security (Canada)

**Europe:**
- NCSC UK, ENISA, CERT-EU
- BSI Germany, ANSSI France, NCSC Netherlands
- CSIRT Italia, CCN-CERT Spain, CNCS Portugal
- CERT-SE Sweden, NCSC-FI Finland, CFCS Denmark, NSM Norway
- CERT.at Austria, CCB Belgium, GovCERT Switzerland
- CERT.PL Poland, NUKIB Czech, SK-CERT Slovakia
- CERT.LV Latvia, SI-CERT Slovenia, CERT.hr Croatia
- CERT-RO Romania, CERT-UA Ukraine, GR-CERT Greece, NCSC Hungary

**Asia-Pacific:**
- JPCERT (Japan), CSA Singapore
- GovCERT.HK, HKCERT (Hong Kong)
- BGD e-GOV CIRT (Bangladesh)

**Oceania:**
- ACSC Australia, AusCERT, CERT NZ

**Other:**
- EG-CERT Egypt, CERT-IL Israel

### Security Vendors (34 sources)
- Microsoft Security
- Google Security
- Cisco Talos
- Cloudflare Blog
- Palo Alto Unit42
- CrowdStrike
- Sophos
- Check Point Research
- Mandiant
- CyberArk
- And many more...

### Research Labs (13 sources)
- Citizen Lab
- Recorded Future
- SANS Internet Storm Center
- Rapid7
- Kaspersky Research
- Trend Micro Research
- And more...

## Tech Stack

- **Backend**:
  - Python 3.8+
  - Flask 3.0.0
  - Feedparser 6.0+
  - APScheduler 3.10.4 (for automatic feed fetching)
  - Requests 2.31.0
  - Transformers (for local ML categorization)
  - PyTorch (for ML model inference)
- **Frontend**:
  - React
  - Axios
  - date-fns
- **Database**: Google Sheets (via Google Apps Script REST API)
- **API Layer**: Google Apps Script (serverless)

## Installation

### Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn

### Quick Setup

**Option 1: Using setup script (Recommended for first time)**
```bash
./setup.sh
```

This will:
- Create a Python virtual environment
- Install all backend dependencies
- Install all frontend dependencies

**Option 2: Manual Setup**

1. **Backend Setup**:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r ../requirements.txt
   ```

2. **Frontend Setup**:
   ```bash
   cd frontend
   npm install
   ```

## Usage

### Starting the Application

**Option 1: Using Python script (Recommended)**
```bash
./start.py
```

Or on Windows:
```bash
python start.py
```

This script will:
- Start the Flask backend on `http://localhost:8000`
- Start the React frontend on `http://localhost:3000`
- Handle port conflicts automatically
- Display logs for both servers

**Option 2: Manual Start**

1. **Start the backend** (in one terminal):
   ```bash
   cd backend
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   python app.py
   ```

2. **Start the frontend** (in another terminal):
   ```bash
   cd frontend
   npm start
   ```

3. **Open your browser** and navigate to `http://localhost:3000`

### Using the Application

1. **Fetch News**:
   - Click the "Fetch News" button to manually fetch articles from all sources
   - Click the gear icon (⚙️) next to Fetch News for **Advanced Fetch Settings**:
     - Select specific countries to fetch from (36 countries available)
     - See source count per country
     - Search and filter countries
     - Select All / Clear All options
   - The app automatically fetches feeds every 12 hours in the background
   - First fetch may take 1-2 minutes as it fetches from 117+ sources

2. **Filter Articles**:
   - **Search**: Use the search bar to find articles by keywords
   - **Category**: Filter by content type (News, Research, Event, Alert, etc.)
   - **Source**: Filter by specific news source (sources show country tags)
   - **Time Range**: Filter by publication date (Last 24 Hours, 7 Days, 30 Days, 90 Days, or All Time)
   - **Country/Region**: Filter by country with searchable dropdown and country flags

3. **Sort Articles**:
   - Use the "Sort By" dropdown above the article list
   - Choose "Newest First" (default) or "Oldest First"

4. **View Statistics**:
   - Check the statistics dashboard for total articles, recent activity, and breakdowns by category and publisher type

5. **Fast Mode**:
   - Enable "Fast mode" in the header to show only articles from the last 24 hours

6. **Re-categorize**:
   - Use the "Re-categorize" button to update content categories for existing articles

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/feeds/fetch` - Manually fetch RSS feeds
  - Optional body parameters:
    - `max_workers`: Number of parallel workers (default: 10)
    - `only_recent`: Fetch only recent articles (default: false)
    - `recent_days`: Days to look back for recent articles (default: 1)
    - `countries`: Array of country names to fetch from (default: null = all countries)
- `GET /api/feeds/sources-by-country` - Get list of countries with RSS sources
  - Returns: `{countries: {country: source_count}, total_countries, total_sources}`
- `GET /api/feeds/schedule` - Get information about automatic feed fetching schedule
- `GET /api/articles` - Get articles with filters and pagination
  - Query parameters: 
    - `page`: Page number (default: 1)
    - `per_page`: Articles per page (default: 50)
    - `category`: Content type filter
    - `publisher_type`: Publisher type filter (Industry, Government, Vendor, Research)
    - `source`: Source name filter
    - `search`: Full-text search
    - `days`: Time range filter (1, 7, 30, 90)
    - `countries`: Comma-separated list of countries
    - `sort_by`: Sort order ('newest' or 'oldest', default: 'newest')
- `GET /api/articles/sources` - Get list of all sources with their primary country
- `GET /api/articles/categories` - Get list of all content categories
- `GET /api/articles/countries` - Get list of all countries/regions
- `GET /api/stats` - Get statistics about articles
  - Query parameters: Same as `/api/articles` for filtered statistics
- `POST /api/articles/delete-by-source` - Delete articles from a specific source
  - Body: `{"source": "Source Name"}`
- `POST /api/cleanup` - Manually clean up old articles
  - Optional body: `{"days": 90}` (default: 90 days)

## Automatic Feed Fetching

The application automatically fetches feeds every 12 hours using APScheduler. The scheduler:
- Runs in the background
- Fetches all feeds in parallel (up to 10 workers)
- Automatically cleans up articles older than 90 days
- Logs all activity for monitoring

To check the next scheduled fetch time:
```bash
curl http://localhost:8000/api/feeds/schedule
```

## Database Management (Google Sheets)

The app uses Google Sheets as a serverless database with automatic management:
- **Automatic Cleanup**: When fetching feeds, articles older than 90 days are automatically deleted
- **Capacity Limit**: Maximum 5,000 articles (auto-deletes oldest when exceeded)
- **Duplicate Prevention**: Articles are deduplicated by URL, so fetching multiple times won't create duplicates
- **HTTP Caching**: Uses ETag, Last-Modified, and Content-Hash to avoid redundant fetches
- **Serverless**: No database server to maintain - data persists in Google Sheets

### Google Sheets Setup

1. Create a new Google Sheet
2. Deploy the Google Apps Script from `google-apps-script/Code.gs`
3. Update `backend/sheets_client.py` with your deployed script URL

## Content Categorization

Articles are automatically categorized using a three-tier ML/AI approach for maximum accuracy:

### Categorization Methods (in priority order):

1. **Groq LLM** (Primary - Most Accurate)
   - Uses `llama-3.1-8b-instant` large language model via Groq API
   - Requires `GROQ_API_KEY` environment variable
   - Fast, accurate, and understands context
   - Get free API key at: https://console.groq.com

2. **Local ML Model** (Fallback - Good Accuracy)
   - Uses `typeform/distilbert-base-uncased-mnli` transformer model
   - Runs locally on your machine (no API needed)
   - Loads automatically on first use (~1 minute download)
   - Works offline and provides confidence scores

3. **Keyword-based** (Last Resort - Reliable)
   - Rule-based categorization using weighted keywords
   - Always available, no dependencies
   - Fast and reliable fallback

### Categories:

Articles are categorized into:
- **News**: Incident reports, breaches, attacks, hacks, ransomware events
- **Alert**: Security advisories, CVE disclosures, vulnerability warnings, patches
- **Research**: Security research, technical analysis, whitepapers, studies
- **Event**: Conferences, webinars, summits, workshops, training

The system automatically tries each method in order until one succeeds, ensuring the best possible categorization accuracy.

## Country/Region Detection

The app automatically detects and tags articles with their country/region based on:
- Top-level domain (TLD) analysis
- Source name patterns
- URL patterns
- Vendor/company locations
- Article content analysis

Supports detection for:
- All G20 countries
- All EU member states
- Major countries from all continents
- Global sources (tagged as "Global")

## Project Structure

```
CyberNewsHub/
├── backend/
│   ├── app.py              # Flask API server with RSS feed configuration
│   ├── sheets_client.py    # Google Sheets API client
│   ├── groq_categorizer.py # Groq LLM-based categorization
│   ├── ml_categorizer.py   # Local ML model-based categorization
│   ├── .env                # Environment variables (API keys, etc.) - not in git
│   └── venv/               # Python virtual environment
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/     # React components
│   │   │   ├── ArticleCard.js
│   │   │   ├── ArticleList.js
│   │   │   ├── Filters.js
│   │   │   ├── Header.js
│   │   │   ├── Stats.js
│   │   │   ├── LoadingSpinner.js
│   │   │   └── FetchSettingsModal.js  # Advanced fetch settings
│   │   ├── App.js          # Main app component
│   │   ├── App.css
│   │   └── index.js        # Entry point
│   └── package.json
├── google-apps-script/
│   └── Code.gs             # Google Apps Script for Sheets API
├── requirements.txt        # Python dependencies
├── start.py               # Script to start both servers
├── setup.sh               # Setup script for first-time installation
└── README.md
```

## Configuration

### Environment Variables

- `PORT`: Backend server port (default: 8000)
- `ARTICLE_RETENTION_DAYS`: Days to keep articles (default: 90)
- `MAX_ARTICLES_PER_FEED`: Maximum articles to fetch per feed (default: 20)
- `REACT_APP_API_URL`: Frontend API base URL (default: http://localhost:8000/api)
- `GROQ_API_KEY`: Groq API key for LLM-based categorization (optional but recommended)
  - Get free API key at: https://console.groq.com
  - Create `backend/.env` file with: `GROQ_API_KEY=your_key_here`
  - The `.env` file is automatically ignored by git for security

### Setting Up Groq API Key (Optional but Recommended)

For the most accurate categorization, set up a Groq API key:

1. Get a free API key from https://console.groq.com
2. Create a `.env` file in the `backend/` directory:
   ```bash
   cd backend
   echo "GROQ_API_KEY=your_key_here" > .env
   ```
3. The `.env` file is already in `.gitignore` and won't be committed

**Note**: The app works without the API key - it will use the local ML model and keyword-based categorization as fallbacks.

### RSS Feed Configuration

RSS feeds are configured in `backend/app.py` in the `RSS_FEEDS` dictionary. Feeds are organized by category:
- `industry`: Industry news sites
- `government`: Government agencies and CERTs
- `vendors`: Security vendor blogs
- `research`: Research labs and organizations

## Troubleshooting

### Port Already in Use

The `start.py` script automatically detects and handles port conflicts:
- For port 3000 (frontend): Prompts to kill existing process
- For port 8000 (backend): Shows error message with instructions

### Feeds Failing

Some feeds may fail due to:
- Network issues
- Feed URL changes
- Server downtime
- Rate limiting

The app continues to work with successful feeds. Check the fetch results for details on failed feeds.

### Database Issues

The app uses Google Sheets as a database. To reset:
1. Clear all rows in the "Articles" sheet (keep headers)
2. Clear all rows in the "FeedCache" sheet (keep headers)
3. Restart the backend

## Future Enhancements

- Implement article bookmarking/favorites
- Add email notifications for breaking news
- Implement user accounts and personalized feeds
- Add RSS feed export functionality
- Export articles to various formats (PDF, CSV, etc.)

## Deployment (Render.com - Free)

### Quick Deploy to Render

Since the app uses Google Sheets as a database (serverless), deployment is simplified:

1. **Deploy Backend**:
   - "New +" → "Web Service"
   - Connect GitHub repo
   - Build: `cd backend && pip install -r ../requirements.txt`
   - Start: `cd backend && python app.py`
   - Plan: Free

2. **Deploy Frontend**:
   - "New +" → "Static Site"
   - Connect same repo
   - Build: `cd frontend && npm install && npm run build`
   - Publish: `frontend/build`
   - Env var: `REACT_APP_API_URL` = `https://your-backend-url.onrender.com/api`

**Note**: No database setup required - data persists in Google Sheets automatically.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

See LICENSE file for details.
