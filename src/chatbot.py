"""
Chatbot Engine for Visit Prioritization System
Handles natural language queries about physicians, slots, and patient prioritization
"""

import re
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd

from .slot_manager import get_slot_manager, SlotManager
from .smart_prioritizer import SmartPrioritizer

# Try to import OllamaLLM for advanced NL processing
try:
    from langchain_ollama.llms import OllamaLLM
    OLLAMA_AVAILABLE = True
except Exception:
    OLLAMA_AVAILABLE = False

class ChatbotEngine:
    """
    Natural language interface for the visit prioritization system
    Handles queries about physicians, slots, appointments, and patient prioritization
    """
    
    def __init__(self, slot_manager: Optional[SlotManager] = None):
        self.slot_manager = slot_manager or get_slot_manager()
        self.prioritizer = SmartPrioritizer(self.slot_manager)
        
        # Query patterns and handlers
        self.query_patterns = {
            'list_physicians': [
                r'list\s+(?:all\s+)?(?:physicians?|doctors?)',
                r'show\s+(?:me\s+)?(?:physicians?|doctors?)',
                r'who\s+are\s+the\s+(?:physicians?|doctors?)',
                r'available\s+(?:physicians?|doctors?)',
                r'what\s+(?:physicians?|doctors?)\s+(?:do\s+)?(?:we\s+)?have',
                r'tell\s+me\s+(?:about\s+)?(?:the\s+)?(?:physicians?|doctors?)'
            ],
            'physician_count': [
                r'how\s+many\s+(?:physicians?|doctors?)',
                r'(?:what.s\s+the\s+)?(?:total\s+)?(?:number\s+of\s+|count\s+of\s+)?(?:physicians?|doctors?)',
                r'count\s+(?:of\s+)?(?:physicians?|doctors?)',
                r'total\s+(?:physicians?|doctors?)'
            ],
            'physician_specialties': [
                r'(?:physicians?|doctors?)\s+(?:with\s+)?specialty\s+(\w+)',
                r'(\w+)\s+specialists?',
                r'find\s+(\w+)\s+(?:physicians?|doctors?)'
            ],
            'available_slots': [
                r'available\s+slots?\s+(?:for\s+)?(.+?)(?:\s+on\s+(.+?))?',
                r'show\s+(?:me\s+)?slots?\s+(?:for\s+)?(.+?)(?:\s+on\s+(.+?))?',
                r'when\s+(?:is|are)\s+(.+?)\s+available(?:\s+on\s+(.+?))?',
                r'what\s+slots?\s+(?:are\s+)?(?:available\s+)?(?:for\s+)?(.+?)(?:\s+on\s+(.+?))?',
                r'(.+?)\s+(?:schedule|availability)(?:\s+on\s+(.+?))?'
            ],
            'slot_count': [
                r'how\s+many\s+slots?\s+(?:are\s+)?available\s+(?:for\s+)?(.+?)(?:\s+on\s+(.+?))?',
                r'count\s+(?:of\s+)?available\s+slots?\s+(?:for\s+)?(.+?)(?:\s+on\s+(.+?))?',
                r'(?:what.s\s+the\s+)?(?:total\s+)?(?:number\s+of\s+)?slots?\s+(?:available\s+)?(?:for\s+)?(.+?)(?:\s+on\s+(.+?))?'
            ],
            'prioritize_patients': [
                r'prioritize\s+patients?(?:\s+for\s+(.+?))?(?:\s+on\s+(.+?))?$',
                r'which\s+patients?\s+should\s+(?:see|visit)\s+(.+?)(?:\s+on\s+(.+?))?',
                r'schedule\s+patients?\s+(?:for\s+)?(.+?)(?:\s+on\s+(.+?))?',
                r'patient\s+prioritization(?:\s+for\s+(.+?))?(?:\s+on\s+(.+?))?'
            ],
            'book_appointment': [
                r'book\s+(?:appointment\s+)?(?:for\s+)?patient\s+(\w+)\s+with\s+(.+?)(?:\s+on\s+(.+?))?',
                r'schedule\s+patient\s+(\w+)\s+(?:with\s+)?(.+?)(?:\s+on\s+(.+?))?'
            ],
            'practitioner_info': [
                r'tell\s+me\s+about\s+(.+)',
                r'information\s+(?:about|on)\s+(.+)',
                r'who\s+is\s+(.+)'
            ],
            'help': [
                r'help\s*\??',
                r'what\s+can\s+(?:you\s+)?do\??',
                r'commands?\??'
            ]
        }
    
    def process_query(self, query: str, patients_csv_path: str = "data/patients.csv") -> Dict[str, Any]:
        """
        Process a natural language query and return structured response
        """
        query = query.strip().lower()
        
        # Try to match query patterns
        for query_type, patterns in self.query_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, query)
                if match:
                    return self._handle_query(query_type, match, query, patients_csv_path)
        
        # If no pattern matches, try LLM-based processing
        if OLLAMA_AVAILABLE:
            return self._handle_llm_query(query, patients_csv_path)
        
        # Fallback response
        return {
            'status': 'unknown',
            'message': "I didn't understand that query. Try asking about physicians, available slots, or patient prioritization.",
            'suggestions': [
                "List all physicians",
                "Show available slots for Dr. Smith on tomorrow",
                "Prioritize patients for Dr. Chen on 2024-01-15",
                "How many slots are available for endocrinology?"
            ]
        }
    
    def _handle_query(
        self, 
        query_type: str, 
        match: re.Match, 
        original_query: str,
        patients_csv_path: str
    ) -> Dict[str, Any]:
        """Handle specific query types"""
        
        if query_type == 'list_physicians':
            return self._list_physicians()
        
        elif query_type == 'physician_count':
            return self._count_physicians()
        
        elif query_type == 'physician_specialties':
            specialty = match.group(1)
            return self._find_physicians_by_specialty(specialty)
        
        elif query_type == 'available_slots':
            practitioner_query = match.group(1)
            date_query = match.group(2) if len(match.groups()) > 1 else None
            return self._get_available_slots(practitioner_query, date_query)
        
        elif query_type == 'slot_count':
            practitioner_query = match.group(1) 
            date_query = match.group(2) if len(match.groups()) > 1 else None
            return self._count_available_slots(practitioner_query, date_query)
        
        elif query_type == 'prioritize_patients':
            practitioner_query = match.group(1) if match.group(1) else None
            date_query = match.group(2) if len(match.groups()) > 1 and match.group(2) else None
            return self._prioritize_patients(practitioner_query, date_query, patients_csv_path)
        
        elif query_type == 'practitioner_info':
            practitioner_query = match.group(1)
            return self._get_practitioner_info(practitioner_query)
        
        elif query_type == 'help':
            return self._get_help()
        
        return {'status': 'error', 'message': 'Query type not implemented'}
    
    def _list_physicians(self) -> Dict[str, Any]:
        """List all available physicians"""
        practitioners = self.slot_manager.get_practitioners()
        
        if not practitioners:
            return {
                'status': 'no_data',
                'message': 'No physicians found in the system.',
                'data': []
            }
        
        practitioner_data = []
        for p in practitioners:
            # Get contact info and truncate if needed
            contact_info = p.contact_phone or p.contact_email or 'N/A'
            contact_display = contact_info[:15] + '...' if len(contact_info) > 15 else contact_info
            
            practitioner_data.append({
                'ID': p.id,
                'Name': p.name,
                'Specialty': p.specialty,
                'Dept': p.department[:15] + '...' if len(p.department) > 15 else p.department,
                'Contact': contact_display
            })
        
        return {
            'status': 'success',
            'message': f'Found {len(practitioners)} physicians:',
            'data': practitioner_data,
            'formatted_response': self._format_physician_list(practitioner_data)
        }
    
    def _count_physicians(self) -> Dict[str, Any]:
        """Count total number of physicians"""
        practitioners = self.slot_manager.get_practitioners()
        count = len(practitioners)
        
        if count == 0:
            return {
                'status': 'no_data',
                'message': 'No physicians found in the system.',
                'count': 0
            }
        
        # Group by specialty for detailed breakdown
        specialty_breakdown = {}
        for p in practitioners:
            specialty = p.specialty
            specialty_breakdown[specialty] = specialty_breakdown.get(specialty, 0) + 1
        
        breakdown_text = []
        for specialty, spec_count in specialty_breakdown.items():
            breakdown_text.append(f"• {specialty}: {spec_count}")
        
        formatted_response = f"""We have {count} physician{'s' if count != 1 else ''} in total:

{chr(10).join(breakdown_text)}"""
        
        return {
            'status': 'success',
            'message': f'We have {count} physician{"s" if count != 1 else ""} in total',
            'count': count,
            'breakdown': specialty_breakdown,
            'formatted_response': formatted_response
        }
    
    def _find_physicians_by_specialty(self, specialty: str) -> Dict[str, Any]:
        """Find physicians by specialty"""
        practitioners = self.slot_manager.get_practitioners_by_specialty(specialty)
        
        if not practitioners:
            # Try broader search
            all_practitioners = self.slot_manager.get_practitioners()
            practitioners = [p for p in all_practitioners if specialty in p.specialty.lower()]
        
        if not practitioners:
            return {
                'status': 'not_found',
                'message': f'No physicians found for specialty: {specialty}',
                'suggestions': [p.specialty for p in self.slot_manager.get_practitioners()]
            }
        
        practitioner_data = [
            {
                'id': p.id,
                'name': p.name,
                'specialty': p.specialty,
                'department': p.department
            } for p in practitioners
        ]
        
        return {
            'status': 'success',
            'message': f'Found {len(practitioners)} physician(s) in {specialty}:',
            'data': practitioner_data,
            'formatted_response': self._format_physician_list(practitioner_data)
        }
    
    def _get_available_slots(self, practitioner_query: str, date_query: Optional[str]) -> Dict[str, Any]:
        """Get available slots for practitioner on date"""
        # Find practitioner
        practitioner = self._find_practitioner(practitioner_query)
        if not practitioner:
            return {
                'status': 'not_found',
                'message': f'Practitioner not found: {practitioner_query}',
                'suggestions': [p.name for p in self.slot_manager.get_practitioners()]
            }
        
        # Parse date
        target_date = self._parse_date(date_query)
        if date_query and not target_date:
            return {
                'status': 'error',
                'message': f'Could not parse date: {date_query}',
                'suggestions': ['today', 'tomorrow', '2024-01-15', 'next monday']
            }
        
        # Get available slots
        slots = self.slot_manager.get_available_slots(
            practitioner_id=practitioner.id,
            date_from=datetime.combine(target_date, datetime.min.time()) if target_date else None,
            date_to=datetime.combine(target_date, datetime.max.time()) if target_date else None
        )
        
        if not slots:
            date_str = target_date.strftime('%Y-%m-%d') if target_date else 'requested period'
            return {
                'status': 'no_slots',
                'message': f'No available slots for {practitioner.name} on {date_str}',
                'practitioner': practitioner.name,
                'date': date_str
            }
        
        slot_data = []
        for slot in slots:
            # Safely handle service_type
            service_types = slot.service_type if slot.service_type else ['General']
            service_text = ', '.join(service_types) if isinstance(service_types, list) else str(service_types)
            
            # Ultra-concise service text to prevent any truncation
            short_service = service_text.replace('diabetes-consultation', 'Diabetes').replace('hormone-therapy', 'Hormone').replace('follow-up', 'Followup').replace('routine-checkup', 'Routine').replace('consultation', 'Consult').replace('-', ' ').replace('  ', ' ').strip()
            
            slot_data.append({
                'Time': f"{slot.start.strftime('%H:%M')}-{slot.end.strftime('%H:%M')}",
                'Date': slot.start.strftime('%Y-%m-%d'), 
                'Duration': f"{slot.duration_minutes}min",
                'Service Type': short_service
                # Removed 'Status': 'Available' - redundant since all are available
            })
        
        return {
            'status': 'success',
            'message': f'Found {len(slots)} available slot(s) for {practitioner.name}:',
            'data': slot_data,
            'practitioner': practitioner.name,
            'date': target_date.strftime('%Y-%m-%d') if target_date else 'multiple dates',
            'formatted_response': self._format_slot_list(slot_data, practitioner.name)
        }
    
    def _count_available_slots(self, practitioner_query: str, date_query: Optional[str]) -> Dict[str, Any]:
        """Count available slots"""
        practitioner = self._find_practitioner(practitioner_query)
        target_date = self._parse_date(date_query) if date_query else None
        
        count = self.slot_manager.count_available_slots(
            practitioner_id=practitioner.id if practitioner else None,
            target_date=target_date
        )
        
        practitioner_name = practitioner.name if practitioner else "all physicians"
        date_str = target_date.strftime('%Y-%m-%d') if target_date else "all dates"
        
        return {
            'status': 'success',
            'message': f'{count} slot(s) available for {practitioner_name} on {date_str}',
            'count': count,
            'practitioner': practitioner_name,
            'date': date_str
        }
    
    def _prioritize_patients(
        self, 
        practitioner_query: Optional[str], 
        date_query: Optional[str],
        patients_csv_path: str
    ) -> Dict[str, Any]:
        """Prioritize patients for available slots"""
        try:
            # Load patients
            df = pd.read_csv(patients_csv_path)
            patients = df.to_dict('records')
            
            if not patients:
                return {
                    'status': 'no_data',
                    'message': 'No patients found in the dataset'
                }
            
            # Find practitioner (optional)
            practitioner = None
            if practitioner_query:
                practitioner = self._find_practitioner(practitioner_query)
                if not practitioner:
                    return {
                        'status': 'not_found',
                        'message': f'Practitioner not found: {practitioner_query}',
                        'suggestions': [p.name for p in self.slot_manager.get_practitioners()]
                    }
            target_date = self._parse_date(date_query) if date_query else None
            
            # Get prioritized patients
            prioritized = self.prioritizer.prioritize_patients_for_slots(
                patients=patients,
                practitioner_id=practitioner.id if practitioner else None,
                target_date=target_date
            )
            
            if not prioritized:
                return {
                    'status': 'no_slots',
                    'message': 'No available slots for the specified criteria'
                }
            
            # Format response
            patient_data = []
            for i, patient in enumerate(prioritized, 1):
                patient_data.append({
                    'rank': i,
                    'patient_id': patient['patient_id'],
                    'name': patient['name'],
                    'priority_level': patient['base_priority_level'],
                    'score': patient['final_score'],
                    'reasons': '; '.join(patient.get('base_reasons', [])),
                    'recommended_for_booking': patient['recommended_for_booking']
                })
            
            practitioner_name = practitioner.name if practitioner else "available physicians"
            date_str = target_date.strftime('%Y-%m-%d') if target_date else "available dates"
            
            return {
                'status': 'success',
                'message': f'Prioritized {len(prioritized)} patient(s) for {practitioner_name} on {date_str}:',
                'data': patient_data,
                'practitioner': practitioner_name,
                'date': date_str,
                'formatted_response': self._format_patient_priority_list(patient_data)
            }
            
        except Exception as e:
            return {
                'status': 'error', 
                'message': f'Error prioritizing patients: {str(e)}'
            }
    
    def _get_practitioner_info(self, practitioner_query: str) -> Dict[str, Any]:
        """Get detailed practitioner information"""
        practitioner = self._find_practitioner(practitioner_query)
        
        if not practitioner:
            return {
                'status': 'not_found',
                'message': f'Practitioner not found: {practitioner_query}',
                'suggestions': [p.name for p in self.slot_manager.get_practitioners()]
            }
        
        # Get today's schedule summary
        today = date.today()
        schedule_summary = self.slot_manager.get_practitioner_schedule_summary(
            practitioner.id, today
        )
        
        return {
            'status': 'success',
            'message': f'Information about {practitioner.name}:',
            'data': {
                'basic_info': practitioner.to_dict(),
                'today_schedule': schedule_summary
            },
            'formatted_response': self._format_practitioner_info(practitioner, schedule_summary)
        }
    
    def _get_help(self) -> Dict[str, Any]:
        """Get help information"""
        help_text = """
Available Commands:
• "List physicians" - Show all available physicians
• "Show endocrinology doctors" - Find physicians by specialty
• "Available slots for Dr. Chen on tomorrow" - Check slot availability
• "How many slots available for Dr. Smith on 2024-01-15" - Count slots
• "Prioritize patients for Dr. Chen on tomorrow" - Get patient recommendations
• "Tell me about Dr. Rodriguez" - Get practitioner information
• "Book appointment for patient 123 with Dr. Chen" - Schedule appointment

Date formats: today, tomorrow, 2024-01-15, next monday
        """.strip()
        
        return {
            'status': 'success',
            'message': 'Available commands and usage:',
            'formatted_response': help_text
        }
    
    # Helper methods
    
    def _find_practitioner(self, query: str) -> Optional[Any]:
        """Find practitioner by name or ID"""
        practitioners = self.slot_manager.search_practitioners(query)
        return practitioners[0] if practitioners else None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse various date formats"""
        if not date_str:
            return None
        
        date_str = date_str.lower().strip()
        
        # Handle relative dates
        if date_str in ['today']:
            return date.today()
        elif date_str in ['tomorrow']:
            return date.today() + timedelta(days=1)
        elif 'next monday' in date_str:
            today = date.today()
            days_ahead = 7 - today.weekday()  # Monday is 0
            return today + timedelta(days=days_ahead)
        
        # Handle absolute dates
        date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d']
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    def _format_physician_list(self, physicians: List[Dict[str, Any]]) -> str:
        """Format physician list for display"""
        lines = []
        for p in physicians:
            lines.append(f"• {p['Name']} - {p['Specialty']} ({p['Dept']})")
        return '\n'.join(lines)
    
    def _format_slot_list(self, slots: List[Dict[str, Any]], practitioner_name: str) -> str:
        """Format slot list for display"""
        lines = [f"Available slots for {practitioner_name}:"]
        for slot in slots:
            lines.append(f"• {slot['Date']} {slot['Time']} ({slot['Duration']}) - {slot['Service Type']}")
        return '\n'.join(lines)
    
    def _format_patient_priority_list(self, patients: List[Dict[str, Any]]) -> str:
        """Format patient priority list for display"""
        lines = ["Prioritized patients for booking:"]
        for p in patients:
            status = "✓ RECOMMENDED" if p['recommended_for_booking'] else "• Waitlisted"
            lines.append(f"{status} #{p['rank']}: {p['name']} ({p['priority_level']}, Score: {p['score']})")
        return '\n'.join(lines)
    
    def _format_practitioner_info(self, practitioner: Any, schedule: Dict[str, Any]) -> str:
        """Format detailed practitioner information"""
        lines = [
            f"Name: {practitioner.name}",
            f"Specialty: {practitioner.specialty}",
            f"Department: {practitioner.department}",
            f"Qualifications: {', '.join(practitioner.qualification)}",
            ""
        ]
        
        if schedule:
            lines.extend([
                f"Today's Schedule ({schedule.get('date', '')}):",
                f"• Total slots: {schedule.get('total_slots', 0)}",
                f"• Available slots: {schedule.get('available_slots', 0)}",
                f"• Booked appointments: {schedule.get('booked_appointments', 0)}",
            ])
            
            if schedule.get('available_slot_times'):
                lines.append(f"• Available times: {', '.join(schedule['available_slot_times'])}")
        
        return '\n'.join(lines)
    
    def _handle_llm_query(self, query: str, patients_csv_path: str) -> Dict[str, Any]:
        """Handle complex queries using LLM"""
        # This would use the LLM to parse complex natural language queries
        # For now, return a structured fallback
        return {
            'status': 'llm_fallback',
            'message': f"Processing complex query: '{query}' - Feature under development",
            'suggestions': [
                "Try a more specific query like 'List physicians'",
                "Ask about available slots for a specific doctor",
                "Request patient prioritization for a practitioner"
            ]
        }

# Convenience function
def create_chatbot() -> ChatbotEngine:
    """Create a chatbot instance"""
    return ChatbotEngine()
