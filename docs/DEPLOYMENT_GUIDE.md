# 🏥 Healthcare Visit Prioritization System - Deployment Guide

## 📋 Table of Contents
1. [System Requirements](#system-requirements)
2. [Local Installation (macOS)](#local-installation-macos)
3. [Docker Installation](#docker-installation)
4. [Usage Guide](#usage-guide)
5. [Troubleshooting](#troubleshooting)
6. [Uninstallation](#uninstallation)

---

## 🖥️ System Requirements

### **Minimum Requirements**
- **OS**: macOS 11.0+ (Big Sur or newer)
- **Architecture**: Apple Silicon (M1/M2/M3/M4) or Intel
- **Python**: 3.9 or higher
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 2GB free space
- **Network**: Internet connection for initial setup

### **Recommended for Optimal Performance**
- **macOS**: 13.0+ (Ventura or newer)
- **RAM**: 16GB or more
- **Storage**: 5GB free space (for LLM models)
- **CPU**: Apple Silicon M4 (optimized for this)

---

## 🏠 Local Installation (macOS)

### **Method 1: Automated Local Setup (Recommended)**

```bash
# 1. Navigate to project directory
cd /Users/chandrikaprasad/Desktop/Visit-priorotizations/visit_prioritization_Chandrika

# 2. Make installer executable
chmod +x setup_local.sh

# 3. Run the local installer
./setup_local.sh
```

**What the installer does:**
- ✅ Detects your Mac architecture (M4 optimized)
- ✅ Installs system dependencies via Homebrew
- ✅ Creates isolated Python virtual environment
- ✅ Installs all required packages
- ✅ Sets up FHIR slot management system
- ✅ Configures AI chatbot with Ollama
- ✅ Creates desktop shortcuts
- ✅ Runs system tests

### **Method 2: Manual Installation**

If you prefer manual control:

```bash
# 1. Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install system dependencies
brew install python@3.11 pkg-config portaudio cmake sqlite3

# 3. Create virtual environment
python3 -m venv ~/.visit_prioritization/venv
source ~/.visit_prioritization/venv/bin/activate

# 4. Install Python packages
pip install -r enhanced_requirements.txt

# 5. Install Ollama for AI features
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3

# 6. Set environment variables
export PYTHONPATH="$(pwd):$PYTHONPATH"
export CHROMA_DIR="$(pwd)/chroma_db"

# 7. Run the application
streamlit run enhanced_app.py
```

---

## 🐳 Docker Installation

### **Method 1: Automated Docker Setup (Recommended)**

```bash
# 1. Navigate to project directory
cd /Users/chandrikaprasad/Desktop/Visit-priorotizations/visit_prioritization_Chandrika

# 2. Make installer executable
chmod +x setup_docker.sh

# 3. Run the Docker installer
./setup_docker.sh
```

**What the Docker installer does:**
- ✅ Checks Docker and Docker Compose installation
- ✅ Installs and configures local Ollama for better performance
- ✅ Builds optimized Docker containers for Apple Silicon
- ✅ Sets up all healthcare AI services
- ✅ Creates management scripts for easy operation
- ✅ Downloads required LLM models
- ✅ Validates complete system functionality

### **Method 2: Manual Docker Setup**

```bash
# 1. Build and start enhanced system
docker-compose -f enhanced_docker-compose.yml up --build

# 2. Access application
open http://localhost:8501
```

### **Docker Management Scripts (Created by Installer)**

```bash
# Start the healthcare system
./start_docker_app.sh

# Stop the healthcare system
./stop_docker_app.sh

# Restart the healthcare system
./restart_docker_app.sh

# View live logs
./view_logs.sh

# Check system status
./check_docker_status.sh

# Clean up Docker resources
./cleanup_docker.sh
```

### **Manual Docker Commands**

```bash
# Build without starting
docker-compose -f enhanced_docker-compose.yml build

# Start in background (detached)
docker-compose -f enhanced_docker-compose.yml up -d

# View logs
docker-compose -f enhanced_docker-compose.yml logs -f

# Stop services
docker-compose -f enhanced_docker-compose.yml down

# Clean up (removes containers and volumes)
docker-compose -f enhanced_docker-compose.yml down -v --rmi all
```

---

## 🚀 Usage Guide

### **Starting the Application**

#### **Local Installation**
```bash
# Option 1: Use desktop app
# Look for "Healthcare Visit Prioritization" in Applications folder

# Option 2: Use launcher script
~/.visit_prioritization/launch_app.sh

# Option 3: Direct command
cd ~/.visit_prioritization && source venv/bin/activate && streamlit run app/enhanced_app.py
```

#### **Docker Installation**
```bash
docker-compose -f enhanced_docker-compose.yml up
```

### **Accessing the Application**

1. **Open your web browser**
2. **Navigate to**: `http://localhost:8501`
3. **You should see**: Healthcare Visit Prioritization System interface

### **Application Features**

#### **🤖 AI Chatbot Assistant**
- **Location**: First tab in the web interface
- **Usage**: Type natural language queries
- **Examples**:
  ```
  "List all physicians"
  "Show available slots for Dr. Chen on tomorrow"
  "How many endocrinology slots are available?"
  "Prioritize patients for cardiology"
  ```

#### **👩‍⚕️ Physicians & Schedules**
- View all available physicians
- Check specialty and department information
- See weekly schedule overview
- Monitor utilization metrics

#### **📅 Slot Management**
- Browse available appointment slots
- Filter by physician, date, or specialty
- View real-time slot statistics
- Manage appointment availability

#### **🎯 Smart Patient Prioritization**
- AI-powered patient prioritization
- Considers available slots automatically
- Specialty-aware matching
- Priority level visualization

#### **📋 Appointment Booking**
- Interactive appointment scheduling
- Conflict detection and prevention
- Real-time slot booking
- Today's appointment overview

#### **📊 Analytics & Reports**
- System utilization metrics
- Practitioner performance tracking
- Booking trends analysis
- Resource optimization insights

### **CLI Tools**

#### **Demo Mode**
```bash
# Local installation
~/.visit_prioritization/run_demo.sh

# Or directly
cd ~/.visit_prioritization/app && python demo_enhanced_system.py --demo
```

#### **Chatbot CLI**
```bash
# Interactive chatbot in terminal
~/.visit_prioritization/chatbot_cli.sh
```

#### **System Tests**
```bash
# Run functionality tests
cd ~/.visit_prioritization/app && python demo_enhanced_system.py --test
```

---

## 🛠️ Troubleshooting

### **Common Issues**

#### **1. Port 8501 Already in Use**
```bash
# Find and kill the process using port 8501
lsof -ti:8501 | xargs kill -9

# Or use a different port
streamlit run enhanced_app.py --server.port=8502
```

#### **2. Ollama Connection Issues**
```bash
# Start Ollama service
ollama serve

# In another terminal, test connection
ollama list

# Pull required model if missing
ollama pull llama3
```

#### **3. Python Package Issues on Apple Silicon**
```bash
# Reinstall with Apple Silicon optimizations
pip install --upgrade --no-cache-dir torch torchvision torchaudio
pip install --upgrade --no-cache-dir numpy scipy scikit-learn
```

#### **4. Virtual Environment Issues**
```bash
# Recreate virtual environment
rm -rf ~/.visit_prioritization/venv
python3 -m venv ~/.visit_prioritization/venv
source ~/.visit_prioritization/venv/bin/activate
pip install -r enhanced_requirements.txt
```

#### **5. Docker Issues**
```bash
# Clear Docker cache
docker system prune -a

# Rebuild from scratch
docker-compose -f enhanced_docker-compose.yml down -v
docker-compose -f enhanced_docker-compose.yml build --no-cache
docker-compose -f enhanced_docker-compose.yml up
```

### **Performance Optimization**

#### **For Apple Silicon (M4)**
```bash
# Set optimization flags
export ARCHFLAGS="-arch arm64"
export _PYTHON_HOST_PLATFORM="macosx-11.0-arm64"

# Use optimized NumPy/SciPy
pip install --upgrade numpy scipy --no-use-pep517
```

#### **Memory Management**
- Close unused browser tabs
- Restart application if memory usage is high
- Use Docker for better resource isolation

---

## 🗑️ Uninstallation

### **Local Installation**

#### **Automated Uninstall**
```bash
# Run the uninstall script
~/.visit_prioritization/uninstall.sh
```

#### **Manual Uninstall**
```bash
# Stop any running processes
pkill -f "streamlit run.*enhanced_app.py"

# Remove installation directory
rm -rf ~/.visit_prioritization

# Remove desktop app (if created)
rm -rf "$HOME/Applications/Healthcare Visit Prioritization.app"
```

### **Docker Installation**
```bash
# Stop and remove containers
docker-compose -f enhanced_docker-compose.yml down -v

# Remove Docker images (optional)
docker rmi $(docker images "*visit*" -q) 2>/dev/null || true
```

### **System Dependencies**
If you want to remove system dependencies (be careful, other apps might use these):

```bash
# Remove Homebrew packages (optional)
brew uninstall ollama python@3.11 cmake portaudio pkg-config sqlite3

# Remove Homebrew itself (optional, if not used by other apps)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/uninstall.sh)"
```

---

## 📚 Additional Resources

### **Configuration Files**
- **Main Config**: `enhanced_app.py`
- **Requirements**: `enhanced_requirements.txt` 
- **Docker**: `enhanced_docker-compose.yml`
- **Models**: `src/fhir_models.py`

### **Data Locations**
- **Local**: `~/.visit_prioritization/data/`
- **Docker**: `/app/data/` (inside container)
- **Vector DB**: `chroma_db/` directory

### **Logs**
- **Installation**: `~/.visit_prioritization/install.log`
- **Application**: Streamlit logs in terminal
- **Docker**: `docker-compose logs`

### **Support**
- Check system requirements
- Review troubleshooting section
- Run diagnostic tests: `python demo_enhanced_system.py --test`
- Check GitHub issues or documentation

---

## 🎯 Quick Start Checklist

### **Local Installation**
- [ ] macOS 11.0+ with Python 3.9+
- [ ] Run `./install.sh`
- [ ] Wait for installation to complete
- [ ] Launch via desktop app or `~/.visit_prioritization/launch_app.sh`
- [ ] Open `http://localhost:8501`

### **Docker Installation**  
- [ ] Docker and Docker Compose installed
- [ ] Run `docker-compose -f enhanced_docker-compose.yml up --build`
- [ ] Open `http://localhost:8501`

### **First Time Usage**
- [ ] Try the AI chatbot: "List all physicians"
- [ ] Check available slots for tomorrow
- [ ] Run patient prioritization demo
- [ ] Book a test appointment

---

**🏥 Healthcare Visit Prioritization System v2.0** | Optimized for macOS Apple Silicon | FHIR Compliant | AI-Enhanced
