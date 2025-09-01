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
        
        # Query patterns and handlers - ordered by specificity (most specific first)
        self.query_patterns = {
            'list_patients': [
                r'^patients?\s*list\s*$',
                r'^list\s+(?:all\s+)?(?:our\s+)?patients?\s*$',
                r'^show\s+(?:me\s+)?(?:all\s+)?(?:our\s+)?patients?\s*$',
                r'^who\s+are\s+(?:our\s+)?patients?\s*$',
                r'^patients?\s*$'
            ],
            'list_physicians': [
                r'^list\s+(?:all\s+)?(?:physicians?|doctors?)(?:\s+we\s+have)?\s*$',
                r'^show\s+(?:me\s+)?(?:all\s+)?(?:physicians?|doctors?)(?:\s+we\s+have)?\s*$',
                r'^who\s+are\s+the\s+(?:physicians?|doctors?)(?:\s+we\s+have)?\s*$',
                r'^what\s+(?:physicians?|doctors?)\s+(?:do\s+)?(?:we\s+)?have\s*$',
                r'^tell\s+me\s+(?:about\s+)?(?:the\s+)?(?:physicians?|doctors?)\s*$',
                r'^(?:physicians?|doctors?)\s+list\s*$',
                r'^(?:physicians?|doctors?)\s*$'
            ],
            'physician_count': [
                r'how\s+many\s+(?:physicians?|doctors?)',
                r'(?:what.s\s+the\s+)?(?:total\s+)?(?:number\s+of\s+|count\s+of\s+)?(?:physicians?|doctors?)',
                r'count\s+(?:of\s+)?(?:physicians?|doctors?)',
                r'total\s+(?:physicians?|doctors?)'
            ],
            'physician_by_gender': [
                r'^(?:male|female)\s+(?:physicians?|doctors?|practitioners?)(?:\s+(?:only|please))?\s*$',
                r'^show\s+(?:me\s+)?(?:all\s+)?(?:male|female)\s+(?:physicians?|doctors?|practitioners?)\s*$',
                r'^list\s+(?:all\s+)?(?:male|female)\s+(?:physicians?|doctors?|practitioners?)\s*$',
                r'^(?:physicians?|doctors?|practitioners?)\s+(?:who\s+are\s+)?(?:male|female)\s*$'
            ],
            'physician_specialties': [
                r'(?:physicians?|doctors?)\s+(?:with\s+)?specialty\s+(\w+)',
                r'(\w+)\s+specialists?',
                r'find\s+(\w+)\s+(?:physicians?|doctors?)',
                r'who\s+are\s+(?:our\s+)?(?:available\s+)?(\w+)s?(?:\s+physicians?|\s+doctors?)?',
                r'(?:available\s+|our\s+)*(\w+)(?:ologists?|ists?)\s*\??',
                r'list\s+(?:of\s+)?(?:our\s+)?(\w+)(?:ologists?|ists?)?\s+(?:physicians?|doctors?|specialists?)?',
                r'show\s+(?:me\s+)?(?:our\s+)?(\w+)\s+(?:physicians?|doctors?|specialists?)',
                r'list\s+(?:of\s+)?(\w+)(?:ology|ists?|ologists?)\s+slots',
                r'(\w+)(?:ology|ologists?)\s+slots\s+available'
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
            'patient_count': [
                r'how\s+many\s+patients?\s+(?:do\s+)?(?:we\s+)?have\??',
                r'(?:what.s\s+the\s+)?(?:total\s+)?(?:number\s+of\s+|count\s+of\s+)?patients?\??',
                r'count\s+(?:of\s+)?(?:our\s+)?patients?',
                r'total\s+patients?'
            ],
            'patient_by_risk': [
                r'^(?:critical|high\s+risk|emergency)\s+patients?(?:\s+(?:only|please))?\s*$',
                r'^show\s+(?:me\s+)?(?:all\s+)?(?:critical|high\s+risk|emergency)\s+patients?\s*$',
                r'^list\s+(?:all\s+)?(?:critical|high\s+risk|emergency)\s+patients?\s*$',
                r'^(?:high|moderate|low)\s+(?:risk\s+)?patients?(?:\s+(?:only|please))?\s*$',
                r'^patients?\s+(?:with\s+)?(?:critical|high|moderate|low)\s+(?:risk\s+)?(?:level|priority)\s*$'
            ],
            'patient_by_condition': [
                r'^how\s+many\s+(diabetic|diabetes|sugar|high\s+bp|hypertension|heart|kidney|stroke)\s+patients?\s*$',
                r'^how\s+many\s+(?:patients?\s+(?:with|have)\s+)?(diabetes|diabetic|sugar|hypertension|high\s+blood\s+pressure|high\s+bp|heart\s+disease|kidney\s+disease|stroke)\s*$',
                r'^count\s+(?:of\s+)?(diabetic|diabetes|sugar|hypertension|high\s+bp|heart|kidney|stroke)\s+patients?\s*$',
                r'^(?:total\s+)?(diabetic|diabetes|sugar|hypertension|high\s+bp|heart|kidney|stroke)\s+patients?\s*$',
                r'^list\s+(?:all\s+)?(diabetic|diabetes|sugar|hypertension|high\s+bp|heart|kidney|stroke)\s+patients?\s*$',
                r'^show\s+(?:me\s+)?(diabetic|diabetes|sugar|hypertension|high\s+bp|heart|kidney|stroke)\s+patients?\s*$',
                r'^(?:diabetic|diabetes|sugar|hypertension|high\s+bp|heart|kidney|stroke)\s+patients?(?:\s+(?:only|please))?\s*$'
            ],
            'patient_conditions': [
                r'what\s+(?:patient\s+)?conditions?\s+(?:do\s+)?(?:we\s+)?(?:have|treat)\??',
                r'list\s+(?:all\s+)?(?:patient\s+)?conditions?',
                r'show\s+(?:me\s+)?(?:patient\s+)?conditions?',
                r'what\s+(?:medical\s+)?conditions?\s+(?:do\s+)?(?:our\s+)?patients?\s+have'
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
        
        elif query_type == 'physician_by_gender':
            gender = self._extract_gender(original_query)
            return self._find_physicians_by_gender(gender)
        
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
        
        elif query_type == 'list_patients':
            return self._list_patients(patients_csv_path)
        
        elif query_type == 'patient_count':
            return self._count_patients(patients_csv_path)
        
        elif query_type == 'patient_by_risk':
            risk_level = self._extract_risk_level(original_query)
            return self._filter_patients_by_risk(risk_level, patients_csv_path)
        
        elif query_type == 'patient_by_condition':
            condition = match.group(1) if match.group(1) else None
            return self._count_patients_by_condition(condition, patients_csv_path)
        
        elif query_type == 'patient_conditions':
            return self._list_patient_conditions(patients_csv_path)
        
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
    
    def _extract_gender(self, query: str) -> str:
        """Extract gender from user query"""
        query_lower = query.lower()
        if 'male' in query_lower and 'female' not in query_lower:
            return 'male'
        elif 'female' in query_lower:
            return 'female'
        else:
            return 'male'  # Default fallback
    
    def _infer_gender_from_name(self, name: str) -> str:
        """Infer gender from first name (for demo purposes)"""
        # Extract first name from full name (e.g., "Dr. John Smith" -> "John")
        parts = name.split()
        first_name = parts[1] if len(parts) > 1 and parts[0].startswith('Dr') else parts[0]
        first_name = first_name.lower()
        
        # Common male names
        male_names = {
            'john', 'michael', 'david', 'james', 'robert', 'william', 'richard', 'thomas', 
            'daniel', 'matthew', 'anthony', 'mark', 'donald', 'steven', 'paul', 'andrew', 
            'joshua', 'kenneth', 'kevin', 'brian', 'george', 'timothy', 'ronald', 'jason',
            'edward', 'jeffrey', 'ryan', 'jacob', 'gary', 'nicholas', 'eric', 'jonathan',
            'stephen', 'larry', 'justin', 'scott', 'brandon', 'benjamin', 'samuel', 'greg',
            'alexander', 'patrick', 'jack', 'dennis', 'jerry', 'tyler', 'aaron', 'jose',
            'henry', 'adam', 'douglas', 'nathan', 'peter', 'zachary', 'kyle', 'noah'
        }
        
        # Common female names  
        female_names = {
            'mary', 'patricia', 'jennifer', 'linda', 'elizabeth', 'barbara', 'susan', 
            'jessica', 'sarah', 'karen', 'nancy', 'lisa', 'betty', 'helen', 'sandra',
            'donna', 'carol', 'ruth', 'sharon', 'michelle', 'laura', 'kimberly',
            'deborah', 'dorothy', 'maria', 'ashley', 'brenda', 'emma', 'olivia', 'sophia', 
            'ava', 'isabella', 'mia', 'abigail', 'emily', 'charlotte', 'harper', 'madison', 
            'amelia', 'sofia', 'evelyn', 'avery', 'chloe', 'ella', 'grace', 'victoria', 'aubrey'
        }
        
        if first_name in male_names:
            return 'male'
        elif first_name in female_names:
            return 'female'
        else:
            # For unknown names, use some heuristics
            if first_name.endswith('a') or first_name.endswith('ia'):
                return 'female'
            else:
                return 'male'
    
    def _find_physicians_by_gender(self, gender: str) -> Dict[str, Any]:
        """Find physicians by gender"""
        try:
            practitioners = self.slot_manager.get_practitioners()
            
            if not practitioners:
                return {
                    'status': 'no_data',
                    'message': 'No physician data found'
                }
            
            # Filter physicians by inferred gender
            filtered_physicians = []
            for practitioner in practitioners:
                practitioner_gender = self._infer_gender_from_name(practitioner.name)
                if practitioner_gender.lower() == gender.lower():
                    filtered_physicians.append({
                        'Name': practitioner.name,
                        'Specialty': practitioner.specialty,
                        'Dept': practitioner.department,
                        'Gender': practitioner_gender.title()
                    })
            
            if not filtered_physicians:
                return {
                    'status': 'not_found',
                    'message': f'No {gender.lower()} physicians found',
                    'suggestions': [
                        f"Try 'list physicians' to see all physicians",
                        f"Ask about '{'female' if gender.lower() == 'male' else 'male'} physicians'",
                        f"Query specific specialties like 'cardiology specialists'"
                    ]
                }
            
            total_physicians = len(practitioners)
            gender_count = len(filtered_physicians)
            percentage = (gender_count / total_physicians * 100) if total_physicians > 0 else 0
            
            # Group by specialty for better presentation
            by_specialty = {}
            for physician in filtered_physicians:
                specialty = physician['Specialty']
                if specialty not in by_specialty:
                    by_specialty[specialty] = []
                by_specialty[specialty].append(physician)
            
            formatted_response = f"""{gender.title()} Physicians: {gender_count} out of {total_physicians} physicians ({percentage:.1f}%)

Breakdown by Specialty:"""
            
            for specialty, physicians in sorted(by_specialty.items()):
                formatted_response += f"\n• {specialty}: {len(physicians)} physician(s)"
                for physician in physicians:
                    formatted_response += f"\n  - {physician['Name']}"
            
            return {
                'status': 'success',
                'message': f'Found {gender_count} {gender.lower()} physicians ({percentage:.1f}% of total)',
                'data': filtered_physicians,
                'count': gender_count,
                'total_physicians': total_physicians,
                'percentage': round(percentage, 1),
                'gender': gender.title(),
                'by_specialty': by_specialty,
                'formatted_response': formatted_response
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error finding physicians by gender: {str(e)}'
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
                'ID': p.id,
                'Name': p.name,
                'Specialty': p.specialty,
                'Dept': p.department[:15] + '...' if len(p.department) > 15 else p.department,
                'Contact': p.contact_phone or p.contact_email or 'N/A'
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

📋 Physician Queries:
• "List physicians" - Show all available physicians
• "Male physicians please" - Show male physicians only
• "Female doctors" - Show female physicians only
• "Show endocrinology doctors" - Find physicians by specialty
• "How many doctors do we have?" - Count physicians
• "Tell me about Dr. Rodriguez" - Get practitioner information

📅 Scheduling & Slots:
• "Available slots for Dr. Chen on tomorrow" - Check slot availability
• "How many slots available for Dr. Smith on 2024-01-15" - Count slots
• "Prioritize patients for Dr. Chen on tomorrow" - Get patient recommendations

👥 Patient Analytics:
• "List patients" - Show all patients with risk assessment
• "Critical patients only" - Filter patients by CRITICAL risk level
• "High risk patients" - Filter patients by HIGH risk level
• "How many patients do we have?" - Count total patients
• "How many diabetic patients?" - Count patients with diabetes
• "Sugar patients" - Show patients with diabetes (sugar condition)
• "High BP patients" - Show patients with hypertension
• "Heart patients" - Show patients with cardiovascular conditions
• "Kidney patients" - Show patients with kidney/renal conditions
• "What conditions do our patients have?" - List all medical conditions

Date formats: today, tomorrow, 2024-01-15, next monday
        """.strip()
        
        return {
            'status': 'success',
            'message': 'Available commands and usage:',
            'formatted_response': help_text
        }
    
    def _list_patients(self, patients_csv_path: str) -> Dict[str, Any]:
        """List all patients with basic information and risk assessment"""
        try:
            df = pd.read_csv(patients_csv_path)
            
            if df.empty:
                return {
                    'status': 'no_data',
                    'message': 'No patient data found',
                    'data': []
                }
            
            # Enhanced patient data with risk assessment and color coding
            patient_data = []
            for _, row in df.iterrows():
                # Calculate risk level based on multiple factors
                risk_info = self._assess_patient_risk(row)
                
                patient_data.append({
                    'Patient ID': row.get('patient_id', 'N/A'),
                    'Name': row.get('name', 'N/A'),
                    'Age': row.get('age', 'N/A'),
                    'Condition': row.get('condition', 'N/A'),
                    'Risk Level': risk_info['level'],
                    'Risk Score': risk_info['score'],
                    'Glucose': f"{row.get('glucose_mg_dL', 'N/A')} mg/dL" if pd.notna(row.get('glucose_mg_dL')) else 'N/A',
                    'BP': f"{row.get('bp_systolic', 'N/A')}/{row.get('bp_diastolic', 'N/A')}" if pd.notna(row.get('bp_systolic')) else 'N/A',
                    'History': (row.get('history', 'None')[:30] + '...') if len(str(row.get('history', ''))) > 30 else row.get('history', 'None')
                })
            
            return {
                'status': 'success',
                'message': f'Found {len(patient_data)} patients:',
                'data': patient_data,
                'formatted_response': self._format_patient_list(patient_data)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error listing patients: {str(e)}'
            }
    
    def _assess_patient_risk(self, patient_row) -> Dict[str, Any]:
        """Assess patient risk level based on multiple medical factors"""
        risk_score = 0
        risk_factors = []
        
        # Glucose-based risk assessment
        try:
            glucose = float(patient_row.get("glucose_mg_dL", 0) or 0)
            if glucose >= 400:
                risk_score += 50
                risk_factors.append("Critical hyperglycemia")
            elif glucose >= 300:
                risk_score += 30
                risk_factors.append("Severe hyperglycemia")
            elif glucose >= 250:
                risk_score += 15
                risk_factors.append("High glucose")
        except (ValueError, TypeError):
            pass
        
        # Blood pressure risk assessment
        try:
            sys_bp = float(patient_row.get("bp_systolic", 0) or 0)
            dia_bp = float(patient_row.get("bp_diastolic", 0) or 0)
            if sys_bp >= 180 or dia_bp >= 110:
                risk_score += 40
                risk_factors.append("Hypertensive crisis")
            elif sys_bp >= 160 or dia_bp >= 100:
                risk_score += 20
                risk_factors.append("High blood pressure")
        except (ValueError, TypeError):
            pass
        
        # Heart rate assessment
        try:
            hr = float(patient_row.get("heart_rate", 0) or 0)
            if hr >= 120:
                risk_score += 10
                risk_factors.append("Tachycardia")
            elif hr <= 50:
                risk_score += 15
                risk_factors.append("Bradycardia")
        except (ValueError, TypeError):
            pass
        
        # Age factor
        try:
            age = int(patient_row.get("age", 0) or 0)
            if age >= 75:
                risk_score += 15
                risk_factors.append("Advanced age")
            elif age >= 65:
                risk_score += 10
                risk_factors.append("Senior patient")
        except (ValueError, TypeError):
            pass
        
        # Medical history assessment
        history = str(patient_row.get("history", "")).lower()
        high_risk_conditions = {
            'stroke': 25, 'heart attack': 25, 'mi': 25, 'cardiac arrest': 30,
            'ckd': 20, 'kidney disease': 20, 'dialysis': 25,
            'cancer': 15, 'chemotherapy': 20,
            'copd': 15, 'asthma': 10
        }
        
        for condition, score in high_risk_conditions.items():
            if condition in history:
                risk_score += score
                risk_factors.append(f"History of {condition}")
        
        # Determine risk level with proper color coding
        if risk_score >= 70:
            level = "CRITICAL"
        elif risk_score >= 45:
            level = "HIGH" 
        elif risk_score >= 25:
            level = "MODERATE"
        else:
            level = "LOW"
        
        return {
            'level': level,
            'score': risk_score,
            'factors': risk_factors
        }
    
    def _format_patient_list(self, patients: List[Dict[str, Any]]) -> str:
        """Format patient list for display with color-coded risk levels"""
        lines = ["Patient List with Risk Assessment:"]
        
        for p in patients:
            risk_level = p['Risk Level']
            risk_emoji = {
                'CRITICAL': '🔴',
                'HIGH': '🟠', 
                'MODERATE': '🟡',
                'LOW': '🟢'
            }.get(risk_level, '⚪')
            
            lines.append(f"{risk_emoji} {p['Name']} (ID: {p['Patient ID']}) - Age {p['Age']}")
            lines.append(f"   Condition: {p['Condition']} | Risk: {risk_level} ({p['Risk Score']})")
            lines.append(f"   Vitals: Glucose {p['Glucose']}, BP {p['BP']}")
            if p['History'] != 'None':
                lines.append(f"   History: {p['History']}")
            lines.append("")  # Empty line for separation
        
        return '\n'.join(lines)
    
    def _count_patients(self, patients_csv_path: str) -> Dict[str, Any]:
        """Count total patients in the system"""
        try:
            df = pd.read_csv(patients_csv_path)
            total_count = len(df)
            
            if total_count == 0:
                return {
                    'status': 'no_data',
                    'message': 'No patient data found',
                    'count': 0
                }
            
            # Get age demographics
            avg_age = df['age'].mean() if 'age' in df else 0
            age_groups = {
                'Children (0-17)': len(df[df['age'] < 18]) if 'age' in df else 0,
                'Adults (18-64)': len(df[(df['age'] >= 18) & (df['age'] < 65)]) if 'age' in df else 0,
                'Seniors (65+)': len(df[df['age'] >= 65]) if 'age' in df else 0
            }
            
            formatted_response = f"""We have {total_count} patients in our system.

Demographics:
• Average age: {avg_age:.1f} years
• Children (0-17): {age_groups['Children (0-17)']} patients
• Adults (18-64): {age_groups['Adults (18-64)']} patients  
• Seniors (65+): {age_groups['Seniors (65+)']} patients"""
            
            return {
                'status': 'success',
                'message': f'We have {total_count} patients in total',
                'count': total_count,
                'demographics': age_groups,
                'avg_age': round(avg_age, 1),
                'formatted_response': formatted_response
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error counting patients: {str(e)}'
            }
    
    def _count_patients_by_condition(self, condition: str, patients_csv_path: str) -> Dict[str, Any]:
        """Count patients by specific medical condition"""
        try:
            df = pd.read_csv(patients_csv_path)
            
            if df.empty:
                return {
                    'status': 'no_data',
                    'message': 'No patient data found'
                }
            
            # Normalize condition search
            condition_lower = condition.lower()
            condition_mapping = {
                'diabetic': ['diabetes', 'diabetic'],
                'diabetes': ['diabetes', 'diabetic'], 
                'sugar': ['diabetes', 'diabetic', 'glucose', 'sugar'],  # Common term for diabetes
                'hypertension': ['hypertension', 'high blood pressure', 'high bp'],
                'high blood pressure': ['hypertension', 'high blood pressure', 'high bp'],
                'high bp': ['hypertension', 'high blood pressure', 'high bp'],
                'bp': ['hypertension', 'high blood pressure', 'high bp'],
                'heart disease': ['heart', 'cardiac', 'cardiovascular'],
                'heart': ['heart', 'cardiac', 'cardiovascular'],
                'kidney': ['kidney', 'renal', 'ckd'],
                'stroke': ['stroke', 'cerebral', 'brain'],
            }
            
            search_terms = condition_mapping.get(condition_lower, [condition_lower])
            
            # Search in condition and history columns
            matching_patients = df[
                df['condition'].str.contains('|'.join(search_terms), case=False, na=False) |
                df['history'].str.contains('|'.join(search_terms), case=False, na=False)
            ]
            
            count = len(matching_patients)
            total_patients = len(df)
            percentage = (count / total_patients * 100) if total_patients > 0 else 0
            
            if count == 0:
                return {
                    'status': 'not_found',
                    'message': f'No patients found with {condition}',
                    'count': 0
                }
            
            # Get sample patient names (first 5)
            sample_patients = matching_patients['name'].head(5).tolist()
            
            formatted_response = f"""Found {count} patients with {condition} ({percentage:.1f}% of total patients).

Sample patients:
{chr(10).join([f"• {name}" for name in sample_patients])}
{'...' if count > 5 else ''}

Total: {count} out of {total_patients} patients"""
            
            return {
                'status': 'success',
                'message': f'Found {count} patients with {condition}',
                'count': count,
                'total_patients': total_patients,
                'percentage': round(percentage, 1),
                'sample_patients': sample_patients,
                'formatted_response': formatted_response
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error counting patients with {condition}: {str(e)}'
            }
    
    def _list_patient_conditions(self, patients_csv_path: str) -> Dict[str, Any]:
        """List all medical conditions present in patient data"""
        try:
            df = pd.read_csv(patients_csv_path)
            
            if df.empty:
                return {
                    'status': 'no_data',
                    'message': 'No patient data found'
                }
            
            # Count conditions
            condition_counts = df['condition'].value_counts().to_dict()
            
            # Also check history for additional conditions
            history_conditions = {}
            for _, row in df.iterrows():
                if pd.notna(row['history']):
                    history = row['history'].lower()
                    for condition in ['diabetes', 'hypertension', 'heart disease', 'stroke', 'kidney disease', 'cancer']:
                        if condition in history:
                            history_conditions[condition] = history_conditions.get(condition, 0) + 1
            
            # Format response
            condition_lines = []
            for condition, count in sorted(condition_counts.items(), key=lambda x: x[1], reverse=True):
                condition_lines.append(f"• {condition}: {count} patients")
            
            if history_conditions:
                condition_lines.append("\nAdditional conditions from patient history:")
                for condition, count in sorted(history_conditions.items(), key=lambda x: x[1], reverse=True):
                    condition_lines.append(f"• {condition.title()}: {count} patients")
            
            formatted_response = f"Patient conditions in our system:\n\n" + '\n'.join(condition_lines)
            
            return {
                'status': 'success',
                'message': f'Found {len(condition_counts)} primary conditions',
                'primary_conditions': condition_counts,
                'history_conditions': history_conditions,
                'formatted_response': formatted_response
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error listing patient conditions: {str(e)}'
            }
    
    def _extract_risk_level(self, query: str) -> str:
        """Extract risk level from user query"""
        query_lower = query.lower()
        if 'critical' in query_lower or 'emergency' in query_lower:
            return 'CRITICAL'
        elif 'high' in query_lower:
            return 'HIGH'
        elif 'moderate' in query_lower:
            return 'MODERATE'
        elif 'low' in query_lower:
            return 'LOW'
        else:
            return 'CRITICAL'  # Default to critical for safety
    
    def _filter_patients_by_risk(self, risk_level: str, patients_csv_path: str) -> Dict[str, Any]:
        """Filter and display patients by risk level"""
        try:
            df = pd.read_csv(patients_csv_path)
            
            if df.empty:
                return {
                    'status': 'no_data',
                    'message': 'No patient data found',
                    'data': []
                }
            
            # Get all patients with risk assessment
            all_patients_data = []
            for _, row in df.iterrows():
                risk_info = self._assess_patient_risk(row)
                if risk_info['level'] == risk_level:
                    all_patients_data.append({
                        'Patient ID': row.get('patient_id', 'N/A'),
                        'Name': row.get('name', 'N/A'),
                        'Age': row.get('age', 'N/A'),
                        'Condition': row.get('condition', 'N/A'),
                        'Risk Level': risk_info['level'],
                        'Risk Score': risk_info['score'],
                        'Glucose': f"{row.get('glucose_mg_dL', 'N/A')} mg/dL" if pd.notna(row.get('glucose_mg_dL')) else 'N/A',
                        'BP': f"{row.get('bp_systolic', 'N/A')}/{row.get('bp_diastolic', 'N/A')}" if pd.notna(row.get('bp_systolic')) else 'N/A',
                        'History': (row.get('history', 'None')[:30] + '...') if len(str(row.get('history', ''))) > 30 else row.get('history', 'None'),
                        'Risk Factors': '; '.join(risk_info.get('factors', [])[:3])  # Show top 3 risk factors
                    })
            
            if not all_patients_data:
                return {
                    'status': 'not_found',
                    'message': f'No patients found with {risk_level} risk level',
                    'count': 0,
                    'suggestions': [
                        f"Try 'list patients' to see all patients",
                        f"Ask 'how many critical patients' to get counts",
                        f"Query 'high risk patients' for HIGH risk patients"
                    ]
                }
            
            total_patients = len(df)
            risk_count = len(all_patients_data)
            percentage = (risk_count / total_patients * 100) if total_patients > 0 else 0
            
            formatted_response = f"""{risk_level} Risk Patients: {risk_count} out of {total_patients} patients ({percentage:.1f}%)

Risk Assessment Criteria:
• CRITICAL: Score ≥70 (Severe hyperglycemia, hypertensive crisis, multiple comorbidities)
• HIGH: Score ≥45 (High glucose/BP, significant medical history)
• MODERATE: Score ≥25 (Elevated vitals, some risk factors)
• LOW: Score <25 (Stable vitals, minimal risk factors)

{risk_level} Patients Found: {risk_count}"""
            
            return {
                'status': 'success',
                'message': f'Found {risk_count} {risk_level} risk patients ({percentage:.1f}% of total)',
                'data': all_patients_data,
                'count': risk_count,
                'total_patients': total_patients,
                'percentage': round(percentage, 1),
                'risk_level': risk_level,
                'formatted_response': formatted_response
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error filtering patients by risk level: {str(e)}'
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
        """Handle complex queries using LLM with full backend awareness"""
        if not OLLAMA_AVAILABLE:
            return {
                'status': 'llm_unavailable',
                'message': f"LLM not available for query: '{query}'",
                'suggestions': ["Try: 'List physicians'", "Ask about available slots", "Request patient prioritization"]
            }
        
        try:
            # Build context about available backend data
            system_context = self._build_system_context()
            
            # Create LLM prompt with system context and user query
            prompt = f"""You are a healthcare system assistant with access to the following data and functions:

{system_context}

User Query: "{query}"

Your task:
1. Understand what the user is asking for
2. Identify the appropriate action from the available functions
3. Extract any parameters (physician names, dates, specialties, etc.)
4. Respond with a JSON object containing the action to take

Available Actions:
- "list_physicians" - show all physicians
- "physician_by_gender" - filter physicians by gender (extract gender parameter: male/female)
- "physician_specialties" - find physicians by specialty (extract specialty parameter)  
- "physician_count" - count physicians
- "available_slots" - show available slots (extract physician and date parameters)
- "slot_count" - count available slots
- "prioritize_patients" - prioritize patients for appointments
- "practitioner_info" - get detailed info about a physician
- "list_patients" - show all patients with risk assessment
- "patient_count" - count total patients in system
- "patient_by_risk" - filter patients by risk level (extract risk_level parameter: CRITICAL/HIGH/MODERATE/LOW)
- "patient_by_condition" - count patients with specific condition (extract condition parameter: diabetes/sugar/hypertension/heart/kidney/stroke)
- "patient_conditions" - list all medical conditions
- "help" - show help information

Response format (JSON only):
{{"action": "ACTION_NAME", "parameters": {{"param1": "value1", "param2": "value2"}}, "reasoning": "brief explanation"}}

If you can't identify a clear action, use "help" action."""

            # Call LLM
            try:
                from langchain_ollama.llms import OllamaLLM
                llm = OllamaLLM(
                    model="llama3", 
                    base_url="http://localhost:11434"
                )
                llm_response = llm.invoke(prompt)
                
                # Parse LLM response
                import json
                import re
                
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if json_match:
                    llm_instruction = json.loads(json_match.group(0))
                    
                    # Execute the identified action
                    action = llm_instruction.get('action', 'help')
                    params = llm_instruction.get('parameters', {})
                    
                    # Map LLM actions to internal handlers
                    return self._execute_llm_action(action, params, query, patients_csv_path)
                    
            except Exception as llm_error:
                print(f"LLM call failed: {llm_error}")
                # Fallback to intelligent pattern matching
                return self._intelligent_fallback_handler(query, patients_csv_path)
                
        except Exception as e:
            print(f"LLM query processing error: {e}")
            return self._intelligent_fallback_handler(query, patients_csv_path)
    
    def _build_system_context(self) -> str:
        """Build context about available system data for LLM"""
        context_parts = []
        
        # Get sample data for context
        practitioners = self.slot_manager.get_practitioners()
        if practitioners:
            specialties = list(set([p.specialty for p in practitioners]))
            sample_names = [p.name for p in practitioners[:3]]
            
            context_parts.extend([
                f"PHYSICIANS: {len(practitioners)} physicians available",
                f"SPECIALTIES: {', '.join(specialties)}",
                f"SAMPLE NAMES: {', '.join(sample_names)}"
            ])
        
        # Slot availability context
        today_slots = self.slot_manager.count_available_slots(target_date=date.today())
        context_parts.append(f"SLOTS: {today_slots} available slots today")
        
        # Add current date context
        context_parts.append(f"TODAY: {date.today()}")
        
        return "\n".join(context_parts)
    
    def _execute_llm_action(self, action: str, params: Dict[str, Any], original_query: str, patients_csv_path: str) -> Dict[str, Any]:
        """Execute action identified by LLM"""
        try:
            if action == "list_physicians":
                return self._list_physicians()
                
            elif action == "physician_specialties":
                specialty = params.get('specialty', '')
                if specialty:
                    return self._find_physicians_by_specialty(specialty)
                    
            elif action == "physician_count":
                return self._count_physicians()
                
            elif action == "physician_by_gender":
                gender = params.get('gender', 'male')
                return self._find_physicians_by_gender(gender)
                
            elif action == "available_slots":
                practitioner = params.get('physician', params.get('practitioner', ''))
                date_str = params.get('date', params.get('when', ''))
                return self._get_available_slots(practitioner, date_str)
                
            elif action == "slot_count":
                practitioner = params.get('physician', params.get('practitioner', ''))
                date_str = params.get('date', params.get('when', ''))
                return self._count_available_slots(practitioner, date_str)
                
            elif action == "prioritize_patients":
                practitioner = params.get('physician', params.get('practitioner', ''))
                date_str = params.get('date', params.get('when', ''))
                return self._prioritize_patients(practitioner, date_str, patients_csv_path)
                
            elif action == "practitioner_info":
                practitioner = params.get('physician', params.get('practitioner', params.get('name', '')))
                return self._get_practitioner_info(practitioner)
                
            elif action == "list_patients":
                return self._list_patients(patients_csv_path)
                
            elif action == "patient_count":
                return self._count_patients(patients_csv_path)
                
            elif action == "patient_by_risk":
                risk_level = params.get('risk_level', params.get('risk', 'CRITICAL')).upper()
                return self._filter_patients_by_risk(risk_level, patients_csv_path)
                
            elif action == "patient_by_condition":
                condition = params.get('condition', params.get('medical_condition', ''))
                return self._count_patients_by_condition(condition, patients_csv_path)
                
            elif action == "patient_conditions":
                return self._list_patient_conditions(patients_csv_path)
                
            else:
                return self._get_help()
                
        except Exception as e:
            return {
                'status': 'execution_error',
                'message': f"Error executing action '{action}': {str(e)}",
                'original_query': original_query
            }
    
    def _intelligent_fallback_handler(self, query: str, patients_csv_path: str) -> Dict[str, Any]:
        """Intelligent fallback when LLM fails - pattern matching with fuzzy logic"""
        query_lower = query.lower()
        
        # Fuzzy specialty matching
        practitioners = self.slot_manager.get_practitioners()
        specialties = [p.specialty.lower() for p in practitioners]
        
        for specialty in specialties:
            if specialty in query_lower or any(word in query_lower for word in specialty.split()):
                return self._find_physicians_by_specialty(specialty)
        
        # Fuzzy physician name matching
        for practitioner in practitioners:
            name_parts = practitioner.name.lower().split()
            if any(part in query_lower for part in name_parts):
                if 'slot' in query_lower or 'available' in query_lower:
                    return self._get_available_slots(practitioner.name, None)
                else:
                    return self._get_practitioner_info(practitioner.name)
        
        # Keyword-based fallback
        if any(word in query_lower for word in ['count', 'many', 'total', 'number']):
            if any(word in query_lower for word in ['physician', 'doctor']):
                return self._count_physicians()
            elif any(word in query_lower for word in ['slot', 'appointment']):
                return self._count_available_slots('', None)
        
        # Default fallback
        return {
            'status': 'not_understood',
            'message': f"I couldn't understand: '{query}'. Let me help you find what you need.",
            'suggestions': [
                "Try: 'Who are our endocrinologists?'",
                "Ask: 'Show me available slots for Dr. Smith'", 
                "Request: 'Prioritize patients for tomorrow'"
            ]
        }

# Convenience function
def create_chatbot() -> ChatbotEngine:
    """Create a chatbot instance"""
    return ChatbotEngine()
