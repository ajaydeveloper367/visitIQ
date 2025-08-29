"""
Enhanced Visit Prioritization App with FHIR Slots and Chatbot
Streamlit web interface for the enhanced healthcare scheduling system
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import json

# Import enhanced modules
from src.slot_manager import get_slot_manager
from src.smart_prioritizer import SmartPrioritizer
from src.chatbot import create_chatbot
from src.fhir_models import AppointmentStatus

# Page configuration
st.set_page_config(
    page_title='Healthcare Visit Prioritization & Scheduling',
    page_icon='🏥',
    layout='wide',
    initial_sidebar_state='expanded'
)

# Initialize components
@st.cache_resource
def get_components():
    slot_manager = get_slot_manager()
    prioritizer = SmartPrioritizer(slot_manager)
    chatbot = create_chatbot()
    return slot_manager, prioritizer, chatbot

slot_manager, prioritizer, chatbot = get_components()

# App header
st.title('🏥 Healthcare Visit Prioritization & Scheduling System')
st.markdown('**Enhanced with FHIR Slots, Smart Prioritization & AI Chatbot**')

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
    return pd.read_csv('data/patients.csv')

patients_df = load_patients()

# ============ AI CHATBOT ASSISTANT ============
if view == '🤖 AI Chatbot Assistant':
    st.header('🤖 AI Assistant')
    st.markdown('Ask me anything about physicians, available slots, or patient prioritization!')
    
    # Chat interface
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Display chat history
    for i, (user_msg, bot_response) in enumerate(st.session_state.chat_history):
        with st.container():
            st.write(f"**You:** {user_msg}")
            st.write(f"**Assistant:** {bot_response}")
            st.divider()
    
    # Input for new query
    user_query = st.text_input(
        'Ask a question:',
        placeholder='e.g., "List all physicians", "Show available slots for Dr. Chen on tomorrow", "Prioritize patients for endocrinology"'
    )
    
    if user_query:
        with st.spinner('Processing your query...'):
            response = chatbot.process_query(user_query)
            
            if response['status'] == 'success':
                formatted_response = response.get('formatted_response', response['message'])
                
                # Display structured data if available
                if 'data' in response and response['data']:
                    st.success(response['message'])
                    
                    # Display data based on query type
                    if isinstance(response['data'], list) and len(response['data']) > 0:
                        if 'name' in response['data'][0] and 'specialty' in response['data'][0]:
                            # Physician data
                            st.dataframe(pd.DataFrame(response['data']))
                        elif 'start_time' in response['data'][0]:
                            # Slot data
                            st.dataframe(pd.DataFrame(response['data']))
                        elif 'patient_id' in response['data'][0]:
                            # Patient priority data
                            df = pd.DataFrame(response['data'])
                            st.dataframe(df.style.background_gradient(subset=['score']))
                    
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
            
            # Add to chat history
            st.session_state.chat_history.append((user_query, formatted_response if 'formatted_response' in response else response['message']))
    
    # Quick action buttons
    st.subheader('Quick Actions')
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button('📝 List All Physicians'):
            response = chatbot.process_query('list all physicians')
            st.dataframe(pd.DataFrame(response['data']))
    
    with col2:
        if st.button('📅 Today\'s Available Slots'):
            response = chatbot.process_query('available slots today')
            if response['data']:
                st.dataframe(pd.DataFrame(response['data']))
            else:
                st.info('No slots available today')
    
    with col3:
        if st.button('🎯 Smart Patient Prioritization'):
            response = chatbot.process_query('prioritize patients')
            if response['data']:
                st.dataframe(pd.DataFrame(response['data']))

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
                
                st.dataframe(pd.DataFrame(weekly_data))

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
        with st.spinner('Running smart prioritization algorithm...'):
            patients = patients_df.to_dict('records')
            
            # Get prioritized patients
            practitioner_id = None if selected_physician == 'Auto-Select Best Match' else selected_physician
            
            prioritized_patients = prioritizer.prioritize_patients_for_slots(
                patients=patients,
                practitioner_id=practitioner_id,
                target_date=priority_date,
                max_patients=max_patients
            )
            
            if prioritized_patients:
                st.success(f'Successfully prioritized {len(prioritized_patients)} patients!')
                
                # Display results
                priority_data = []
                for i, patient in enumerate(prioritized_patients, 1):
                    priority_data.append({
                        'Rank': i,
                        'Patient ID': patient['patient_id'],
                        'Name': patient['name'],
                        'Age': patient['age'],
                        'Condition': patient['condition'],
                        'Priority Level': patient['base_priority_level'],
                        'Final Score': round(patient['final_score'], 1),
                        'Recommended': '✅ YES' if patient['recommended_for_booking'] else '⏳ Waitlist',
                        'Key Reasons': '; '.join(patient.get('base_reasons', [])[:2])  # Top 2 reasons
                    })
                
                priority_df = pd.DataFrame(priority_data)
                
                # Color coding for priority levels
                def highlight_priority(val):
                    if val == 'Emergency':
                        return 'background-color: #ffebee; color: #c62828;'
                    elif val == 'High':
                        return 'background-color: #fff3e0; color: #ef6c00;'
                    elif val == 'Medium':
                        return 'background-color: #f3e5f5; color: #7b1fa2;'
                    else:
                        return 'background-color: #e8f5e8; color: #2e7d32;'
                
                styled_df = priority_df.style.applymap(highlight_priority, subset=['Priority Level'])
                styled_df = styled_df.background_gradient(subset=['Final Score'], cmap='RdYlGn')
                
                st.dataframe(styled_df, use_container_width=True)
                
                # Summary statistics
                st.subheader('📊 Prioritization Summary')
                col1, col2, col3, col4 = st.columns(4)
                
                priority_counts = priority_df['Priority Level'].value_counts()
                
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
            
            st.dataframe(pd.DataFrame(appointments_data))
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
        st.dataframe(
            practitioner_df.style.background_gradient(subset=['Utilization %'], cmap='RdYlGn'),
            use_container_width=True
        )

# Footer
st.markdown('---')
st.markdown('**Healthcare Visit Prioritization System** | Enhanced with FHIR Standards, Smart AI Prioritization & Conversational Interface')

