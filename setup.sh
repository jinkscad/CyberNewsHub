#!/bin/bash

echo "🛡️  CyberNewsHub Setup Script"
echo "=============================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ first."
    exit 1
fi

echo "✅ Python and Node.js are installed"
echo ""

# Setup backend
echo "📦 Setting up backend..."
cd backend
python3 -m venv venv 2>/dev/null || python3 -m venv venv
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
pip install -q --upgrade pip
pip install -q -r ../requirements.txt
echo "✅ Backend setup complete"
echo ""

# Setup frontend
echo "📦 Setting up frontend..."
cd ../frontend
npm install --silent
echo "✅ Frontend setup complete"
echo ""

cd ..
echo "🎉 Setup complete!"
echo ""
echo "To start the application, simply run:"
echo "  ./start.py"
echo ""
echo "Or use npm:"
echo "  npm start"
echo ""
echo "The app will be available at http://localhost:3000"

