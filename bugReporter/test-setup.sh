#!/bin/bash

echo "🧪 Testing Bug Reporter Setup"
echo "=============================="

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please copy env.example to .env and configure it."
    exit 1
fi

echo "✅ .env file exists"

# Check if dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "❌ node_modules not found. Running npm install..."
    npm install
fi

echo "✅ Dependencies installed"

# Test if worker can start (with timeout)
echo "🔄 Testing worker startup..."
timeout 3s npm run worker:dev > /dev/null 2>&1
if [ $? -eq 124 ]; then
    echo "✅ Worker starts successfully"
else
    echo "❌ Worker failed to start"
    exit 1
fi

# Test if frontend can start (with timeout)
echo "🔄 Testing frontend startup..."
timeout 3s npm run dev > /dev/null 2>&1
if [ $? -eq 124 ]; then
    echo "✅ Frontend starts successfully"
else
    echo "❌ Frontend failed to start"
    exit 1
fi

echo ""
echo "🎉 All tests passed! Your Bug Reporter is ready to use."
echo ""
echo "To start the application:"
echo "1. Terminal 1: npm run worker:dev"
echo "2. Terminal 2: npm run dev"
echo "3. Open http://localhost:5173"
echo ""
echo "Default admin login: Use ADMIN_EMAIL and ADMIN_PASSWORD environment variables"
