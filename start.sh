#!/bin/bash

echo "🎓 Starting AI Teacher System (Full Version)..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip first
echo "Upgrading pip..."
pip install --upgrade pip

# Install full dependencies
echo "Installing full dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Please edit .env file and add your OpenAI API key for full functionality"
    echo "⚠️  Without API key, the AI features will not work properly"
fi

# Start simple backend server
echo "🚀 Starting simple backend server..."
cd backend
python main.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Check if backend is running
if curl -f http://localhost:8000/ > /dev/null 2>&1; then
    echo "✅ Backend server started successfully at http://localhost:8000"
else
    echo "❌ Backend server failed to start"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Start frontend server
echo "🌐 Starting frontend server..."
cd ../frontend
python3 -m http.server 8080 &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 2

echo "✅ Frontend server started at http://localhost:8080"
echo ""
echo "🎉 AI Teacher (Full Version) is ready!"
echo "📖 Open http://localhost:8080 in your browser"
echo "📋 API docs available at http://localhost:8000/docs"
echo ""
echo "Note: This is the full version with AI capabilities. Make sure your .env file contains valid API keys."
echo ""
echo "To stop the servers, press Ctrl+C"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "✅ Servers stopped"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Keep script running
wait
