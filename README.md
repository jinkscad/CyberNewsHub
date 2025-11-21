# CyberNewsHub

A modern web application that aggregates cybersecurity news from leading sources around the world, including industry news sites, government agencies, security vendors, and research labs. Features global coverage of G20 countries, EU member states, and sources from all continents.

## Features

- **Comprehensive News Aggregation**: Fetches news from 90+ authoritative cybersecurity sources
- **Global Coverage**: Sources from all continents (except Antarctica), G20 countries, and EU member states
- **Automatic Updates**: Automatically fetches feeds every 12 hours in the background
- **Manual Updates**: Fetch the latest news on-demand with a single click
- **Advanced Filtering**: 
  - Filter by content category (News, Research, Event, Alert, etc.)
  - Filter by source (with country tags)
  - Filter by country/region (with searchable dropdown and country flags)
  - Filter by time range (24 hours, 7 days, 30 days, 90 days, or all time)
  - Full-text search across titles and descriptions
- **Smart Sorting**: Sort articles by newest first or oldest first
- **Content Categorization**: Automatically categorizes articles as News, Research, Events, Alerts, etc.
- **Country Detection**: Automatically detects and tags articles with their country/region
- **Publisher Classification**: Identifies sources as Industry, Government, Vendor, or Research
- **Beautiful UI**: Modern, responsive design with smooth animations and dark theme
- **Statistics Dashboard**: View total articles, recent activity, category breakdowns, and publisher type statistics
- **Fast Mode**: Option to show only articles from the last 24 hours for faster loading
- **Pagination**: Navigate through large collections of articles efficiently
- **Automatic Cleanup**: Automatically removes articles older than 90 days to keep the database lean
- **HTTP Caching**: Intelligent caching to reduce redundant feed fetches and improve performance

## News Sources

The application aggregates news from **90+ sources** across four categories:

### Industry News Sites (29 sources)
- The Hacker News
- BleepingComputer
- Krebs on Security
- Dark Reading
- SecurityWeek
- InfoSecurity Magazine
- Security Boulevard
- IT Security Guru
- CyberScoop
- Security Affairs
- The Register Security
- ZDNet Security
- And many more...

### Government Agencies (16 sources)
- CISA (United States)
- US-CERT Alerts
- NCSC (United Kingdom)
- ENISA (European Union)
- CERT-EU
- CSA Singapore
- Canadian Centre for Cyber Security (CCCS)
- And more from various countries...

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
  - SQLAlchemy 2.0+
  - Feedparser 6.0+
  - APScheduler 3.10.4 (for automatic feed fetching)
  - Requests 2.31.0
- **Frontend**: 
  - React
  - Axios
  - date-fns
- **Database**: SQLite

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
   - Click the "Fetch Latest News" button to manually fetch articles from all sources
   - The app automatically fetches feeds every 12 hours in the background
   - First fetch may take 1-2 minutes as it fetches from 90+ sources

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
- `POST /api/feeds/fetch` - Manually fetch all RSS feeds
  - Optional body parameters:
    - `max_workers`: Number of parallel workers (default: 10)
    - `only_recent`: Fetch only recent articles (default: false)
    - `recent_days`: Days to look back for recent articles (default: 1)
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

## Database Management

The app automatically manages database size by:
- **Automatic Cleanup**: When fetching feeds, articles older than 90 days are automatically deleted
- **Configurable Retention**: Set `ARTICLE_RETENTION_DAYS` environment variable to change retention period (default: 90 days)
- **Duplicate Prevention**: Articles are deduplicated by URL, so fetching multiple times won't create duplicates
- **HTTP Caching**: Uses ETag, Last-Modified, and Content-Hash to avoid redundant fetches

To customize retention period:
```bash
export ARTICLE_RETENTION_DAYS=60  # Keep only last 60 days
```

## Content Categorization

Articles are automatically categorized into:
- **News**: General cybersecurity news and updates
- **Research**: Security research, analysis, and reports
- **Event**: Security conferences, webinars, and events
- **Alert**: Security alerts, advisories, and warnings
- **Vulnerability**: Vulnerability disclosures and patches
- **Uncategorized**: Articles that don't fit other categories

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
│   ├── cybernews.db        # SQLite database (created automatically)
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
│   │   │   └── LoadingSpinner.js
│   │   ├── App.js          # Main app component
│   │   ├── App.css
│   │   └── index.js        # Entry point
│   └── package.json
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

If you need to reset the database:
```bash
cd backend
rm cybernews.db
python app.py  # Database will be recreated automatically
```

## Future Enhancements

- Add more RSS feed sources
- Implement article bookmarking/favorites
- Add email notifications for breaking news
- Implement user accounts and personalized feeds
- Add RSS feed export functionality
- Enhanced article tagging and categorization
- Add dark mode theme toggle
- Export articles to various formats (PDF, CSV, etc.)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

See LICENSE file for details.
