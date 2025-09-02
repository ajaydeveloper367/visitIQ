"""
VisitIQ Medical Document Processing System
Handles multiple file formats: PDF, JPG, PNG, DICOM, Word, HL7, etc.
Supports multiple reports per patient with temporal tracking.
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging
from pathlib import Path

# Document processing imports (would be installed as needed)
try:
    import PyPDF2
    import fitz  # PyMuPDF for advanced PDF processing
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("⚠️ PDF processing not available. Install: pip install PyPDF2 PyMuPDF")

try:
    from PIL import Image
    import pytesseract  # OCR for image-based reports
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("⚠️ OCR not available. Install: pip install pillow pytesseract")

try:
    import pydicom  # DICOM medical imaging
    DICOM_AVAILABLE = True
except ImportError:
    DICOM_AVAILABLE = False
    print("⚠️ DICOM processing not available. Install: pip install pydicom")

logger = logging.getLogger(__name__)

class MedicalDocumentProcessor:
    """
    Advanced Medical Document Processing System
    
    Features:
    - Multi-format support (PDF, JPG, PNG, DICOM, Word, HL7)
    - Multiple reports per patient
    - Temporal data tracking
    - Medical data extraction with AI/LLM
    - Integration with existing prioritization
    """
    
    def __init__(self, documents_root: str = "data/patient_documents"):
        self.documents_root = Path(documents_root)
        self.documents_root.mkdir(parents=True, exist_ok=True)
        
        # Supported file types
        self.supported_formats = {
            '.pdf': self._process_pdf,
            '.jpg': self._process_image,
            '.jpeg': self._process_image,
            '.png': self._process_image,
            '.dcm': self._process_dicom,
            '.doc': self._process_word,
            '.docx': self._process_word,
            '.hl7': self._process_hl7,
            '.txt': self._process_text,
            '.json': self._process_json_report
        }
        
        # Medical data patterns for extraction
        self.medical_patterns = {
            'glucose': [r'glucose[:\s]*(\d+\.?\d*)\s*mg/dL', r'glucose[:\s]*(\d+\.?\d*)'],
            'bp_systolic': [r'BP[:\s]*(\d+)/\d+', r'blood pressure[:\s]*(\d+)/\d+'],
            'bp_diastolic': [r'BP[:\s]*\d+/(\d+)', r'blood pressure[:\s]*\d+/(\d+)'],
            'heart_rate': [r'HR[:\s]*(\d+)', r'heart rate[:\s]*(\d+)', r'pulse[:\s]*(\d+)'],
            'hba1c': [r'hba1c[^\d]*(\d+\.?\d*)\s*%'],
            'weight': [r'weight[:\s]*(\d+\.?\d*)\s*(?:kg|lbs)', r'wt[:\s]*(\d+\.?\d*)'],
            'height': [r'height[:\s]*(\d+\.?\d*)\s*(?:cm|ft|in)', r'ht[:\s]*(\d+\.?\d*)'],
            'temperature': [r'temp[:\s]*(\d+\.?\d*)', r'temperature[:\s]*(\d+\.?\d*)']
        }
        # Patient identity patterns
        self.identity_patterns = {
            'patient_id': [r'(?:patient id|mrn|id)[\s:#]*([A-Za-z0-9\-]+)'],
            'patient_name': [r'(?:patient name|name)[\s:]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)']
        }
        
        print(f"🏥 Medical Document Processor initialized")
        print(f"📁 Documents directory: {self.documents_root}")
        print(f"📋 Supported formats: {list(self.supported_formats.keys())}")
    
    def organize_patient_documents(self, patient_id: str) -> Dict[str, List[Dict]]:
        """
        Organize all documents for a specific patient by type and date
        
        Expected directory structure:
        data/patient_documents/
        ├── patient_001/
        │   ├── lab_reports/
        │   │   ├── 2024-01-15_glucose_test.pdf
        │   │   └── 2024-02-20_hba1c_report.pdf
        │   ├── imaging/
        │   │   ├── 2024-01-10_chest_xray.jpg
        │   │   └── 2024-02-15_ecg.pdf
        │   ├── vitals/
        │   │   ├── 2024-01-15_vitals.json
        │   │   └── 2024-02-20_vitals.json
        │   └── clinical_notes/
        │       ├── 2024-01-15_visit_notes.pdf
        │       └── 2024-02-20_progress_notes.docx
        """
        patient_dir = self.documents_root / f"patient_{str(patient_id).zfill(3)}"
        
        if not patient_dir.exists():
            print(f"⚠️ No documents found for patient {patient_id}")
            return {}
        
        documents = {
            'lab_reports': [],
            'imaging': [],
            'vitals': [],
            'clinical_notes': [],
            'discharge_summaries': [],
            'prescriptions': [],
            'other': []
        }
        
        # Scan all subdirectories
        for category in documents.keys():
            category_dir = patient_dir / category
            if category_dir.exists():
                for file_path in category_dir.glob("*"):
                    if file_path.suffix.lower() in self.supported_formats:
                        documents[category].append({
                            'file_path': str(file_path),
                            'filename': file_path.name,
                            'date': self._extract_date_from_filename(file_path.name),
                            'type': file_path.suffix.lower(),
                            'size': file_path.stat().st_size,
                            'modified': datetime.fromtimestamp(file_path.stat().st_mtime)
                        })
        
        # Sort by date (most recent first)
        for category in documents:
            documents[category].sort(key=lambda x: x['date'] or datetime.min, reverse=True)
        
        return documents
    
    def process_all_patient_documents(self, patient_id: str) -> Dict[str, Any]:
        """
        Process all documents for a patient and extract medical data
        """
        print(f"\n🔍 Processing all documents for Patient {patient_id}")
        print("=" * 50)
        
        documents = self.organize_patient_documents(patient_id)
        extracted_data = {
            'patient_id': patient_id,
            'last_updated': datetime.now().isoformat(),
            'document_summary': {},
            'latest_vitals': {},
            'lab_results': [],
            'clinical_timeline': [],
            'risk_factors': [],
            'medications': [],
            'diagnoses': []
        }
        
        total_docs = sum(len(docs) for docs in documents.values())
        processed_docs = 0
        
        print(f"📋 Found {total_docs} documents across {len([k for k, v in documents.items() if v])} categories")
        
        # Process each category
        for category, doc_list in documents.items():
            if not doc_list:
                continue
                
            print(f"\n📂 Processing {category}: {len(doc_list)} files")
            extracted_data['document_summary'][category] = len(doc_list)
            
            for doc_info in doc_list:
                try:
                    # Extract data based on file type
                    file_extension = doc_info['type']
                    processor = self.supported_formats.get(file_extension)
                    
                    if processor:
                        doc_data = processor(doc_info['file_path'], doc_info)
                        
                        # Integrate extracted data
                        self._integrate_document_data(extracted_data, doc_data, category, doc_info)
                        processed_docs += 1
                        
                        print(f"   ✅ {doc_info['filename']}: {len(doc_data.get('extracted_values', {}))} values extracted")
                    else:
                        print(f"   ⚠️ {doc_info['filename']}: Unsupported format")
                        
                except Exception as e:
                    print(f"   ❌ {doc_info['filename']}: Error - {e}")
        
        print(f"\n✅ Processed {processed_docs}/{total_docs} documents successfully")
        
        # Generate comprehensive patient profile
        patient_profile = self._generate_patient_profile(extracted_data)
        
        return patient_profile
    
    def _process_pdf(self, file_path: str, doc_info: Dict) -> Dict[str, Any]:
        """Process PDF medical documents (lab reports, clinical notes, etc.)
        - Primary: extract text via PyMuPDF
        - Fallback: OCR each page if text is empty (image-only PDFs)
        """
        if not PDF_AVAILABLE:
            return {'error': 'PDF processing not available'}
        
        try:
            doc = fitz.open(file_path)
            text_chunks: List[str] = []
            for page in doc:
                t = page.get_text() or ""
                if t.strip():
                    text_chunks.append(t)
            # OCR fallback if needed
            if not text_chunks and OCR_AVAILABLE:
                import io
                for page in doc:
                    pix = page.get_pixmap()
                    try:
                        img_bytes = pix.tobytes("png")
                        image = Image.open(io.BytesIO(img_bytes))
                        ocr_text = pytesseract.image_to_string(image)
                        if ocr_text.strip():
                            text_chunks.append(ocr_text)
                    except Exception:
                        continue
            full_text = "\n".join(text_chunks)
            page_count = len(doc)
            doc.close()

            # Extract medical + identity data
            extracted_values = self._extract_medical_values(full_text)
            extracted_values.update(self._extract_patient_identity(full_text))
            
            return {
                'text_content': full_text[:2000] + "..." if len(full_text) > 2000 else full_text,
                'extracted_values': extracted_values,
                'page_count': page_count,
                'processing_method': 'PDF text extraction' if text_chunks else 'PDF OCR extraction'
            }
            
        except Exception as e:
            return {'error': f'PDF processing failed: {str(e)}'}
    
    def _process_image(self, file_path: str, doc_info: Dict) -> Dict[str, Any]:
        """Process image-based medical documents (X-rays, lab results, etc.)"""
        if not OCR_AVAILABLE:
            return {'error': 'OCR processing not available'}
        
        try:
            # Open image and perform OCR
            image = Image.open(file_path)
            
            # Extract text using OCR
            ocr_text = pytesseract.image_to_string(image)
            
            # Extract medical + identity data
            extracted_values = self._extract_medical_values(ocr_text)
            extracted_values.update(self._extract_patient_identity(ocr_text))
            
            return {
                'text_content': ocr_text[:1000] + "..." if len(ocr_text) > 1000 else ocr_text,
                'extracted_values': extracted_values,
                'image_dimensions': image.size,
                'processing_method': 'OCR text extraction'
            }
            
        except Exception as e:
            return {'error': f'Image processing failed: {str(e)}'}
    
    def _process_dicom(self, file_path: str, doc_info: Dict) -> Dict[str, Any]:
        """Process DICOM medical imaging files"""
        if not DICOM_AVAILABLE:
            return {'error': 'DICOM processing not available'}
        
        try:
            ds = pydicom.dcmread(file_path)
            
            extracted_values = {
                'patient_name': str(ds.get('PatientName', '')),
                'patient_id': str(ds.get('PatientID', '')),
                'study_date': str(ds.get('StudyDate', '')),
                'modality': str(ds.get('Modality', '')),
                'body_part': str(ds.get('BodyPartExamined', '')),
                'study_description': str(ds.get('StudyDescription', ''))
            }
            
            return {
                'dicom_metadata': extracted_values,
                'extracted_values': extracted_values,
                'processing_method': 'DICOM metadata extraction'
            }
            
        except Exception as e:
            return {'error': f'DICOM processing failed: {str(e)}'}
    
    def _process_word(self, file_path: str, doc_info: Dict) -> Dict[str, Any]:
        """Process Word documents (clinical notes, reports)"""
        try:
            # Would use python-docx for .docx files
            # For now, return placeholder
            return {
                'extracted_values': {},
                'processing_method': 'Word document processing (placeholder)',
                'note': 'Install python-docx for full Word document support'
            }
        except Exception as e:
            return {'error': f'Word processing failed: {str(e)}'}
    
    def _process_hl7(self, file_path: str, doc_info: Dict) -> Dict[str, Any]:
        """Process HL7 medical messages"""
        try:
            with open(file_path, 'r') as f:
                hl7_content = f.read()
            
            # Basic HL7 parsing (would use proper HL7 library in production)
            extracted_values = {}
            
            return {
                'hl7_content': hl7_content[:500] + "..." if len(hl7_content) > 500 else hl7_content,
                'extracted_values': extracted_values,
                'processing_method': 'HL7 message parsing'
            }
        except Exception as e:
            return {'error': f'HL7 processing failed: {str(e)}'}
    
    def _process_text(self, file_path: str, doc_info: Dict) -> Dict[str, Any]:
        """Process plain text medical files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            
            extracted_values = self._extract_medical_values(text_content)
            
            return {
                'text_content': text_content[:1000] + "..." if len(text_content) > 1000 else text_content,
                'extracted_values': extracted_values,
                'processing_method': 'Text file processing'
            }
        except Exception as e:
            return {'error': f'Text processing failed: {str(e)}'}
    
    def _process_json_report(self, file_path: str, doc_info: Dict) -> Dict[str, Any]:
        """Process structured JSON medical reports"""
        try:
            with open(file_path, 'r') as f:
                json_data = json.load(f)
            
            # Extract medical values from structured data
            extracted_values = self._extract_from_structured_data(json_data)
            
            return {
                'json_data': json_data,
                'extracted_values': extracted_values,
                'processing_method': 'Structured JSON parsing'
            }
        except Exception as e:
            return {'error': f'JSON processing failed: {str(e)}'}
    
    def _extract_medical_values(self, text: str) -> Dict[str, Any]:
        """Extract medical values using regex patterns and LLM"""
        import re
        
        extracted = {}
        
        # Use regex patterns for common medical values
        for key, patterns in self.medical_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        extracted[key] = float(match.group(1))
                        break
                    except ValueError:
                        extracted[key] = match.group(1)
                        break
        
        # Table-friendly fallbacks (values often appear without labels on the same line)
        try:
            m = re.search(r'(\d{2,3})\s*/\s*(\d{2,3})\s*mmhg', text, re.IGNORECASE)
            if m:
                extracted.setdefault('bp_systolic', float(m.group(1)))
                extracted.setdefault('bp_diastolic', float(m.group(2)))
        except Exception:
            pass
        try:
            m = re.search(r'(\d{2,3})\s*bpm', text, re.IGNORECASE)
            if m:
                extracted.setdefault('heart_rate', float(m.group(1)))
        except Exception:
            pass
        try:
            m = re.search(r'(\d{2,3}\.?\d*)\s*[fFcC]\b', text)
            if m:
                extracted.setdefault('temperature', float(m.group(1)))
        except Exception:
            pass
        try:
            m = re.search(r'(\d{2,3})\s*%\s*(?:oxygen|o2|saturation)?', text, re.IGNORECASE)
            if m:
                extracted.setdefault('oxygen_saturation', float(m.group(1)))
        except Exception:
            pass
        # TODO: Optionally integrate LLM for advanced medical data extraction
        # This would use the existing LLM to understand medical context
        
        return extracted

    def _extract_patient_identity(self, text: str) -> Dict[str, Any]:
        """Extract patient id and name if present in text."""
        import re
        identity: Dict[str, Any] = {}
        # Work line-by-line to avoid capturing across newlines
        for line in text.splitlines():
            l = line.strip()
            if not l:
                continue
            low = l.lower()
            # Patient ID
            m = re.search(r'^(?:patient\s*id|mrn|id)[\s:#-]*([A-Za-z0-9\-]+)\s*$', low, re.IGNORECASE)
            if m and 'patient_id' not in identity:
                identity['patient_id'] = m.group(1).strip()
                continue
            # Patient Name
            m = re.search(r'^(?:patient\s*name|name)[\s:]*([A-Z][A-Za-z\-]+(?:\s+[A-Z][A-Za-z\-]+)+)\s*$', l, re.IGNORECASE)
            if m and 'patient_name' not in identity:
                identity['patient_name'] = m.group(1).strip()
                continue
            # Physician
            m = re.search(r'^(?:physician|doctor)\s*[:]\s*(.*)$', l, re.IGNORECASE)
            if m and 'physician' not in identity:
                identity['physician'] = m.group(1).strip()
                continue
        return identity
    
    def _extract_from_structured_data(self, data: Dict) -> Dict[str, Any]:
        """Extract medical values from structured data (JSON, etc.)"""
        extracted = {}
        
        # Common medical field mappings
        field_mappings = {
            'glucose': ['glucose', 'blood_glucose', 'bg', 'glucose_mg_dl'],
            'bp_systolic': ['systolic', 'bp_sys', 'blood_pressure_systolic'],
            'bp_diastolic': ['diastolic', 'bp_dia', 'blood_pressure_diastolic'],
            'heart_rate': ['heart_rate', 'hr', 'pulse', 'beats_per_minute'],
            'temperature': ['temperature', 'temp', 'body_temp'],
            'weight': ['weight', 'wt', 'body_weight'],
            'height': ['height', 'ht', 'body_height']
        }
        
        def extract_nested(obj, target_keys):
            """Recursively search for target keys in nested dictionaries"""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key.lower() in target_keys:
                        return value
                    elif isinstance(value, (dict, list)):
                        result = extract_nested(value, target_keys)
                        if result is not None:
                            return result
            elif isinstance(obj, list):
                for item in obj:
                    result = extract_nested(item, target_keys)
                    if result is not None:
                        return result
            return None
        
        # Extract values using field mappings
        for medical_key, possible_keys in field_mappings.items():
            value = extract_nested(data, possible_keys)
            if value is not None:
                extracted[medical_key] = value
        
        return extracted
    
    def _extract_date_from_filename(self, filename: str) -> Optional[datetime]:
        """Extract date from filename (various formats)"""
        import re
        
        # Common date patterns in filenames
        patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # 2024-01-15
            r'(\d{2}-\d{2}-\d{4})',  # 01-15-2024
            r'(\d{4}_\d{2}_\d{2})',  # 2024_01_15
            r'(\d{8})',              # 20240115
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                date_str = match.group(1)
                try:
                    if '-' in date_str:
                        if len(date_str.split('-')[0]) == 4:  # YYYY-MM-DD
                            return datetime.strptime(date_str, '%Y-%m-%d')
                        else:  # MM-DD-YYYY
                            return datetime.strptime(date_str, '%m-%d-%Y')
                    elif '_' in date_str:  # YYYY_MM_DD
                        return datetime.strptime(date_str, '%Y_%m_%d')
                    elif len(date_str) == 8:  # YYYYMMDD
                        return datetime.strptime(date_str, '%Y%m%d')
                except ValueError:
                    continue
        
        return None
    
    def _integrate_document_data(self, extracted_data: Dict, doc_data: Dict, category: str, doc_info: Dict):
        """Integrate data from a single document into the patient profile"""
        if 'error' in doc_data:
            return
        
        doc_values = doc_data.get('extracted_values', {})
        doc_date = doc_info['date'] or doc_info['modified']
        
        # Update latest vitals with most recent values
        for key, value in doc_values.items():
            if key in ['glucose', 'bp_systolic', 'bp_diastolic', 'heart_rate', 'temperature', 'weight']:
                current_date = extracted_data['latest_vitals'].get(f'{key}_date')
                if not current_date or doc_date > datetime.fromisoformat(current_date):
                    extracted_data['latest_vitals'][key] = value
                    extracted_data['latest_vitals'][f'{key}_date'] = doc_date.isoformat()
        
        # Add to clinical timeline
        timeline_entry = {
            'date': doc_date.isoformat(),
            'document': doc_info['filename'],
            'category': category,
            'values': doc_values,
            'source': doc_data.get('processing_method', 'unknown')
        }
        extracted_data['clinical_timeline'].append(timeline_entry)
    
    def _generate_patient_profile(self, extracted_data: Dict) -> Dict[str, Any]:
        """Generate comprehensive patient profile for prioritization system"""
        
        # Convert to format compatible with existing prioritization system
        patient_profile = {
            'patient_id': extracted_data['patient_id'],
            'name': f"Patient {extracted_data['patient_id']}",  # Would be extracted from documents
            'age': 45,  # Would be calculated from DOB in documents
            'condition': self._determine_primary_condition(extracted_data),
            
            # Latest vitals (compatible with existing system)
            'glucose_mg_dL': extracted_data['latest_vitals'].get('glucose', 100),
            'bp_systolic': extracted_data['latest_vitals'].get('bp_systolic', 120),
            'bp_diastolic': extracted_data['latest_vitals'].get('bp_diastolic', 80),
            'heart_rate': extracted_data['latest_vitals'].get('heart_rate', 72),
            'bmi': 25.0,  # Would be calculated from height/weight
            
            # Enhanced data from documents
            'document_count': sum(extracted_data['document_summary'].values()),
            'last_document_date': max([entry['date'] for entry in extracted_data['clinical_timeline']], default=''),
            'document_types': list(extracted_data['document_summary'].keys()),
            'clinical_timeline': extracted_data['clinical_timeline'],
            'risk_factors': extracted_data['risk_factors'],
            
            # Notes and history (enhanced)
            'notes': f"Multi-document patient with {len(extracted_data['clinical_timeline'])} clinical entries",
            'history': "; ".join(extracted_data['risk_factors'][:3]) if extracted_data['risk_factors'] else "See clinical timeline"
        }
        
        return patient_profile
    
    def _determine_primary_condition(self, extracted_data: Dict) -> str:
        """Determine primary medical condition from document analysis"""
        # This would use LLM to analyze all documents and determine primary condition
        # For now, return a placeholder
        
        timeline = extracted_data['clinical_timeline']
        if not timeline:
            return "Unknown"
        
        # Simple heuristic based on glucose levels
        latest_glucose = extracted_data['latest_vitals'].get('glucose')
        if latest_glucose:
            if latest_glucose > 300:
                return "Type 1 Diabetes"
            elif latest_glucose > 200:
                return "Type 2 Diabetes"
            elif latest_glucose > 140:
                return "Prediabetes"
        
        return "Multiple Conditions"

# Usage example and testing functions
def create_sample_patient_documents():
    """Create sample patient document structure for testing"""
    processor = MedicalDocumentProcessor()
    
    # Create sample documents directory structure
    sample_patients = ['001', '002', '003']
    
    for patient_id in sample_patients:
        patient_dir = processor.documents_root / f"patient_{patient_id}"
        
        # Create subdirectories
        for category in ['lab_reports', 'imaging', 'vitals', 'clinical_notes']:
            category_dir = patient_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)
            
            # Create sample files
            if category == 'vitals':
                # Sample JSON vitals
                sample_vitals = {
                    'date': '2024-01-15',
                    'glucose': 250 + int(patient_id) * 10,
                    'bp_systolic': 140 + int(patient_id) * 5,
                    'bp_diastolic': 90 + int(patient_id) * 2,
                    'heart_rate': 80 + int(patient_id) * 3,
                    'weight': 70 + int(patient_id) * 2,
                    'temperature': 98.6
                }
                
                vitals_file = category_dir / f"2024-01-15_vitals.json"
                with open(vitals_file, 'w') as f:
                    json.dump(sample_vitals, f, indent=2)
            
            elif category == 'clinical_notes':
                # Sample text clinical note
                sample_note = f"""
Patient {patient_id} Clinical Visit - January 15, 2024

Chief Complaint: Follow-up for diabetes management

Vitals:
- Blood Pressure: {140 + int(patient_id) * 5}/{90 + int(patient_id) * 2} mmHg
- Heart Rate: {80 + int(patient_id) * 3} bpm
- Glucose: {250 + int(patient_id) * 10} mg/dL
- Weight: {70 + int(patient_id) * 2} kg

Assessment: Diabetes management, glucose levels elevated
Plan: Adjust medication, follow-up in 3 months
                """
                
                note_file = category_dir / f"2024-01-15_visit_notes.txt"
                with open(note_file, 'w') as f:
                    f.write(sample_note)
    
    print("✅ Sample patient documents created")
    print(f"📁 Location: {processor.documents_root}")
    return processor

if __name__ == "__main__":
    # Demo the system
    print("🏥 MEDICAL DOCUMENT PROCESSING SYSTEM DEMO")
    print("=" * 60)
    
    # Create sample documents
    processor = create_sample_patient_documents()
    
    # Process a sample patient
    patient_profile = processor.process_all_patient_documents("001")
    
    print("\n📊 GENERATED PATIENT PROFILE:")
    print("=" * 40)
    for key, value in patient_profile.items():
        if key == 'clinical_timeline':
            print(f"{key}: {len(value)} entries")
        else:
            print(f"{key}: {value}")
