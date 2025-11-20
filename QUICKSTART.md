# 🚀 Quick Start Guide

## One-Command Setup & Start

### First Time Setup
```bash
./setup.sh
```

### Start the Application

**Option 1: Python script (Recommended)**
```bash
./start.py
```

**Option 2: npm (if you have Node.js)**
```bash
npm install  # First time only
npm start
```

That's it! The app will be available at **http://localhost:3000**

## What Happens

1. **Setup** (`./setup.sh`):
   - Creates Python virtual environment
   - Installs backend dependencies
   - Installs frontend dependencies

2. **Start** (`./start.py`):
   - Starts Flask backend on port 5000
   - Starts React frontend on port 3000
   - Opens automatically in your browser

## First Steps After Starting

1. Click **"🔄 Fetch Latest News"** to aggregate articles from all sources
2. Wait a few moments for the fetch to complete
3. Browse articles, use filters, and search!

## Troubleshooting

### Port Already in Use
If port 5000 or 3000 is already in use:
- Backend: Edit `backend/app.py` and change the port
- Frontend: React will prompt you to use a different port

### Setup Fails
Make sure you have:
- Python 3.8+ installed
- Node.js 16+ installed
- Internet connection (for downloading packages)

### Backend Won't Start
```bash
cd backend
source venv/bin/activate
pip install -r ../requirements.txt
python app.py
```

### Frontend Won't Start
```bash
cd frontend
npm install
npm start
```

## Stop the Application

Press `Ctrl+C` in the terminal where you ran `./start.py`

