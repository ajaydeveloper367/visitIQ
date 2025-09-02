#!/usr/bin/env python3
"""
Medical Document Generator for VisitIQ Testing
Creates realistic multi-format medical documents using local LLM (Ollama/LLaMA)

Usage:
    python tools/generate_medical_documents.py --patients 10 --reports-per-patient 5
    python tools/generate_medical_documents.py --help
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import random
from typing import Dict, List, Any, Optional
import requests

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

class MedicalDocumentGenerator:
    """
    Generates realistic medical documents using local LLM
    Creates multiple formats: PDF, JSON, text files, etc.
    """
    
    def __init__(self, 
                 output_dir: str = "data/patient_documents",
                 llm_base_url: str = "http://localhost:11434",
                 llm_model: str = "llama3"):
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        
        # Medical specialties and conditions
        self.specialties = [
            "Endocrinology", "Cardiology", "Nephrology", "Internal Medicine",
            "Family Medicine", "Pulmonology", "Neurology", "Rheumatology",
            "Gastroenterology", "Hematology", "Infectious Disease"
        ]
        
        self.conditions = [
            "Type 1 Diabetes", "Type 2 Diabetes", "Prediabetes", "Hypertension",
            "Heart Disease", "Chronic Kidney Disease", "COPD", "Asthma",
            "Rheumatoid Arthritis", "Osteoarthritis", "Depression", "Anxiety",
            "Stroke History", "Peripheral Neuropathy", "Sleep Apnea"
        ]
        
        self.medications = [
            "Metformin", "Insulin", "Lisinopril", "Atorvastatin", "Aspirin",
            "Amlodipine", "Metoprolol", "Omeprazole", "Albuterol", "Prednisone",
            "Gabapentin", "Sertraline", "Warfarin", "Furosemide", "Levothyroxine"
        ]
        
        # Generate realistic patient names (US-based, easy to pronounce)
        self.first_names = [
            "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
            "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
            "Thomas", "Sarah", "Christopher", "Karen", "Charles", "Nancy", "Daniel", "Lisa",
            "Matthew", "Betty", "Anthony", "Helen", "Mark", "Sandra", "Donald", "Donna",
            "Steven", "Carol", "Paul", "Ruth", "Andrew", "Sharon", "Joshua", "Michelle",
            "Kenneth", "Laura", "Kevin", "Sarah", "Brian", "Kimberly", "George", "Deborah",
            "Timothy", "Dorothy", "Ronald", "Lisa", "Jason", "Nancy", "Edward", "Karen",
            "Jeffrey", "Betty", "Ryan", "Helen", "Jacob", "Sandra", "Gary", "Donna"
        ]
        
        self.last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
            "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
            "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
            "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
            "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
            "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
            "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker"
        ]
        
        print(f"🏥 Medical Document Generator initialized")
        print(f"📁 Output directory: {self.output_dir}")
        print(f"🤖 LLM endpoint: {self.llm_base_url}")
        print(f"🧠 Model: {self.llm_model}")
        
        # PDF helper availability
        try:
            import fitz  # PyMuPDF
            self._pdf_available = True
        except Exception:
            self._pdf_available = False
        
    def _call_llm(self, prompt: str, max_tokens: int = 500) -> str:
        """Call local Ollama LLM"""
        try:
            response = requests.post(
                f"{self.llm_base_url}/api/generate",
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_ctx": 2048,
                        "temperature": 0.7,
                        "num_predict": max_tokens
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                print(f"⚠️ LLM request failed: {response.status_code}")
                return ""
                
        except Exception as e:
            print(f"⚠️ LLM call failed: {e}")
            return ""
    
    def _generate_patient_profile(self, patient_id: str) -> Dict[str, Any]:
        """Generate a realistic patient profile"""
        age = random.randint(18, 85)
        gender = random.choice(["Male", "Female"])
        name = f"{random.choice(self.first_names)} {random.choice(self.last_names)}"
        primary_condition = random.choice(self.conditions)
        
        # Generate secondary conditions based on age and primary condition
        secondary_conditions = []
        if age > 50:
            secondary_conditions.extend(random.sample(["Hypertension", "High Cholesterol", "Sleep Apnea"], 
                                                    random.randint(0, 2)))
        if "Diabetes" in primary_condition:
            secondary_conditions.extend(random.sample(["Diabetic Neuropathy", "Retinopathy", "CKD stage 3"], 
                                                    random.randint(0, 2)))
        
        return {
            "patient_id": patient_id,
            "name": name,
            "age": age,
            "gender": gender,
            "primary_condition": primary_condition,
            "secondary_conditions": list(set(secondary_conditions)),
            "medications": random.sample(self.medications, random.randint(2, 5))
        }
    
    def _generate_realistic_vitals(self, patient_profile: Dict, date: datetime) -> Dict[str, Any]:
        """Generate realistic vital signs based on patient condition"""
        condition = patient_profile["primary_condition"]
        age = patient_profile["age"]
        
        # Base vitals with condition-specific variations
        if "Diabetes" in condition:
            glucose = random.randint(180, 400) if "Type 1" in condition else random.randint(150, 350)
            bp_sys = random.randint(130, 180)
            bp_dia = random.randint(85, 110)
        elif "Hypertension" in condition:
            glucose = random.randint(90, 140)
            bp_sys = random.randint(140, 190)
            bp_dia = random.randint(90, 120)
        elif "Heart Disease" in condition:
            glucose = random.randint(90, 160)
            bp_sys = random.randint(120, 170)
            bp_dia = random.randint(75, 100)
            heart_rate = random.randint(55, 95)  # Often on beta blockers
        else:
            glucose = random.randint(80, 140)
            bp_sys = random.randint(110, 140)
            bp_dia = random.randint(70, 90)
        
        # Age-adjusted heart rate
        if age > 70:
            heart_rate = random.randint(65, 90)
        else:
            heart_rate = random.randint(70, 100)
        
        return {
            "date": date.strftime("%Y-%m-%d"),
            "time": date.strftime("%H:%M"),
            "glucose_mg_dL": glucose,
            "bp_systolic": bp_sys,
            "bp_diastolic": bp_dia,
            "heart_rate": heart_rate,
            "temperature_f": round(random.uniform(97.8, 99.2), 1),
            "weight_kg": round(random.uniform(50, 120), 1),
            "height_cm": random.randint(150, 190),
            "oxygen_saturation": random.randint(94, 100),
            "respiratory_rate": random.randint(12, 20),
            "pain_scale": random.randint(0, 5),
            "notes": f"Patient reports {'good' if random.random() > 0.3 else 'moderate'} energy level"
        }
    
    def generate_vitals_json(self, patient_profile: Dict, date: datetime, output_dir: Path) -> str:
        """Generate JSON vitals file"""
        vitals = self._generate_realistic_vitals(patient_profile, date)
        
        filename = f"{date.strftime('%Y-%m-%d')}_vitals.json"
        filepath = output_dir / "vitals" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(vitals, f, indent=2)
        
        return str(filepath)
    
    def generate_clinical_note(self, patient_profile: Dict, date: datetime, output_dir: Path) -> str:
        """Generate clinical note using LLM"""
        vitals = self._generate_realistic_vitals(patient_profile, date)
        
        prompt = f"""Write a realistic clinical note for a patient visit. Use professional medical language.

Patient Information:
- Name: {patient_profile['name']}
- Age: {patient_profile['age']} years old {patient_profile['gender']}
- Primary Condition: {patient_profile['primary_condition']}
- Secondary Conditions: {', '.join(patient_profile['secondary_conditions'])}
- Current Medications: {', '.join(patient_profile['medications'])}

Visit Date: {date.strftime('%B %d, %Y')}

Current Vitals:
- Blood Pressure: {vitals['bp_systolic']}/{vitals['bp_diastolic']} mmHg
- Heart Rate: {vitals['heart_rate']} bpm
- Glucose: {vitals['glucose_mg_dL']} mg/dL
- Temperature: {vitals['temperature_f']}°F
- Weight: {vitals['weight_kg']} kg
- Oxygen Saturation: {vitals['oxygen_saturation']}%

Write a clinical note including:
1. Chief Complaint
2. History of Present Illness  
3. Physical Examination findings
4. Assessment and Plan
5. Medication adjustments (if needed)
6. Follow-up recommendations

Keep it realistic and medically accurate. Use standard medical abbreviations."""

        clinical_note = self._call_llm(prompt, max_tokens=800)
        
        if not clinical_note:
            # Fallback clinical note
            clinical_note = f"""CLINICAL NOTE - {date.strftime('%B %d, %Y')}

Patient: {patient_profile['name']} ({patient_profile['age']}yo {patient_profile['gender']})

CHIEF COMPLAINT: Follow-up for {patient_profile['primary_condition']}

HISTORY OF PRESENT ILLNESS:
Patient returns for routine follow-up. Reports {'good' if random.random() > 0.4 else 'fair'} medication adherence. 
{'No new symptoms reported.' if random.random() > 0.3 else 'Reports mild fatigue and occasional dizziness.'}

PHYSICAL EXAMINATION:
Vital Signs: BP {vitals['bp_systolic']}/{vitals['bp_diastolic']}, HR {vitals['heart_rate']}, Temp {vitals['temperature_f']}°F, O2 Sat {vitals['oxygen_saturation']}%
Weight: {vitals['weight_kg']} kg
General: {'Well-appearing' if random.random() > 0.2 else 'Appears mildly fatigued'}
Cardiovascular: {'Regular rate and rhythm, no murmurs' if vitals['heart_rate'] < 100 else 'Mildly tachycardic, regular rhythm'}
Respiratory: Clear to auscultation bilaterally

ASSESSMENT AND PLAN:
1. {patient_profile['primary_condition']}: {'Stable on current regimen' if random.random() > 0.3 else 'Requires medication adjustment'}
   - Continue {random.choice(patient_profile['medications'])}
   - {'Laboratory studies ordered' if 'Diabetes' in patient_profile['primary_condition'] else 'Monitor symptoms'}

FOLLOW-UP: {random.choice(['3 months', '6 months', '4 weeks'])}

Electronically signed by Dr. {random.choice(['Smith', 'Johnson', 'Williams', 'Brown'])}"""

        # Write TXT
        txt_filename = f"{date.strftime('%Y-%m-%d')}_clinical_note.txt"
        txt_path = output_dir / "clinical_notes" / txt_filename
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        txt_path.write_text(clinical_note, encoding="utf-8")

        # Also write PDF if available
        pdf_path = output_dir / "clinical_notes" / f"{date.strftime('%Y-%m-%d')}_clinical_note.pdf"
        self._write_pdf_safe(clinical_note, pdf_path)
        
        return str(pdf_path if pdf_path.exists() else txt_path)
    
    def generate_lab_report(self, patient_profile: Dict, date: datetime, output_dir: Path) -> str:
        """Generate lab report text file using LLM"""
        
        prompt = f"""Generate a realistic laboratory report for a patient with {patient_profile['primary_condition']}.

Patient: {patient_profile['name']} (Age: {patient_profile['age']})
Test Date: {date.strftime('%B %d, %Y')}

Include these lab values with realistic ranges:
- Complete Blood Count (CBC)
- Comprehensive Metabolic Panel (CMP)
- Lipid Panel
- HbA1c (if diabetic)
- Thyroid Function (if indicated)
- Kidney function tests

Format as a professional lab report with:
1. Patient demographics
2. Ordering physician  
3. Lab values with reference ranges
4. Abnormal values flagged
5. Lab technician signature

Make values consistent with the patient's condition. Use proper medical formatting."""

        lab_report = self._call_llm(prompt, max_tokens=800)
        
        if not lab_report:
            # Fallback lab report
            glucose_fasting = random.randint(200, 350) if "Diabetes" in patient_profile['primary_condition'] else random.randint(80, 110)
            hba1c = round(random.uniform(8.5, 12.0), 1) if "Diabetes" in patient_profile['primary_condition'] else round(random.uniform(4.5, 6.0), 1)
            
            lab_report = f"""LABORATORY REPORT

Patient Name: {patient_profile['name']}
DOB: {(datetime.now() - timedelta(days=patient_profile['age']*365)).strftime('%m/%d/%Y')}
Patient ID: {patient_profile['patient_id']}
Date of Service: {date.strftime('%m/%d/%Y')}
Ordering Physician: Dr. {random.choice(['Martinez', 'Chen', 'Patel', 'Davis'])}

COMPLETE METABOLIC PANEL:
Glucose, Fasting          {glucose_fasting} mg/dL        [70-100]     {'HIGH' if glucose_fasting > 100 else ''}
BUN                       {random.randint(15, 45)} mg/dL         [7-25]       {'HIGH' if random.random() > 0.7 else ''}
Creatinine               {round(random.uniform(0.8, 2.5), 1)} mg/dL        [0.6-1.2]    {'HIGH' if random.random() > 0.6 else ''}
Sodium                   {random.randint(135, 145)} mEq/L        [135-145]
Potassium                {round(random.uniform(3.5, 5.0), 1)} mEq/L         [3.5-5.0]
Chloride                 {random.randint(95, 108)} mEq/L        [95-108]

LIPID PANEL:
Total Cholesterol        {random.randint(180, 280)} mg/dL        [<200]       {'HIGH' if random.random() > 0.4 else ''}
HDL Cholesterol          {random.randint(35, 80)} mg/dL         [>40]
LDL Cholesterol          {random.randint(100, 180)} mg/dL        [<100]       {'HIGH' if random.random() > 0.5 else ''}
Triglycerides           {random.randint(120, 300)} mg/dL        [<150]       {'HIGH' if random.random() > 0.4 else ''}

DIABETES MONITORING:
Hemoglobin A1c           {hba1c}%              [<7.0%]      {'HIGH' if hba1c > 7.0 else ''}

Results reviewed and approved by Dr. {random.choice(['Johnson', 'Williams', 'Brown', 'Garcia'])}, MD
Lab Director: {random.choice(['Regional Medical Center', 'City General Hospital', 'Valley Health Labs'])}"""

        # Write TXT
        txt_filename = f"{date.strftime('%Y-%m-%d')}_lab_report.txt"
        txt_path = output_dir / "lab_reports" / txt_filename
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        txt_path.write_text(lab_report, encoding="utf-8")

        # Also write PDF if available
        pdf_path = output_dir / "lab_reports" / f"{date.strftime('%Y-%m-%d')}_lab_report.pdf"
        self._write_pdf_safe(lab_report, pdf_path)
        
        return str(pdf_path if pdf_path.exists() else txt_path)
    
    def generate_prescription_record(self, patient_profile: Dict, date: datetime, output_dir: Path) -> str:
        """Generate prescription/medication record"""
        
        prompt = f"""Generate a realistic prescription record for:

Patient: {patient_profile['name']} (Age: {patient_profile['age']})
Condition: {patient_profile['primary_condition']}
Current Medications: {', '.join(patient_profile['medications'])}
Date: {date.strftime('%B %d, %Y')}

Include:
1. Prescribing physician information
2. Medication details (name, strength, quantity, directions)  
3. Refills authorized
4. Generic substitution allowed/not allowed
5. Patient counseling notes
6. Pharmacy information

Format as a professional prescription record with proper medical abbreviations."""

        prescription = self._call_llm(prompt, max_tokens=600)
        
        if not prescription:
            # Fallback prescription
            med = random.choice(patient_profile['medications'])
            prescription = f"""PRESCRIPTION RECORD

Patient: {patient_profile['name']}
DOB: {(datetime.now() - timedelta(days=patient_profile['age']*365)).strftime('%m/%d/%Y')}
Address: 123 Main St, City, State 12345
Phone: (555) 123-4567

Prescriber: Dr. {random.choice(['Anderson', 'Thompson', 'Wilson', 'Taylor'])}
DEA#: BA1234567    NPI: 1234567890
Address: 456 Medical Plaza, Suite 200
Phone: (555) 987-6543

Date: {date.strftime('%m/%d/%Y')}

Rx: {med} {random.choice(['25mg', '50mg', '100mg', '500mg', '10mg'])}
Sig: Take {random.choice(['1', '2'])} tablet{'s' if random.random() > 0.5 else ''} by mouth {random.choice(['daily', 'twice daily', 'three times daily'])}
     {'with food' if random.random() > 0.5 else 'on empty stomach'}
Quantity: {random.choice(['30', '60', '90'])} tablets
Refills: {random.choice(['3', '5', '0'])}
Generic Substitution: {'Allowed' if random.random() > 0.3 else 'Not Allowed'}

Patient Counseling:
- {'Take with food to reduce stomach upset' if random.random() > 0.5 else 'Monitor blood sugar regularly'}
- {'Report any unusual side effects' if random.random() > 0.4 else 'Follow up in 3 months'}
- Store at room temperature

Dispensed by: Regional Pharmacy
Pharmacist: Dr. {random.choice(['Lee', 'Kumar', 'Rodriguez', 'Kim'])}
Date Filled: {date.strftime('%m/%d/%Y')}"""

        filename = f"{date.strftime('%Y-%m-%d')}_prescription.txt"
        filepath = output_dir / "prescriptions" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            f.write(prescription)
        
        return str(filepath)
    
    def generate_discharge_summary(self, patient_profile: Dict, date: datetime, output_dir: Path) -> str:
        """Generate hospital discharge summary"""
        
        prompt = f"""Generate a realistic hospital discharge summary for:

Patient: {patient_profile['name']} (Age: {patient_profile['age']})
Primary Diagnosis: {patient_profile['primary_condition']}
Secondary Diagnoses: {', '.join(patient_profile['secondary_conditions'])}
Discharge Date: {date.strftime('%B %d, %Y')}

Include:
1. Admission/Discharge dates
2. Attending physician
3. Principal and secondary diagnoses
4. Hospital course summary
5. Discharge medications
6. Activity restrictions
7. Follow-up appointments
8. Patient instructions

Use proper medical terminology and format."""

        discharge_summary = self._call_llm(prompt, max_tokens=800)
        
        if not discharge_summary:
            # Fallback discharge summary
            admit_date = date - timedelta(days=random.randint(2, 7))
            discharge_summary = f"""DISCHARGE SUMMARY

Patient: {patient_profile['name']}
MRN: {patient_profile['patient_id']}
DOB: {(datetime.now() - timedelta(days=patient_profile['age']*365)).strftime('%m/%d/%Y')}

Admission Date: {admit_date.strftime('%m/%d/%Y')}
Discharge Date: {date.strftime('%m/%d/%Y')}
Length of Stay: {(date - admit_date).days} days

Attending Physician: Dr. {random.choice(['Miller', 'Davis', 'Wilson', 'Moore'])}
Primary Care Physician: Dr. {random.choice(['Brown', 'Jones', 'Garcia', 'Rodriguez'])}

PRINCIPAL DIAGNOSIS: {patient_profile['primary_condition']}

SECONDARY DIAGNOSES:
{chr(10).join([f'- {condition}' for condition in patient_profile['secondary_conditions']])}

HOSPITAL COURSE:
Patient admitted for management of {patient_profile['primary_condition']}. {'Responded well to treatment' if random.random() > 0.3 else 'Required adjustment of medication regimen'}. Vital signs stabilized and patient demonstrated good understanding of discharge instructions.

DISCHARGE MEDICATIONS:
{chr(10).join([f'- {med}' for med in patient_profile['medications'][:3]])}

ACTIVITY: {'No restrictions' if random.random() > 0.4 else 'Light activity only for 1 week'}

FOLLOW-UP:
- Primary Care Physician in 1-2 weeks
- {'Specialist consultation as needed' if random.random() > 0.5 else 'Endocrinology in 1 month'}

PATIENT EDUCATION:
Patient and family educated regarding medication compliance, dietary modifications, and when to seek medical attention.

Electronically signed by:
Dr. {random.choice(['Thompson', 'Anderson', 'White', 'Harris'])}, MD
Date: {date.strftime('%m/%d/%Y %H:%M')}"""

        # Write TXT
        txt_filename = f"{date.strftime('%Y-%m-%d')}_discharge_summary.txt"
        txt_path = output_dir / "discharge_summaries" / txt_filename
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        txt_path.write_text(discharge_summary, encoding="utf-8")

        # Also write PDF if available
        pdf_path = output_dir / "discharge_summaries" / f"{date.strftime('%Y-%m-%d')}_discharge_summary.pdf"
        self._write_pdf_safe(discharge_summary, pdf_path)
        
        return str(pdf_path if pdf_path.exists() else txt_path)
    
    def generate_patient_documents(self, patient_id: str, num_reports: int = 5) -> Dict[str, Any]:
        """Generate all document types for a single patient"""
        print(f"\n👤 Generating documents for Patient {patient_id}")
        
        # Create patient profile
        patient_profile = self._generate_patient_profile(patient_id)
        patient_dir = self.output_dir / f"patient_{patient_id.zfill(3)}"
        
        print(f"   Name: {patient_profile['name']}")
        print(f"   Age: {patient_profile['age']} | Condition: {patient_profile['primary_condition']}")
        
        generated_files = []
        
        # Generate documents over the past 6 months
        start_date = datetime.now() - timedelta(days=180)
        
        for i in range(num_reports):
            # Spread documents over time
            doc_date = start_date + timedelta(days=random.randint(0, 180))
            
            # Generate different types of documents
            document_types = [
                ("vitals", self.generate_vitals_json),
                ("clinical_note", self.generate_clinical_note),
                ("lab_report", self.generate_lab_report),
                ("prescription", self.generate_prescription_record),
            ]
            
            # Occasionally add discharge summary
            if random.random() > 0.8:
                document_types.append(("discharge_summary", self.generate_discharge_summary))
            
            # Generate 2-3 document types per visit
            selected_types = random.sample(document_types, random.randint(2, min(3, len(document_types))))
            
            print(f"   📅 {doc_date.strftime('%Y-%m-%d')}: Generating {len(selected_types)} documents")
            
            for doc_type, generator_func in selected_types:
                try:
                    filepath = generator_func(patient_profile, doc_date, patient_dir)
                    generated_files.append({
                        'type': doc_type,
                        'date': doc_date.isoformat(),
                        'filepath': filepath,
                        'filename': Path(filepath).name
                    })
                    print(f"      ✅ {doc_type}: {Path(filepath).name}")
                except Exception as e:
                    print(f"      ❌ {doc_type}: Error - {e}")
        
        # Save patient summary
        summary = {
            'patient_profile': patient_profile,
            'generated_documents': generated_files,
            'generation_date': datetime.now().isoformat(),
            'total_documents': len(generated_files)
        }
        
        summary_file = patient_dir / "patient_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"   📋 Generated {len(generated_files)} documents total")
        return summary
    
    def generate_batch_documents(self, num_patients: int = 10, reports_per_patient: int = 5, start_id: int = 1):
        """Generate documents for multiple patients"""
        print(f"\n🏥 GENERATING MEDICAL DOCUMENTS FOR {num_patients} PATIENTS")
        print(f"📊 Target: {reports_per_patient} reports per patient = {num_patients * reports_per_patient} total documents")
        print("=" * 70)
        
        # Test LLM connection
        test_response = self._call_llm("Say 'LLM connection successful'")
        if test_response:
            print(f"✅ LLM Connection: Working ({self.llm_model})")
        else:
            print(f"⚠️ LLM Connection: Failed - Using fallback text generation")
        
        all_summaries = []
        total_docs = 0
        
        for patient_num in range(0, num_patients):
            patient_id = str(start_id + patient_num).zfill(3)
            
            try:
                summary = self.generate_patient_documents(patient_id, reports_per_patient)
                all_summaries.append(summary)
                total_docs += summary['total_documents']
                
            except Exception as e:
                print(f"❌ Patient {patient_id}: Generation failed - {e}")
        
        # Create master index
        master_index = {
            'generation_summary': {
                'total_patients': len(all_summaries),
                'total_documents': total_docs,
                'generation_date': datetime.now().isoformat(),
                'generator_version': '1.0',
                'llm_model': self.llm_model
            },
            'patients': all_summaries
        }
        
        index_file = self.output_dir / "document_index.json"
        with open(index_file, 'w') as f:
            json.dump(master_index, f, indent=2)
        
        print("\n" + "=" * 70)
        print(f"🎉 GENERATION COMPLETE!")
        print(f"👥 Patients: {len(all_summaries)}")
        print(f"📄 Total Documents: {total_docs}")
        print(f"📁 Output Directory: {self.output_dir}")
        print(f"📋 Master Index: {index_file}")
        print("\n🚀 Ready to test with VisitIQ application!")
        
        return master_index

    def _write_pdf_safe(self, text: str, out_path: Path):
        """Best-effort PDF writer using PyMuPDF; no-op if unavailable."""
        try:
            if not self._pdf_available:
                return
            import fitz
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)  # A4
            rect = fitz.Rect(50, 50, 545, 792)
            page.insert_textbox(rect, text, fontname="helv", fontsize=11, align=0)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(out_path))
            doc.close()
        except Exception:
            pass

def main():
    parser = argparse.ArgumentParser(description="Generate realistic medical documents for VisitIQ testing")
    parser.add_argument("--patients", type=int, default=10, help="Number of patients to generate (default: 10)")
    parser.add_argument("--reports-per-patient", type=int, default=5, help="Number of reports per patient (default: 5)")
    parser.add_argument("--output-dir", type=str, default="data/patient_documents", help="Output directory")
    parser.add_argument("--llm-url", type=str, default="http://localhost:11434", help="LLM base URL")
    parser.add_argument("--llm-model", type=str, default="llama3", help="LLM model name")
    parser.add_argument("--start-id", type=int, default=1, help="Starting patient ID (e.g., 151)")
    
    args = parser.parse_args()
    
    print("🏥 MEDICAL DOCUMENT GENERATOR")
    print("=" * 50)
    print(f"Configuration:")
    print(f"  Patients: {args.patients}")
    print(f"  Reports per patient: {args.reports_per_patient}")
    print(f"  Output directory: {args.output_dir}")
    print(f"  LLM: {args.llm_model} @ {args.llm_url}")
    
    generator = MedicalDocumentGenerator(
        output_dir=args.output_dir,
        llm_base_url=args.llm_url,
        llm_model=args.llm_model
    )
    
    generator.generate_batch_documents(args.patients, args.reports_per_patient, start_id=args.start_id)

if __name__ == "__main__":
    main()
