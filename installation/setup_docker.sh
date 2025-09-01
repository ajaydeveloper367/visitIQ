#!/bin/bash

# Healthcare Visit Prioritization System - Docker Setup Script
# Based on proven Docker + Ollama approach
# Optimized for macOS (Apple Silicon M4)

set -e

echo "🏥 Healthcare Visit Prioritization System - Docker Setup"
echo "========================================================"
echo "Optimized for macOS Apple Silicon (M1/M2/M3/M4)"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Detect operating system
OS="$(uname -s)"
case "${OS}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=macOS;;
    *)          MACHINE="UNKNOWN:${OS}"
esac

echo -e "${BLUE}📋 Detected OS: ${MACHINE}${NC}"
echo

# Detect architecture
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" ]]; then
    echo -e "${GREEN}✅ Detected Apple Silicon (optimized for M4)${NC}"
elif [[ "$ARCH" == "x86_64" ]]; then
    echo -e "${YELLOW}⚠️  Detected Intel Mac${NC}"
else
    echo -e "${RED}❌ Unsupported architecture: $ARCH${NC}"
    exit 1
fi
echo

# Check Docker installation
check_docker() {
    echo -e "${BLUE}🐳 Checking Docker installation...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed.${NC}"
        echo
        echo "Please install Docker Desktop for Mac:"
        echo "1. Visit: https://docs.docker.com/desktop/install/mac-install/"
        echo "2. Download Docker Desktop for Mac (Apple Silicon or Intel)"
        echo "3. Install and start Docker Desktop"
        echo "4. Run this script again"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}❌ Docker Compose is not installed.${NC}"
        echo "Docker Compose should be included with Docker Desktop."
        echo "Please reinstall Docker Desktop or install Docker Compose separately."
        exit 1
    fi
    
    echo -e "${GREEN}✅ Docker and Docker Compose are installed${NC}"
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        echo -e "${RED}❌ Docker daemon is not running.${NC}"
        echo "Please start Docker Desktop and try again."
        exit 1
    fi
    
    echo -e "${GREEN}✅ Docker daemon is running${NC}"
    echo
}

# Install Ollama locally (for better performance)
install_ollama() {
    echo -e "${BLUE}🤖 Setting up Ollama LLM service...${NC}"
    
    # Check if Ollama is already installed
    if command -v ollama &> /dev/null; then
        echo -e "${GREEN}✅ Ollama is already installed${NC}"
        OLLAMA_VERSION=$(ollama --version 2>/dev/null | head -1 || echo "unknown")
        echo "   Version: ${OLLAMA_VERSION}"
    else
        echo "📥 Installing Ollama..."
        
        case "${MACHINE}" in
            macOS)
                echo "   Installing Ollama for macOS..."
                if command -v brew &> /dev/null; then
                    echo "   Using Homebrew to install Ollama..."
                    brew install ollama
                    echo "   Starting Ollama service..."
                    brew services start ollama
                else
                    echo "   Homebrew not found. Installing Homebrew first..."
                    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                    
                    # Add Homebrew to PATH for Apple Silicon
                    if [[ "$ARCH" == "arm64" ]]; then
                        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
                        eval "$(/opt/homebrew/bin/brew shellenv)"
                    fi
                    
                    brew install ollama
                    brew services start ollama
                fi
                ;;
            Linux)
                echo "   Installing Ollama for Linux..."
                curl -fsSL https://ollama.com/install.sh | sh
                ;;
            *)
                echo -e "${RED}❌ Unsupported operating system: ${MACHINE}${NC}"
                exit 1
                ;;
        esac
        
        echo -e "${GREEN}✅ Ollama installed successfully${NC}"
    fi
    
    echo
    
    # Start Ollama service
    echo -e "${BLUE}🔍 Checking if Ollama is running...${NC}"
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Ollama service is already running and accessible${NC}"
    elif pgrep -f "ollama" > /dev/null; then
        echo -e "${GREEN}✅ Ollama process is running, waiting for it to be ready...${NC}"
    else
        echo -e "${BLUE}🚀 Starting Ollama service...${NC}"
        
        case "${MACHINE}" in
            macOS)
                if command -v brew &> /dev/null; then
                    echo "   Starting Ollama with Homebrew services..."
                    brew services start ollama 2>/dev/null || {
                        echo "   Homebrew service failed, starting manually..."
                        nohup ollama serve > /tmp/ollama.log 2>&1 &
                    }
                else
                    echo "   Starting Ollama manually..."
                    nohup ollama serve > /tmp/ollama.log 2>&1 &
                fi
                sleep 3
                ;;
            Linux)
                echo "   Starting Ollama in the background..."
                nohup ollama serve > /tmp/ollama.log 2>&1 &
                sleep 3
                ;;
        esac
    fi
    
    # Wait for Ollama to be ready
    echo -e "${BLUE}⏳ Waiting for Ollama to be ready...${NC}"
    TIMEOUT=30
    COUNT=0
    
    while ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; do
        if [ $COUNT -ge $TIMEOUT ]; then
            echo -e "${RED}❌ Ollama failed to start within ${TIMEOUT} seconds${NC}"
            echo "   Check the logs: tail /tmp/ollama.log"
            exit 1
        fi
        sleep 1
        COUNT=$((COUNT + 1))
    done
    
    echo -e "${GREEN}✅ Ollama is running and ready!${NC}"
    
    # Pull recommended model for healthcare system
    echo -e "${BLUE}📥 Downloading recommended LLM model...${NC}"
    echo "   This may take several minutes depending on your connection..."
    echo "   Downloading llama3 for healthcare AI assistance..."
    ollama pull llama3 2>/dev/null || {
        echo -e "${YELLOW}⚠️  Failed to download model automatically${NC}"
        echo "   You can download it later with: ollama pull llama3"
    }
    
    if ollama list | grep -q "llama3"; then
        echo -e "${GREEN}✅ LLM model ready for healthcare AI features${NC}"
    fi
}

# Build and start Docker containers
setup_docker_containers() {
    echo -e "${BLUE}🚀 Building and starting Docker containers...${NC}"
    
    # Check which docker-compose file to use
    if [[ -f "enhanced_docker-compose.yml" ]]; then
        COMPOSE_FILE="enhanced_docker-compose.yml"
        echo "   Using enhanced Docker Compose configuration..."
    else
        COMPOSE_FILE="docker-compose.yml"
        echo "   Using standard Docker Compose configuration..."
    fi
    
    # Build containers
    echo "   Building Docker images (this may take several minutes)..."
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    
    # Start containers in detached mode
    echo "   Starting Docker containers..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    echo -e "${GREEN}✅ Docker containers started${NC}"
    
    # Wait for services to be ready
    echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"
    sleep 15
    
    # Check if web application is running
    TIMEOUT=60
    COUNT=0
    
    while ! curl -s http://localhost:8501 >/dev/null 2>&1; do
        if [ $COUNT -ge $TIMEOUT ]; then
            echo -e "${RED}❌ Web application failed to start within ${TIMEOUT} seconds${NC}"
            echo "   Check the logs: docker-compose -f $COMPOSE_FILE logs"
            exit 1
        fi
        sleep 2
        COUNT=$((COUNT + 2))
    done
    
    echo -e "${GREEN}✅ Web application is ready!${NC}"
}

# Create management scripts
create_management_scripts() {
    echo -e "${BLUE}🔧 Creating management scripts...${NC}"
    
    # Determine compose file
    COMPOSE_FILE="enhanced_docker-compose.yml"
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        COMPOSE_FILE="docker-compose.yml"
    fi
    
    # Start script
    cat > "start_docker_app.sh" << EOF
#!/bin/bash
# Healthcare Visit Prioritization System - Docker Startup

echo "🏥 Starting Healthcare Visit Prioritization System (Docker)"
echo "=========================================================="
echo

# Start Ollama if not running
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "🤖 Starting Ollama service..."
    if command -v brew &> /dev/null; then
        brew services start ollama
    else
        nohup ollama serve > /tmp/ollama.log 2>&1 &
    fi
    sleep 3
fi

# Start Docker containers
echo "🚀 Starting Docker containers..."
docker-compose -f "$COMPOSE_FILE" up -d

echo
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check services
if curl -s http://localhost:8501 >/dev/null 2>&1; then
    echo "✅ Healthcare application is running!"
    echo
    echo "🌐 Access the application at: http://localhost:8501"
    echo "🤖 Ollama API available at: http://localhost:11434"
    echo
    echo "🏥 Features available:"
    echo "• AI Chatbot Assistant"
    echo "• Smart Patient Prioritization"
    echo "• FHIR Slot Management"
    echo "• Real-time Appointment Booking"
    echo "• Advanced Analytics"
    echo
    echo "📋 Management commands:"
    echo "• View logs:     docker-compose -f $COMPOSE_FILE logs -f"
    echo "• Stop system:   ./stop_docker_app.sh"
    echo "• Restart:       ./restart_docker_app.sh"
else
    echo "❌ Application failed to start. Check logs:"
    echo "   docker-compose -f $COMPOSE_FILE logs"
fi
EOF

    # Stop script
    cat > "stop_docker_app.sh" << EOF
#!/bin/bash
# Healthcare Visit Prioritization System - Docker Shutdown

echo "🏥 Stopping Healthcare Visit Prioritization System (Docker)"
echo "=========================================================="
echo

echo "🛑 Stopping Docker containers..."
docker-compose -f "$COMPOSE_FILE" down

echo "✅ Docker containers stopped"
echo
echo "Note: Ollama service is still running for other applications."
echo "To stop Ollama: brew services stop ollama"
EOF

    # Restart script
    cat > "restart_docker_app.sh" << EOF
#!/bin/bash
# Healthcare Visit Prioritization System - Docker Restart

echo "🏥 Restarting Healthcare Visit Prioritization System (Docker)"
echo "==========================================================="
echo

echo "🔄 Restarting Docker containers..."
docker-compose -f "$COMPOSE_FILE" restart

echo "⏳ Waiting for services to be ready..."
sleep 10

if curl -s http://localhost:8501 >/dev/null 2>&1; then
    echo "✅ System restarted successfully!"
    echo "🌐 Access at: http://localhost:8501"
else
    echo "❌ Restart failed. Check logs:"
    echo "   docker-compose -f $COMPOSE_FILE logs"
fi
EOF

    # Logs viewer script
    cat > "view_logs.sh" << EOF
#!/bin/bash
# Healthcare Visit Prioritization System - Log Viewer

echo "🏥 Healthcare Visit Prioritization System - Logs"
echo "==============================================="
echo
echo "Press Ctrl+C to exit log viewer"
echo

docker-compose -f "$COMPOSE_FILE" logs -f
EOF

    # Status checker script
    cat > "check_docker_status.sh" << EOF
#!/bin/bash
# Healthcare Visit Prioritization System - Status Checker

echo "🏥 Healthcare Visit Prioritization System - Docker Status"
echo "========================================================"
echo

# Check Docker containers
echo "🐳 Docker Containers:"
docker-compose -f "$COMPOSE_FILE" ps

echo
echo "🔍 Service Status:"

# Check web application
if curl -s http://localhost:8501 >/dev/null 2>&1; then
    echo "✅ Healthcare Web App: Running (http://localhost:8501)"
else
    echo "❌ Healthcare Web App: Not accessible"
fi

# Check Ollama
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "✅ Ollama LLM Service: Running (http://localhost:11434)"
    MODELS=\$(ollama list 2>/dev/null | tail -n +2 | wc -l)
    echo "   📦 Available models: \$MODELS"
else
    echo "❌ Ollama LLM Service: Not running"
    echo "   Start with: brew services start ollama"
fi

echo
echo "📊 Resource Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || echo "   Docker stats not available"

echo
echo "🚀 Quick Actions:"
echo "• Start system:   ./start_docker_app.sh"
echo "• Stop system:    ./stop_docker_app.sh"
echo "• View logs:      ./view_logs.sh"
echo "• Restart:        ./restart_docker_app.sh"
EOF

    # Cleanup script
    cat > "cleanup_docker.sh" << EOF
#!/bin/bash
# Healthcare Visit Prioritization System - Docker Cleanup

echo "🧹 Healthcare Visit Prioritization System - Docker Cleanup"
echo "========================================================="
echo

echo "⚠️  This will remove all Docker containers, images, and volumes"
echo "   for the Healthcare Visit Prioritization System."
echo

read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo

if [[ \$REPLY =~ ^[Yy]\$ ]]; then
    echo "🗑️  Cleaning up Docker resources..."
    
    # Stop and remove containers
    docker-compose -f "$COMPOSE_FILE" down -v --rmi all 2>/dev/null || true
    
    # Remove any dangling images
    docker image prune -f
    
    # Remove any dangling volumes
    docker volume prune -f
    
    echo "✅ Docker cleanup completed"
    echo
    echo "Note: Management scripts are preserved."
    echo "To rebuild and restart: ./start_docker_app.sh"
else
    echo "Cleanup cancelled"
fi
EOF

    # Make all scripts executable
    chmod +x start_docker_app.sh
    chmod +x stop_docker_app.sh
    chmod +x restart_docker_app.sh
    chmod +x view_logs.sh
    chmod +x check_docker_status.sh
    chmod +x cleanup_docker.sh
    
    echo -e "${GREEN}✅ Management scripts created${NC}"
}

# Run system validation
validate_system() {
    echo -e "${BLUE}🧪 Validating system installation...${NC}"
    
    # Check Docker containers
    if docker-compose -f "${COMPOSE_FILE:-enhanced_docker-compose.yml}" ps | grep -q "Up"; then
        echo "✅ Docker containers are running"
    else
        echo -e "${RED}❌ Docker containers are not running${NC}"
        exit 1
    fi
    
    # Check web application
    if curl -s http://localhost:8501 >/dev/null 2>&1; then
        echo "✅ Web application is accessible"
    else
        echo -e "${RED}❌ Web application is not accessible${NC}"
        exit 1
    fi
    
    # Check Ollama
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "✅ Ollama service is accessible"
    else
        echo -e "${YELLOW}⚠️  Ollama service is not accessible${NC}"
    fi
    
    echo -e "${GREEN}✅ System validation completed${NC}"
}

# Display completion message
show_completion() {
    echo
    echo -e "${GREEN}🎉 Healthcare Visit Prioritization System (Docker) ready!${NC}"
    echo "================================================================"
    echo
    echo -e "${BLUE}🌐 Application Access:${NC}"
    echo "   • Main Application:  http://localhost:8501"
    echo "   • Ollama LLM API:    http://localhost:11434"
    echo
    echo -e "${BLUE}🚀 Management Scripts:${NC}"
    echo "   • Start system:      ./start_docker_app.sh"
    echo "   • Stop system:       ./stop_docker_app.sh"
    echo "   • Restart system:    ./restart_docker_app.sh"
    echo "   • View logs:         ./view_logs.sh"
    echo "   • Check status:      ./check_docker_status.sh"
    echo "   • Cleanup Docker:    ./cleanup_docker.sh"
    echo
    echo -e "${BLUE}🏥 Healthcare AI Features:${NC}"
    echo "   • 🤖 AI Chatbot: 'List all physicians'"
    echo "   • 📅 Smart Slots: 'Show available slots for tomorrow'"
    echo "   • 🎯 Patient Priority: 'Prioritize patients for endocrinology'"
    echo "   • 📋 Booking: 'Book appointment for patient 123'"
    echo "   • 📊 Analytics: Real-time utilization tracking"
    echo
    echo -e "${BLUE}🔧 Docker Commands:${NC}"
    echo "   • View containers:   docker-compose ps"
    echo "   • Follow logs:       docker-compose logs -f"
    echo "   • Shell access:      docker-compose exec app bash"
    echo
    echo -e "${BLUE}💡 Pro Tips:${NC}"
    echo "   • Use 'docker system prune' to free disk space"
    echo "   • Ollama models are persistent across container restarts"
    echo "   • Application data is stored in Docker volumes"
    echo
    echo -e "${GREEN}Ready to transform healthcare scheduling with AI! 🏥🚀${NC}"
}

# Main setup process
main() {
    echo "Starting Healthcare Visit Prioritization System Docker setup..."
    
    check_docker
    install_ollama
    setup_docker_containers
    create_management_scripts
    validate_system
    show_completion
    
    echo "Docker setup completed successfully!"
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${RED}Setup cancelled by user${NC}"; exit 1' INT

# Run main setup
main "$@"

