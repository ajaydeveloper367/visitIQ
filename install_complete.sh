#!/bin/bash
# Healthcare Visit Prioritization System - ONE-COMMAND INSTALLER
# Zero manual steps, completely automated installation

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
INSTALL_DIR="$HOME/.visit_prioritization"

echo -e "${BLUE}🏥 Healthcare Visit Prioritization System - ONE-COMMAND INSTALLER${NC}"
echo "=================================================================="
echo -e "${GREEN}✨ Completely automated installation - Zero manual steps!${NC}"
echo

# Silent installation function
install_silent() {
    local cmd="$1"
    local desc="$2"
    echo -n "   $desc..."
    if eval "$cmd" >/dev/null 2>&1; then
        echo -e " ${GREEN}✅${NC}"
        return 0
    else
        echo -e " ${RED}❌${NC}"
        return 1
    fi
}

# Check architecture
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" ]]; then
    echo -e "${GREEN}✅ Mac Apple Silicon detected${NC}"
else
    echo -e "${GREEN}✅ Intel Mac detected${NC}"
fi

# 1. Install Homebrew (silent)
if ! command -v brew &> /dev/null; then
    echo "🍺 Installing Homebrew..."
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" 2>/dev/null
    if [[ "$ARCH" == "arm64" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
    echo -e "${GREEN}✅ Homebrew installed${NC}"
else
    echo -e "${GREEN}✅ Homebrew already installed${NC}"
fi

# 2. Install system dependencies (silent)
echo "📦 Installing system dependencies..."
export HOMEBREW_NO_AUTO_UPDATE=1
export HOMEBREW_NO_ENV_HINTS=1
brew install --quiet ollama python@3.11 pkg-config portaudio cmake sqlite3 git 2>/dev/null
echo -e "${GREEN}✅ System dependencies installed${NC}"

# 3. Start Ollama and pull model (silent)
echo "🤖 Setting up AI models..."
brew services start ollama 2>/dev/null
sleep 3
ollama pull llama3 >/dev/null 2>&1 &
echo -e "${GREEN}✅ AI setup started (downloading in background)${NC}"

# 4. Create installation directory
echo "📁 Creating installation..."
rm -rf "$INSTALL_DIR" 2>/dev/null
mkdir -p "$INSTALL_DIR"/{app,data,chroma_db,logs}
echo -e "${GREEN}✅ Installation directory created${NC}"

# 5. Create Python environment (silent)
echo "🐍 Setting up Python environment..."
python3 -m venv "$INSTALL_DIR/venv" 2>/dev/null
source "$INSTALL_DIR/venv/bin/activate"
pip install --quiet --upgrade pip setuptools wheel

# 6. Install Python packages (silent, fixed requirements)
echo "📚 Installing AI packages..."
cat > "$INSTALL_DIR/requirements_fixed.txt" << 'EOF'
streamlit>=1.33.0,<2.0.0
fastapi>=0.110.0,<1.0.0
uvicorn>=0.22.0,<1.0.0
requests>=2.31.0,<3.0.0
pandas>=2.1.0,<3.0.0
numpy>=1.24.0,<2.0.0
scikit-learn>=1.3.0,<2.0.0
ortools>=9.8.0,<10.0.0
torch>=2.1.0,<3.0.0
transformers>=4.35.0,<5.0.0
sentence-transformers>=2.2.2,<3.0.0
langchain>=0.1.0,<0.3.0
langchain-ollama>=0.1.0,<1.0.0
pydantic>=2.5.0,<3.0.0
python-dateutil>=2.8.0,<3.0.0
click>=8.0.0,<9.0.0
rich>=13.0.0,<14.0.0
plotly>=5.17.0,<6.0.0
tqdm>=4.65.0,<5.0.0
psutil>=5.9.0,<6.0.0
EOF

pip install --quiet -r "$INSTALL_DIR/requirements_fixed.txt"
echo -e "${GREEN}✅ AI packages installed${NC}"

# 7. Copy application files
echo "📋 Copying application..."
cp -r . "$INSTALL_DIR/app/"
cp -r data/* "$INSTALL_DIR/data/" 2>/dev/null || true
cp -r chroma_db "$INSTALL_DIR/" 2>/dev/null || true
echo -e "${GREEN}✅ Application copied${NC}"

# 8. Configure Streamlit (NO EMAIL PROMPT)
echo "⚙️ Configuring system..."
mkdir -p ~/.streamlit
cat > ~/.streamlit/config.toml << 'EOF'
[global]
showWarningOnDirectExecution = false

[server]
headless = true
port = 8501
enableCORS = false

[browser]
gatherUsageStats = false

[client]
showErrorDetails = false
EOF

# Create credentials to skip email prompt
cat > ~/.streamlit/credentials.toml << 'EOF'
[general]
email = ""
EOF

echo -e "${GREEN}✅ System configured${NC}"

# 9. Create launcher script (NON-INTERACTIVE)
echo "🚀 Creating launcher..."
cat > "$INSTALL_DIR/launch.sh" << 'LAUNCHER_EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate

export PYTHONPATH="$PWD/app:$PYTHONPATH"
export CHROMA_DIR="$PWD/chroma_db"
export OLLAMA_URL="http://localhost:11434"
export STREAMLIT_SERVER_HEADLESS="true"

# Start Ollama if not running
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    brew services start ollama
    sleep 2
fi

echo "🏥 Healthcare Visit Prioritization System"
echo "🌐 Opening: http://localhost:8501"
echo "🤖 AI Chatbot ready with natural language queries!"
echo

# Open browser automatically
sleep 2 && open http://localhost:8501 &

# Start app (non-interactive)
if [[ -f "app/enhanced_app.py" ]]; then
    streamlit run app/enhanced_app.py --server.port=8501 --server.headless=true
else
    streamlit run app/app.py --server.port=8501 --server.headless=true
fi
LAUNCHER_EOF

chmod +x "$INSTALL_DIR/launch.sh"

# 10. Create desktop app
mkdir -p ~/Applications/"Healthcare Scheduler.app"/Contents/MacOS
cat > ~/Applications/"Healthcare Scheduler.app"/Contents/MacOS/"Healthcare Scheduler" << 'EOF'
#!/bin/bash
cd ~/.visit_prioritization
./launch.sh
EOF
chmod +x ~/Applications/"Healthcare Scheduler.app"/Contents/MacOS/"Healthcare Scheduler"

echo -e "${GREEN}✅ Desktop app created${NC}"

# 11. Create quick commands
cat > "$INSTALL_DIR/start.sh" << 'EOF'
#!/bin/bash
cd ~/.visit_prioritization && ./launch.sh
EOF
chmod +x "$INSTALL_DIR/start.sh"

# Create global command
sudo ln -sf "$INSTALL_DIR/start.sh" /usr/local/bin/healthcare-start 2>/dev/null || true

echo -e "${GREEN}✅ Quick commands created${NC}"

# 12. LAUNCH IMMEDIATELY
echo
echo -e "${BLUE}🎉 INSTALLATION COMPLETE!${NC}"
echo "=================================================================="
echo
echo -e "${GREEN}🚀 Starting Healthcare System NOW...${NC}"
echo -e "${GREEN}🌐 Browser will open automatically to: http://localhost:8501${NC}"
echo
echo -e "${BLUE}📱 Usage:${NC}"
echo "   • Desktop App: 'Healthcare Scheduler' in Applications"
echo "   • Command: 'healthcare-start' from anywhere"  
echo "   • Direct: ~/.visit_prioritization/launch.sh"
echo
echo -e "${BLUE}🤖 Try these AI queries:${NC}"
echo '   • "List all physicians"'
echo '   • "Show available slots for tomorrow"'
echo '   • "Prioritize patients for endocrinology"'
echo
echo -e "${GREEN}✨ Zero-click healthcare AI scheduling is ready!${NC}"
echo

# AUTO-LAUNCH THE SYSTEM
cd "$INSTALL_DIR"
./launch.sh &

echo "🎯 System is starting... Browser will open shortly!"

