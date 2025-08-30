# 🛠️ VisitIQ - Technical Documentation
## Healthcare Visit Prioritization System

### **Architecture Overview**
VisitIQ is a comprehensive healthcare scheduling and prioritization system built with modern AI/ML technologies and FHIR R4 compliance. The system uses a microservices-like architecture with modular components.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │   AI Chatbot    │    │  FHIR Backend   │
│   (Streamlit)   │◄──►│   (LangChain)   │◄──►│  (Slot Manager) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                       ▲                       ▲
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Smart Prioritizer│    │ Vector Database │    │ FHIR Data Models│
│  (RAG + ML)     │◄──►│ (Embeddings +   │◄──►│ (Healthcare     │
│                 │    │  Similarity)    │    │  Standards)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## 📁 **File Structure & Components**

### **Core Application Files**

#### **1. `enhanced_app.py`** - Main Streamlit Application
- **Purpose**: Primary web interface and UI orchestration
- **Technologies**: Streamlit, Pandas, Python
- **Key Features**:
  - Lazy loading with `@st.cache_resource` for performance optimization
  - Session state management for UI interactions
  - Professional healthcare-focused UI design
  - Three main interaction modes: Quick Actions, AI Chatbot, Manual Scheduling

**Key Code Patterns:**
```python
@st.cache_resource
def get_slot_manager_cached():
    return get_slot_manager()  # Lazy initialization

# Session state for UI control
if st.session_state.get('physicians_clicked', False):
    # Render physician table outside column constraints
```

#### **2. `src/chatbot.py`** - Natural Language Interface
- **Purpose**: Conversational AI for healthcare queries
- **Technologies**: LangChain, Ollama LLM, Regex Pattern Matching
- **Architecture**: Hybrid approach with regex fallback

**Query Processing Pipeline:**
```python
def process_query(self, query: str) -> Dict[str, Any]:
    # 1. Pattern matching (fast)
    # 2. LLM processing (if available)  
    # 3. Structured response formatting
```

**Supported Query Types:**
- `list_physicians` - "List all physicians"
- `physician_count` - "How many physicians do you have?"
- `available_slots` - "Show available slots for Dr. Chen"
- `prioritize_patients` - "Prioritize patients for Dr. Rodriguez"

#### **3. `src/smart_prioritizer.py`** - Slot-Aware AI Prioritization
- **Purpose**: Context-aware patient prioritization considering available slots
- **Technologies**: RAG (Retrieval Augmented Generation), ML scoring
- **Key Innovation**: Combines medical urgency with slot availability

**Prioritization Algorithm:**
```python
def prioritize_patients_for_slots(self, patients, practitioner_id=None):
    # 1. Get base priority from RAG system
    priority_result = rag_prioritize_row(patient)
    
    # 2. Apply slot-aware scoring
    slot_aware_score = base_weight + base_score + specialty_match + urgency_modifier
    
    # 3. Sort by final score and select top N for available slots
```

#### **4. `src/prioritizer.py`** - RAG-Based Priority Engine
- **Purpose**: Core ML/AI prioritization using semantic similarity
- **Technologies**: Sentence Transformers, scikit-learn, Ollama LLM
- **Architecture**: Local vector store with persistent embeddings

**RAG Implementation:**
```python
# Vector Storage
EMBEDDINGS_FILE = "embeddings.npy"  # NumPy array of embeddings
DOCS_FILE = "docs.json"            # Patient documents as text
IDS_FILE = "ids.json"              # Patient IDs

# Similarity Search
def _query_similar_docs(query_text: str, k: int = 3):
    # 1. Embed query using sentence-transformers
    # 2. Use NearestNeighbors (cosine similarity) 
    # 3. Return top-k similar patient records
```

**LLM Integration:**
```python
def rag_prioritize_row(row: Dict) -> Dict:
    # 1. Retrieve similar patient cases from vector store
    docs = _query_similar_docs(patient_text, k=3)
    
    # 2. Create LLM prompt with context
    prompt = f"Patient: {patient_text}\nSimilar Cases: {retrieved_text}"
    
    # 3. Get structured JSON response from Ollama
    # 4. Fallback to rule-based if LLM fails
```

#### **5. `src/fhir_models.py`** - Healthcare Data Standards
- **Purpose**: FHIR R4 compliant data models
- **Technologies**: Python dataclasses, Enums, datetime handling
- **Standards Compliance**: Full FHIR resource modeling

**FHIR Resources Implemented:**
```python
@dataclass
class FHIRPractitioner:    # Healthcare provider info
@dataclass  
class FHIRSchedule:        # When practitioner is available
@dataclass
class FHIRSlot:           # Specific bookable time slots
@dataclass
class FHIRAppointment:    # Booked patient appointments
```

**Key Features:**
- Automatic slot generation with lunch breaks
- Status management (FREE, BUSY, etc.)
- ISO datetime serialization
- Validation and data integrity

#### **6. `src/slot_manager.py`** - FHIR Slot Orchestration
- **Purpose**: Manages all slot-related operations and FHIR resource coordination
- **Technologies**: FHIR models, datetime processing, JSON persistence
- **Key Operations**: Slot creation, availability checking, appointment booking

### **Configuration & Deployment Files**

#### **`enhanced_requirements.txt`** - Python Dependencies
```
streamlit>=1.28.0          # Web framework
pandas>=2.0.0              # Data manipulation
sentence-transformers      # ML embeddings
scikit-learn              # Machine learning
langchain-ollama          # LLM integration  
numpy                     # Numerical computing
```

#### **`visitiq.sh`** - Application Management Script
```bash
./visitiq.sh start    # Start the application
./visitiq.sh stop     # Stop all services
./visitiq.sh restart  # Restart application
./visitiq.sh status   # Check system health
```

#### **Docker Configuration**
- `Dockerfile.enhanced` - Main application container
- `enhanced_docker-compose.yml` - Multi-service orchestration
- `llm/Dockerfile.llm` - Ollama LLM service container

### **Data Storage & Persistence**

#### **Vector Database (`chroma_db/`)**
```
chroma_db/
├── embeddings.npy        # Patient record embeddings (ML vectors)
├── docs.json            # Patient documents as text
├── ids.json             # Patient ID mappings
```

**Storage Pattern:**
- **Embeddings**: 384-dimensional vectors from sentence-transformers
- **Documents**: Structured patient text for RAG context
- **Persistence**: NumPy binary + JSON for fast loading

#### **Sample Data (`data/`)**
- `patients.csv` - Sample patient records with medical conditions
- `partners.csv` - Healthcare provider information

---

## 🧠 **AI/ML Technologies Deep Dive**

### **1. Sentence Transformers (all-MiniLM-L6-v2)**
```python
# Convert patient records to 384-dim vectors
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(patient_texts)

# Patient record example:
"Patient ID: 001. Name: John Doe. Age: 45. Condition: Type 2 Diabetes. 
Vitals: Glucose 380; BP 140/90; HR 78. History: Family diabetes history."
```

### **2. Vector Similarity Search**
```python
# Use cosine similarity for finding similar patients
nn = NearestNeighbors(n_neighbors=3, metric="cosine")
nn.fit(stored_embeddings)
distances, indices = nn.kneighbors(query_embedding)
```

### **3. Ollama LLM Integration**
```python
# LLM prompt for clinical decision making
prompt = f"""
You are a clinical assistant. Use patient record and similar cases to decide priority.
Return JSON: {{"priority_level": "High", "score": 85, "reasons": ["glucose >350"]}}

Patient: {current_patient}
Similar Cases: {retrieved_contexts}
"""
```

### **4. Rule-Based Fallback System**
```python
# Emergency thresholds when LLM unavailable
EMERGENCY_GLUCOSE = 400      # mg/dL
HIGH_BP_SYSTOLIC = 180      # mmHg  
HIGH_BP_DIASTOLIC = 110     # mmHg

def rule_based_priority_row(patient_data):
    if patient_data['glucose_mg_dL'] > EMERGENCY_GLUCOSE:
        return {"priority_level": "Emergency", "score": 100}
```

---

## 🔧 **Performance Optimizations**

### **1. Lazy Loading Pattern**
```python
@st.cache_resource
def get_components():
    # Only initialize heavy ML components when needed
    # Cached across Streamlit reruns
    return slot_manager, prioritizer, chatbot
```

### **2. Session State Management**
```python
# Efficient UI state control
if not any([st.session_state.get('physicians_clicked', False),
           st.session_state.get('slots_clicked', False)]):
    # Only render buttons when no table active
```

### **3. Dynamic Table Rendering**
```python
# Responsive table heights based on data
dynamic_height = min(len(df) * 35 + 50, 400)
st.data_editor(df, height=dynamic_height)
```

### **4. Vector Database Optimization**
- **Persistent embeddings** - Pre-computed and stored as NumPy arrays
- **Fast similarity search** - scikit-learn NearestNeighbors with cosine metric
- **Minimal memory footprint** - JSON + binary storage

---

## 🏗️ **Development Patterns & Best Practices**

### **Error Handling Strategy**
```python
# Graceful LLM fallbacks
try:
    llm_result = call_ollama(prompt)
    return parse_json_response(llm_result)
except Exception:
    return rule_based_fallback(patient_data)
```

### **FHIR Compliance Patterns**
```python
# Proper FHIR resource serialization
def to_dict(self) -> Dict[str, Any]:
    data = asdict(self)
    data['start'] = self.start.isoformat()  # ISO 8601
    data['status'] = self.status.value      # Enum to string
    return data
```

### **UI State Management**
```python
# Clean session state control
def reset_all_table_states():
    st.session_state.physicians_clicked = False
    st.session_state.slots_clicked = False  
    st.session_state.processing_prioritization = False
```

---

## 🚀 **Deployment Architecture**

### **Local Development**
```bash
# Native Python environment
python -m venv venv
source venv/bin/activate
pip install -r enhanced_requirements.txt
streamlit run enhanced_app.py --server.port 8501
```

### **Docker Production**
```yaml
# enhanced_docker-compose.yml
services:
  app:
    build: .
    ports: ["8501:8501"]
    depends_on: [ollama]
    
  ollama:
    image: ollama/ollama
    ports: ["11434:11434"]
    command: ["serve", "llama3"]
```

### **Scaling Considerations**
- **Stateless design** - All state in session/database
- **Microservice ready** - Modular component architecture
- **EHR integration points** - FHIR-compliant data exchange
- **Horizontal scaling** - Vector database can be distributed

---

## 📊 **Data Flow Diagrams**

This section provides comprehensive visual representations of how data flows through different components of the VisitIQ system.

### **1. Overall System Architecture Flow**

```mermaid
flowchart TD
    subgraph "Input Data Sources"
        PatientsCSV["📄 patients.csv<br/>Patient Records"]
        PartnersCSV["📄 partners.csv<br/>Healthcare Providers"]
        UserInput["👤 User Input<br/>Web Interface"]
    end

    subgraph "Core Data Processing"
        DataLoader["🔄 Data Loader<br/>CSV → Dict conversion"]
        VectorStore["🧠 Vector Database<br/>Patient Embeddings"]
        FHIRModels["📋 FHIR Models<br/>Standards Compliance"]
    end

    subgraph "AI/ML Engine"
        SentenceTransformer["🤖 Sentence Transformer<br/>all-MiniLM-L6-v2"]
        Embeddings["📊 Embeddings<br/>384-dimensional vectors"]
        RAGSystem["🔍 RAG System<br/>Similarity Search"]
        OllamaLLM["🦙 Ollama LLM<br/>llama3 model"]
        RuleBasedFallback["⚙️ Rule-Based Fallback<br/>Emergency thresholds"]
    end

    subgraph "Business Logic"
        SmartPrioritizer["🎯 Smart Prioritizer<br/>Slot-aware ranking"]
        SlotManager["📅 Slot Manager<br/>FHIR slot operations"]
        ChatbotEngine["💬 Chatbot Engine<br/>NL query processing"]
        Optimizer["📈 OR-Tools Optimizer<br/>Resource allocation"]
    end

    subgraph "User Interface"
        StreamlitApp["🌐 Streamlit Web App<br/>Main Interface"]
        QuickActions["⚡ Quick Actions<br/>Button Interface"]
        ChatInterface["💬 Chat Interface<br/>Natural Language"]
        TableViews["📊 Table Views<br/>Data Display"]
    end

    subgraph "Output & Results"
        PriorityResults["🎯 Priority Rankings<br/>Scored patient list"]
        BookingRecommendations["📋 Booking Recommendations<br/>Ready-to-book patients"]
        Appointments["📅 Appointments<br/>Booked slots"]
        Reports["📊 Analytics Reports<br/>System insights"]
    end

    PatientsCSV --> DataLoader
    PartnersCSV --> DataLoader
    UserInput --> StreamlitApp
    
    DataLoader --> VectorStore
    DataLoader --> FHIRModels
    
    VectorStore --> SentenceTransformer
    SentenceTransformer --> Embeddings
    Embeddings --> RAGSystem
    
    RAGSystem --> OllamaLLM
    RAGSystem --> RuleBasedFallback
    OllamaLLM --> SmartPrioritizer
    RuleBasedFallback --> SmartPrioritizer
    
    FHIRModels --> SlotManager
    SmartPrioritizer --> SlotManager
    
    StreamlitApp --> QuickActions
    StreamlitApp --> ChatInterface
    StreamlitApp --> ChatbotEngine
    
    ChatbotEngine --> SmartPrioritizer
    ChatbotEngine --> SlotManager
    
    SmartPrioritizer --> PriorityResults
    SmartPrioritizer --> BookingRecommendations
    SlotManager --> Appointments
    
    QuickActions --> TableViews
    PriorityResults --> TableViews
    BookingRecommendations --> TableViews
    Appointments --> TableViews
    
    Optimizer --> Reports
    
    style PatientsCSV fill:#e1f5fe
    style VectorStore fill:#f3e5f5
    style RAGSystem fill:#fff3e0
    style SmartPrioritizer fill:#e8f5e8
    style StreamlitApp fill:#fce4ec
```

### **2. Patient Prioritization Data Flow**

```mermaid
flowchart TD
    subgraph "1. Patient Prioritization Data Flow"
        direction TB
        PatientData["📋 Patient Record<br/>Name, Age, Condition<br/>Glucose, BP, History"]
        
        subgraph "Text Processing"
            TextComposer["🔤 Text Composer<br/>Create patient summary"]
            PatientText["📝 Patient Text<br/>'John, 45, Diabetes<br/>Glucose: 380, BP: 140/90'"]
        end
        
        subgraph "Vector Processing"
            Embedding["🤖 Sentence Transformer<br/>Text → 384D vector"]
            VectorDB["🗃️ Vector Database<br/>Stored embeddings"]
            SimilaritySearch["🔍 Cosine Similarity<br/>Find top-k similar patients"]
            SimilarCases["📚 Retrieved Cases<br/>Historical similar patients"]
        end
        
        subgraph "AI Decision Making"
            LLMPrompt["📝 LLM Prompt<br/>Current + Similar cases"]
            OllamaCall["🦙 Ollama LLM<br/>Clinical reasoning"]
            RuleEngine["⚙️ Rule-Based Backup<br/>Glucose>400=Emergency"]
            PriorityJSON["📄 Priority Result<br/>{'level': 'Emergency'<br/>'score': 95<br/>'reasons': [...]}"]
        end
        
        PatientData --> TextComposer
        TextComposer --> PatientText
        PatientText --> Embedding
        Embedding --> SimilaritySearch
        VectorDB --> SimilaritySearch
        SimilaritySearch --> SimilarCases
        
        PatientText --> LLMPrompt
        SimilarCases --> LLMPrompt
        LLMPrompt --> OllamaCall
        OllamaCall --> PriorityJSON
        
        PatientData --> RuleEngine
        RuleEngine --> PriorityJSON
        
        style PatientData fill:#e3f2fd
        style VectorDB fill:#f3e5f5
        style OllamaCall fill:#fff8e1
        style PriorityJSON fill:#e8f5e8
    end
```

### **3. Chatbot Natural Language Processing Flow**

```mermaid
flowchart TD
    subgraph "2. Chatbot Natural Language Processing Flow"
        direction TB
        UserQuery["👤 User Query<br/>'List all physicians'<br/>'Show Dr. Chen slots'<br/>'Prioritize patients'"]
        
        subgraph "Query Analysis"
            RegexMatcher["🔍 Regex Pattern Matching<br/>Fast query classification"]
            QueryType["🏷️ Query Type Detection<br/>list_physicians<br/>available_slots<br/>prioritize_patients"]
            ParamExtractor["📝 Parameter Extraction<br/>Practitioner name<br/>Date references"]
        end
        
        subgraph "Query Processing Paths"
            PhysicianHandler["👨‍⚕️ Physician Handler<br/>List all practitioners"]
            SlotHandler["📅 Slot Handler<br/>Get available slots"]
            PriorityHandler["🎯 Priority Handler<br/>Run patient prioritization"]
            CountHandler["🔢 Count Handler<br/>Count physicians/slots"]
        end
        
        subgraph "Data Retrieval"
            SlotManager["📋 Slot Manager<br/>FHIR operations"]
            SmartPrioritizer["🧠 Smart Prioritizer<br/>AI prioritization"]
            PatientCSV["📄 Patient Data<br/>CSV file loading"]
        end
        
        subgraph "Response Formatting"
            DataFormatter["🎨 Response Formatter<br/>Structure data for display"]
            TableGenerator["📊 Table Generator<br/>Create data tables"]
            TextResponse["📝 Text Response<br/>Natural language answers"]
        end
        
        subgraph "Output Types"
            StructuredData["📋 Structured Data<br/>Tables & Charts"]
            ConversationalReply["💬 Conversational Reply<br/>Formatted text response"]
            ErrorMessage["⚠️ Error Handling<br/>Helpful error messages"]
        end
        
        UserQuery --> RegexMatcher
        RegexMatcher --> QueryType
        QueryType --> ParamExtractor
        
        QueryType --> PhysicianHandler
        QueryType --> SlotHandler
        QueryType --> PriorityHandler
        QueryType --> CountHandler
        
        PhysicianHandler --> SlotManager
        SlotHandler --> SlotManager
        PriorityHandler --> SmartPrioritizer
        PriorityHandler --> PatientCSV
        CountHandler --> SlotManager
        
        SlotManager --> DataFormatter
        SmartPrioritizer --> DataFormatter
        PatientCSV --> SmartPrioritizer
        
        DataFormatter --> TableGenerator
        DataFormatter --> TextResponse
        
        TableGenerator --> StructuredData
        TextResponse --> ConversationalReply
        DataFormatter --> ErrorMessage
        
        style UserQuery fill:#e1f5fe
        style RegexMatcher fill:#fff3e0
        style SmartPrioritizer fill:#e8f5e8
        style StructuredData fill:#f3e5f5
    end
```

### **4. FHIR Slot Management Data Flow**

```mermaid
flowchart TD
    subgraph "3. FHIR Slot Management Data Flow"
        direction TB
        
        subgraph "FHIR Resource Creation"
            PractitionerData["👨‍⚕️ Practitioner Data<br/>Name, Specialty<br/>Department, Contact"]
            ScheduleData["📋 Schedule Data<br/>Service category<br/>Available times"]
            SlotGenerator["🏭 FHIR Slot Generator<br/>Create time slots"]
            
            PractitionerData --> ScheduleData
            ScheduleData --> SlotGenerator
        end
        
        subgraph "Slot Generation Logic"
            DateRange["📅 Date Range<br/>Start: 9:00 AM<br/>End: 5:00 PM"]
            TimeSlots["⏰ Time Slot Creation<br/>30-minute intervals"]
            LunchBreak["🍽️ Lunch Break Logic<br/>12:00-1:00 PM skip"]
            SlotStatus["📊 Slot Status<br/>FREE, BUSY, UNAVAILABLE"]
            
            DateRange --> TimeSlots
            TimeSlots --> LunchBreak
            LunchBreak --> SlotStatus
        end
        
        subgraph "FHIR Data Models"
            FHIRPractitioner["👨‍⚕️ FHIR Practitioner<br/>id, name, specialty<br/>qualifications"]
            FHIRSchedule["📋 FHIR Schedule<br/>practitioner_id<br/>service_type"]
            FHIRSlot["📅 FHIR Slot<br/>start, end, status<br/>practitioner_id"]
            FHIRAppointment["📝 FHIR Appointment<br/>patient_id, slot_id<br/>booked status"]
        end
        
        subgraph "Data Persistence"
            JSONStorage["💾 JSON Storage<br/>practitioners.json<br/>slots.json<br/>appointments.json"]
            DataValidation["✅ Data Validation<br/>FHIR R4 compliance<br/>ISO datetime format"]
        end
        
        subgraph "Slot Operations"
            SlotQuery["🔍 Slot Query<br/>Filter by date<br/>Filter by practitioner"]
            AvailabilityCheck["✅ Availability Check<br/>is_available property<br/>Status = FREE"]
            SlotBooking["📋 Slot Booking<br/>Update status to BUSY<br/>Create appointment"]
            ConflictDetection["⚠️ Conflict Detection<br/>Prevent double-booking"]
        end
        
        SlotGenerator --> FHIRSlot
        PractitionerData --> FHIRPractitioner
        ScheduleData --> FHIRSchedule
        SlotStatus --> FHIRSlot
        
        FHIRPractitioner --> JSONStorage
        FHIRSchedule --> JSONStorage
        FHIRSlot --> JSONStorage
        
        JSONStorage --> DataValidation
        DataValidation --> SlotQuery
        
        SlotQuery --> AvailabilityCheck
        AvailabilityCheck --> SlotBooking
        SlotBooking --> ConflictDetection
        SlotBooking --> FHIRAppointment
        
        FHIRAppointment --> JSONStorage
        
        style FHIRPractitioner fill:#e8f5e8
        style FHIRSlot fill:#e1f5fe
        style JSONStorage fill:#fff3e0
        style ConflictDetection fill:#ffebee
    end
```

### **5. Smart Slot-Aware Prioritization Flow**

```mermaid
flowchart TD
    subgraph "4. Smart Slot-Aware Prioritization Flow"
        direction TB
        
        subgraph "Input Processing"
            PatientList["👥 Patient List<br/>50 patients waiting<br/>Various conditions"]
            TargetDate["📅 Target Date<br/>Tomorrow's appointments"]
            PractitionerID["👨‍⚕️ Practitioner Filter<br/>Dr. Chen (optional)"]
            MaxPatients["🔢 Max Patients<br/>Based on available slots"]
        end
        
        subgraph "Availability Analysis"
            SlotCounter["🔢 Slot Counter<br/>count_available_slots()"]
            AvailableSlots["📊 Available Slots<br/>8 slots tomorrow<br/>Dr. Chen: Endocrinology"]
            CapacityLimit["⚖️ Capacity Limiting<br/>max_patients = 8"]
        end
        
        subgraph "Individual Patient Analysis"
            PatientLoop["🔄 For Each Patient<br/>Individual processing"]
            RAGPriority["🤖 RAG Prioritization<br/>Base priority + score"]
            SpecialtyMatching["🎯 Specialty Matching<br/>Diabetes → Endocrinology<br/>+10 bonus points"]
            UrgencyModifier["⏰ Urgency Modifier<br/>Overdue patients<br/>Time-sensitive conditions"]
            SlotAwareScore["📊 Slot-Aware Score<br/>Final composite score"]
        end
        
        subgraph "Ranking & Selection"
            ScoreRanking["📊 Score Ranking<br/>Sort by final_score DESC"]
            TopNSelection["🔝 Top N Selection<br/>Select top 8 patients<br/>(matching slot count)"]
            BookingFlag["✅ Booking Recommendation<br/>Mark recommended_for_booking"]
        end
        
        subgraph "Enhanced Patient Record"
            BaseRecord["📋 Base Patient Record<br/>Original patient data"]
            EnhancedRecord["📋 Enhanced Record<br/>+ base_priority_level<br/>+ specialty_match_score<br/>+ final_score<br/>+ recommended_for_booking<br/>+ booking_reasons"]
        end
        
        subgraph "Output Results"
            PrioritizedList["📋 Prioritized List<br/>8 patients ranked 1-8<br/>Ready for booking"]
            BookingReasons["📝 Booking Reasons<br/>'High medical priority'<br/>'Good specialty match'<br/>'Overdue for follow-up'"]
        end
        
        PatientList --> PatientLoop
        TargetDate --> SlotCounter
        PractitionerID --> SlotCounter
        SlotCounter --> AvailableSlots
        AvailableSlots --> CapacityLimit
        CapacityLimit --> MaxPatients
        
        PatientLoop --> RAGPriority
        RAGPriority --> SpecialtyMatching
        SpecialtyMatching --> UrgencyModifier
        UrgencyModifier --> SlotAwareScore
        
        BaseRecord --> EnhancedRecord
        SlotAwareScore --> EnhancedRecord
        
        EnhancedRecord --> ScoreRanking
        ScoreRanking --> TopNSelection
        MaxPatients --> TopNSelection
        TopNSelection --> BookingFlag
        
        BookingFlag --> PrioritizedList
        BookingFlag --> BookingReasons
        
        style PatientList fill:#e1f5fe
        style RAGPriority fill:#fff8e1
        style SpecialtyMatching fill:#e8f5e8
        style PrioritizedList fill:#f3e5f5
    end
```

### **6. Appointment Booking Process Flow**

```mermaid
flowchart TD
    subgraph "5. Appointment Booking Process Flow"
        direction TB
        
        subgraph "Booking Initiation"
            UserSelection["👤 User Selection<br/>Manual booking interface<br/>Select patient + practitioner"]
            PriorityRecommendation["🎯 Priority Recommendation<br/>From smart prioritization<br/>Recommended patients"]
            BookingTrigger["🚀 Booking Trigger<br/>Manual button click<br/>(Future: Auto-booking)"]
        end
        
        subgraph "Pre-Booking Validation"
            PatientLookup["👤 Patient Lookup<br/>Verify patient exists<br/>Get patient details"]
            PractitionerLookup["👨‍⚕️ Practitioner Lookup<br/>Verify doctor exists<br/>Check specialties"]
            DateValidation["📅 Date Validation<br/>Future date only<br/>Within 30-day window"]
        end
        
        subgraph "Slot Discovery"
            SlotQuery["🔍 Available Slot Query<br/>Filter by practitioner<br/>Filter by date"]
            SlotFiltering["🎯 Slot Filtering<br/>Status = FREE<br/>start > now()"]
            SlotPresentation["📋 Slot Presentation<br/>Time options display<br/>Duration information"]
        end
        
        subgraph "Slot Selection & Validation"
            SlotSelection["⏰ Slot Selection<br/>User picks time slot<br/>30-min appointment"]
            AvailabilityCheck["✅ Final Availability Check<br/>Ensure still FREE<br/>Prevent conflicts"]
            ConflictDetection["⚠️ Conflict Detection<br/>No double-booking<br/>Race condition handling"]
        end
        
        subgraph "Appointment Creation"
            FHIRAppointmentBuild["📝 FHIR Appointment Creation<br/>id: appt-slot-patient<br/>status: BOOKED<br/>start/end times"]
            SlotStatusUpdate["📊 Slot Status Update<br/>FREE → BUSY<br/>Link to appointment"]
            ReasonCapture["📝 Reason & Notes<br/>reason_code<br/>description"]
        end
        
        subgraph "Data Persistence"
            AppointmentStorage["💾 Appointment Storage<br/>Save to appointments.json<br/>FHIR compliant format"]
            SlotStorage["💾 Slot Update Storage<br/>Update slots.json<br/>Status change"]
            DataValidation["✅ Data Validation<br/>ISO datetime format<br/>FHIR R4 compliance"]
        end
        
        subgraph "Booking Confirmation"
            SuccessResponse["✅ Success Confirmation<br/>Appointment ID<br/>Date/Time display"]
            ErrorHandling["❌ Error Handling<br/>Slot unavailable<br/>Booking conflicts"]
            NotificationTrigger["📧 Notification Trigger<br/>(Future: Email/SMS)"]
        end
        
        UserSelection --> PatientLookup
        PriorityRecommendation --> PatientLookup
        BookingTrigger --> PatientLookup
        
        PatientLookup --> PractitionerLookup
        PractitionerLookup --> DateValidation
        DateValidation --> SlotQuery
        
        SlotQuery --> SlotFiltering
        SlotFiltering --> SlotPresentation
        SlotPresentation --> SlotSelection
        
        SlotSelection --> AvailabilityCheck
        AvailabilityCheck --> ConflictDetection
        ConflictDetection --> FHIRAppointmentBuild
        
        FHIRAppointmentBuild --> ReasonCapture
        ReasonCapture --> SlotStatusUpdate
        SlotStatusUpdate --> AppointmentStorage
        
        AppointmentStorage --> SlotStorage
        SlotStorage --> DataValidation
        DataValidation --> SuccessResponse
        
        ConflictDetection --> ErrorHandling
        AvailabilityCheck --> ErrorHandling
        SuccessResponse --> NotificationTrigger
        
        style PatientLookup fill:#e1f5fe
        style ConflictDetection fill:#ffebee
        style FHIRAppointmentBuild fill:#e8f5e8
        style SuccessResponse fill:#f1f8e9
    end
```

### **7. Vector Database & RAG System Data Flow**

```mermaid
flowchart TD
    subgraph "6. Vector Database & RAG System Data Flow"
        direction TB
        
        subgraph "Knowledge Base Creation"
            PatientCSV["📄 patients.csv<br/>Historical patient records<br/>Name, age, condition, vitals"]
            TextExtraction["📝 Text Extraction<br/>Create patient summaries<br/>'John, 45, Diabetes, Glucose: 380'"]
            SentenceModel["🤖 Sentence Transformer<br/>all-MiniLM-L6-v2 model<br/>Text → Vector conversion"]
            
            PatientCSV --> TextExtraction
            TextExtraction --> SentenceModel
        end
        
        subgraph "Embedding Generation"
            VectorComputation["🧮 Vector Computation<br/>384-dimensional embeddings<br/>Mathematical representations"]
            EmbeddingStorage["💾 Embedding Storage<br/>embeddings.npy<br/>NumPy binary format"]
            DocumentStorage["📚 Document Storage<br/>docs.json<br/>Original text summaries"]
            IDMapping["🗺️ ID Mapping<br/>ids.json<br/>Patient ID references"]
            
            SentenceModel --> VectorComputation
            VectorComputation --> EmbeddingStorage
            TextExtraction --> DocumentStorage
            PatientCSV --> IDMapping
        end
        
        subgraph "Query Processing"
            NewPatient["👤 New Patient Query<br/>Current patient to prioritize"]
            QueryEmbedding["🎯 Query Embedding<br/>Convert patient to vector<br/>Same transformer model"]
            SimilarityComputation["🔍 Similarity Search<br/>Cosine distance calculation<br/>Find nearest neighbors"]
            
            NewPatient --> QueryEmbedding
            QueryEmbedding --> SimilarityComputation
            EmbeddingStorage --> SimilarityComputation
        end
        
        subgraph "Context Retrieval"
            TopKSelection["🔝 Top-K Selection<br/>Retrieve 3 most similar<br/>Historical patient cases"]
            ContextAssembly["📋 Context Assembly<br/>Combine similar cases<br/>Create knowledge context"]
            RelevanceFiltering["🎯 Relevance Filtering<br/>Distance threshold<br/>Quality control"]
            
            SimilarityComputation --> TopKSelection
            DocumentStorage --> TopKSelection
            TopKSelection --> ContextAssembly
            ContextAssembly --> RelevanceFiltering
        end
        
        subgraph "LLM Integration"
            PromptConstruction["📝 Prompt Construction<br/>Current patient + context<br/>Clinical reasoning request"]
            OllamaLLM["🦙 Ollama LLM Call<br/>llama3 model<br/>Clinical decision making"]
            ResponseParsing["🔧 Response Parsing<br/>Extract JSON priority<br/>priority_level, score, reasons"]
            
            RelevanceFiltering --> PromptConstruction
            NewPatient --> PromptConstruction
            PromptConstruction --> OllamaLLM
            OllamaLLM --> ResponseParsing
        end
        
        subgraph "Fallback & Validation"
            RuleBasedFallback["⚙️ Rule-Based Fallback<br/>If LLM fails<br/>Glucose > 400 = Emergency"]
            ResultValidation["✅ Result Validation<br/>JSON format check<br/>Priority level validation"]
            FinalPriority["🎯 Final Priority Result<br/>Structured priority decision<br/>Ready for slot allocation"]
            
            ResponseParsing --> ResultValidation
            ResultValidation --> FinalPriority
            ResponseParsing --> RuleBasedFallback
            RuleBasedFallback --> FinalPriority
        end
        
        style PatientCSV fill:#e3f2fd
        style VectorComputation fill:#f3e5f5
        style SimilarityComputation fill:#fff8e1
        style OllamaLLM fill:#e8f5e8
        style FinalPriority fill:#f1f8e9
    end
```

### **8. Complete User Interface Data Flow**

```mermaid
flowchart TD
    subgraph "7. Complete User Interface Data Flow"
        direction TB
        
        subgraph "User Entry Points"
            WebBrowser["🌐 Web Browser<br/>http://localhost:8501<br/>Streamlit interface"]
            QuickActions["⚡ Quick Action Buttons<br/>📝 List Physicians<br/>📅 Today's Slots<br/>🎯 Smart Prioritization"]
            ChatInterface["💬 Chat Interface<br/>Natural language queries<br/>'Show Dr. Chen slots'"]
            ManualBooking["📋 Manual Booking<br/>Appointment booking form<br/>Patient + Doctor selection"]
        end
        
        subgraph "Session Management"
            StreamlitSession["🔄 Streamlit Session State<br/>physicians_clicked<br/>slots_clicked<br/>processing_prioritization"]
            UIStateControl["🎛️ UI State Control<br/>Show/hide components<br/>Button visibility logic"]
            CacheResource["⚡ Cache Resource<br/>@st.cache_resource<br/>Lazy loading optimization"]
        end
        
        subgraph "Backend Processing Routes"
            SlotManagerRoute["📅 Slot Manager Route<br/>get_practitioners()<br/>get_available_slots()"]
            ChatbotRoute["🤖 Chatbot Route<br/>process_query()<br/>Pattern matching + LLM"]
            PrioritizerRoute["🎯 Prioritizer Route<br/>prioritize_patients_for_slots()<br/>RAG + ML scoring"]
            BookingRoute["📋 Booking Route<br/>book_appointment()<br/>FHIR appointment creation"]
        end
        
        subgraph "Data Processing Layer"
            DataFormatter["🎨 Data Formatter<br/>Dict → DataFrame<br/>Column mapping"]
            TableRenderer["📊 Table Renderer<br/>st.dataframe()<br/>Dynamic height calculation"]
            ErrorHandler["⚠️ Error Handler<br/>Graceful error display<br/>User-friendly messages"]
            SuccessHandler["✅ Success Handler<br/>Confirmation messages<br/>Result summaries"]
        end
        
        subgraph "Display Components"
            PhysicianTable["👨‍⚕️ Physician Table<br/>ID, Name, Specialty<br/>Full-width display"]
            SlotsTable["📅 Slots Table<br/>Time, Date, Duration<br/>Service type"]
            PriorityTable["🎯 Priority Table<br/>Rank, Patient, Score<br/>Recommendations"]
            AppointmentConfirm["📋 Appointment Confirmation<br/>Booking details<br/>Success/error status"]
        end
        
        subgraph "Navigation & Flow Control"
            BackButtons["⬅️ Back to Quick Actions<br/>Reset session states<br/>Return to main menu"]
            TableVisibility["👁️ Table Visibility Control<br/>any_table_active logic<br/>Mutual exclusion"]
            RerunTrigger["🔄 Streamlit Rerun<br/>st.rerun()<br/>UI refresh"]
        end
        
        WebBrowser --> StreamlitSession
        StreamlitSession --> UIStateControl
        UIStateControl --> QuickActions
        UIStateControl --> ChatInterface
        UIStateControl --> ManualBooking
        
        QuickActions --> CacheResource
        ChatInterface --> CacheResource
        ManualBooking --> CacheResource
        
        CacheResource --> SlotManagerRoute
        CacheResource --> ChatbotRoute
        CacheResource --> PrioritizerRoute
        CacheResource --> BookingRoute
        
        SlotManagerRoute --> DataFormatter
        ChatbotRoute --> DataFormatter
        PrioritizerRoute --> DataFormatter
        BookingRoute --> DataFormatter
        
        DataFormatter --> TableRenderer
        DataFormatter --> ErrorHandler
        DataFormatter --> SuccessHandler
        
        TableRenderer --> PhysicianTable
        TableRenderer --> SlotsTable
        TableRenderer --> PriorityTable
        SuccessHandler --> AppointmentConfirm
        
        PhysicianTable --> BackButtons
        SlotsTable --> BackButtons
        PriorityTable --> BackButtons
        AppointmentConfirm --> BackButtons
        
        BackButtons --> TableVisibility
        TableVisibility --> RerunTrigger
        RerunTrigger --> StreamlitSession
        
        style WebBrowser fill:#e3f2fd
        style StreamlitSession fill:#fff3e0
        style CacheResource fill:#f3e5f5
        style TableRenderer fill:#e8f5e8
        style BackButtons fill:#fce4ec
    end
```

### **Key Data Flow Insights**

#### **📊 Data Journey Overview:**
```
CSV Files → Vector Embeddings → AI Analysis → Priority Scores → 
Slot Matching → Booking Recommendations → User Interface → 
Manual/Auto Booking → FHIR Appointments
```

#### **🤖 AI Processing Pipeline:**
```
Patient Text → 384D Vector → Similarity Search → 
Historical Cases → LLM Reasoning → Priority Decision → 
Slot-Aware Ranking → Booking Recommendations
```

#### **🎯 Smart Features Flow:**
```
Natural Language Query → Pattern Recognition → 
Data Retrieval → Processing → Formatted Response → 
UI Display → User Action
```

#### **💡 System Architecture Benefits:**
- **Modular Design** - Clear separation of concerns between components
- **Data Persistence** - JSON storage with FHIR R4 compliance validation
- **Error Handling** - Graceful fallbacks at every processing level
- **Performance Optimization** - Caching and lazy loading throughout
- **User Experience** - Multiple interaction methods with consistent data flow

---

## 🔍 **Testing & Debugging**

### **Component Testing**
```python
# Test RAG prioritization
test_patient = {"name": "Test", "glucose_mg_dL": 450}
priority = rag_prioritize_row(test_patient)
assert priority['priority_level'] == 'Emergency'
```

### **Performance Monitoring**
- **Streamlit metrics** - Built-in performance dashboard
- **LLM response times** - Configurable timeouts (15s default)
- **Vector search latency** - Sub-millisecond similarity queries

### **Logging Strategy**
```python
# Structured logging for debugging
logger.info(f"Processing {len(patients)} patients for {practitioner_id}")
logger.debug(f"RAG retrieved {len(contexts)} similar cases")
```

---

## 📚 **Integration Points**

### **External Systems**
- **EHR/EMR Integration** - FHIR R4 API endpoints
- **Calendar Systems** - iCal/CalDAV export capability  
- **Notification Services** - Email/SMS appointment reminders
- **Analytics Platforms** - Usage metrics and optimization insights

### **API Design**
```python
# RESTful endpoints (future)
GET  /api/practitioners           # List all practitioners
POST /api/slots/search           # Find available slots
POST /api/patients/prioritize    # Run AI prioritization
POST /api/appointments           # Book appointment
```

---

## 🛠️ **Troubleshooting Guide**

### **Common Issues**

1. **Ollama Connection Failed**
   ```bash
   # Start Ollama service
   docker run -d -p 11434:11434 ollama/ollama
   ollama pull llama3
   ```

2. **Vector Database Not Found**
   ```python
   # Rebuild embeddings
   build_vectorstore_from_csv("data/patients.csv")
   ```

3. **Streamlit Performance Issues**
   ```python
   # Clear cache
   st.cache_resource.clear()
   ```

4. **FHIR Model Validation Errors**
   ```python
   # Check dataclass field order (non-default args first)
   ```

This technical documentation provides developers with complete understanding of the VisitIQ architecture, implementation patterns, and deployment strategies for maintaining and extending the healthcare prioritization system.
