# CyberNewsHub

A modern web application that aggregates cybersecurity news from leading sources around the world, including industry news sites, government agencies, security vendors, and research labs.

## Features

- **Comprehensive News Aggregation**: Fetches news from 30+ authoritative cybersecurity sources
- **Real-time Updates**: Fetch the latest news with a single click
- **Advanced Filtering**: Filter by category, source, time range, and search keywords
- **Beautiful UI**: Modern, responsive design with smooth animations
- **Statistics Dashboard**: View total articles, recent activity, and category breakdowns
- **Pagination**: Navigate through large collections of articles efficiently
- **Automatic Cleanup**: Automatically removes articles older than 90 days to keep the database lean

## News Sources

### Industry News Sites
- The Hacker News
- BleepingComputer
- Krebs on Security
- Dark Reading
- SC Magazine
- SecurityWeek

### Government Agencies
- CISA (United States)
- US-CERT Alerts
- ENISA (European Union)
- NCSC (United Kingdom)
- CERT-EU
- CSA Singapore
- Canadian Centre for Cyber Security (CCCS)

### Security Vendors
- Microsoft Security Blog
- Google Security Blog
- Cisco Talos
- Cloudflare Blog
- Palo Alto Unit42
- CrowdStrike
- FireEye
- Sophos
- Kaspersky SecureList

### Research Labs
- Citizen Lab
- Check Point Research
- Recorded Future
- SANS Internet Storm Center
- Rapid7

## Tech Stack

- **Backend**: Python, Flask, SQLAlchemy, Feedparser
- **Frontend**: React, Axios, date-fns
- **Database**: SQLite

## Installation

### Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

1. Navigate to the project root directory:
```bash
cd CyberNewsHub
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Start the backend server:
```bash
cd backend
python app.py
```

The backend API will be running on `http://localhost:8000` (using 8000 to avoid common port conflicts)

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

The frontend will be running on `http://localhost:3000`

## Usage

### Quick Start (Easiest)

**Option 1: Using Python script (Recommended)**
```bash
./start.py
```

Or on Windows:
```bash
python start.py
```

**Option 2: Using npm (if you have Node.js installed)**
```bash
# First time: install concurrently
npm install

# Then start both servers
npm start
```

Both methods will start both backend and frontend servers automatically!

### Manual Start

If you prefer to start servers separately:

1. **Start the backend**:
   ```bash
   cd backend
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   python app.py
   ```

2. **Start the frontend** (in a new terminal):
   ```bash
   cd frontend
   npm start
   ```

3. **Open your browser** and navigate to `http://localhost:3000`
4. **Fetch news**: Click the "Fetch Latest News" button to aggregate articles from all sources (this may take 1-2 minutes)
5. **Filter articles**: Use the search bar, category dropdown, source dropdown, or time range filter
6. **Read articles**: Click on any article title or "Read Full Article" to open the original source

**Note**: The first fetch may take 1-2 minutes as it fetches from 30+ sources. Some feeds may fail (this is normal), but you'll still get articles from successful feeds.

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/feeds/fetch` - Fetch all RSS feeds (automatically cleans up old articles)
- `GET /api/articles` - Get articles with filters and pagination
  - Query parameters: `page`, `per_page`, `category`, `source`, `search`, `days`
- `GET /api/articles/sources` - Get list of all sources
- `GET /api/articles/categories` - Get list of all categories
- `GET /api/stats` - Get statistics about articles
- `POST /api/cleanup` - Manually clean up old articles (optional: `{"days": 90}` in body)

## Database Management

The app automatically manages database size by:
- **Automatic Cleanup**: When fetching feeds, articles older than 90 days are automatically deleted
- **Configurable Retention**: Set `ARTICLE_RETENTION_DAYS` environment variable to change retention period (default: 90 days)
- **Duplicate Prevention**: Articles are deduplicated by URL, so fetching multiple times won't create duplicates

To customize retention period, set the environment variable:
```bash
export ARTICLE_RETENTION_DAYS=60  # Keep only last 60 days
```

## Project Structure

```
CyberNewsHub/
├── backend/
│   └── app.py              # Flask API server
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── App.js          # Main app component
│   │   └── index.js        # Entry point
│   └── package.json
├── requirements.txt        # Python dependencies
├── .gitignore
└── README.md
```

## Future Enhancements

- Add NewsAPI, GNews API, and Mediastack integration for additional sources
- Implement article bookmarking/favorites
- Add email notifications for breaking news
- Implement user accounts and personalized feeds
- Add RSS feed export functionality
- Implement article tagging and categorization
- Add dark mode theme

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

See LICENSE file for details.
