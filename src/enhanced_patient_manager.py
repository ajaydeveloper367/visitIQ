"""
Enhanced Patient Manager with Multi-Format Document Support
Integrates Medical Document Processing with existing VisitIQ prioritization
"""

import os
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from pathlib import Path

from medical_document_processor import MedicalDocumentProcessor

class EnhancedPatientManager:
    """
    Enhanced Patient Manager that handles multiple data sources:
    - Traditional CSV data (for backward compatibility)
    - Multi-format medical documents (PDF, JPG, DICOM, etc.)
    - Multiple reports per patient with temporal tracking
    """
    
    def __init__(self, 
                 csv_path: str = "data/patients.csv",
                 documents_path: str = "data/patient_documents",
                 cache_path: str = "data/patient_cache.json"):
        
        self.csv_path = csv_path
        self.documents_path = documents_path
        self.cache_path = cache_path
        
        # Initialize document processor
        self.document_processor = MedicalDocumentProcessor(documents_path)
        
        # Load cached processed data
        self.patient_cache = self._load_cache()
        
        print("🏥 Enhanced Patient Manager initialized")
        print(f"📄 CSV data: {csv_path}")
        print(f"📁 Documents: {documents_path}")
        print(f"💾 Cache: {cache_path}")
    
    def get_all_patients(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Vector-first loader. Reads patients from chroma_db/metadatas.json.
        If vector DB is missing, falls back to processing documents only.
        CSV is not used.
        """
        print("\n🔍 Loading patient data (Vector-first)...")

        # 1) Vector DB metadata
        try:
            base_app = Path(__file__).resolve().parents[1]  # .../app
            candidates = [base_app / 'chroma_db' / 'metadatas.json', base_app.parent / 'chroma_db' / 'metadatas.json']
            for mp in candidates:
                if mp.exists():
                    with open(mp, 'r', encoding='utf-8') as f:
                        metas = json.load(f)
                    # Accept structured patient or patient_doc (docs-only mode)
                    patients_meta = [m for m in metas if m.get('type') in ('patient', 'patient_doc')]
                    if patients_meta:
                        normalized: List[Dict[str, Any]] = []
                        for m in patients_meta:
                            pid = str(m.get('patient_id', m.get('id', '')))
                            # For docs-only, use raw patient_id (not zero-padded) to avoid confusion
                            if m.get('type') == 'patient_doc':
                                pid_norm = pid
                            else:
                                pid_norm = pid.zfill(3)
                            normalized.append({
                                'patient_id': pid_norm,
                                'name': m.get('name', 'Unknown Patient'),
                                'age': int((m.get('age') or 50)),
                                'condition': m.get('condition', 'Unknown'),
                                'glucose_mg_dL': float(m.get('glucose_mg_dL') or 0),
                                'bp_systolic': float(m.get('bp_systolic') or 0),
                                'bp_diastolic': float(m.get('bp_diastolic') or 0),
                                'heart_rate': float(m.get('heart_rate') or 0),
                                'hba1c': float(m.get('hba1c') or 0),
                                'history': m.get('history', ''),
                                'notes': m.get('notes', ''),
                                # Enriched triage fields (if present from docs-only LLM normalization)
                                'risk_level': m.get('risk_level'),
                                'risk_score': m.get('risk_score'),
                                'medical_reasons': m.get('medical_reasons'),
                                'document_count': m.get('document_count', 1 if m.get('type')=='patient_doc' else m.get('document_count', 0)),
                                'last_document_date': m.get('last_document_date'),
                                'data_source': 'VectorDB'
                            })
                        print(f"✅ Loaded {len(normalized)} patients from Vector DB")
                        return normalized
        except Exception as e:
            print(f"⚠️ Vector DB read failed: {e}")

        # 2) Documents only (no CSV)
        enhanced_patients: List[Dict[str, Any]] = []
        docs_dir = Path(self.documents_path)
        if docs_dir.exists():
            for patient_dir in docs_dir.iterdir():
                if patient_dir.is_dir() and patient_dir.name.startswith('patient_'):
                    patient_id = patient_dir.name.replace('patient_', '')
                    if patient_id in self.patient_cache and not force_refresh:
                        enhanced_patient = self.patient_cache[patient_id]
                    else:
                        enhanced_patient = self.document_processor.process_all_patient_documents(patient_id)
                        self.patient_cache[patient_id] = enhanced_patient
                        self._save_cache()
                    enhanced_patients.append(enhanced_patient)

        print(f"✅ Loaded {len(enhanced_patients)} patients from documents")
        return enhanced_patients
    
    def get_patient_by_id(self, patient_id: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get detailed patient information by ID"""
        patient_id = str(patient_id).zfill(3)
        
        if patient_id in self.patient_cache and not force_refresh:
            return self.patient_cache[patient_id]
        
        if self._has_documents(patient_id):
            enhanced_patient = self.document_processor.process_all_patient_documents(patient_id)
            self.patient_cache[patient_id] = enhanced_patient
            self._save_cache()
            return enhanced_patient
        
        # No CSV fallback; try documents only
        if self._has_documents(patient_id):
            enhanced_patient = self.document_processor.process_all_patient_documents(patient_id)
            self.patient_cache[patient_id] = enhanced_patient
            self._save_cache()
            return enhanced_patient

        return None
    
    def get_patient_documents_summary(self, patient_id: str) -> Dict[str, Any]:
        """Get summary of all documents for a patient"""
        patient_id = str(patient_id).zfill(3)
        documents = self.document_processor.organize_patient_documents(patient_id)
        
        total_docs = sum(len(docs) for docs in documents.values())
        
        summary = {
            'patient_id': patient_id,
            'total_documents': total_docs,
            'categories': {},
            'date_range': None,
            'latest_document': None
        }
        
        all_dates = []
        latest_doc = None
        latest_date = None
        
        for category, doc_list in documents.items():
            if doc_list:
                summary['categories'][category] = {
                    'count': len(doc_list),
                    'latest': doc_list[0]['filename'],
                    'latest_date': doc_list[0]['date'].isoformat() if doc_list[0]['date'] else 'Unknown'
                }
                
                for doc in doc_list:
                    if doc['date']:
                        all_dates.append(doc['date'])
                        if not latest_date or doc['date'] > latest_date:
                            latest_date = doc['date']
                            latest_doc = doc
        
        if all_dates:
            summary['date_range'] = {
                'earliest': min(all_dates).isoformat(),
                'latest': max(all_dates).isoformat()
            }
        
        if latest_doc:
            summary['latest_document'] = {
                'filename': latest_doc['filename'],
                'category': next(cat for cat, docs in documents.items() if latest_doc in docs),
                'date': latest_doc['date'].isoformat()
            }
        
        return summary
    
    def get_patient_timeline(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get chronological timeline of all patient documents and events"""
        patient_data = self.get_patient_by_id(patient_id)
        
        if not patient_data or 'clinical_timeline' not in patient_data:
            return []
        
        # Sort timeline by date
        timeline = sorted(
            patient_data['clinical_timeline'],
            key=lambda x: x['date'],
            reverse=True
        )
        
        return timeline
    
    def search_patients_by_condition(self, condition: str) -> List[Dict[str, Any]]:
        """Search patients by medical condition"""
        all_patients = self.get_all_patients()
        
        matching_patients = []
        for patient in all_patients:
            if condition.lower() in patient.get('condition', '').lower():
                matching_patients.append(patient)
        
        return matching_patients
    
    def get_patients_with_recent_documents(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get patients with documents updated in the last N days"""
        cutoff_date = datetime.now() - pd.Timedelta(days=days)
        recent_patients = []
        
        all_patients = self.get_all_patients()
        for patient in all_patients:
            last_doc_date = patient.get('last_document_date')
            if last_doc_date:
                try:
                    doc_date = datetime.fromisoformat(last_doc_date.replace('Z', '+00:00'))
                    if doc_date > cutoff_date:
                        recent_patients.append(patient)
                except:
                    continue
        
        return recent_patients
    
    # CSV loader removed for vector-first workflow
    def _load_csv_patients(self) -> List[Dict[str, Any]]:  # kept for compatibility, returns empty
        return []
    
    def _enhance_csv_patient(self, csv_patient: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance CSV patient data with additional metadata"""
        enhanced = csv_patient.copy()
        
        # Add enhanced metadata
        enhanced.update({
            'data_source': 'CSV',
            'document_count': 0,
            'last_document_date': None,
            'document_types': [],
            'clinical_timeline': [],
            'risk_factors': enhanced.get('history', '').split('; ') if enhanced.get('history') else []
        })
        
        return enhanced
    
    def _has_documents(self, patient_id: str) -> bool:
        """Check if patient has document files"""
        patient_dir = Path(self.documents_path) / f"patient_{patient_id}"
        return patient_dir.exists() and any(patient_dir.iterdir())
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load cached processed patient data"""
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading cache: {e}")
        
        return {}
    
    def _save_cache(self):
        """Save processed patient data to cache"""
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, 'w') as f:
                json.dump(self.patient_cache, f, indent=2, default=str)
        except Exception as e:
            print(f"❌ Error saving cache: {e}")
    
    def refresh_patient_data(self, patient_id: Optional[str] = None):
        """Refresh patient data by reprocessing documents"""
        if patient_id:
            # Refresh specific patient
            patient_id = str(patient_id).zfill(3)
            if patient_id in self.patient_cache:
                del self.patient_cache[patient_id]
            self.get_patient_by_id(patient_id, force_refresh=True)
            print(f"✅ Refreshed data for patient {patient_id}")
        else:
            # Refresh all patients
            self.patient_cache.clear()
            self.get_all_patients(force_refresh=True)
            print("✅ Refreshed data for all patients")
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get statistics about the patient data system"""
        all_patients = self.get_all_patients()
        
        stats = {
            'total_patients': len(all_patients),
            'data_sources': {'CSV': 0, 'Documents': 0, 'Mixed': 0},
            'document_types': {},
            'conditions': {},
            'total_documents': 0,
            'latest_activity': None
        }
        
        latest_dates = []
        
        for patient in all_patients:
            # Data source classification
            if patient.get('document_count', 0) > 0:
                if 'CSV' in patient.get('data_source', ''):
                    stats['data_sources']['Mixed'] += 1
                else:
                    stats['data_sources']['Documents'] += 1
            else:
                stats['data_sources']['CSV'] += 1
            
            # Document types
            for doc_type in patient.get('document_types', []):
                stats['document_types'][doc_type] = stats['document_types'].get(doc_type, 0) + 1
            
            # Conditions
            condition = patient.get('condition', 'Unknown')
            stats['conditions'][condition] = stats['conditions'].get(condition, 0) + 1
            
            # Document count
            stats['total_documents'] += patient.get('document_count', 0)
            
            # Latest activity
            if patient.get('last_document_date'):
                try:
                    date = datetime.fromisoformat(patient['last_document_date'].replace('Z', '+00:00'))
                    latest_dates.append(date)
                except:
                    pass
        
        if latest_dates:
            stats['latest_activity'] = max(latest_dates).isoformat()
        
        return stats

# Integration function for existing prioritization system
def get_enhanced_patients_for_prioritization() -> List[Dict[str, Any]]:
    """
    Get patient data in format compatible with existing prioritization system
    This is the main integration point with your current VisitIQ system
    """
    manager = EnhancedPatientManager()
    enhanced_patients = manager.get_all_patients()
    
    # Convert to format expected by existing prioritization system
    compatible_patients = []
    
    for patient in enhanced_patients:
        # Ensure all required fields are present for existing system
        compatible_patient = {
            'patient_id': patient.get('patient_id', 'Unknown'),
            'name': patient.get('name', 'Unknown Patient'),
            'age': patient.get('age', 50),
            'condition': patient.get('condition', 'Unknown'),
            'glucose_mg_dL': patient.get('glucose_mg_dL', 100),
            'bp_systolic': patient.get('bp_systolic', 120),
            'bp_diastolic': patient.get('bp_diastolic', 80),
            'heart_rate': patient.get('heart_rate', 72),
            'bmi': patient.get('bmi', 25.0),
            'notes': patient.get('notes', ''),
            'history': patient.get('history', ''),
            
            # Enhanced fields (backward compatible)
            'data_source': patient.get('data_source', 'CSV'),
            'document_count': patient.get('document_count', 0),
            'last_document_date': patient.get('last_document_date'),
            'enhanced_data_available': patient.get('document_count', 0) > 0,
            # Triaged fields (from docs-only enrichment if present)
            'risk_level': patient.get('risk_level'),
            'risk_score': patient.get('risk_score'),
            'medical_reasons': patient.get('medical_reasons')
        }
        
        compatible_patients.append(compatible_patient)
    
    return compatible_patients

if __name__ == "__main__":
    # Demo the enhanced patient manager
    print("🏥 ENHANCED PATIENT MANAGER DEMO")
    print("=" * 50)
    
    manager = EnhancedPatientManager()
    
    # Get system stats
    stats = manager.get_system_stats()
    print("\n📊 SYSTEM STATISTICS:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Test integration function
    print("\n🔄 TESTING INTEGRATION WITH EXISTING SYSTEM:")
    compatible_patients = get_enhanced_patients_for_prioritization()
    
    print(f"✅ Generated {len(compatible_patients)} patients in compatible format")
    if compatible_patients:
        sample = compatible_patients[0]
        print("\n📋 Sample patient record:")
        for key, value in sample.items():
            print(f"   {key}: {value}")
