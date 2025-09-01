"""
Enhanced Visit Prioritization App with FHIR Slots and Chatbot
Streamlit web interface for the enhanced healthcare scheduling system
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import json
import os
from pathlib import Path

# Import enhanced modules
from src.slot_manager import get_slot_manager
from src.smart_prioritizer import SmartPrioritizer
from src.smart_llm_chatbot import create_chatbot
from src.fhir_models import AppointmentStatus

# Page configuration
st.set_page_config(
    page_title='VisitIQ - Agilon Health',
    page_icon='🏥',
    layout='wide',
    initial_sidebar_state='expanded'
)



# Disable Streamlit's default error handling options
# Hide Streamlit style elements including error suggestions
hide_streamlit_style = """
<style>
/* Import Google Fonts for better typography */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Poppins:wght@300;400;500;600;700&display=swap');

/* Hide ALL Streamlit menu elements */
.stAppHeader {
    display: none !important;
}
#MainMenu {
    visibility: hidden !important;
}
[data-testid="stToolbar"] {
    display: none !important;
}
[data-testid="stDecoration"] {
    display: none !important;
}
.stActionButton {
    display: none !important;
}
button[kind="header"] {
    display: none !important;
}
button[title*="Deploy"] {
    display: none !important;
}
button[title*="Settings"] {
    display: none !important;
}
.stException > div[data-testid="stException"] > div > div:last-child {
    display: none !important;
}
.stException a[href*="google"], .stException a[href*="chatgpt"] {
    display: none !important;
}
footer {
    display: none !important;
}
.stAppFooter {
    display: none !important;
}

/* Modern, Human-Centered Design System */
:root {
    --primary-blue: #2563eb;
    --primary-light: #3b82f6;
    --secondary-teal: #14b8a6;
    --accent-purple: #8b5cf6;
    --warm-gray: #6b7280;
    --light-gray: #f8fafc;
    --success-green: #10b981;
    --warning-orange: #f59e0b;
    --error-red: #ef4444;
    --white: #ffffff;
    --shadow-soft: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    --shadow-medium: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    --border-radius: 12px;
    --border-radius-lg: 16px;
}

/* Global styling improvements */
.main {
    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
    padding: 1rem;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Beautiful company header with human touch */
.company-header {
    background: linear-gradient(135deg, #2563eb 0%, #3b82f6 50%, #14b8a6 100%);
    color: white;
    padding: 2rem;
    border-radius: var(--border-radius-lg);
    margin-bottom: 2rem;
    text-align: center;
    box-shadow: var(--shadow-medium);
    position: relative;
    overflow: hidden;
}

.company-header::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Ccircle cx='30' cy='30' r='2'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E") repeat;
    pointer-events: none;
}

.company-header h2, .company-header h4, .company-header p {
    position: relative;
    z-index: 1;
}

/* Simple sidebar styling - back to working state */
.css-1d391kg {
    background: var(--white);
    border-right: 1px solid #e2e8f0;
    box-shadow: var(--shadow-soft);
}

.css-1d391kg .stRadio > div {
    background: var(--white);
    border-radius: var(--border-radius);
    padding: 1rem;
    margin-bottom: 0.5rem;
    border: 1px solid #e2e8f0;
    transition: all 0.2s ease;
}

.css-1d391kg .stRadio > div:hover {
    border-color: var(--primary-light);
    box-shadow: var(--shadow-soft);
    transform: translateY(-1px);
}



/* Beautiful cards for content sections */
.metric-card {
    background: var(--white);
    border-radius: var(--border-radius);
    padding: 1.5rem;
    margin: 1rem 0;
    box-shadow: var(--shadow-soft);
    border-left: 4px solid var(--primary-blue);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-medium);
}

/* Enhanced buttons */
.stButton > button {
    background: linear-gradient(135deg, var(--primary-blue), var(--primary-light));
    color: white;
    border: none;
    border-radius: var(--border-radius);
    padding: 0.75rem 1.5rem;
    font-weight: 500;
    font-family: 'Inter', sans-serif;
    transition: all 0.2s ease;
    box-shadow: var(--shadow-soft);
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-medium);
    background: linear-gradient(135deg, var(--primary-light), var(--secondary-teal));
}

/* Modern success/info/warning messages */
.stAlert {
    border-radius: var(--border-radius);
    border: none;
    box-shadow: var(--shadow-soft);
    font-family: 'Inter', sans-serif;
}

.stSuccess {
    background: linear-gradient(135deg, #ecfdf5, #d1fae5);
    border-left: 4px solid var(--success-green);
    color: #065f46;
}

.stInfo {
    background: linear-gradient(135deg, #eff6ff, #dbeafe);
    border-left: 4px solid var(--primary-blue);
    color: #1e3a8a;
}

.stWarning {
    background: linear-gradient(135deg, #fffbeb, #fef3c7);
    border-left: 4px solid var(--warning-orange);
    color: #92400e;
}

/* Enhanced data tables */
.stDataFrame {
    border-radius: var(--border-radius);
    overflow: hidden;
    box-shadow: var(--shadow-soft);
    margin: 1rem 0;
}

.stDataFrame > div {
    border-radius: var(--border-radius);
}

/* Modern metrics display */
[data-testid="metric-container"] {
    background: var(--white);
    border-radius: var(--border-radius);
    padding: 1.5rem;
    box-shadow: var(--shadow-soft);
    border: 1px solid #e2e8f0;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

[data-testid="metric-container"]:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-medium);
    border-color: var(--primary-light);
}

[data-testid="metric-container"] [data-testid="metric-value"] {
    font-family: 'Poppins', sans-serif;
    font-weight: 600;
    color: var(--primary-blue);
}

/* Input fields styling */
.stTextInput > div > div > input {
    border-radius: var(--border-radius);
    border: 2px solid #e2e8f0;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
    font-family: 'Inter', sans-serif;
}

.stTextInput > div > div > input:focus {
    border-color: var(--primary-light);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.stSelectbox > div > div > div {
    border-radius: var(--border-radius);
    border: 2px solid #e2e8f0;
    transition: border-color 0.2s ease;
}

/* Enhanced chat interface */
.chat-message {
    background: var(--white);
    border-radius: var(--border-radius);
    padding: 1rem;
    margin: 0.5rem 0;
    box-shadow: var(--shadow-soft);
    border-left: 4px solid var(--secondary-teal);
}

/* Loading animations */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.loading {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* Status indicators */
.status-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.875rem;
    font-weight: 500;
    font-family: 'Inter', sans-serif;
}

.status-success {
    background: #dcfce7;
    color: #166534;
}

.status-warning {
    background: #fef3c7;
    color: #92400e;
}

.status-error {
    background: #fecaca;
    color: #991b1b;
}

/* Modern section headers */
h1, h2, h3 {
    font-family: 'Poppins', sans-serif;
    font-weight: 600;
    color: #1f2937;
    margin-bottom: 1rem;
}

/* Soft dividers */
hr {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
    margin: 2rem 0;
}

/* Enhanced tooltips and help text */
.stTooltipIcon {
    color: var(--primary-blue);
}

/* Professional yet warm footer */
.footer-branding {
    background: var(--white);
    border-radius: var(--border-radius);
    padding: 1.5rem;
    margin-top: 2rem;
    box-shadow: var(--shadow-soft);
    border-top: 3px solid var(--secondary-teal);
}

/* Responsive design improvements */
@media (max-width: 768px) {
    .company-header {
        padding: 1.5rem;
    }
    
    .main {
        padding: 0.5rem;
    }
}

/* Accessibility improvements */
button:focus, input:focus, select:focus {
    outline: 2px solid var(--primary-blue);
    outline-offset: 2px;
}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Initialize components with lazy loading for better startup performance
@st.cache_resource
def get_slot_manager_cached():
    """Get slot manager - lightweight initialization"""
    return get_slot_manager()

@st.cache_resource  
def get_prioritizer_cached():
    """Get prioritizer - initialized when needed"""
    slot_manager = get_slot_manager_cached()
    return SmartPrioritizer(slot_manager)

@st.cache_resource
def get_chatbot_cached():
    """Get chatbot - initialized when needed"""
    slot_manager = get_slot_manager_cached()
    # Try to get LLM client for enhanced functionality
    try:
        import ollama
        llm_client = ollama
    except ImportError:
        llm_client = None
    return create_chatbot(slot_manager, llm_client)

# Initialize components for optimal hackathon demo performance
slot_manager = get_slot_manager_cached()

# Background AI model optimization (non-blocking for smooth demo experience)
if 'models_preloaded' not in st.session_state:
    st.session_state.models_preloaded = False
    st.session_state.preload_attempted = False



# Custom company header
st.markdown(
    """
    <div class="company-header">
        <h2 style="margin: 0; color: white;">🏥 VisitIQ</h2>
        <h4 style="margin: 0; color: #e0e7ff; font-weight: normal;">Agilon Health - Healthcare Visit Prioritization System</h4>
        <p style="margin: 0; color: #c7d2fe; font-size: 0.9em;">Team GridMind | AI-Enhanced FHIR-Compliant Scheduling</p>
    </div>
    """, 
    unsafe_allow_html=True
)

# Show loading message
if 'app_initialized' not in st.session_state:
    st.success("🚀 VisitIQ loaded successfully! AI components initialize when first used.")
    st.session_state.app_initialized = True

# Sidebar navigation
st.sidebar.header('Navigation')
view = st.sidebar.radio(
    'Choose View',
    [
        '🤖 AI Chatbot Assistant',
        '👩‍⚕️ Physicians & Schedules',
        '📅 Slot Management',
        '🎯 Smart Patient Prioritization',
        '📋 Appointment Booking',
        '📊 Analytics & Reports'
    ]
)

# Load patient data
@st.cache_data
def load_patients():
    def find_patients_csv():
        env_dir = os.getenv('VISITIQ_DATA_DIR')
        if env_dir:
            candidate = Path(env_dir) / 'patients.csv'
            if candidate.exists():
                return candidate
        candidates = [
            Path('data') / 'patients.csv',
            Path.cwd() / 'data' / 'patients.csv',
            Path(__file__).resolve().parent / 'data' / 'patients.csv'
        ]
        base = Path(__file__).resolve()
        for parent in [base.parent, *base.parents]:
            candidates.append(parent / 'data' / 'patients.csv')
        for c in candidates:
            if c.exists():
                return c
        raise FileNotFoundError("patients.csv not found. Set VISITIQ_DATA_DIR or place under data/patients.csv.")

    path = find_patients_csv()
    st.session_state['patients_csv_path'] = str(path)
    return pd.read_csv(path)

patients_df = load_patients()

# ============ AI CHATBOT ASSISTANT ============
if view == '🤖 AI Chatbot Assistant':
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #eff6ff, #dbeafe); 
                    border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem;
                    border-left: 4px solid #3b82f6;">
            <h2 style="color: #1e3a8a; margin: 0 0 0.5rem 0; font-family: 'Poppins', sans-serif;">
                👋 Hello! I'm your VisitIQ Assistant
            </h2>
            <p style="color: #1e40af; margin: 0; font-size: 1rem;">
                I'm here to help you navigate healthcare scheduling with ease. Ask me anything about 
                physicians, appointment availability, or patient prioritization - I speak human! 😊
            </p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # Chat interface - FIXED: Proper session state initialization
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # FIXED: Initialize form state to prevent first-run duplicacy  
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False
    
    # Display chat history with beautiful styling
    for i, (user_msg, bot_response) in enumerate(st.session_state.chat_history):
        # User message
        st.markdown(
            f"""
            <div style="background: #f8fafc; border-radius: 12px; padding: 1rem; 
                        margin: 0.5rem 0; border-left: 4px solid #14b8a6;">
                <strong style="color: #0f766e;">👤 You:</strong> 
                <span style="color: #374151;">{user_msg}</span>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # Assistant response
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, #ecfdf5, #d1fae5); 
                        border-radius: 12px; padding: 1rem; margin: 0.5rem 0 1.5rem 0; 
                        border-left: 4px solid #10b981;">
                <strong style="color: #065f46;">🤖 VisitIQ Assistant:</strong> 
                <span style="color: #374151;">{bot_response}</span>
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    # Input for new query with helpful examples
    st.markdown(
        """
        <div style="margin: 1.5rem 0 1rem 0;">
            <h4 style="color: #374151; margin-bottom: 0.5rem;">💬 What can I help you with today?</h4>
            <p style="color: #6b7280; font-size: 0.9em; margin-bottom: 1rem;">
                Try asking natural questions like you would to a colleague...
            </p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # Simple input form that clears on submit
    with st.form(key="chat_form", clear_on_submit=True):
        user_query = st.text_input(
            'Ask a question:',
            placeholder='💭 "Who are our available endocrinologists?" or "Show me Dr. Chen\'s schedule for tomorrow"',
            label_visibility='collapsed'
        )
        submitted = st.form_submit_button("Send")
    
    if submitted and user_query and not st.session_state.form_submitted:
        # FIXED: Prevent first-run duplicacy by tracking form submission state
        st.session_state.form_submitted = True
        
        with st.spinner('🔍 Analyzing your query...'):
            # Process the query
            chatbot = get_chatbot_cached()
            patients_csv_path = st.session_state.get('patients_csv_path', 'data/patients.csv')
            response = chatbot.process_query(user_query, patients_csv_path)
            
            # Add to chat history
            st.session_state.chat_history.append((user_query, response.get('message', 'Query processed')))
        
        # Reset form state after processing
        st.session_state.form_submitted = False
        
        # Display response immediately
        if response['status'] == 'success':
            formatted_response = response.get('formatted_response', response['message'])
            
            # Display structured data if available
            if 'data' in response and response['data']:
                st.success(response['message'])
                
                # Display data based on query type
                if isinstance(response['data'], list) and len(response['data']) > 0:
                    if 'Name' in response['data'][0] and 'Specialty' in response['data'][0]:
                        # Physician data with column configuration
                        df = pd.DataFrame(response['data'])
                        st.dataframe(
                            df, 
                            use_container_width=True,
                            column_config={
                                "ID": st.column_config.TextColumn("ID", width="small"),
                                "Name": st.column_config.TextColumn("Name", width="medium"),
                                "Specialty": st.column_config.TextColumn("Specialty", width="medium"), 
                                "Dept": st.column_config.TextColumn("Department", width="medium"),
                                "Contact": st.column_config.TextColumn("Contact", width="medium")
                            }
                        )
                    elif 'Time' in response['data'][0]:
                        # Slot data - dynamic height based on data size
                        df = pd.DataFrame(response['data'])
                        dynamic_height = min(len(df) * 35 + 50, 400)  # Cap at 400px for chat
                        st.data_editor(
                            df, 
                            use_container_width=True,
                            height=dynamic_height,
                            disabled=True,  # Read-only
                            hide_index=True
                        )
                    elif 'Patient ID' in response['data'][0] and 'Risk Level' in response['data'][0]:
                        # Patient data with risk assessment and color coding
                        df = pd.DataFrame(response['data'])
                        
                        # Color coding function for risk levels
                        def highlight_risk_level(val):
                            if val in ['CRITICAL', 'Emergency']:
                                return 'background-color: #ffebee; color: #d32f2f; font-weight: 600; border-left: 4px solid #d32f2f;'
                            elif val in ['HIGH', 'High']:
                                return 'background-color: #fff3e0; color: #f57c00; font-weight: 600; border-left: 4px solid #f57c00;'
                            elif val in ['MODERATE', 'Medium']:
                                return 'background-color: #f3f4f6; color: #6b7280; font-weight: 500; border-left: 4px solid #6b7280;'
                            elif val in ['LOW', 'Low']:
                                return 'background-color: #f0f9f0; color: #2e7d32; font-weight: 500; border-left: 4px solid #2e7d32;'
                            return ''
                        
                        # Apply styling with MODERN pandas method (map instead of deprecated applymap)
                        try:
                            styled_df = df.style.map(highlight_risk_level, subset=['Risk Level'])  # FIXED: map instead of applymap
                            print(f"✅ Applied color styling to {len(df)} patients")
                        except Exception as e:
                            print(f"❌ Styling error: {e}")
                            styled_df = df.style  # Fallback to basic styling
                        
                        st.dataframe(
                            styled_df,
                            use_container_width=True,
                            height=min(len(df) * 35 + 50, 600),  # Show all patients with scrollbar
                            column_config={
                                "Patient ID": st.column_config.TextColumn("ID", width="small"),
                                "Name": st.column_config.TextColumn("Name", width="medium"),
                                "Age": st.column_config.NumberColumn("Age", width="small"),
                                "Condition": st.column_config.TextColumn("Condition", width="medium"),
                                "Risk Level": st.column_config.TextColumn("Risk", width="small"),
                                "Risk Score": st.column_config.NumberColumn("Score", width="small"),
                                "Glucose": st.column_config.TextColumn("Glucose", width="small"),
                                "BP": st.column_config.TextColumn("BP", width="small"),
                                "History": st.column_config.TextColumn("History", width="medium"),
                                "Medical Reasons": st.column_config.TextColumn("Medical Reasons", width="large"),
                                "Reasoning Source": st.column_config.TextColumn("AI Method", width="medium")
                            }
                        )
                        # Don't show formatted_response for patient tables - avoid duplication
                        
                    elif 'patient_id' in response['data'][0]:
                        # Patient priority data
                        df = pd.DataFrame(response['data'])
                        st.dataframe(df.style.background_gradient(subset=['score']), use_container_width=True)
                        # Don't show formatted_response for priority data - avoid duplication
                        
                    else:
                        # For other data types, show both table and formatted response
                        st.code(formatted_response, language='text')
                else:
                    # Only show formatted_response if no structured data
                    st.code(formatted_response, language='text')
            else:
                st.success(formatted_response)
            
        elif response['status'] == 'not_found':
            st.warning(response['message'])
            if 'suggestions' in response:
                st.write('**Suggestions:**')
                for suggestion in response['suggestions']:
                    st.write(f"• {suggestion}")
        
        elif response['status'] == 'no_slots':
            st.info(response['message'])
        
        else:
            st.error(response.get('message', 'Unknown error occurred'))
            if 'suggestions' in response:
                st.write('**Try these instead:**')
                for suggestion in response['suggestions']:
                    st.write(f"• {suggestion}")
        
        # Add to chat history (already handled above)
        # st.session_state.chat_history.append((user_query, formatted_response if 'formatted_response' in response else response['message']))
    
    # Initialize session state for button tracking
    if 'processing_prioritization' not in st.session_state:
        st.session_state.processing_prioritization = False
    
    # Initialize session state variables first
    if 'slots_clicked' not in st.session_state:
        st.session_state.slots_clicked = False
    if 'physicians_clicked' not in st.session_state:
        st.session_state.physicians_clicked = False
    
    # Check if any table is currently displayed
    any_table_active = (st.session_state.get('physicians_clicked', False) or 
                       st.session_state.get('slots_clicked', False) or 
                       st.session_state.get('processing_prioritization', False))
    
    # Only show Quick Actions if NO table is displayed
    if not any_table_active:
        # Quick action buttons with friendly styling
        st.markdown(
            """
            <div style="margin: 2rem 0 1rem 0;">
                <h4 style="color: #374151; margin-bottom: 0.5rem;">⚡ Quick Actions</h4>
                <p style="color: #6b7280; font-size: 0.9em; margin-bottom: 1rem;">
                    Click these buttons for instant insights:
                </p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button('📝 List All Physicians'):
                st.session_state.physicians_clicked = True
                st.rerun()
        
        with col2:
            if st.button('📅 Today\'s Available Slots'):
                st.session_state.slots_clicked = True
                st.rerun()
        
        with col3:
            if st.button('🎯 Smart Patient Prioritization'):
                st.session_state.processing_prioritization = True
                st.rerun()
    
    # Display physicians table OUTSIDE of columns to use full width  
    if st.session_state.physicians_clicked:
        st.markdown("---")
        st.subheader("📝 All Physicians")
        
        chatbot = get_chatbot_cached()
        patients_csv_path = st.session_state.get('patients_csv_path', 'data/patients.csv')
        response = chatbot.process_query('list all physicians', patients_csv_path)
        if response.get('data'):
            df = pd.DataFrame(response['data'])
            # Dynamic height based on data size (35px per row + 50px header)
            dynamic_height = min(len(df) * 35 + 50, 400)  # Cap at 400px max
            st.data_editor(
                df, 
                use_container_width=True,
                height=dynamic_height,
                disabled=True,
                hide_index=True
            )
            
            if st.button('🔄 Back to Quick Actions', key='physicians_back'):
                st.session_state.physicians_clicked = False
                st.rerun()
        else:
            st.info(response.get('message', 'No physician data available'))
            if st.button('🔄 Back to Quick Actions', key='physicians_back_empty'):
                st.session_state.physicians_clicked = False
                st.rerun()
        
    # Display slots table OUTSIDE of columns to use full width        
    if st.session_state.slots_clicked:
        st.markdown("---")
        st.subheader("📅 Available Slots Today")
        
        chatbot = get_chatbot_cached()
        patients_csv_path = st.session_state.get('patients_csv_path', 'data/patients.csv')
        response = chatbot.process_query('available slots today', patients_csv_path)
        if response.get('data'):
            df = pd.DataFrame(response['data'])
            # Dynamic height based on data size (35px per row + 50px header)
            dynamic_height = min(len(df) * 35 + 50, 500)  # Cap at 500px max for slots
            st.data_editor(
                df, 
                use_container_width=True,
                height=dynamic_height,
                disabled=True,
                hide_index=True
            )
            
            if st.button('🔄 Back to Quick Actions', key='slots_back'):
                st.session_state.slots_clicked = False
                st.rerun()
        else:
            st.info('No slots available today')
            if st.button('🔄 Back to Quick Actions', key='slots_back_empty'):
                st.session_state.slots_clicked = False
                st.rerun()
    
    # Handle prioritization processing
    if st.session_state.processing_prioritization:
        with st.spinner('🔄 Running smart patient prioritization...'):
            try:
                chatbot = get_chatbot_cached()
                patients_csv_path = st.session_state.get('patients_csv_path', 'data/patients.csv')
                response = chatbot.process_query('prioritize patients', patients_csv_path)
                
                if response.get('status') == 'success' and response.get('data'):
                    st.success(f"✅ {response.get('message', 'Prioritization completed')}")
                    
                    # Create clean dataframe without redundant index
                    df = pd.DataFrame(response['data'])
                    
                    # Clean up the display - remove redundant/non-functional columns
                    columns_to_remove = ['rank', 'recommended_for_booking']
                    for col in columns_to_remove:
                        if col in df.columns:
                            df = df.drop(columns=[col])
                    
                    # Reset index to start from 1 and rename it
                    df.index = df.index + 1
                    df.index.name = 'Priority Rank'
                    
                    st.dataframe(df, use_container_width=True)
                else:
                    st.warning(f"⚠️ {response.get('message', 'No prioritization data available')}")
                    if 'suggestions' in response:
                        st.write("**Suggestions:**")
                        for suggestion in response['suggestions']:
                            st.write(f"• {suggestion}")
            except Exception as e:
                st.error(f"❌ Error during prioritization: {str(e)}")
            finally:
                # Reset the processing state and add a reset button
                st.session_state.processing_prioritization = False
                if st.button('🔄 Back to Quick Actions', key='prioritization_back'):
                    st.session_state.processing_prioritization = False
                    st.rerun()

# ============ PHYSICIANS & SCHEDULES ============
elif view == '👩‍⚕️ Physicians & Schedules':
    st.header('👩‍⚕️ Physicians & Schedules')
    
    # Display all physicians
    physicians = slot_manager.get_practitioners()
    
    if physicians:
        physicians_data = []
        for p in physicians:
            # Get today's schedule info
            today_summary = slot_manager.get_practitioner_schedule_summary(p.id, date.today())
            physicians_data.append({
                'ID': p.id,
                'Name': p.name,
                'Specialty': p.specialty,
                'Department': p.department,
                'Today\'s Slots': today_summary.get('total_slots', 0),
                'Available Today': today_summary.get('available_slots', 0),
                'Utilization %': round((today_summary.get('booked_appointments', 0) / max(today_summary.get('total_slots', 1), 1)) * 100, 1)
            })
        
        physicians_df = pd.DataFrame(physicians_data)
        st.dataframe(physicians_df, use_container_width=True)
        
        # Detailed physician view
        st.subheader('Physician Details')
        selected_physician = st.selectbox(
            'Select physician for detailed view:',
            options=[p.id for p in physicians],
            format_func=lambda x: next(p.name for p in physicians if p.id == x)
        )
        
        if selected_physician:
            physician = slot_manager.get_practitioner(selected_physician)
            col1, col2 = st.columns(2)
            
            with col1:
                st.write('**Basic Information:**')
                st.write(f'**Name:** {physician.name}')
                st.write(f'**Specialty:** {physician.specialty}')
                st.write(f'**Department:** {physician.department}')
                st.write(f'**Qualifications:** {", ".join(physician.qualification)}')
                
            with col2:
                # Weekly schedule overview
                st.write('**This Week\'s Schedule:**')
                weekly_data = []
                for i in range(7):
                    check_date = date.today() + timedelta(days=i)
                    summary = slot_manager.get_practitioner_schedule_summary(selected_physician, check_date)
                    weekly_data.append({
                        'Date': check_date.strftime('%Y-%m-%d'),
                        'Day': check_date.strftime('%A'),
                        'Total Slots': summary.get('total_slots', 0),
                        'Available': summary.get('available_slots', 0),
                        'Booked': summary.get('booked_appointments', 0)
                    })
                
                st.dataframe(pd.DataFrame(weekly_data), use_container_width=True)

# ============ SLOT MANAGEMENT ============
elif view == '📅 Slot Management':
    st.header('📅 Slot Management')
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        physicians = slot_manager.get_practitioners()
        physician_options = ['All Physicians'] + [p.id for p in physicians]
        selected_physician = st.selectbox(
            'Select Physician:',
            options=physician_options,
            format_func=lambda x: 'All Physicians' if x == 'All Physicians' else next(p.name for p in physicians if p.id == x)
        )
    
    with col2:
        selected_date = st.date_input(
            'Select Date:',
            value=date.today(),
            min_value=date.today(),
            max_value=date.today() + timedelta(days=30)
        )
    
    with col3:
        specialties = list(set(p.specialty for p in physicians))
        specialty_filter = st.selectbox('Filter by Specialty:', ['All'] + specialties)
    
    # Get available slots
    practitioner_id = None if selected_physician == 'All Physicians' else selected_physician
    specialty = None if specialty_filter == 'All' else specialty_filter
    
    available_slots = slot_manager.get_available_slots(
        practitioner_id=practitioner_id,
        date_from=datetime.combine(selected_date, datetime.min.time()),
        date_to=datetime.combine(selected_date, datetime.max.time()),
        specialty=specialty
    )
    
    st.subheader(f'Available Slots - {selected_date.strftime("%A, %B %d, %Y")}')
    
    if available_slots:
        slots_data = []
        for slot in available_slots:
            practitioner = slot_manager.get_practitioner(slot.practitioner_id)
            slots_data.append({
                'Slot ID': slot.id,
                'Physician': practitioner.name if practitioner else 'Unknown',
                'Specialty': slot.specialty,
                'Start Time': slot.start.strftime('%H:%M'),
                'End Time': slot.end.strftime('%H:%M'),
                'Duration (min)': slot.duration_minutes,
                'Service Type': ', '.join(slot.service_type),
                'Status': slot.status.value
            })
        
        slots_df = pd.DataFrame(slots_data)
        st.dataframe(slots_df, use_container_width=True)
        
        # Slot statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric('Total Available Slots', len(available_slots))
        
        with col2:
            endocrinology_slots = len([s for s in available_slots if 'endocrinology' in s.specialty.lower()])
            st.metric('Endocrinology Slots', endocrinology_slots)
        
        with col3:
            cardiology_slots = len([s for s in available_slots if 'cardiology' in s.specialty.lower()])
            st.metric('Cardiology Slots', cardiology_slots)
        
        with col4:
            family_med_slots = len([s for s in available_slots if 'family' in s.specialty.lower()])
            st.metric('Family Medicine Slots', family_med_slots)
        
    else:
        st.info('No available slots found for the selected criteria.')

# ============ SMART PATIENT PRIORITIZATION ============
elif view == '🎯 Smart Patient Prioritization':
    st.header('🎯 Smart Patient Prioritization')
    
    # Configuration
    col1, col2, col3 = st.columns(3)
    
    with col1:
        physicians = slot_manager.get_practitioners()
        physician_options = ['Auto-Select Best Match'] + [p.id for p in physicians]
        selected_physician = st.selectbox(
            'Select Physician:',
            options=physician_options,
            format_func=lambda x: 'Auto-Select Best Match' if x == 'Auto-Select Best Match' else next(p.name for p in physicians if p.id == x)
        )
    
    with col2:
        priority_date = st.date_input(
            'Prioritization Date:',
            value=date.today() + timedelta(days=1),
            min_value=date.today(),
            max_value=date.today() + timedelta(days=30)
        )
    
    with col3:
        max_patients = st.number_input(
            'Max Patients to Prioritize:',
            min_value=1,
            max_value=20,
            value=10,
            help='Leave empty to use available slot count'
        )
    
    if st.button('🎯 Run Smart Prioritization', type='primary'):
        with st.spinner('🚀 Running optimized AI prioritization...'):
            patients = patients_df.to_dict('records')
            
            # Background model preloading (first time only, non-blocking)
            if not st.session_state.preload_attempted:
                try:
                    from src.prioritizer import preload_models
                    preload_models()  # Run in background, don't wait for completion
                    st.session_state.models_preloaded = True
                except:
                    st.session_state.models_preloaded = False
                st.session_state.preload_attempted = True
            
            # Performance metrics for hackathon demo
            import time
            start_time = time.time()
            
            # Get prioritized patients with optimized batch processing
            practitioner_id = None if selected_physician == 'Auto-Select Best Match' else selected_physician
            prioritizer = get_prioritizer_cached()
            
            prioritized_patients = prioritizer.prioritize_patients_for_slots(
                patients=patients,
                practitioner_id=practitioner_id,
                target_date=priority_date,
                max_patients=max_patients
            )
            
            # Show performance metrics
            processing_time = time.time() - start_time
            
            if prioritized_patients:
                st.success(f'🎯 Successfully prioritized {len(prioritized_patients)} patients in {processing_time:.2f} seconds!')
                st.info(f'⚡ Processing rate: {len(patients)/processing_time:.1f} patients/second')
                
                # Display results
                priority_data = []
                for i, patient in enumerate(prioritized_patients, 1):
                    priority_data.append({
                        'Rank': i,
                        'Patient ID': patient['patient_id'],
                        'Name': patient['name'],
                        'Age': patient['age'],
                        'Condition': patient['condition'],
                        'Risk Level': patient['base_priority_level'],
                        'Risk Score': round(patient['base_score'], 1),
                        'Medical Reasons': '; '.join(patient.get('base_reasons', [])[:2]) if patient.get('base_reasons') else 'Normal parameters',
                        'AI Method': patient.get('reasoning_source', '❓ Unknown')
                    })
                
                priority_df = pd.DataFrame(priority_data)
                
                # Gentle professional color coding for priority levels
                def highlight_priority(val):
                    if val == 'Emergency':
                        return 'background-color: #ffebee; color: #d32f2f; font-weight: 600; border-left: 4px solid #d32f2f;'
                    elif val == 'High':
                        return 'background-color: #fff3e0; color: #f57c00; font-weight: 600; border-left: 4px solid #f57c00;'
                    elif val == 'Medium':
                        return 'background-color: #f3f4f6; color: #6b7280; font-weight: 500; border-left: 4px solid #6b7280;'
                    else:  # Low
                        return 'background-color: #f0f9f0; color: #2e7d32; font-weight: 500; border-left: 4px solid #2e7d32;'
                

                
                # Clean up the display - remove redundant columns if they exist
                display_df = priority_df.copy()
                if 'Rank' in display_df.columns:
                    display_df = display_df.drop(columns=['Rank'])  # Remove redundant rank column
                
                # Reset index to start from 1 for better readability
                display_df.index = display_df.index + 1
                display_df.index.name = 'Priority Rank'
                
                styled_df = display_df.style.applymap(highlight_priority, subset=['Risk Level'])
                # Only color code risk levels, not reasoning source
                # Remove background_gradient due to matplotlib dependency
                # styled_df = styled_df.background_gradient(subset=['Final Score'], cmap='RdYlGn')
                
                st.dataframe(
                    styled_df, 
                    use_container_width=True,
                    column_config={
                        "Patient ID": st.column_config.TextColumn("ID", width="small"),
                        "Name": st.column_config.TextColumn("Name", width="medium"),
                        "Age": st.column_config.NumberColumn("Age", width="small"),
                        "Condition": st.column_config.TextColumn("Condition", width="medium"),
                        "Risk Level": st.column_config.TextColumn("Risk Level", width="small"),
                        "Risk Score": st.column_config.NumberColumn("Risk Score", width="small"),
                        "Medical Reasons": st.column_config.TextColumn("Medical Reasons", width="large"),
                        "AI Method": st.column_config.TextColumn("AI Method", width="medium")
                    }
                )
                
                # Summary statistics
                st.subheader('📊 Prioritization Summary')
                col1, col2, col3, col4 = st.columns(4)
                
                priority_counts = priority_df['Risk Level'].value_counts()
                
                with col1:
                    st.metric('Emergency Cases', priority_counts.get('Emergency', 0))
                with col2:
                    st.metric('High Priority', priority_counts.get('High', 0))
                with col3:
                    st.metric('Medium Priority', priority_counts.get('Medium', 0))
                with col4:
                    st.metric('Low Priority', priority_counts.get('Low', 0))
                
                # Recommended actions
                st.subheader('💡 Recommended Actions')
                recommended = [p for p in prioritized_patients if p['recommended_for_booking']]
                
                if recommended:
                    st.write(f'**✅ {len(recommended)} patients recommended for immediate booking:**')
                    for patient in recommended[:5]:  # Show top 5
                        st.write(f'• **{patient["name"]}** ({patient["base_priority_level"]} priority) - {patient.get("booking_reasons", ["Medical priority"])[0]}')
                
            else:
                st.warning('No patients could be prioritized. Check available slots.')

# ============ APPOINTMENT BOOKING ============
elif view == '📋 Appointment Booking':
    st.header('📋 Appointment Booking')
    
    # Two-column layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader('📅 Book New Appointment')
        
        # Patient selection
        patients = patients_df.to_dict('records')
        patient_options = {f"{p['patient_id']} - {p['name']}": p for p in patients}
        selected_patient_key = st.selectbox(
            'Select Patient:',
            options=list(patient_options.keys())
        )
        selected_patient = patient_options[selected_patient_key]
        
        # Practitioner selection
        physicians = slot_manager.get_practitioners()
        practitioner_options = {f"{p.name} ({p.specialty})": p for p in physicians}
        selected_practitioner_key = st.selectbox(
            'Select Practitioner:',
            options=list(practitioner_options.keys())
        )
        selected_practitioner = practitioner_options[selected_practitioner_key]
        
        # Date selection
        booking_date = st.date_input(
            'Select Date:',
            value=date.today() + timedelta(days=1),
            min_value=date.today(),
            max_value=date.today() + timedelta(days=30)
        )
        
        # Get available slots for selected practitioner and date
        available_slots = slot_manager.get_available_slots(
            practitioner_id=selected_practitioner.id,
            date_from=datetime.combine(booking_date, datetime.min.time()),
            date_to=datetime.combine(booking_date, datetime.max.time())
        )
        
        if available_slots:
            slot_options = {f"{s.start.strftime('%H:%M')} - {s.end.strftime('%H:%M')}": s for s in available_slots}
            selected_slot_key = st.selectbox(
                'Select Time Slot:',
                options=list(slot_options.keys())
            )
            selected_slot = slot_options[selected_slot_key]
            
            # Appointment details
            reason = st.selectbox(
                'Reason for Visit:',
                ['Diabetes Follow-up', 'New Patient Consultation', 'Medication Review', 'Complications Check', 'Routine Check-up']
            )
            
            notes = st.text_area('Additional Notes:', height=100)
            
            if st.button('📋 Book Appointment', type='primary'):
                appointment = slot_manager.book_appointment(
                    slot_id=selected_slot.id,
                    patient_id=str(selected_patient['patient_id']),
                    patient_name=selected_patient['name'],
                    reason_code=reason.lower().replace(' ', '-'),
                    description=notes,
                    priority='routine'
                )
                
                if appointment:
                    st.success(f'✅ Appointment successfully booked!')
                    st.write(f'**Patient:** {appointment.patient_name}')
                    st.write(f'**Practitioner:** {appointment.practitioner_name}')
                    st.write(f'**Date & Time:** {appointment.start.strftime("%Y-%m-%d %H:%M")}')
                    st.write(f'**Appointment ID:** {appointment.id}')
                else:
                    st.error('❌ Failed to book appointment. Slot may no longer be available.')
        else:
            st.info('No available slots for the selected practitioner and date.')
    
    with col2:
        st.subheader('📋 Today\'s Appointments')
        
        # Display today's appointments
        today_appointments = slot_manager.get_appointments(target_date=date.today())
        
        if today_appointments:
            appointments_data = []
            for apt in today_appointments:
                appointments_data.append({
                    'Time': apt.start.strftime('%H:%M'),
                    'Patient': apt.patient_name,
                    'Practitioner': apt.practitioner_name,
                    'Reason': apt.reason_code.replace('-', ' ').title(),
                    'Status': apt.status.value.title()
                })
            
            st.dataframe(pd.DataFrame(appointments_data), use_container_width=True)
        else:
            st.info('No appointments scheduled for today.')
        
        # Quick stats
        st.subheader('📊 Quick Stats')
        
        total_slots_today = len(slot_manager.get_available_slots(
            date_from=datetime.combine(date.today(), datetime.min.time()),
            date_to=datetime.combine(date.today(), datetime.max.time())
        ))
        
        booked_today = len(today_appointments)
        
        col3, col4 = st.columns(2)
        with col3:
            st.metric('Available Slots Today', total_slots_today)
        with col4:
            st.metric('Booked Appointments', booked_today)

# ============ ANALYTICS & REPORTS ============
elif view == '📊 Analytics & Reports':
    st.header('📊 Analytics & Reports')
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input('Start Date', value=date.today() - timedelta(days=7))
    with col2:
        end_date = st.date_input('End Date', value=date.today())
    
    # System utilization
    st.subheader('🏥 System Utilization')
    
    utilization = slot_manager.get_slot_utilization(
        date_from=datetime.combine(start_date, datetime.min.time()),
        date_to=datetime.combine(end_date, datetime.max.time())
    )
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('Total Slots', utilization['total_slots'])
    with col2:
        st.metric('Available Slots', utilization['available_slots'])
    with col3:
        st.metric('Booked Slots', utilization['booked_slots'])
    with col4:
        st.metric('Utilization Rate', f"{utilization['utilization_rate']}%")
    
    # Practitioner-wise utilization
    st.subheader('👩‍⚕️ Practitioner Utilization')
    
    practitioners = slot_manager.get_practitioners()
    practitioner_stats = []
    
    for practitioner in practitioners:
        prac_util = slot_manager.get_slot_utilization(
            practitioner_id=practitioner.id,
            date_from=datetime.combine(start_date, datetime.min.time()),
            date_to=datetime.combine(end_date, datetime.max.time())
        )
        
        practitioner_stats.append({
            'Name': practitioner.name,
            'Specialty': practitioner.specialty,
            'Total Slots': prac_util['total_slots'],
            'Available': prac_util['available_slots'],
            'Booked': prac_util['booked_slots'],
            'Utilization %': prac_util['utilization_rate']
        })
    
    practitioner_df = pd.DataFrame(practitioner_stats)
    if not practitioner_df.empty:
        # Remove background_gradient due to matplotlib dependency
        st.dataframe(practitioner_df, use_container_width=True)

# Push branding further down with more space
st.markdown("<br><br>", unsafe_allow_html=True)

# Footer branding - positioned lower
st.markdown(
    """
    <div style="margin: 4rem 0 1rem 0;">
        <hr style="border: none; height: 1px; background: linear-gradient(90deg, transparent, #e2e8f0, transparent); margin: 2rem 0;">
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="footer-branding" style="text-align: center; color: #6b7280; font-size: 0.95em; margin: 2rem 0 3rem 0; padding: 1.5rem;">
        <div style="margin-bottom: 0.75rem;">
            <span style="font-size: 1.1em; color: #2563eb; font-weight: 600;">🏥 VisitIQ</span> 
            <span style="margin: 0 0.75rem; color: #14b8a6;">•</span>
            <span style="color: #1f2937; font-weight: 500;">Agilon Health</span>
            <span style="margin: 0 0.75rem; color: #14b8a6;">•</span>
            <span style="color: #6b7280; font-style: italic;">Team GridMind</span>
        </div>
        <div style="color: #9ca3af; font-size: 0.85em; margin-top: 0.5rem;">
            🤖 AI-Enhanced • 🏥 FHIR-Compliant • 📊 Healthcare Scheduling Intelligence
        </div>
    </div>
    """, 
    unsafe_allow_html=True
)
