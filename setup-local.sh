#!/bin/bash
"""
VisitIQ Healthcare System - Local Installation
Clean installation without modifying source directory
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
INSTALL_DIR="$HOME/.visitiq"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${BLUE}🏥 VisitIQ Healthcare System - Local Setup${NC}"
echo -e "${BLUE}============================================${NC}"
echo "📍 Source: $SOURCE_DIR"
echo "📦 Install: $INSTALL_DIR"
echo

# Clean install - remove existing installation
if [[ -d "$INSTALL_DIR" ]]; then
    echo -e "${YELLOW}🧹 Removing existing installation...${NC}"
    rm -rf "$INSTALL_DIR"
fi

# Create installation directory
echo -e "${BLUE}📁 Creating installation directory...${NC}"
mkdir -p "$INSTALL_DIR"/{app,data,chroma_db,logs}

# Check system requirements
echo -e "${BLUE}🔍 Checking system requirements...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.9+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✅ Python $PYTHON_VERSION${NC}"

# Check/Install Homebrew
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}🍺 Installing Homebrew...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add to PATH for Apple Silicon
    if [[ "$(uname -m)" == "arm64" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
fi

# Install system dependencies
echo -e "${BLUE}📦 Installing system dependencies...${NC}"
brew install --quiet ollama pkg-config portaudio cmake sqlite3 git 2>/dev/null || true
echo -e "${GREEN}✅ System dependencies installed${NC}"

# Setup Python environment
echo -e "${BLUE}🐍 Setting up Python environment...${NC}"
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"

# Install Python packages
pip install --quiet --upgrade pip setuptools wheel

# Copy requirements file and install
cp "$SOURCE_DIR/installation/local/enhanced_requirements.txt" "$INSTALL_DIR/"
pip install --quiet -r "$INSTALL_DIR/enhanced_requirements.txt"
echo -e "${GREEN}✅ Python packages installed${NC}"

# Copy application files (preserve source directory clean)
echo -e "${BLUE}📋 Installing application...${NC}"
cp -r "$SOURCE_DIR/src" "$INSTALL_DIR/app/"
cp -r "$SOURCE_DIR/app.py" "$INSTALL_DIR/app/"
cp -r "$SOURCE_DIR/tools" "$INSTALL_DIR/"

# Copy vector database if exists
if [[ -d "$SOURCE_DIR/chroma_db" ]]; then
    cp -r "$SOURCE_DIR/chroma_db"/* "$INSTALL_DIR/chroma_db/" 2>/dev/null || true
fi

echo -e "${GREEN}✅ Application installed${NC}"

# Setup Ollama
echo -e "${BLUE}🤖 Setting up Ollama LLM...${NC}"

# Start Ollama
brew services start ollama 2>/dev/null || ollama serve &
sleep 3

# Check if accessible
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Ollama service running${NC}"
    
    # Download model
    echo -e "${BLUE}📥 Downloading AI model (this may take a few minutes)...${NC}"
    ollama pull llama3 2>/dev/null || echo -e "${YELLOW}⚠️  Model download failed, will use fallback${NC}"
else
    echo -e "${YELLOW}⚠️  Ollama service not accessible, using fallback mode${NC}"
fi

# Copy unified management script
echo -e "${BLUE}🚀 Installing management script...${NC}"
cp "$SOURCE_DIR/visitiq" "$INSTALL_DIR/visitiq"
chmod +x "$INSTALL_DIR/visitiq"

# Create desktop app (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${BLUE}🖥️  Creating desktop application...${NC}"
    
    APP_BUNDLE="$HOME/Applications/VisitIQ.app"
    mkdir -p "$APP_BUNDLE/Contents/MacOS"
    
    cat > "$APP_BUNDLE/Contents/MacOS/VisitIQ" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
./start.sh
EOF
    chmod +x "$APP_BUNDLE/Contents/MacOS/VisitIQ"
    
    cat > "$APP_BUNDLE/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>VisitIQ</string>
    <key>CFBundleIdentifier</key>
    <string>com.gridmind.visitiq</string>
    <key>CFBundleName</key>
    <string>VisitIQ</string>
    <key>CFBundleVersion</key>
    <string>2.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
</dict>
</plist>
EOF
    
    echo -e "${GREEN}✅ Desktop application created${NC}"
fi

# Final summary
echo
echo -e "${GREEN}🎉 VisitIQ Healthcare System installed successfully!${NC}"
echo "================================================================"
echo
echo -e "${BLUE}📍 Installation Location:${NC} $INSTALL_DIR"
echo
echo -e "${BLUE}🚀 How to use:${NC}"
echo "   $INSTALL_DIR/visitiq {start|stop|restart|status|logs|generate-data|uninstall}"
echo
echo -e "${BLUE}📋 Common commands:${NC}"
echo "   • Generate data:  $INSTALL_DIR/visitiq generate-data"
echo "   • Start system:   $INSTALL_DIR/visitiq start"  
echo "   • Check status:   $INSTALL_DIR/visitiq status"
echo "   • View logs:      $INSTALL_DIR/visitiq logs"
echo "   • Stop system:    $INSTALL_DIR/visitiq stop"
echo "   • Uninstall:      $INSTALL_DIR/visitiq uninstall"
echo
echo -e "${BLUE}🌐 Web Interface:${NC} http://localhost:8501"
echo -e "${BLUE}🖥️  Desktop App:${NC} VisitIQ (in Applications folder)"
echo
echo -e "${YELLOW}⚠️  Important:${NC} Run data generation first:"
echo "   cd $INSTALL_DIR && ./visitiq generate-data"
echo
echo -e "${GREEN}Ready to transform healthcare scheduling! 🏥✨${NC}"
