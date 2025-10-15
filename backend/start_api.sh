#!/bin/bash
echo "🚀 Starting Ixora AI Assistant API..."
echo ""
echo "Checking components..."

# Test database
if [ -f "ixora_chat.db" ]; then
    echo "✅ Database ready"
else
    echo "⚠️  Database not found - initializing..."
    uv run python database/init_db.py
fi

echo ""
echo "Starting API server..."
echo "📍 API: http://localhost:8000"
echo "📖 Docs: http://localhost:8000/docs"
echo "🔐 Admin: http://localhost:8000/admin/login"
echo ""

uv run python api.py
