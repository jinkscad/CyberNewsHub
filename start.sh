#!/bin/bash

echo "Starting CyberNewsHub..."
echo ""

# Check if virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo "Virtual environment not found. Running setup first..."
    ./setup.sh
    echo ""
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

# Start backend
echo "Starting backend server..."
cd backend
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
python app.py > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 3

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "Backend failed to start. Check backend.log for errors."
    exit 1
fi

echo "Backend running on http://localhost:5000 (PID: $BACKEND_PID)"

# Start frontend
echo "Starting frontend server..."
cd frontend
npm start > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait a moment for frontend to start
sleep 5

echo "Frontend starting on http://localhost:3000 (PID: $FRONTEND_PID)"
echo ""
echo "CyberNewsHub is starting up!"
echo ""
echo "Logs:"
echo "   Backend:  tail -f backend.log"
echo "   Frontend: tail -f frontend.log"
echo ""
echo "Open http://localhost:3000 in your browser"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for user interrupt
wait

