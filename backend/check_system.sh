#!/bin/bash

# Ixora AI Assistant - System Check Script
# Quick validation of system components

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo ""
echo -e "${BOLD}${BLUE}Ixora AI Assistant - System Check${NC}"
echo ""

# Counter for results
TOTAL=0
PASSED=0

# Function to check file
check_file() {
    TOTAL=$((TOTAL + 1))
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

# Function to check directory
check_dir() {
    TOTAL=$((TOTAL + 1))
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${YELLOW}⚠${NC} $2"
        return 1
    fi
}

# 1. Environment Configuration
echo -e "${BOLD}${BLUE}1. ENVIRONMENT CONFIGURATION${NC}"
echo ""

check_file ".env" ".env file exists"
check_file ".env.example" ".env.example file exists"
check_file ".env.production" ".env.production file exists (for Docker)"

echo ""

# 2. Core Application Files
echo -e "${BOLD}${BLUE}2. CORE APPLICATION FILES${NC}"
echo ""

check_file "api.py" "Main API file"
check_file "admin_api.py" "Admin API file"
check_file "main.py" "CLI interface"
check_file "pyproject.toml" "Project configuration"

echo ""

# 3. Agent Modules
echo -e "${BOLD}${BLUE}3. AGENT MODULES${NC}"
echo ""

check_file "agent/unified_agent.py" "Unified Agent (RAG + Booking)"
check_file "agent/supervisor.py" "Supervisor Agent"
check_file "agent/rag_nodes.py" "RAG Nodes"
check_file "agent/graph.py" "Booking Graph"
check_file "agent/nodes.py" "Booking Nodes"

echo ""

# 4. RAG System
echo -e "${BOLD}${BLUE}4. RAG SYSTEM${NC}"
echo ""

check_file "rag/document_loader.py" "Document Loader"
check_file "rag/vector_store.py" "Vector Store Manager"
check_file "rag/rag_chain.py" "RAG Query Chain"
check_file "rag/init_vectorstore.py" "Vector Store Initializer"

echo ""

# 5. Database
echo -e "${BOLD}${BLUE}5. DATABASE${NC}"
echo ""

check_file "database/models.py" "Database Models"
check_file "database/database.py" "Database Connection"
check_file "database/chat_logger.py" "Chat Logger"
check_file "database/init_db.py" "Database Initializer"

echo ""

# 6. Admin System
echo -e "${BOLD}${BLUE}6. ADMIN SYSTEM${NC}"
echo ""

check_file "admin/auth.py" "Admin Authentication"

echo ""

# 7. Frontend
echo -e "${BOLD}${BLUE}7. FRONTEND${NC}"
echo ""

check_file "frontend/src/App.jsx" "React Chat App"
check_file "frontend/admin.html" "Admin Panel UI"
check_file "frontend/package.json" "Frontend Dependencies"

echo ""

# 8. Docker
echo -e "${BOLD}${BLUE}8. DOCKER CONFIGURATION${NC}"
echo ""

check_file "Dockerfile" "Backend Dockerfile"
check_file "docker-compose.yml" "Docker Compose Config"
check_file "frontend/Dockerfile" "Frontend Dockerfile"

echo ""

# 9. Documentation
echo -e "${BOLD}${BLUE}9. DOCUMENTATION${NC}"
echo ""

check_file "README.md" "Main README"
check_file "QUICK_START.md" "Quick Start Guide"
check_file "DOCKER_DEPLOYMENT.md" "Docker Deployment Guide"
check_file "COMPLETION_SUMMARY.md" "Completion Summary"

echo ""

# 10. Runtime Data
echo -e "${BOLD}${BLUE}10. RUNTIME DATA${NC}"
echo ""

check_dir "chroma_db" "Vector store initialized (chroma_db/)"
check_file "ixora_chat.db" "SQLite database initialized"

echo ""

# Summary
echo -e "${BOLD}${BLUE}================================================${NC}"
echo -e "${BOLD}${BLUE}SUMMARY${NC}"
echo -e "${BOLD}${BLUE}================================================${NC}"
echo ""
echo -e "Total Checks: $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $((TOTAL - PASSED))${NC}"
echo ""

if [ $PASSED -eq $TOTAL ]; then
    echo -e "${GREEN}${BOLD}✓ All checks passed! System is ready.${NC}"
    echo ""
    echo "Quick Start:"
    echo "  • Development: uv run python api.py"
    echo "  • Production:  docker-compose up -d"
    echo "  • Docs:        http://localhost:8000/docs"
    echo ""
elif [ $PASSED -ge $((TOTAL * 80 / 100)) ]; then
    echo -e "${YELLOW}${BOLD}⚠ Most checks passed. Minor setup needed.${NC}"
    echo ""
    echo "If vector store or database are missing:"
    echo "  1. uv run python database/init_db.py"
    echo "  2. uv run python rag/init_vectorstore.py"
    echo ""
else
    echo -e "${RED}${BOLD}✗ Some components are missing.${NC}"
    echo ""
    echo "Setup steps:"
    echo "  1. Ensure .env file is configured"
    echo "  2. Run: uv sync"
    echo "  3. Run: uv run python database/init_db.py"
    echo "  4. Run: uv run python rag/init_vectorstore.py"
    echo ""
    echo "See QUICK_START.md for details"
    echo ""
fi
