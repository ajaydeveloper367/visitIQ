#!/bin/bash
"""
VisitIQ Healthcare System - Docker Installation
Simple containerized deployment
"""

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🏥 VisitIQ Healthcare System - Docker Setup${NC}"
echo -e "${BLUE}============================================${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker Desktop${NC}"
    echo "   Download from: https://www.docker.com/products/docker-desktop"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker environment ready${NC}"

# Use docker compose (newer) or docker-compose (legacy)
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

echo -e "${BLUE}📋 Setting up Docker containers...${NC}"

# Generate data first (if needed)
if [[ ! -f "data/patients.csv" ]]; then
    echo -e "${BLUE}📊 Generating healthcare data...${NC}"
    python3 tools/generate_data.py --data-dir data 2>/dev/null || {
        echo -e "${BLUE}📦 Data will be generated in container${NC}"
    }
fi

# Build and start containers
echo -e "${BLUE}🐳 Building containers...${NC}"
$COMPOSE_CMD -f installation/docker/enhanced_docker-compose.yml build --quiet

echo -e "${BLUE}🚀 Starting VisitIQ system...${NC}"
$COMPOSE_CMD -f installation/docker/enhanced_docker-compose.yml up -d

# Wait for services to be ready
echo -e "${BLUE}⏳ Waiting for services to start...${NC}"
sleep 10

# Check if services are running
if $COMPOSE_CMD -f installation/docker/enhanced_docker-compose.yml ps | grep -q "Up"; then
    echo -e "${GREEN}✅ VisitIQ system is running!${NC}"
    echo
    echo -e "${BLUE}🌐 Web Interface:${NC} http://localhost:8501"
    echo -e "${BLUE}🤖 Ollama API:${NC} http://localhost:11434"
    echo
    echo -e "${BLUE}💡 Useful commands:${NC}"
    echo "   • View logs:    $COMPOSE_CMD -f installation/docker/enhanced_docker-compose.yml logs -f"
    echo "   • Stop system:  $COMPOSE_CMD -f installation/docker/enhanced_docker-compose.yml down"
    echo "   • Restart:      $COMPOSE_CMD -f installation/docker/enhanced_docker-compose.yml restart"
    echo
    echo -e "${GREEN}🎉 Healthcare AI scheduling is ready!${NC}"
    
    # Open browser
    sleep 2 && open http://localhost:8501 2>/dev/null &
    
else
    echo -e "${RED}❌ Failed to start services${NC}"
    echo "Check logs with: $COMPOSE_CMD -f installation/docker/enhanced_docker-compose.yml logs"
    exit 1
fi
