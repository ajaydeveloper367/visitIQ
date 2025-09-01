"""
Demo Script for Enhanced Visit Prioritization System
Demonstrates FHIR slots, smart prioritization, and chatbot capabilities
"""

import os
import sys
from datetime import date, timedelta, datetime
import pandas as pd

# Add src to path for imports
sys.path.append('src')

from src.slot_manager import get_slot_manager
from src.smart_prioritizer import SmartPrioritizer
from src.chatbot import create_chatbot

def demonstrate_system():
    """Comprehensive demo of the enhanced system"""
    
    print("🏥 ENHANCED VISIT PRIORITIZATION SYSTEM DEMO")
    print("=" * 60)
    
    # Initialize components
    print("\n1️⃣ Initializing system components...")
    slot_manager = get_slot_manager()
    prioritizer = SmartPrioritizer(slot_manager)
    chatbot = create_chatbot()
    print("✅ System components initialized successfully!")
    
    # Display practitioners
    print("\n2️⃣ Available Practitioners:")
    practitioners = slot_manager.get_practitioners()
    for p in practitioners:
        print(f"   • {p.name} - {p.specialty} ({p.department})")
    
    # Display available slots for tomorrow
    print("\n3️⃣ Available Slots for Tomorrow:")
    tomorrow = date.today() + timedelta(days=1)
    slots = slot_manager.get_available_slots(
        date_from=datetime.combine(tomorrow, datetime.min.time()),
        date_to=datetime.combine(tomorrow, datetime.max.time())
    )
    
    if slots:
        for slot in slots[:5]:  # Show first 5 slots
            practitioner = slot_manager.get_practitioner(slot.practitioner_id)
            print(f"   • {slot.start.strftime('%H:%M')}-{slot.end.strftime('%H:%M')} with {practitioner.name} ({slot.specialty})")
        if len(slots) > 5:
            print(f"   ... and {len(slots) - 5} more slots")
    else:
        print("   No available slots found for tomorrow")
    
    # Demonstrate smart prioritization
    print("\n4️⃣ Smart Patient Prioritization:")
    if os.path.exists('data/patients.csv'):
        patients_df = pd.read_csv('data/patients.csv')
        patients = patients_df.to_dict('records')
        
        # Prioritize for endocrinologist
        endocrinologist = next((p for p in practitioners if 'endocrin' in p.specialty.lower()), None)
        
        if endocrinologist:
            prioritized = prioritizer.prioritize_patients_for_slots(
                patients=patients,
                practitioner_id=endocrinologist.id,
                target_date=tomorrow,
                max_patients=5
            )
            
            print(f"   Top patients for {endocrinologist.name} on {tomorrow}:")
            for i, patient in enumerate(prioritized, 1):
                print(f"   {i}. {patient['name']} (Priority: {patient['base_priority_level']}, Score: {patient['final_score']:.1f})")
                if patient.get('base_reasons'):
                    print(f"      Reasons: {'; '.join(patient['base_reasons'][:2])}")
    
    # Demonstrate chatbot
    print("\n5️⃣ Chatbot Interface Demo:")
    
    test_queries = [
        "List all physicians",
        f"Available slots for Dr. Chen on {tomorrow}",
        "How many slots are available for endocrinology?",
        "Prioritize patients for tomorrow"
    ]
    
    for query in test_queries:
        print(f"\n   🤖 Query: '{query}'")
        response = chatbot.process_query(query)
        
        if response['status'] == 'success':
            print(f"   ✅ Response: {response['message']}")
            if 'data' in response and response['data']:
                if isinstance(response['data'], list) and len(response['data']) > 0:
                    print(f"      Found {len(response['data'])} results")
        else:
            print(f"   ⚠️  Response: {response.get('message', 'Unknown response')}")
    
    # System statistics
    print("\n6️⃣ System Statistics:")
    utilization = slot_manager.get_slot_utilization()
    print(f"   • Total slots in system: {utilization['total_slots']}")
    print(f"   • Available slots: {utilization['available_slots']}")
    print(f"   • Booked slots: {utilization['booked_slots']}")
    print(f"   • Utilization rate: {utilization['utilization_rate']}%")
    
    print("\n7️⃣ Quick Feature Overview:")
    print("   🏥 FHIR-compliant slot management")
    print("   🤖 AI-powered chatbot interface")
    print("   🎯 Smart patient prioritization with RAG")
    print("   📅 Real-time appointment booking")
    print("   📊 Comprehensive analytics and reporting")
    print("   🔧 Specialty-aware practitioner matching")
    
    print("\n" + "=" * 60)
    print("🚀 Demo completed! Run 'streamlit run enhanced_app.py' to explore the full UI")
    print("💬 Try these chatbot queries in the web interface:")
    print("   • 'List all physicians'")
    print("   • 'Show available slots for Dr. Chen on tomorrow'") 
    print("   • 'Prioritize patients for endocrinology'")
    print("   • 'How many slots are available today?'")

def run_quick_test():
    """Quick functionality test"""
    print("🧪 Running Quick System Test...")
    
    try:
        # Test slot manager
        slot_manager = get_slot_manager()
        practitioners = slot_manager.get_practitioners()
        assert len(practitioners) > 0, "No practitioners found"
        print("✅ Slot Manager: OK")
        
        # Test smart prioritizer
        prioritizer = SmartPrioritizer(slot_manager)
        if os.path.exists('data/patients.csv'):
            patients_df = pd.read_csv('data/patients.csv')
            patients = patients_df.to_dict('records')[:3]  # Test with 3 patients
            
            prioritized = prioritizer.prioritize_patients_for_slots(
                patients=patients,
                target_date=date.today() + timedelta(days=1),
                max_patients=3
            )
            assert len(prioritized) <= 3, "Prioritization failed"
            print("✅ Smart Prioritizer: OK")
        
        # Test chatbot
        chatbot = create_chatbot()
        response = chatbot.process_query("list physicians")
        assert response['status'] == 'success', "Chatbot failed"
        print("✅ Chatbot: OK")
        
        print("🎉 All systems operational!")
        return True
        
    except Exception as e:
        print(f"❌ System test failed: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Visit Prioritization System Demo')
    parser.add_argument('--test', action='store_true', help='Run quick functionality test')
    parser.add_argument('--demo', action='store_true', help='Run full demonstration')
    
    args = parser.parse_args()
    
    if args.test:
        run_quick_test()
    elif args.demo:
        demonstrate_system()
    else:
        print("Usage: python demo_enhanced_system.py --demo | --test")
        print("  --demo: Run full system demonstration")
        print("  --test: Run quick functionality test")
