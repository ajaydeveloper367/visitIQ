"""
Smart LLM Healthcare Chatbot - Data-Focused Approach
- LLM gets only relevant data for each query type
- Ensures LLM actually processes REAL data
- Focused prompts for reliable responses
"""

import pandas as pd
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class SmartLLMHealthcareChatbot:
    """Smart LLM approach - focused data processing"""
    
    def __init__(self, slot_manager, llm_client=None):
        self.slot_manager = slot_manager
        self.llm_client = llm_client
    
    def process_query(self, query: str, patients_csv_path: str = '') -> Dict[str, Any]:
        """Process query with focused LLM approach (vector/enhanced only)."""
        query = query.strip()
        
        if not query:
            return self._get_help()
        
        # Basic routing for efficiency
        if re.search(r'\b(?:help|usage)\b', query, re.IGNORECASE):
            return self._get_help()
        if re.search(r'^(?:hi|hello|hey)$', query, re.IGNORECASE):
            return self._get_greeting()
        
        # Smart query categorization and focused LLM processing
        return self._process_with_focused_llm(query, patients_csv_path)

    def _load_patients_df(self) -> pd.DataFrame:
        """Load patients from enhanced manager/vector DB (no CSV)."""
        try:
            # 1) Preferred: use enhanced patient manager (vector-first)
            try:
                # package-relative import when used from src
                from .enhanced_patient_manager import get_enhanced_patients_for_prioritization
            except Exception:
                # absolute import when src is on path
                from enhanced_patient_manager import get_enhanced_patients_for_prioritization
            enhanced_patients = get_enhanced_patients_for_prioritization()
            return pd.DataFrame(enhanced_patients)
        except Exception:
            pass

        # 2) Robust fallback: read vector DB metadatas.json directly (installed app path)
        try:
            import os, json
            candidates = [
                os.path.expanduser('~/.visitiq/app/chroma_db/metadatas.json'),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'chroma_db', 'metadatas.json')
            ]
            for mp in candidates:
                if os.path.exists(mp):
                    with open(mp, 'r', encoding='utf-8') as f:
                        metas = json.load(f)
                    patients_meta = [m for m in metas if m.get('type') == 'patient']
                    if patients_meta:
                        normalized = []
                        for m in patients_meta:
                            normalized.append({
                                'patient_id': str(m.get('patient_id', m.get('id', ''))).zfill(3),
                                'name': m.get('name', 'Unknown Patient'),
                                'age': int((m.get('age') or 50)),
                                'condition': m.get('condition', 'Unknown'),
                                'glucose_mg_dL': float(m.get('glucose_mg_dL') or 0),
                                'bp_systolic': float(m.get('bp_systolic') or 0),
                                'bp_diastolic': float(m.get('bp_diastolic') or 0),
                                'heart_rate': float(m.get('heart_rate') or 0),
                                'history': m.get('history', ''),
                                'notes': m.get('notes', '')
                            })
                        return pd.DataFrame(normalized)
        except Exception:
            pass

        # 3) Nothing found
        return pd.DataFrame([])
    
    def _process_with_focused_llm(self, query: str, patients_csv_path: str) -> Dict[str, Any]:
        """Process queries with LLM intelligence + fast data access"""
        try:
            # Get relevant data fast
            query_type, relevant_data = self._get_relevant_data(query, patients_csv_path)
            
            # LLM provides intelligent medical analysis and reasoning
            prompt = f"""You are an advanced medical AI with clinical reasoning capabilities. 

QUERY: "{query}"
DATA TYPE: {query_type}

REAL HEALTHCARE DATA:
{relevant_data}

MEDICAL AI INSTRUCTIONS:
🧠 USE YOUR MEDICAL INTELLIGENCE to:
1. Analyze clinical data with medical reasoning
2. Assess patient risk using medical knowledge 
3. Prioritize patients based on clinical severity
4. Provide evidence-based medical explanations
5. Consider multiple factors: vitals, age, history, conditions

📋 ONLY FALLBACK TO BASIC RULES if you cannot provide medical reasoning

For patient queries:
- Apply clinical judgment to risk assessment
- Consider interaction between conditions, vitals, and demographics  
- Explain WHY certain patients are higher risk
- Use medical terminology appropriately

Return JSON with your intelligent medical analysis:
{{
  "status": "success",
  "message": "Your clinical assessment summary", 
  "formatted_response": "Detailed medical reasoning and analysis",
  "query_type": "{query_type}",
  "medical_intelligence_used": true,
  "clinical_reasoning": "Your medical reasoning process"
}}

Provide your intelligent medical analysis now:"""

            # Get LLM analysis
            llm_response = self._query_llm(prompt)
            
            if llm_response:
                try:
                    # Extract JSON from LLM response
                    json_start = llm_response.find('{')
                    json_end = llm_response.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_text = llm_response[json_start:json_end]
                        result = json.loads(json_text)
                        
                        # Add structured data for app.py display
                        result = self._add_structured_data(result, query, query_type, patients_csv_path)
                        return result
                except json.JSONDecodeError:
                    pass
            
            # Fallback to intelligent parsing
            return self._intelligent_fallback(query, query_type, relevant_data, patients_csv_path)
                
        except Exception as e:
            logger.error(f"Smart processing error: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error processing query: {str(e)}',
                'suggestions': ['Try rephrasing your question', 'Ask for "help"']
            }
    
    def _parse_physician_data(self, relevant_data: str, query: str) -> Dict[str, Any]:
        """FAST physician data parsing - no LLM delays"""
        physicians_data = []
        lines = relevant_data.split('\n')[1:]  # Skip "PHYSICIANS:" header
        
        for line in lines:
            if line.strip() and '. ' in line:
                # Parse: "1. Dr. Joseph Johnson - Nephrology (Internal Medicine)"
                parts = line.split('. ', 1)[1].split(' - ')
                if len(parts) >= 2:
                    name = parts[0]
                    specialty_dept = parts[1]
                    if '(' in specialty_dept:
                        specialty = specialty_dept.split('(')[0].strip()
                        dept = specialty_dept.split('(')[1].replace(')', '').strip()
                    else:
                        specialty = specialty_dept.strip()
                        dept = specialty_dept.strip()
                    
                    physicians_data.append({
                        'Name': name,
                        'Specialty': specialty,
                        'Dept': dept
                    })
        
        return {
            'status': 'success',
            'message': f'Found {len(physicians_data)} physicians in our healthcare system',
            'data': physicians_data,
            'formatted_response': f'Healthcare team: {len(physicians_data)} physicians across multiple specialties.',
            'query_type': 'physician_query'
        }
    
    def _parse_patient_data(self, relevant_data: str, query: str, patients_csv_path: str) -> Dict[str, Any]:
        """FAST patient data parsing - structured response"""
        try:
            df = self._load_patients_df()
            query_lower = query.lower()
            
            # Filter based on query
            if 'critical' in query_lower:
                # Filter critical patients (glucose > 200 or bp > 140)
                critical_df = df[
                    (df['glucose_mg_dL'] > 200) | 
                    (df['bp_systolic'] > 140) | 
                    (df['condition'].str.contains('Critical', case=False, na=False))
                ]
                patients_data = []
                for _, row in critical_df.iterrows():
                    risk_level = 'CRITICAL' if row['glucose_mg_dL'] > 250 or row['bp_systolic'] > 160 else 'HIGH'
                    patients_data.append({
                        'Name': row['name'],
                        'Age': row['age'],
                        'Condition': row['condition'],
                        'Risk Level': risk_level,
                        'Glucose': f"{row['glucose_mg_dL']} mg/dL",
                        'BP': f"{row['bp_systolic']}/{row['bp_diastolic']}"
                    })
                
                return {
                    'status': 'success',
                    'message': f'Found {len(patients_data)} critical patients requiring immediate attention',
                    'data': patients_data,
                    'formatted_response': f'Critical Patient Alert: {len(patients_data)} patients need urgent care',
                    'query_type': 'patient_critical'
                }
            
            elif any(word in query_lower for word in ['diabetes', 'sugar', 'diabetic']):
                # Filter diabetic patients
                diabetic_df = df[df['condition'].str.contains('Diabetes', case=False, na=False)]
                patients_data = []
                for _, row in diabetic_df.iterrows():
                    patients_data.append({
                        'Name': row['name'],
                        'Age': row['age'],
                        'Condition': row['condition'],
                        'Glucose': f"{row['glucose_mg_dL']} mg/dL",
                        'Status': 'Controlled' if row['glucose_mg_dL'] < 140 else 'High'
                    })
                
                return {
                    'status': 'success',
                    'message': f'Found {len(patients_data)} diabetic patients',
                    'data': patients_data,
                    'formatted_response': f'Diabetic Patient Management: {len(patients_data)} patients monitored',
                    'query_type': 'patient_diabetes'
                }
            
            else:
                # General patient list
                patients_data = []
                for _, row in df.head(20).iterrows():  # Show first 20
                    risk_score = self._calculate_risk_score(row)
                    patients_data.append({
                        'Name': row['name'],
                        'Age': row['age'],
                        'Condition': row['condition'],
                        'Risk Score': risk_score,
                        'Glucose': f"{row['glucose_mg_dL']} mg/dL",
                        'BP': f"{row['bp_systolic']}/{row['bp_diastolic']}"
                    })
                
                return {
                    'status': 'success',
                    'message': f'Patient Database: {len(df)} total patients (showing first {len(patients_data)})',
                    'data': patients_data,
                    'formatted_response': f'Patient Overview: {len(patients_data)} patients displayed',
                    'query_type': 'patient_list'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Patient data error: {str(e)}',
                'formatted_response': 'Unable to load patient data. Please check data files.'
            }
    
    def _parse_scheduling_data(self, relevant_data: str, query: str) -> Dict[str, Any]:
        """FAST scheduling data parsing"""
        try:
            slots = self.slot_manager.get_available_slots()
            slots_data = []
            
            for slot in slots[:15]:  # Show first 15 slots
                slots_data.append({
                    'Date': slot.start.strftime('%Y-%m-%d'),
                    'Time': slot.start.strftime('%H:%M'),
                    'Duration': f"{slot.duration}min",
                    'Physician ID': slot.practitioner_id,
                    'Status': slot.status
                })
            
            return {
                'status': 'success',
                'message': f'Available Slots: {len(slots)} total appointments',
                'data': slots_data,
                'formatted_response': f'Scheduling Overview: {len(slots_data)} slots available',
                'query_type': 'scheduling'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Scheduling error: {str(e)}',
                'formatted_response': 'Unable to load scheduling data.'
            }
    
    def _parse_general_data(self, relevant_data: str, query: str) -> Dict[str, Any]:
        """FAST general system overview"""
        try:
            practitioners = self.slot_manager.get_practitioners()
            overview_data = []
            
            for p in practitioners:
                overview_data.append({
                    'Name': p.name,
                    'Specialty': p.specialty,
                    'Department': p.department,
                    'Type': 'Physician'
                })
            
            return {
                'status': 'success',
                'message': f'System Overview: {len(practitioners)} physicians available',
                'data': overview_data,
                'formatted_response': f'Healthcare System: {len(practitioners)} active physicians',
                'query_type': 'general'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'System error: {str(e)}',
                'formatted_response': 'Unable to load system data.'
            }

    # ===================== Department & Slots Enhancements =====================
    _DEPARTMENT_ALIASES = {
        'endocrinology': ['endocrinology', 'endocrinologist', 'diabetes'],
        'cardiology': ['cardiology', 'cardiologist', 'heart'],
        'neurology': ['neurology', 'neurologist', 'brain', 'stroke'],
        'orthopedics': ['orthopedics', 'orthopedic', 'bone', 'joint'],
        'pulmonology': ['pulmonology', 'pulmonary', 'respiratory', 'asthma', 'copd'],
        'nephrology': ['nephrology', 'renal', 'kidney'],
        'gastroenterology': ['gastroenterology', 'gi', 'stomach', 'liver'],
        'dermatology': ['dermatology', 'skin'],
        'oncology': ['oncology', 'cancer'],
        'pediatrics': ['pediatrics', 'children'],
        'gynecology': ['gynecology', 'obgyn', 'women'],
        'ophthalmology': ['ophthalmology', 'eye'],
        'psychiatry': ['psychiatry', 'mental'],
        'radiology': ['radiology', 'imaging'],
        'urology': ['urology', 'urinary'],
        'rheumatology': ['rheumatology'],
        'hematology': ['hematology', 'blood'],
        'infectious disease': ['infectious', 'id'],
        'otolaryngology': ['ent', 'otolaryngology']
    }

    def _detect_department(self, text: str) -> Optional[str]:
        q = text.lower()
        for dept, aliases in self._DEPARTMENT_ALIASES.items():
            if any(a in q for a in aliases):
                return dept
        return None

    def _parse_time_window(self, text: str):
        now = datetime.now()
        start = now
        q = text.lower()
        if 'tomorrow' in q:
            start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif 'month' in q:
            end = start + timedelta(days=30)
        elif 'week' in q or '7 days' in q:
            end = start + timedelta(days=7)
        elif 'today' in q:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        else:
            end = start + timedelta(days=7)
        return start, end
    
    def _calculate_risk_score(self, row) -> int:
        """Calculate patient risk score"""
        score = 0
        
        # Glucose risk
        glucose = row.get('glucose_mg_dL', 0)
        if glucose > 200:
            score += 40
        elif glucose > 140:
            score += 20
            
        # BP risk  
        bp_sys = row.get('bp_systolic', 0)
        if bp_sys > 140:
            score += 30
        elif bp_sys > 130:
            score += 15
            
        # Age risk
        age = row.get('age', 0)
        if age > 70:
            score += 20
        elif age > 60:
            score += 10
            
        return min(score, 100)
    
    def _add_structured_data(self, result: Dict[str, Any], query: str, query_type: str, patients_csv_path: str) -> Dict[str, Any]:
        """Add structured data based on query type for app.py display"""
        query_lower = query.lower()
        
        if query_type == "physician_query":
            practitioners = self.slot_manager.get_practitioners()
            
            # Filter based on specific query
            if any(term in query_lower for term in ['endocrinologist', 'endocrinology']):
                filtered = [p for p in practitioners if 'endocrinology' in p.specialty.lower()]
            elif any(term in query_lower for term in ['cardiologist', 'cardiology']):
                filtered = [p for p in practitioners if 'cardiology' in p.specialty.lower()]
            else:
                filtered = practitioners
                
            result['data'] = [{'Name': p.name, 'Specialty': p.specialty, 'Dept': p.department} for p in filtered]
            
        elif query_type == "patient_query":
            result['data'] = self._get_patient_structured_data(query, patients_csv_path)
            
        return result
    
    def _get_patient_structured_data(self, query: str, patients_csv_path: str) -> List[Dict[str, Any]]:
        """Get structured patient data using batch RAG so counts match the header refresh (vector-first)."""
        try:
            # Vector-first patient load
            df = self._load_patients_df()
            print(f"✅ Chatbot using ENHANCED patients: {len(df)} total (vector/doc)")

            if df is None or df.empty:
                return []

            query_lower = query.lower()

            # Batch LLM prioritization for ALL rows (fast + consistent)
            try:
                try:
                    from .prioritizer import rag_prioritize_batch, rule_based_priority_row
                except Exception:
                    from prioritizer import rag_prioritize_batch, rule_based_priority_row
            except Exception:
                rag_prioritize_batch = None
                from prioritizer import rule_based_priority_row  # type: ignore

            rows = df.to_dict(orient='records')
            if rag_prioritize_batch is not None:
                try:
                    batch_results = rag_prioritize_batch(rows)
                except Exception:
                    batch_results = [rule_based_priority_row(r) for r in rows]
            else:
                batch_results = [rule_based_priority_row(r) for r in rows]

            # Build patient table
            all_patients_data: List[Dict[str, Any]] = []
            for row, pr in zip(rows, batch_results):
                reasons = pr.get('reasons') or []
                source = pr.get('reasoning_source') or '🧠 LLM Medical Analysis'
                all_patients_data.append({
                    'Patient ID': row.get('patient_id'),
                    'Name': row.get('name'),
                    'Age': row.get('age'),
                    'Condition': row.get('condition'),
                    'Risk Level': pr.get('priority_level'),
                    'Risk Score': pr.get('score'),
                    'Medical Reasons': ', '.join(reasons) if isinstance(reasons, list) else str(reasons),
                    'Glucose': f"{row.get('glucose_mg_dL', '')} mg/dL",
                    'BP': f"{row.get('bp_systolic', '')}/{row.get('bp_diastolic', '')}",
                    'History': row.get('history', 'No history'),
                    'Reasoning Source': source
                })

            # Sort by medical priority then score
            priority_order = {'Emergency': 4, 'High': 3, 'Medium': 2, 'Low': 1}
            all_patients_data.sort(
                key=lambda x: (
                    priority_order.get(x.get('Risk Level'), 0),
                    -int(x.get('Risk Score') or 0)
                ),
                reverse=True
            )

            # Apply query filtering after sorting
            def include(rec: Dict[str, Any]) -> bool:
                if 'critical' in query_lower:
                    return rec.get('Risk Level') in ['Emergency', 'High']
                if any(w in query_lower for w in ['diabetic', 'diabetes', 'sugar']):
                    return 'diabetes' in str(rec.get('Condition', '')).lower()
                return True

            patients_data = [rec for rec in all_patients_data if include(rec)]
            return patients_data

        except Exception as e:
            logger.error(f"Patient data error: {str(e)}")
            return []
    
    def _intelligent_fallback(self, query: str, query_type: str, relevant_data: str, patients_csv_path: str) -> Dict[str, Any]:
        """Intelligent fallback when LLM fails"""
        query_lower = query.lower()
        
        if query_type == "physician_query":
            practitioners = self.slot_manager.get_practitioners()
            
            # Specific filtering
            if any(term in query_lower for term in ['endocrinologist', 'endocrinology']):
                filtered = [p for p in practitioners if 'endocrinology' in p.specialty.lower()]
                message = f"Found {len(filtered)} endocrinologist{'s' if len(filtered) != 1 else ''}"
                response = f"Endocrinology specialists: {len(filtered)} physician{'s' if len(filtered) != 1 else ''} available"
            elif 'how many' in query_lower or 'count' in query_lower:
                message = f"We have {len(practitioners)} physicians total"
                response = f"Physician count: {len(practitioners)} doctors across {len(set(p.specialty for p in practitioners))} specialties"
                filtered = practitioners
            else:
                filtered = practitioners
                message = f"Found {len(filtered)} physicians in our healthcare system"
                response = f"Healthcare team: {len(filtered)} physicians across multiple specialties"
                
            return {
                'status': 'success',
                'message': message,
                'formatted_response': response,
                'data': [{'Name': p.name, 'Specialty': p.specialty, 'Dept': p.department} for p in filtered],
                'query_type': query_type
            }
            
        elif query_type == "patient_query":
            try:
                # FIXED: Use enhanced patient manager for consistent patient count
                try:
                    import sys
                    import os
                    
                    # Add the root src directory to Python path
                    root_src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
                    if root_src_path not in sys.path:
                        sys.path.append(root_src_path)
                    
                    from enhanced_patient_manager import get_enhanced_patients_for_prioritization
                    enhanced_patients = get_enhanced_patients_for_prioritization()
                    df = pd.DataFrame(enhanced_patients)
                    print(f"✅ Patient query using ENHANCED patients: {len(df)} total")
                except Exception as e:
                    df = self._load_patients_df()
                
                if 'how many' in query_lower or 'count' in query_lower:
                    message = f"We have {len(df)} patients total in our system"
                    response = f"Patient database: {len(df)} total patients with {len(df[df['condition'].str.contains('Diabetes', case=False, na=False)])} diabetic, {len(df[df['bp_systolic'] > 140])} hypertensive"
                else:
                    patients_data = self._get_patient_structured_data(query, patients_csv_path)
                    if 'critical' in query_lower:
                        critical_count = len([p for p in patients_data if p['Risk Level'] in ['Emergency', 'High']])
                        message = f"Found {critical_count} critical patients requiring immediate attention"
                        response = f"Critical patient alert: {critical_count} patients with high-risk medical conditions need urgent care"
                    else:
                        message = f"Patient database: {len(df)} total patients"
                        response = f"Patient overview: showing patient records with detailed medical assessments"
                
                return {
                    'status': 'success',
                    'message': message,
                    'formatted_response': response,
                    'data': self._get_patient_structured_data(query, patients_csv_path),
                    'query_type': query_type
                }
                
            except Exception as e:
                return {
                    'status': 'error',
                    'message': f'Patient data error: {str(e)}',
                    'formatted_response': 'Unable to access patient database'
                }
        
        # Default fallback
        return {
            'status': 'success',
            'message': 'Query processed',
            'formatted_response': relevant_data,
            'query_type': query_type
        }
    
    def _get_relevant_data(self, query: str, patients_csv_path: str) -> tuple[str, str]:
        """Get only relevant data for the specific query"""
        query_lower = query.lower()
        
        # Physician-related queries
        if any(word in query_lower for word in ['physician', 'doctor', 'specialist', 'cardiologist', 'endocrinologist']):
            practitioners = self.slot_manager.get_practitioners()
            data = "PHYSICIANS:\n"
            for i, p in enumerate(practitioners, 1):
                data += f"{i}. {p.name} - {p.specialty} ({p.department})\n"
            return "physician_query", data
        
        # Patient-related queries
        elif any(word in query_lower for word in ['patient', 'critical', 'diabetes', 'sugar', 'bp', 'blood pressure', 'heart']):
            try:
                df = self._load_patients_df()
                data = f"PATIENTS (Total: {len(df)}):\n"
                
                # Include relevant patient details
                for _, row in df.head(10).iterrows():  # Limit to prevent overload
                    data += f"Patient {row.get('patient_id', 'N/A')}: {row.get('name', 'N/A')} | "
                    data += f"Age: {row.get('age', 'N/A')} | "
                    data += f"Condition: {row.get('condition', 'N/A')} | "
                    data += f"Glucose: {row.get('glucose_mg_dL', 'N/A')} mg/dL | "
                    data += f"BP: {row.get('bp_systolic', 'N/A')}/{row.get('bp_diastolic', 'N/A')}\n"
                
                if len(df) > 10:
                    data += f"... and {len(df) - 10} more patients\n"
                
                return "patient_query", data
            except Exception as e:
                return "patient_query", f"Patient data error: {str(e)}"
        
        # Scheduling/slot queries
        elif any(word in query_lower for word in ['slot', 'appointment', 'schedule', 'available']):
            try:
                slots = self.slot_manager.get_available_slots()
                data = f"AVAILABLE SLOTS (Total: {len(slots)}):\n"
                for slot in slots[:10]:  # Show first 10
                    data += f"Slot: {slot.start.strftime('%Y-%m-%d %H:%M')} | "
                    data += f"Physician ID: {slot.practitioner_id} | "
                    data += f"Duration: {slot.duration}min\n"
                return "scheduling_query", data
            except Exception as e:
                return "scheduling_query", f"Scheduling data error: {str(e)}"
        
        # Default - mixed query
        else:
            practitioners = self.slot_manager.get_practitioners()
            data = f"SYSTEM OVERVIEW:\n"
            data += f"Physicians: {len(practitioners)} total\n"
            for p in practitioners[:5]:
                data += f"- {p.name} ({p.specialty})\n"
            
            try:
                df = self._load_patients_df()
                data += f"\nPatients: {len(df)} total\n"
                data += f"Sample conditions: {', '.join(df['condition'].unique()[:5])}\n"
            except:
                data += "\nPatient data unavailable\n"
            
            return "general_query", data
    
    def _query_llm(self, prompt: str) -> Optional[str]:
        """Query LLM with focused prompt for intelligent responses"""
        try:
            if self.llm_client and hasattr(self.llm_client, 'chat'):
                response = self.llm_client.chat(
                    model="llama3",
                    messages=[{"role": "user", "content": prompt}],
                    stream=False,
                    options={"temperature": 0.1, "top_p": 0.9, "num_ctx": 4096}
                )
                
                if hasattr(response, 'message') and hasattr(response.message, 'content'):
                    return response.message.content.strip()
                else:
                    return str(response).strip()
            return None
        except Exception as e:
            logger.error(f"LLM query error: {str(e)}")
            return None
    
    def _get_help(self) -> Dict[str, Any]:
        """Help response"""
        return {
            'status': 'success',
            'message': 'Smart LLM Healthcare Assistant',
            'formatted_response': '''🤖 Smart Healthcare Assistant

💬 ASK NATURALLY:
• "List all physicians"
• "Show critical patients" 
• "Find diabetic patients"
• "Available cardiologists"
• "Who needs urgent care?"

🧠 POWERED BY REAL DATA:
✅ Live physician database
✅ Real patient records
✅ Actual appointment slots
✅ Medical intelligence

💡 Just ask - I process real data!'''
        }
    
    def _get_greeting(self) -> Dict[str, Any]:
        """Greeting response"""
        return {
            'status': 'success',
            'message': 'Hello! Smart healthcare assistant ready.',
            'formatted_response': '👋 Hi! I can analyze real patient and physician data. What would you like to know?'
        }


# Factory function
def create_chatbot(slot_manager, llm_client=None):
    """Create smart LLM healthcare chatbot"""
    return SmartLLMHealthcareChatbot(slot_manager, llm_client)
