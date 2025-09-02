"""
Smart LLM Healthcare Chatbot - Data-Focused Approach
- LLM gets only relevant data for each query type
- Ensures LLM actually processes REAL data
- Focused prompts for reliable responses
"""

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
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """Process query with focused LLM approach"""
        query = query.strip()
        
        if not query:
            return self._get_help()
        
        # Basic routing for efficiency
        if re.search(r'\b(?:help|usage)\b', query, re.IGNORECASE):
            return self._get_help()
        if re.search(r'^(?:hi|hello|hey)$', query, re.IGNORECASE):
            return self._get_greeting()
        
        # Smart query categorization and focused LLM processing
        return self._process_with_focused_llm(query)

    def _normalize_text(self, text: str) -> str:
        """Lowercase and remove non-letters for robust matching."""
        return re.sub(r'[^a-z]', '', text.lower())

    def _detect_specialty_from_query(self, query_lower: str) -> Optional[str]:
        """Detect canonical specialty from the query (handles variants like 'ortho pedic')."""
        qn = self._normalize_text(query_lower)
        # Common specialties and aliases
        specialties = [
            ("endocrinology", ["endocrinology", "endocrinologist", "endocrine"]),
            ("cardiology", ["cardiology", "cardiologist", "cardiac"]),
            ("orthopedic", [
                "orthopedic", "orthopaedic", "orthopedics", "orthopaedics", "ortho"
            ]),
            ("neurology", ["neurology", "neurologist", "neuro"]),
            ("nephrology", ["nephrology", "nephrologist", "nephro"]),
            ("dermatology", ["dermatology", "dermatologist", "derma"]),
            ("gastroenterology", ["gastroenterology", "gastroenterologist", "gastro"]),
            ("pediatrics", ["pediatrics", "pediatrician", "paediatrics", "paediatrician"]),
            ("familymedicine", ["familymedicine", "family", "primarycare"]),
            ("internalmedicine", ["internalmedicine", "internal"]),
        ]
        for canonical, aliases in specialties:
            for alias in aliases:
                if self._normalize_text(alias) in qn:
                    return canonical
        # Generic fallbacks for *ology
        if "ology" in qn:
            return None
        # Heuristic: detect 'orthop' root
        if "orthop" in qn:
            return "orthopedic"
        return None

    def _detect_specialties_from_query(self, query: str) -> List[str]:
        """Detect one or more specialties from the query using aliases and live data.
        Returns canonical strings suitable for matching against practitioner.specialty.
        """
        qn = self._normalize_text(query)
        ql = query.lower()
        # Tokenize on letters for boundary-aware matching (prevents 'ent' in 'patients')
        q_tokens = set(re.findall(r'[a-z]+', ql))
        # Static alias map (broad coverage)
        alias_map = {
            'cardiology': ['cardiology', 'cardiologist', 'cardiac', 'cardio'],
            'endocrinology': ['endocrinology', 'endocrinologist', 'endocrine', 'endo'],
            'orthopedic': ['orthopedic', 'orthopaedic', 'orthopedics', 'orthopaedics', 'ortho', 'orthop'],
            'neurology': ['neurology', 'neurologist', 'neuro'],
            'nephrology': ['nephrology', 'nephrologist', 'nephro'],
            'dermatology': ['dermatology', 'dermatologist', 'derma', 'skin'],
            'gastroenterology': ['gastroenterology', 'gastroenterologist', 'gastro', 'gi'],
            'pediatrics': ['pediatrics', 'pediatrician', 'paediatrics', 'paediatrician', 'peds'],
            'family medicine': ['familymedicine', 'family', 'primarycare', 'fm'],
            'internal medicine': ['internalmedicine', 'internal', 'im'],
            'otolaryngology': ['otolaryngology', 'ent'],
            'psychiatry': ['psychiatry', 'psychiatrist', 'psych'],
            'pulmonology': ['pulmonology', 'pulmonary', 'pulmo', 'respiratory'],
            'rheumatology': ['rheumatology', 'rheumatologist', 'rheum'],
            'hematology': ['hematology', 'heme'],
            'oncology': ['oncology', 'oncologist', 'onco', 'cancer'],
            'urology': ['urology', 'urologist', 'uro'],
            'ophthalmology': ['ophthalmology', 'ophthalmologist', 'optho', 'eye'],
            'obstetrics and gynecology': ['obgyn', 'ob/gyn', 'obstetrics', 'gynecology', 'gynecologist'],
            'allergy and immunology': ['allergy', 'immunology', 'allergist', 'immunologist'],
            'geriatrics': ['geriatrics', 'geriatric'],
            'infectious disease': ['infectiousdisease', 'id', 'infection'],
            'pain medicine': ['pain', 'painmedicine'],
            'sports medicine': ['sports', 'sportsmedicine'],
            'emergency medicine': ['emergency', 'er', 'ed', 'emergencymedicine'],
        }
        detected: List[str] = []
        # Alias matching with token awareness and safe substring fallback for longer aliases
        for canonical, aliases in alias_map.items():
            for alias in aliases:
                alias_tokens = re.findall(r'[a-z]+', alias.lower())
                if alias_tokens:
                    if len(alias_tokens) == 1:
                        if alias_tokens[0] in q_tokens:
                            detected.append(canonical)
                            break
                    else:
                        if all(tok in q_tokens for tok in alias_tokens):
                            detected.append(canonical)
                            break
                # Safe normalized substring fallback only for aliases length >=4
                norm_alias = self._normalize_text(alias)
                if len(norm_alias) >= 4 and norm_alias in qn:
                    detected.append(canonical)
                    break
        # Dynamic matching against live practitioner specialties
        try:
            practitioners = self.slot_manager.get_practitioners()
            for p in practitioners:
                spec = getattr(p, 'specialty', '')
                if not spec:
                    continue
                spec_norm = self._normalize_text(spec)
                # token-wise match: if any token of specialty appears in query
                tokens = [t for t in re.split(r'[^a-z]+', spec_norm) if t]
                if any(t and t in qn for t in tokens):
                    if spec.lower() not in detected:
                        detected.append(spec.lower())
        except Exception:
            pass
        # Deduplicate while preserving order
        result: List[str] = []
        seen = set()
        for s in detected:
            if s not in seen:
                seen.add(s)
                result.append(s)
        return result

    def _detect_requested_risk_levels(self, query: str) -> List[str]:
        """Detect requested patient risk levels from query (robust to typos).
        Returns a list of risk levels to include among: 'Emergency','High','Medium','Low'.
        Empty list means no explicit filter requested.
        """
        ql = query.lower()
        qn = self._normalize_text(query)
        requested: List[str] = []
        # Emergency (handles 'emergency', 'emergnecy', 'emerg', 'urgent')
        if ('emerg' in qn) or ('urgent' in ql):
            requested.append('Emergency')
        # Critical → Emergency + High
        if 'critic' in qn:  # matches 'critical'
            if 'Emergency' not in requested:
                requested.append('Emergency')
            requested.append('High')
        # High risk
        if ('highrisk' in qn) or (('high' in ql) and ('risk' in ql)):
            requested.append('High')
        # Medium risk
        if 'medium' in ql:
            requested.append('Medium')
        # Low risk
        if 'low' in ql:
            requested.append('Low')
        # Deduplicate preserving order
        seen = set()
        ordered = []
        for r in requested:
            if r not in seen:
                seen.add(r)
                ordered.append(r)
        return ordered

    def _extract_simple_date(self, query: str) -> Optional[datetime.date]:
        """Extract a simple date reference from query. Supports 'today'."""
        ql = query.lower()
        if 'today' in ql:
            from datetime import date as _date
            return _date.today()
        return None
    
    def _process_with_focused_llm(self, query: str) -> Dict[str, Any]:
        """Process queries with LLM intelligence + fast data access"""
        try:
            # Get relevant data fast
            query_type, relevant_data = self._get_relevant_data(query)
            
            # Retrieve knowledge snippets from local vector DB (RAG)
            rag_snippets = self._retrieve_similar_docs(query, k=4)
            snippets_text = "\n\n---\n\n".join(rag_snippets) if rag_snippets else ""
            
            # LLM provides intelligent medical analysis and reasoning
            prompt = f"""You are an advanced medical AI with clinical reasoning capabilities. 

QUERY: "{query}"
DATA TYPE: {query_type}

REAL HEALTHCARE DATA:
{relevant_data}

KNOWLEDGE SNIPPETS (vector DB):
{snippets_text}

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
                        result = self._add_structured_data(result, query, query_type)
                        return result
                except json.JSONDecodeError:
                    pass
            
            # Fallback to intelligent parsing
            return self._intelligent_fallback(query, query_type, relevant_data)
                
        except Exception as e:
            logger.error(f"Smart processing error: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error processing query: {str(e)}',
                'suggestions': ['Try rephrasing your question', 'Ask for "help"']
            }

    def _retrieve_similar_docs(self, query_text: str, k: int = 3) -> List[str]:
        """Query local vector DB under chroma_db/ and return top-k doc texts."""
        # Strategy:
        # 1) Try persisted ChromaDB store (duckdb+parquet) using query_embeddings
        # 2) Fallback to lightweight numpy+sklearn index over docs.json/embeddings.npy
        # 3) If both unavailable, return []
        try:
            import os
            from typing import Optional
            # SentenceTransformer for query embeddings
            try:
                from sentence_transformers import SentenceTransformer as _ST
            except Exception:
                _ST = None  # Will trigger fallback below

            # Attempt ChromaDB first if available
            try:
                import chromadb
                from chromadb.config import Settings as _ChromaSettings
                if _ST is not None:
                    base_dir = os.getenv('CHROMA_DIR', 'chroma_db')
                    client = chromadb.Client(_ChromaSettings(chroma_db_impl="duckdb+parquet", persist_directory=base_dir))

                    # Pick collection: env override -> named common -> first available
                    collection_name: Optional[str] = os.getenv('VISITIQ_CHROMA_COLLECTION')
                    if collection_name is None:
                        # Prefer commonly used names if present
                        available = [c.name for c in client.list_collections()]
                        preferred = ['visitiq_docs', 'medical_knowledge', 'knowledge_base']
                        found = next((n for n in preferred if n in available), None)
                        collection_name = found or (available[0] if available else None)

                    if collection_name:
                        coll = client.get_collection(collection_name)
                        # Build embedding for the query and ask Chroma to return similar docs
                        model = _ST('all-MiniLM-L6-v2')
                        q_emb = model.encode([query_text], show_progress_bar=False)
                        results = coll.query(query_embeddings=q_emb, n_results=max(1, k))
                        docs = results.get('documents') or []
                        if isinstance(docs, list) and len(docs) > 0:
                            return [d for d in docs[0] if isinstance(d, str)]
            except Exception:
                # If Chroma path fails, continue to numpy fallback
                pass

            # Fallback: numpy + sklearn over local files
            try:
                import json as _json
                import numpy as _np
                from sklearn.neighbors import NearestNeighbors as _NN

                base_dir = os.getenv('CHROMA_DIR', 'chroma_db')
                docs_path = os.path.join(base_dir, 'docs.json')
                emb_path = os.path.join(base_dir, 'embeddings.npy')
                if not (os.path.exists(docs_path) and os.path.exists(emb_path)):
                    return []

                with open(docs_path, 'r') as f:
                    docs = _json.load(f)
                emb = _np.load(emb_path)
                if not isinstance(docs, list) or emb is None or len(docs) == 0:
                    return []

                if _ST is None:
                    return []
                model = _ST('all-MiniLM-L6-v2')
                q_emb = model.encode([query_text], show_progress_bar=False)
                nn = _NN(n_neighbors=min(k, len(docs)), metric='cosine')
                nn.fit(emb)
                _, idxs = nn.kneighbors(q_emb, return_distance=True)
                idxs = idxs[0].tolist()
                return [docs[i] for i in idxs]
            except Exception:
                return []
        except Exception:
            return []
    
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
    
    def _parse_patient_data(self, relevant_data: str, query: str) -> Dict[str, Any]:
        """Vector-only: return knowledge snippets as formatted_response, no CSV usage."""
        snippets = self._retrieve_similar_docs(query, k=10)
        return {
            'status': 'success',
            'message': 'Patient query processed using vector knowledge only',
            'data': [],
            'formatted_response': "\n---\n".join(snippets) if snippets else 'No relevant knowledge snippets found.',
            'query_type': 'patient_query'
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
    
    def _add_structured_data(self, result: Dict[str, Any], query: str, query_type: str) -> Dict[str, Any]:
        """Add structured data based on query type for app.py display"""
        query_lower = query.lower()
        
        if query_type == "physician_query":
            # Vector-only physician listing
            detected_list = self._detect_specialties_from_query(query)
            vector_docs = self._list_physicians_from_vector(detected_list)
            result['data'] = vector_docs
            label = ", ".join(detected_list) if detected_list else "physicians"
            result['formatted_response'] = f"Found {len(vector_docs)} {label} in knowledge base."
            
        elif query_type == "patient_query":
            # If user asks for available/scheduled patients:
            ql = query.lower()
            if any(k in ql for k in [
                'available patients', 'available patient', 'patients available', 'available ptients',
                'scheduled patients', 'patients scheduled', 'patients today', 'today'
            ]):
                try:
                    target_date = self._extract_simple_date(query)
                    # If NOT today-specific, list ALL patients from vector DB (per requirement)
                    if not target_date and ('available patients' in ql or 'available patient' in ql or 'patients available' in ql):
                        patients_kb = self._list_patients_from_vector()
                        result['data'] = patients_kb
                        result['formatted_response'] = f"Found {len(patients_kb)} patients in the system."
                        result['message'] = result['formatted_response']
                        result['status'] = 'success'
                        return result
                    from .fhir_models import AppointmentStatus as _ApptStatus
                    appts = self.slot_manager.get_appointments(target_date=target_date)
                    # Consider only booked appointments
                    appts = [a for a in appts if getattr(a, 'status', None) == _ApptStatus.BOOKED]
                    rows: List[Dict[str, Any]] = []
                    for a in appts:
                        rows.append({
                            'Time': a.start.strftime('%Y-%m-%d %H:%M'),
                            'Patient': a.patient_name,
                            'Practitioner': a.practitioner_name,
                            'Reason': a.reason_code.replace('-', ' ').title() if isinstance(a.reason_code, str) else '',
                            'Status': str(a.status.name if hasattr(a.status, 'name') else a.status)
                        })
                    # If no scheduled patients found, show all patients from vector DB as fallback
                    if not rows:
                        patients_kb = self._list_patients_from_vector()
                        result['data'] = patients_kb
                        if target_date:
                            result['formatted_response'] = f"No patients scheduled today. Showing {len(patients_kb)} patients from knowledge base."
                        else:
                            result['formatted_response'] = f"No patients scheduled in the system. Showing {len(patients_kb)} patients from knowledge base."
                        result['message'] = result['formatted_response']
                        result['status'] = 'success'
                        return result
                    # Otherwise return scheduled rows
                    result['data'] = rows
                    # Always override with a clear, non-LLM summary and return immediately
                    if target_date:
                        result['formatted_response'] = f"Found {len(rows)} patients scheduled today."
                    else:
                        result['formatted_response'] = f"Found {len(rows)} patients scheduled in the system."
                    result['message'] = result['formatted_response']
                    result['status'] = 'success'
                    return result
                except Exception:
                    result['data'] = []
                    result['formatted_response'] = "No patients found."
                    result['message'] = result['formatted_response']
                    result['status'] = 'success'
                    return result
            else:
                # Respect vector-only directive for other patient queries
                result['data'] = []
            
        elif query_type == "scheduling_query":
            # Vector-only physician list when user mentions doctors in scheduling context
            if any(w in query_lower for w in ['doctor', 'physician', 'specialist']):
                detected_list = self._detect_specialties_from_query(query)
                vector_docs = self._list_physicians_from_vector(detected_list)
                result['data'] = vector_docs
                result['formatted_response'] = f"Found {len(vector_docs)} physicians for scheduling context."
        
        return result

    def _list_physicians_from_vector(self, detected_specialties: List[str]) -> List[Dict[str, Any]]:
        """Try listing physicians from a Chroma collection or docs.json when slot data is empty.
        Expected collection name from env VISITIQ_PHYSICIANS_COLLECTION or fallbacks.
        Returns a list of dicts with keys: Name, Specialty, Dept when possible.
        """
        try:
            import os
            # Try Chroma collection with physician metadata
            try:
                import chromadb
                from chromadb.config import Settings as _ChromaSettings
                base_dir = os.getenv('CHROMA_DIR', 'chroma_db')
                client = chromadb.Client(_ChromaSettings(chroma_db_impl="duckdb+parquet", persist_directory=base_dir))
                cname = os.getenv('VISITIQ_PHYSICIANS_COLLECTION')
                if cname is None:
                    available = [c.name for c in client.list_collections()]
                    preferred = ['physicians', 'doctors', 'providers']
                    found = next((n for n in preferred if n in available), None)
                    cname = found or (available[0] if available else None)
                if cname:
                    coll = client.get_collection(cname)
                    # Pull all ids in small batches
                    # If metadatas contain name/specialty/department, use them
                    results = coll.get()  # may return all
                    docs = []
                    metas = results.get('metadatas') or []
                    for md in metas:
                        if not isinstance(md, dict):
                            continue
                        name = md.get('name') or md.get('Name')
                        spec = md.get('specialty') or md.get('Specialty')
                        dept = md.get('department') or md.get('Dept') or md.get('Department')
                        if name and spec:
                            docs.append({'Name': name, 'Specialty': spec, 'Dept': dept or ''})
                    # Optional specialty filter
                    if detected_specialties:
                        def _norm(s: str) -> str:
                            return self._normalize_text(s or '')
                        dns = {_norm(d) for d in detected_specialties}
                        docs = [d for d in docs if any(dn in _norm(d.get('Specialty')) for dn in dns)]
                    return docs
            except Exception:
                pass
            # Fallback: parse docs.json lines heuristically if present
            try:
                import json as _json
                base_dir = os.getenv('CHROMA_DIR', 'chroma_db')
                docs_path = os.path.join(base_dir, 'docs.json')
                if os.path.exists(docs_path):
                    with open(docs_path, 'r') as f:
                        items = _json.load(f)
                    docs: List[Dict[str, Any]] = []
                    for it in items if isinstance(items, list) else []:
                        if isinstance(it, dict) and {'name', 'specialty'} <= set(k.lower() for k in it.keys()):
                            name = it.get('name') or it.get('Name')
                            spec = it.get('specialty') or it.get('Specialty')
                            dept = it.get('department') or it.get('Dept')
                            docs.append({'Name': name, 'Specialty': spec, 'Dept': dept or ''})
                    if detected_specialties:
                        def _norm(s: str) -> str:
                            return self._normalize_text(s or '')
                        dns = {_norm(d) for d in detected_specialties}
                        docs = [d for d in docs if any(dn in _norm(d.get('Specialty')) for dn in dns)]
                    return docs
            except Exception:
                pass
            return []
        except Exception:
            return []

    def _list_patients_from_vector(self) -> List[Dict[str, Any]]:
        """List patients using vector knowledge base when no scheduled patients are found.
        Tries to extract simple patient records (Name, Condition) from metadatas or docs.json.
        """
        try:
            import os
            # Try Chroma collection likely to contain patients
            try:
                import chromadb
                from chromadb.config import Settings as _ChromaSettings
                base_dir = os.getenv('CHROMA_DIR', 'chroma_db')
                client = chromadb.Client(_ChromaSettings(chroma_db_impl="duckdb+parquet", persist_directory=base_dir))
                preferred = [
                    os.getenv('VISITIQ_PATIENTS_COLLECTION') or '',
                    'patients', 'patient_records', 'kb_patients'
                ]
                available = [c.name for c in client.list_collections()]
                cname = next((n for n in preferred if n and n in available), None) or (available[0] if available else None)
                if cname:
                    coll = client.get_collection(cname)
                    results = coll.get()
                    docs = []
                    metas = results.get('metadatas') or []
                    for md in metas:
                        if not isinstance(md, dict):
                            continue
                        name = md.get('name') or md.get('patient_name') or md.get('Name')
                        cond = md.get('condition') or md.get('Condition')
                        if name:
                            docs.append({'Patient': name, 'Condition': cond or ''})
                    return docs[:100]
            except Exception:
                pass
            # Fallback docs.json
            try:
                import json as _json
                base_dir = os.getenv('CHROMA_DIR', 'chroma_db')
                docs_path = os.path.join(base_dir, 'docs.json')
                if os.path.exists(docs_path):
                    with open(docs_path, 'r') as f:
                        items = _json.load(f)
                    docs: List[Dict[str, Any]] = []
                    for it in items if isinstance(items, list) else []:
                        if isinstance(it, dict) and ('name' in it or 'patient_name' in it):
                            name = it.get('patient_name') or it.get('name') or it.get('Name')
                            cond = it.get('condition') or it.get('Condition')
                            docs.append({'Patient': name, 'Condition': cond or ''})
                    return docs[:100]
            except Exception:
                pass
            return []
        except Exception:
            return []
    
    def _get_patient_structured_data(self, query: str) -> List[Dict[str, Any]]:
        """Vector-only: no CSV; return empty list or build from vector if needed."""
        return []
    
    def _intelligent_fallback(self, query: str, query_type: str, relevant_data: str) -> Dict[str, Any]:
        """Intelligent fallback when LLM fails"""
        query_lower = query.lower()
        
        if query_type == "physician_query":
            practitioners = self.slot_manager.get_practitioners()
            
            # Specific filtering
            detected_list = self._detect_specialties_from_query(query)
            if detected_list:
                dns = {self._normalize_text(d) for d in detected_list}
                filtered = [
                    p for p in practitioners
                    if any(dn in self._normalize_text(p.specialty) for dn in dns)
                ]
                label = ", ".join(detected_list)
                message = f"Found {len(filtered)} {label} physician{'s' if len(filtered) != 1 else ''}"
                response = f"{label.title()} specialists: {len(filtered)} physician{'s' if len(filtered) != 1 else ''} available"
            elif any(term in query_lower for term in ['endocrinologist', 'endocrinology']):
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
            snippets = self._retrieve_similar_docs(query, k=10)
            response_text = "\n---\n".join(snippets) if snippets else "No relevant knowledge snippets found."
            return {
                'status': 'success',
                'message': 'Patient query processed using vector knowledge only',
                'formatted_response': response_text,
                'data': [],
                'query_type': query_type
            }
        
        # Default fallback
        return {
            'status': 'success',
            'message': 'Query processed',
            'formatted_response': relevant_data,
            'query_type': query_type
        }
    
    def _get_relevant_data(self, query: str) -> tuple[str, str]:
        """Get only relevant data for the specific query"""
        query_lower = query.lower()
        
        # Patient-related queries
        if any(word in query_lower for word in ['patient', 'patients', 'critical', 'diabetes', 'sugar', 'bp', 'blood pressure', 'heart']):
            # Vector-only context for patients
            snippets = self._retrieve_similar_docs(query, k=10)
            data = "KNOWLEDGE (Patients):\n" + "\n---\n".join(snippets)
            return "patient_query", data
        
        # Physician-related queries (expanded) or explicit specialty aliases detected
        detected_specs = self._detect_specialties_from_query(query)
        if any(
            word in query_lower for word in [
                'physician', 'doctor', 'specialist', 'cardiologist',
                'endocrinologist', 'orthopedic', 'orthopaedic', 'ortho'
            ]
        ) or bool(detected_specs):
            # Vector-only context for physicians
            snippets = self._retrieve_similar_docs(query, k=8)
            data = "KNOWLEDGE (Physicians):\n" + "\n---\n".join(snippets)
            return "physician_query", data
        
        # Scheduling/slot queries
        elif any(word in query_lower for word in ['slot', 'appointment', 'schedule', 'available']):
            # Vector-only context for scheduling
            snippets = self._retrieve_similar_docs(query, k=8)
            data = "KNOWLEDGE (Scheduling):\n" + "\n---\n".join(snippets)
            return "scheduling_query", data
        
        # Default - mixed query
        else:
            practitioners = self.slot_manager.get_practitioners()
            data = f"SYSTEM OVERVIEW:\n"
            data += f"Physicians: {len(practitioners)} total\n"
            for p in practitioners[:5]:
                data += f"- {p.name} ({p.specialty})\n"
            
            # Vector-only: do not use CSV in overview; add note instead
            data += "\nPatients: (vector-backed overview)\n"
            
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
