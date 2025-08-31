#!/bin/bash
# VisitIQ - Healthcare Visit Prioritization System
# Simple init script for start/stop/status operations
# Company: Agilon Health | Team: GridMind

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# App configuration
APP_NAME="VisitIQ"
COMPANY="Agilon Health"
TEAM="GridMind"
PORT=8501
INSTALL_DIR="$HOME/.visit_prioritization"

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}🏥 ${APP_NAME}${NC}"
    echo -e "${BLUE}   ${COMPANY}${NC}"
    echo -e "${BLUE}   Team: ${TEAM}${NC}"
    echo -e "${BLUE}================================${NC}"
    echo
}

check_installation() {
    if [[ ! -d "$INSTALL_DIR" ]]; then
        echo -e "${RED}❌ VisitIQ not installed. Run setup first.${NC}"
        echo -e "${YELLOW}   Try: ./setup_local.sh${NC}"
        exit 1
    fi
}

get_app_pid() {
    pgrep -f "streamlit run.*enhanced_app.py" 2>/dev/null || echo ""
}

get_ollama_pid() {
    pgrep -f "ollama serve" 2>/dev/null || echo ""
}

check_port() {
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

status() {
    print_header
    echo -e "${BLUE}📊 System Status${NC}"
    echo "=================="
    
    # Check if app is running
    APP_PID=$(get_app_pid)
    if [[ -n "$APP_PID" ]]; then
        echo -e "${GREEN}✅ VisitIQ: Running (PID: $APP_PID)${NC}"
        echo -e "${GREEN}   🌐 Web Interface: http://localhost:$PORT${NC}"
    else
        echo -e "${RED}❌ VisitIQ: Stopped${NC}"
    fi
    
    # Check Ollama service
    OLLAMA_PID=$(get_ollama_pid)
    if [[ -n "$OLLAMA_PID" ]] && curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Ollama LLM Service: Running (PID: $OLLAMA_PID)${NC}"
        MODELS=$(ollama list 2>/dev/null | tail -n +2 | wc -l || echo "0")
        echo -e "${GREEN}   📦 Available Models: $MODELS${NC}"
    else
        echo -e "${YELLOW}⚠️  Ollama LLM Service: Not running${NC}"
    fi
    
    # Check installation
    if [[ -f "$INSTALL_DIR/start_healthcare_app.sh" ]]; then
        echo -e "${GREEN}✅ Installation: Complete${NC}"
    else
        echo -e "${RED}❌ Installation: Incomplete${NC}"
    fi
    
    # Check data
    if [[ -f "$INSTALL_DIR/data/patients.csv" ]]; then
        PATIENT_COUNT=$(tail -n +2 "$INSTALL_DIR/data/patients.csv" 2>/dev/null | wc -l || echo "0")
        echo -e "${GREEN}✅ Patient Data: $PATIENT_COUNT patients loaded${NC}"
    else
        echo -e "${YELLOW}⚠️  Patient Data: Not found${NC}"
    fi
    
    echo
}

start() {
    print_header
    echo -e "${BLUE}🚀 Starting VisitIQ...${NC}"
    echo
    
    check_installation
    
    # Check if already running
    APP_PID=$(get_app_pid)
    if [[ -n "$APP_PID" ]]; then
        echo -e "${YELLOW}⚠️  VisitIQ is already running (PID: $APP_PID)${NC}"
        echo -e "${BLUE}   🌐 Access: http://localhost:$PORT${NC}"
        return 0
    fi
    
    # Start Ollama if not running
    if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo -e "${BLUE}🤖 Starting Ollama LLM service...${NC}"
        if command -v ollama >/dev/null 2>&1; then
            ollama serve &
            sleep 3
        else
            echo -e "${YELLOW}⚠️  Ollama not found, some AI features may not work${NC}"
        fi
    fi
    
    # Start the application
    echo -e "${BLUE}🏥 Launching VisitIQ web interface...${NC}"
    "$INSTALL_DIR/start_healthcare_app.sh" &
    
    # Wait for startup
    echo -e "${BLUE}⏳ Waiting for application to start...${NC}"
    for i in {1..30}; do
        if check_port; then
            break
        fi
        sleep 1
        echo -n "."
    done
    echo
    
    if check_port; then
        echo -e "${GREEN}✅ VisitIQ started successfully!${NC}"
        echo
        echo -e "${BLUE}🌐 Web Interface: ${GREEN}http://localhost:$PORT${NC}"
        echo -e "${BLUE}🤖 AI Features: ${GREEN}Enabled${NC}"
        echo -e "${BLUE}📊 Healthcare Scheduling System: ${GREEN}Ready${NC}"
        echo
        echo -e "${YELLOW}💡 Use './visitiq.sh status' to check system health${NC}"
        echo -e "${YELLOW}💡 Use './visitiq.sh stop' to shut down${NC}"
    else
        echo -e "${RED}❌ Failed to start VisitIQ${NC}"
        echo -e "${YELLOW}   Check logs for details${NC}"
        exit 1
    fi
}

stop() {
    print_header
    echo -e "${BLUE}🛑 Stopping VisitIQ...${NC}"
    echo
    
    # Stop main application
    APP_PID=$(get_app_pid)
    if [[ -n "$APP_PID" ]]; then
        echo -e "${BLUE}   Stopping web interface (PID: $APP_PID)...${NC}"
        pkill -f "streamlit run.*enhanced_app.py" || true
        sleep 2
        
        # Force kill if still running
        APP_PID=$(get_app_pid)
        if [[ -n "$APP_PID" ]]; then
            echo -e "${YELLOW}   Force stopping...${NC}"
            kill -9 $APP_PID 2>/dev/null || true
        fi
        
        echo -e "${GREEN}   ✅ Web interface stopped${NC}"
    else
        echo -e "${YELLOW}   VisitIQ was not running${NC}"
    fi
    
    # Optionally stop Ollama (commented out to keep it running for other apps)
    # OLLAMA_PID=$(get_ollama_pid)
    # if [[ -n "$OLLAMA_PID" ]]; then
    #     echo -e "${BLUE}   Stopping Ollama service...${NC}"
    #     pkill -f "ollama serve" || true
    #     echo -e "${GREEN}   ✅ Ollama service stopped${NC}"
    # fi
    
    echo -e "${GREEN}✅ VisitIQ stopped successfully${NC}"
    echo
}

restart() {
    print_header
    echo -e "${BLUE}🔄 Restarting VisitIQ...${NC}"
    echo
    stop
    sleep 2
    start
}

logs() {
    print_header
    echo -e "${BLUE}📋 Recent Logs${NC}"
    echo "==============="
    
    if [[ -f "$INSTALL_DIR/install.log" ]]; then
        echo -e "${BLUE}Installation Log (last 10 lines):${NC}"
        tail -n 10 "$INSTALL_DIR/install.log"
        echo
    fi
    
    if [[ -f "/tmp/ollama.log" ]]; then
        echo -e "${BLUE}Ollama Service Log (last 10 lines):${NC}"
        tail -n 10 "/tmp/ollama.log"
    fi
}

usage() {
    print_header
    echo -e "${BLUE}Usage:${NC}"
    echo "  ./visitiq.sh {start|stop|restart|status|logs}"
    echo
    echo -e "${BLUE}Commands:${NC}"
    echo "  start     - Start VisitIQ system"
    echo "  stop      - Stop VisitIQ system"
    echo "  restart   - Restart VisitIQ system"
    echo "  status    - Show system status"
    echo "  logs      - Show recent logs"
    echo
    echo -e "${BLUE}Examples:${NC}"
    echo "  ./visitiq.sh start     # Start the system"
    echo "  ./visitiq.sh status    # Check if running"
    echo "  ./visitiq.sh restart   # Restart with new changes"
    echo
}

# Main command handling
case "${1:-}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    *)
        usage
        exit 1
        ;;
esac
