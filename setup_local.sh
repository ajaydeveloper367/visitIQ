#!/bin/bash

# Healthcare Visit Prioritization System - Local Setup Script
# Based on proven Ollama installation approach
# Optimized for macOS (Apple Silicon M4)

set -e

echo "🏥 Healthcare Visit Prioritization System - Local Setup"
echo "======================================================="
echo "Optimized for macOS Apple Silicon (M1/M2/M3/M4)"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="Healthcare Visit Prioritization"
INSTALL_DIR="$HOME/.visit_prioritization"
VENV_DIR="$INSTALL_DIR/venv"
DATA_DIR="$INSTALL_DIR/data"
LOG_FILE="$INSTALL_DIR/install.log"

# Detect operating system
OS="$(uname -s)"
case "${OS}" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=macOS;;
    *)          MACHINE="UNKNOWN:${OS}"
esac

echo -e "${BLUE}📋 Detected OS: ${MACHINE}${NC}"
echo

# Detect architecture (M4 optimizations)
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

# Function to log messages
log_message() {
    # Create log directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
    echo "$(date): $1" >> "$LOG_FILE" 2>/dev/null || true
    echo -e "$1"
}

# Check Python version
check_python() {
    echo -e "${BLUE}🐍 Checking Python installation...${NC}"
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        if [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -ge 9 ]]; then
            echo -e "${GREEN}✅ Python $PYTHON_VERSION found${NC}"
        else
            echo -e "${RED}❌ Python 3.9+ required, found $PYTHON_VERSION${NC}"
            echo "Please install Python 3.9+ from https://www.python.org/downloads/"
            exit 1
        fi
    else
        echo -e "${RED}❌ Python 3 not found${NC}"
        echo "Please install Python 3.9+ from https://www.python.org/downloads/"
        exit 1
    fi
}

# Install Homebrew and system dependencies
install_system_deps() {
    echo -e "${BLUE}📦 Installing system dependencies...${NC}"
    
    # Check and install Homebrew
    if ! command -v brew &> /dev/null; then
        echo -e "${YELLOW}⚠️  Homebrew not found. Installing...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Add Homebrew to PATH for Apple Silicon
        if [[ "$ARCH" == "arm64" ]]; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    else
        echo -e "${GREEN}✅ Homebrew found${NC}"
    fi
    
    # Install essential packages
    echo "   Installing essential packages..."
    brew install --quiet pkg-config portaudio cmake sqlite3 git || true
    
    # For Apple Silicon, install additional optimizations
    if [[ "$ARCH" == "arm64" ]]; then
        echo "   Installing Apple Silicon optimizations..."
        # Install Rust for some Python packages
        if ! command -v rustc &> /dev/null; then
            curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
            source ~/.cargo/env
        fi
        
        # Set environment variables for Apple Silicon
        export ARCHFLAGS="-arch arm64"
        export _PYTHON_HOST_PLATFORM="macosx-11.0-arm64"
        export MACOSX_DEPLOYMENT_TARGET="11.0"
    fi
    
    echo -e "${GREEN}✅ System dependencies installed${NC}"
}

# Install Ollama (using your proven approach)
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
                    echo "   Downloading Ollama directly..."
                    curl -fsSL https://ollama.com/install.sh | sh
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
    ollama pull llama3 2>/dev/null || {
        echo -e "${YELLOW}⚠️  Failed to download model automatically${NC}"
        echo "   You can download it later with: ollama pull llama3"
    }
}

# Create installation directory
setup_directories() {
    echo -e "${BLUE}📁 Setting up installation directories...${NC}"
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$VENV_DIR"
    mkdir -p "$DATA_DIR"
    mkdir -p "$INSTALL_DIR/logs"
    touch "$LOG_FILE"
    
    echo -e "${GREEN}✅ Directories created: $INSTALL_DIR${NC}"
}

# Create Python virtual environment
setup_python_env() {
    echo -e "${BLUE}🐍 Creating Python virtual environment...${NC}"
    
    # Remove existing venv if it exists
    if [[ -d "$VENV_DIR" ]]; then
        rm -rf "$VENV_DIR"
    fi
    
    # Create new virtual environment
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip for Apple Silicon compatibility
    pip install --upgrade pip setuptools wheel
    
    # For Apple Silicon, install some packages with specific configurations
    if [[ "$ARCH" == "arm64" ]]; then
        echo "   Installing Apple Silicon optimized packages..."
        # Install numpy with optimized BLAS
        pip install numpy --no-use-pep517
        # Install PyTorch for Apple Silicon
        pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cpu
    fi
    
    # Install application requirements
    if [[ -f "enhanced_requirements.txt" ]]; then
        echo "   Installing enhanced requirements..."
        pip install -r enhanced_requirements.txt
    else
        echo "   Installing basic requirements..."
        pip install -r requirements.txt
        # Add enhanced packages
        pip install sentence-transformers langchain-ollama chromadb ortools pydantic plotly
    fi
    
    echo -e "${GREEN}✅ Python environment setup complete${NC}"
}

# Copy application files
setup_application() {
    echo -e "${BLUE}📋 Setting up application files...${NC}"
    
    # Copy application files
    cp -r . "$INSTALL_DIR/app/"
    
    # Setup data directory
    if [[ -d "data" ]]; then
        cp -r data/* "$DATA_DIR/" 2>/dev/null || true
    fi
    
    # Copy vector database if exists
    if [[ -d "chroma_db" ]]; then
        cp -r chroma_db "$INSTALL_DIR/" 2>/dev/null || true
    fi
    
    echo -e "${GREEN}✅ Application files setup complete${NC}"
}

# Create launcher scripts
create_launchers() {
    echo -e "${BLUE}🚀 Creating launcher scripts...${NC}"
    
    # Main launcher script
    cat > "$INSTALL_DIR/start_healthcare_app.sh" << 'EOF'
#!/bin/bash
# Healthcare Visit Prioritization System Launcher

cd "$(dirname "$0")"
source venv/bin/activate

export PYTHONPATH="$PWD/app:$PYTHONPATH"
export CHROMA_DIR="$PWD/chroma_db"
export OLLAMA_URL="http://localhost:11434"

echo "🏥 Starting Healthcare Visit Prioritization System..."
echo "🤖 AI Chatbot and Smart Prioritization System"
echo "======================================================="
echo
echo "🌐 Application will be available at: http://localhost:8501"
echo "🤖 Ollama LLM service running at: http://localhost:11434"
echo
echo "Press Ctrl+C to stop the application"
echo

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "⚠️  Starting Ollama service..."
    ollama serve &
    sleep 3
fi

# Start the enhanced healthcare app
if [[ -f "app/enhanced_app.py" ]]; then
    streamlit run app/enhanced_app.py --server.port=8501 --server.address=localhost
else
    streamlit run app/app.py --server.port=8501 --server.address=localhost
fi
EOF

    # Demo launcher
    cat > "$INSTALL_DIR/run_demo.sh" << 'EOF'
#!/bin/bash
# Healthcare System Demo Launcher

cd "$(dirname "$0")"
source venv/bin/activate

export PYTHONPATH="$PWD/app:$PYTHONPATH"
export CHROMA_DIR="$PWD/chroma_db"
export OLLAMA_URL="http://localhost:11434"

echo "🧪 Healthcare Visit Prioritization System - Demo Mode"
echo "====================================================="
echo

cd app
python demo_enhanced_system.py --demo
EOF

    # Chatbot CLI
    cat > "$INSTALL_DIR/chatbot_cli.sh" << 'EOF'
#!/bin/bash
# Healthcare System Chatbot CLI

cd "$(dirname "$0")"
source venv/bin/activate

export PYTHONPATH="$PWD/app:$PYTHONPATH"
export CHROMA_DIR="$PWD/chroma_db"
export OLLAMA_URL="http://localhost:11434"

echo "🤖 Healthcare Visit Prioritization - AI Chatbot CLI"
echo "=================================================="
echo "Ask questions like:"
echo "• 'List all physicians'"
echo "• 'Show available slots for tomorrow'"
echo "• 'Prioritize patients for endocrinology'"
echo "• Type 'exit' to quit"
echo

python << 'PYTHON_EOF'
import sys
sys.path.append('app/src')

try:
    from chatbot import create_chatbot
    
    chatbot = create_chatbot()
    
    while True:
        try:
            query = input("\n🏥 Ask me: ")
            if query.lower() in ['exit', 'quit', 'bye', 'stop']:
                print("👋 Thank you for using Healthcare Visit Prioritization System!")
                break
            
            if not query.strip():
                continue
                
            response = chatbot.process_query(query)
            
            if response.get('formatted_response'):
                print(f"\n🤖 {response['formatted_response']}")
            else:
                print(f"\n🤖 {response.get('message', 'No response available')}")
        
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

except ImportError as e:
    print(f"❌ Failed to import chatbot module: {e}")
    print("Please ensure the application is properly installed.")
PYTHON_EOF
EOF

    # System status checker
    cat > "$INSTALL_DIR/check_status.sh" << 'EOF'
#!/bin/bash
# Healthcare System Status Checker

cd "$(dirname "$0")"
source venv/bin/activate

echo "🏥 Healthcare Visit Prioritization System - Status Check"
echo "======================================================"
echo

# Check Ollama
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "✅ Ollama service: Running (http://localhost:11434)"
    MODELS=$(ollama list 2>/dev/null | tail -n +2 | wc -l)
    echo "   📦 Available models: $MODELS"
else
    echo "❌ Ollama service: Not running"
    echo "   Start with: ollama serve"
fi

# Check Python environment
if [[ -f "venv/bin/activate" ]]; then
    echo "✅ Python environment: Ready"
    PYTHON_VER=$(venv/bin/python --version)
    echo "   🐍 $PYTHON_VER"
else
    echo "❌ Python environment: Not found"
fi

# Check application files
if [[ -f "app/enhanced_app.py" ]]; then
    echo "✅ Healthcare application: Enhanced version ready"
elif [[ -f "app/app.py" ]]; then
    echo "✅ Healthcare application: Basic version ready"
else
    echo "❌ Healthcare application: Not found"
fi

# Check data
if [[ -d "data" && -f "data/patients.csv" ]]; then
    PATIENT_COUNT=$(tail -n +2 data/patients.csv | wc -l)
    echo "✅ Patient data: $PATIENT_COUNT patients loaded"
else
    echo "❌ Patient data: Not found"
fi

echo
echo "🚀 To start the system:"
echo "   ./start_healthcare_app.sh"
EOF

    # Make all scripts executable
    chmod +x "$INSTALL_DIR/start_healthcare_app.sh"
    chmod +x "$INSTALL_DIR/run_demo.sh"
    chmod +x "$INSTALL_DIR/chatbot_cli.sh"
    chmod +x "$INSTALL_DIR/check_status.sh"
    
    echo -e "${GREEN}✅ Launcher scripts created${NC}"
}

# Create desktop app
create_desktop_app() {
    echo -e "${BLUE}🖥️  Creating desktop application...${NC}"
    
    APPS_DIR="$HOME/Applications"
    mkdir -p "$APPS_DIR"
    
    APP_BUNDLE="$APPS_DIR/Healthcare Visit Prioritization.app"
    mkdir -p "$APP_BUNDLE/Contents/MacOS"
    mkdir -p "$APP_BUNDLE/Contents/Resources"
    
    # App launcher
    cat > "$APP_BUNDLE/Contents/MacOS/Healthcare Visit Prioritization" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
./start_healthcare_app.sh
EOF
    chmod +x "$APP_BUNDLE/Contents/MacOS/Healthcare Visit Prioritization"
    
    # App icon (create a simple text-based icon)
    cat > "$APP_BUNDLE/Contents/Resources/icon.txt" << 'EOF'
🏥 Healthcare Visit Prioritization System
EOF
    
    # Info.plist
    cat > "$APP_BUNDLE/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>Healthcare Visit Prioritization</string>
    <key>CFBundleIdentifier</key>
    <string>com.healthcare.visitprioritization</string>
    <key>CFBundleName</key>
    <string>Healthcare Visit Prioritization</string>
    <key>CFBundleVersion</key>
    <string>2.0</string>
    <key>CFBundleShortVersionString</key>
    <string>2.0</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
</dict>
</plist>
EOF
    
    echo -e "${GREEN}✅ Desktop application created${NC}"
}

# Run post-installation tests
run_tests() {
    echo -e "${BLUE}🧪 Running post-installation tests...${NC}"
    
    source "$VENV_DIR/bin/activate"
    cd "$INSTALL_DIR/app"
    
    export PYTHONPATH="$INSTALL_DIR/app:$PYTHONPATH"
    export CHROMA_DIR="$INSTALL_DIR/chroma_db"
    export OLLAMA_URL="http://localhost:11434"
    
    # Test Python imports
    python -c "
import sys
sys.path.append('src')
try:
    from slot_manager import get_slot_manager
    from smart_prioritizer import SmartPrioritizer
    from chatbot import create_chatbot
    print('✅ All core modules imported successfully')
except Exception as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
" || {
    echo -e "${RED}❌ Module import tests failed${NC}"
    exit 1
}
    
    # Test Ollama connection
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "✅ Ollama connection test passed"
    else
        echo -e "${YELLOW}⚠️  Ollama connection test failed (service may not be running)${NC}"
    fi
    
    echo -e "${GREEN}✅ Post-installation tests completed${NC}"
}

# Create uninstall script
create_uninstaller() {
    cat > "$INSTALL_DIR/uninstall.sh" << 'EOF'
#!/usr/bin/env bash
# Healthcare Visit Prioritization System - Uninstaller

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="$HOME/.visit_prioritization"
APP_BUNDLE="$HOME/Applications/Healthcare Visit Prioritization.app"

echo -e "${BLUE}🏥 Healthcare Visit Prioritization System - Uninstaller${NC}"
echo "=========================================================="
echo -e "${YELLOW}This will completely remove the application and all its data.${NC}"
echo
echo "What will be removed:"
echo "• Application files and data ($INSTALL_DIR)"
echo "• Desktop application ($APP_BUNDLE)"
echo "• Virtual environment and dependencies"
echo
echo -e "${YELLOW}What will NOT be removed:${NC}"
echo "• Homebrew (may be used by other apps)"
echo "• Python system installation"
echo "• Ollama (may be used by other apps)"
echo

read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}🗑️  Uninstalling Healthcare Visit Prioritization System...${NC}"
    
    # Stop any running processes
    echo "   Stopping running processes..."
    pkill -f "streamlit run.*enhanced_app.py" 2>/dev/null || true
    pkill -f "streamlit run.*app.py" 2>/dev/null || true
    
    # Remove installation directory
    if [[ -d "$INSTALL_DIR" ]]; then
        echo "   Removing installation directory..."
        rm -rf "$INSTALL_DIR"
        echo "✅ Removed installation directory"
    fi
    
    # Remove desktop app
    if [[ -d "$APP_BUNDLE" ]]; then
        echo "   Removing desktop application..."
        rm -rf "$APP_BUNDLE"
        echo "✅ Removed desktop application"
    fi
    
    echo
    echo -e "${GREEN}✅ Uninstallation completed successfully${NC}"
    echo
    echo -e "${BLUE}Optional cleanup (run manually if desired):${NC}"
    echo "• Remove Ollama: brew uninstall ollama"
    echo "• Remove Homebrew packages: brew uninstall pkg-config portaudio cmake sqlite3"
    echo "• Stop Ollama service: brew services stop ollama"
    
else
    echo -e "${YELLOW}Uninstallation cancelled.${NC}"
fi
EOF
    chmod +x "$INSTALL_DIR/uninstall.sh"
}

# Display completion message
show_completion() {
    echo
    echo -e "${GREEN}🎉 Healthcare Visit Prioritization System installed successfully!${NC}"
    echo "=================================================================="
    echo
    echo -e "${BLUE}📍 Installation Location:${NC} $INSTALL_DIR"
    echo
    echo -e "${BLUE}🚀 How to run the system:${NC}"
    echo "   • Desktop App:  Open 'Healthcare Visit Prioritization' from Applications"
    echo "   • Command Line: $INSTALL_DIR/start_healthcare_app.sh"
    echo "   • Demo Mode:    $INSTALL_DIR/run_demo.sh"
    echo "   • Chatbot CLI:  $INSTALL_DIR/chatbot_cli.sh"
    echo "   • Status Check: $INSTALL_DIR/check_status.sh"
    echo
    echo -e "${BLUE}🌐 Access URLs:${NC}"
    echo "   • Web Application: http://localhost:8501"
    echo "   • Ollama API:      http://localhost:11434"
    echo
    echo -e "${BLUE}🤖 AI Chatbot Features:${NC}"
    echo "   • 'List all physicians'"
    echo "   • 'Show available slots for tomorrow'"
    echo "   • 'Prioritize patients for endocrinology'"
    echo "   • 'Book appointment for patient 123 with Dr. Smith'"
    echo
    echo -e "${BLUE}🔧 Management:${NC}"
    echo "   • Uninstall: $INSTALL_DIR/uninstall.sh"
    echo "   • Logs: $INSTALL_DIR/logs/"
    echo "   • Data: $INSTALL_DIR/data/"
    echo
    echo -e "${BLUE}📚 Documentation:${NC} See DEPLOYMENT_GUIDE.md for detailed usage"
    echo
    echo -e "${GREEN}Ready to revolutionize healthcare scheduling! 🏥✨${NC}"
}

# Main installation process
main() {
    log_message "Starting Healthcare Visit Prioritization System installation..."
    
    check_python
    install_system_deps
    install_ollama
    setup_directories
    setup_python_env
    setup_application
    create_launchers
    create_desktop_app
    run_tests
    create_uninstaller
    show_completion
    
    log_message "Installation completed successfully!"
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${RED}Installation cancelled by user${NC}"; exit 1' INT

# Run main installation
main "$@"
