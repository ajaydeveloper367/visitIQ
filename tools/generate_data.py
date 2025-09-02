#!/usr/bin/env python3
"""
Healthcare Data Generator
Generates realistic patient and physician data for the VisitIQ system
"""

import json
import csv
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random
import numpy as np

# US-based names for realistic data
FIRST_NAMES = [
    'James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda',
    'David', 'Elizabeth', 'William', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica',
    'Thomas', 'Sarah', 'Christopher', 'Karen', 'Charles', 'Nancy', 'Daniel', 'Lisa',
    'Matthew', 'Helen', 'Anthony', 'Sandra', 'Mark', 'Donna', 'Donald', 'Carol',
    'Steven', 'Ruth', 'Paul', 'Sharon', 'Andrew', 'Michelle', 'Joshua', 'Laura',
    'Kenneth', 'Sarah', 'Kevin', 'Kimberly', 'Brian', 'Deborah', 'George', 'Dorothy',
    'Edward', 'Lisa', 'Ronald', 'Nancy', 'Timothy', 'Karen', 'Jason', 'Betty',
    'Jeffrey', 'Helen', 'Ryan', 'Sandra', 'Jacob', 'Donna', 'Gary', 'Carol'
]

LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
    'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
    'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson',
    'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson', 'Walker',
    'Young', 'Allen', 'King', 'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill', 'Flores',
    'Green', 'Adams', 'Nelson', 'Baker', 'Hall', 'Rivera', 'Campbell', 'Mitchell',
    'Carter', 'Roberts', 'Gomez', 'Phillips', 'Evans', 'Turner', 'Diaz', 'Parker'
]

DOCTOR_TITLES = ['Dr.', 'Dr.', 'Dr.', 'Professor']  # Weighted toward Dr.

SPECIALTIES = [
    {'name': 'Family Medicine', 'dept': 'Primary Care'},
    {'name': 'Endocrinology', 'dept': 'Internal Medicine'}, 
    {'name': 'Cardiology', 'dept': 'Cardiovascular Medicine'},
    {'name': 'Nephrology', 'dept': 'Internal Medicine'},
    {'name': 'Internal Medicine', 'dept': 'Internal Medicine'},
    {'name': 'Dermatology', 'dept': 'Dermatology'},
    {'name': 'Orthopedics', 'dept': 'Orthopedic Surgery'},
    {'name': 'Neurology', 'dept': 'Neurosciences'}
]

CONDITIONS = [
    'Type 1 Diabetes', 'Type 2 Diabetes', 'Prediabetes', 'Gestational Diabetes',
    'Hypertension', 'Hyperlipidemia', 'Obesity', 'Metabolic Syndrome',
    'Chronic Kidney Disease', 'Heart Disease', 'Stroke History', 'Peripheral Neuropathy'
]

MEDICAL_HISTORY = [
    'Family history of diabetes', 'Hypertension', 'High cholesterol', 'Smoking history',
    'Previous stroke', 'Heart attack history', 'CKD stage 3', 'Diabetic neuropathy',
    'Retinopathy', 'Peripheral vascular disease', 'Sleep apnea', 'Depression'
]

class DataGenerator:
    """Generates healthcare data for VisitIQ system"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        random.seed(42)  # For reproducible data
    
    def generate_patients(self, count: int = 50) -> List[Dict[str, Any]]:
        """Generate patient data"""
        patients = []
        
        for i in range(1, count + 1):
            # Basic demographics
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            age = random.randint(18, 85)
            
            # Condition (weighted toward diabetes for healthcare focus)
            condition_weights = [0.3, 0.4, 0.1, 0.05] + [0.15/8] * 8
            condition = random.choices(CONDITIONS, weights=condition_weights)[0]
            
            # Realistic vitals based on condition
            if 'Diabetes' in condition:
                glucose = random.randint(80, 450)  # Wide range for prioritization
                if glucose > 400:
                    bp_sys = random.randint(160, 200)  # Often comorbid
                    bp_dia = random.randint(90, 120)
                elif glucose > 300:
                    bp_sys = random.randint(140, 180)
                    bp_dia = random.randint(85, 110)
                else:
                    bp_sys = random.randint(110, 160)
                    bp_dia = random.randint(70, 95)
            else:
                glucose = random.randint(80, 140)
                bp_sys = random.randint(110, 180)
                bp_dia = random.randint(70, 110)
            
            heart_rate = random.randint(60, 120)
            bmi = round(random.uniform(18.5, 45.0), 1)
            
            # Medical history (1-3 conditions)
            num_history = random.randint(1, 3)
            history = '; '.join(random.sample(MEDICAL_HISTORY, num_history))
            
            # Clinical notes
            notes_options = [
                "Patient reports good medication adherence",
                "Needs dietary counseling", 
                "Foot exam due",
                "Eye exam overdue",
                "Reports occasional dizziness",
                "Difficulty with glucose monitoring",
                "Medication side effects reported",
                "Weight loss goals discussed",
                "Exercise program recommended",
                "Follow-up in 3 months"
            ]
            notes = random.choice(notes_options)
            
            patient = {
                'patient_id': i,
                'name': f"{first_name} {last_name}",
                'age': age,
                'condition': condition,
                'glucose_mg_dL': glucose,
                'bp_systolic': bp_sys,
                'bp_diastolic': bp_dia,
                'heart_rate': heart_rate,
                'bmi': bmi,
                'notes': notes,
                'history': history
            }
            
            patients.append(patient)
        
        return patients
    
    def generate_physicians(self, count: int = 12) -> List[Dict[str, Any]]:
        """Generate physician data"""
        physicians = []
        used_names = set()
        
        for i in range(1, count + 1):
            # Generate unique name
            while True:
                first_name = random.choice(FIRST_NAMES)
                last_name = random.choice(LAST_NAMES)
                full_name = f"{first_name} {last_name}"
                if full_name not in used_names:
                    used_names.add(full_name)
                    break
            
            title = random.choice(DOCTOR_TITLES)
            specialty_info = random.choice(SPECIALTIES)
            
            # Generate qualifications based on specialty
            base_quals = ['MD']
            if specialty_info['name'] == 'Family Medicine':
                base_quals.append('Board Certified Family Medicine')
            elif specialty_info['name'] == 'Endocrinology':
                base_quals.extend(['Board Certified Internal Medicine', 'Board Certified Endocrinology'])
            elif specialty_info['name'] == 'Cardiology':
                base_quals.extend(['Board Certified Internal Medicine', 'Board Certified Cardiology'])
            else:
                base_quals.append(f"Board Certified {specialty_info['name']}")
            
            # Contact info
            phone = f"+1-555-{random.randint(1000, 9999)}"
            email = f"{first_name.lower()}.{last_name.lower()}@hospital.com"
            
            physician = {
                'id': f"prac-{i:03d}",
                'name': f"{title} {first_name} {last_name}",
                'specialty': specialty_info['name'],
                'department': specialty_info['dept'],
                'qualification': base_quals,
                'active': True,
                'contact_phone': phone,
                'contact_email': email
            }
            
            physicians.append(physician)
        
        return physicians
    
    def generate_schedules(self, physicians: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate schedule data for physicians"""
        schedules = []
        
        service_types_map = {
            'Family Medicine': ['general-consultation', 'preventive-care', 'chronic-disease'],
            'Endocrinology': ['diabetes-consultation', 'hormone-therapy', 'follow-up'],
            'Cardiology': ['cardiac-consultation', 'echo-study', 'stress-test'],
            'Nephrology': ['kidney-consultation', 'dialysis-eval', 'transplant-consult'],
            'Internal Medicine': ['internal-consult', 'comprehensive-exam', 'chronic-care'],
            'Dermatology': ['skin-exam', 'mole-check', 'dermatology-consult'],
            'Orthopedics': ['joint-eval', 'orthopedic-consult', 'post-op-check'],
            'Neurology': ['neuro-eval', 'headache-consult', 'neuro-follow-up']
        }
        
        for i, physician in enumerate(physicians, 1):
            specialty = physician['specialty']
            service_category = specialty.lower().replace(' ', '-')
            service_types = service_types_map.get(specialty, ['general-consultation'])
            
            schedule = {
                'id': f"sched-{i:03d}",
                'practitioner_id': physician['id'],
                'service_category': service_category,
                'service_type': service_types,
                'specialty': specialty,
                'planning_horizon': 30,
                'comment': f"{specialty} scheduling"
            }
            
            schedules.append(schedule)
        
        return schedules
    
    def generate_slots(self, physicians: List[Dict[str, Any]], schedules: List[Dict[str, Any]], 
                      weeks: int = 4) -> List[Dict[str, Any]]:
        """Generate appointment slots"""
        slots = []
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for week in range(weeks):
            for weekday in range(5):  # Monday-Friday
                current_date = start_date + timedelta(weeks=week, days=weekday)
                
                for physician in physicians:
                    physician_id = physician['id']
                    schedule = next((s for s in schedules if s['practitioner_id'] == physician_id), None)
                    
                    if not schedule:
                        continue
                    
                    # Generate slots for the day (9 AM - 5 PM, 30-min slots, skip lunch)
                    current_time = current_date.replace(hour=9, minute=0)
                    end_time = current_date.replace(hour=17, minute=0)
                    lunch_start = current_date.replace(hour=12, minute=0)
                    lunch_end = current_date.replace(hour=13, minute=0)
                    
                    while current_time < end_time:
                        # Skip lunch hour
                        if lunch_start <= current_time < lunch_end:
                            current_time = lunch_end
                            continue
                        
                        slot_end = current_time + timedelta(minutes=30)
                        if slot_end > end_time:
                            break
                        
                        slot_id = f"slot-{physician_id}-{current_time.strftime('%Y%m%d-%H%M')}"
                        
                        slot = {
                            'id': slot_id,
                            'schedule_id': schedule['id'],
                            'practitioner_id': physician_id,
                            'status': 'free',
                            'start': current_time.isoformat(),
                            'end': slot_end.isoformat(),
                            'service_category': schedule['service_category'],
                            'service_type': schedule['service_type'],
                            'specialty': schedule['specialty'],
                            'appointment_type': 'routine',
                            'comment': None,
                            'overbooked': False
                        }
                        
                        slots.append(slot)
                        current_time = slot_end
        
        return slots
    
    def save_to_csv(self, data: List[Dict[str, Any]], filename: str):
        """Save data to CSV file"""
        if not data:
            return
        
        filepath = os.path.join(self.data_dir, filename)
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        print(f"✅ Saved {len(data)} records to {filepath}")
    
    def save_to_json(self, data: List[Dict[str, Any]], filename: str):
        """Save data to JSON file"""
        filepath = os.path.join(self.data_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved {len(data)} records to {filepath}")
    
    def generate_all_data(self, 
                         patients: int = 50, 
                         physicians: int = 12, 
                         weeks: int = 4):
        """Generate all healthcare data"""
        print("🏥 VisitIQ Healthcare Data Generator")
        print("=" * 50)
        
        # Generate physicians first (needed for schedules/slots)
        print(f"👨‍⚕️ Generating {physicians} physicians...")
        physician_data = self.generate_physicians(physicians)
        
        print(f"📅 Generating schedules...")
        schedule_data = self.generate_schedules(physician_data)
        
        print(f"⏰ Generating {weeks} weeks of appointment slots...")
        slot_data = self.generate_slots(physician_data, schedule_data, weeks)
        
        print(f"👥 Generating {patients} patients...")
        patient_data = self.generate_patients(patients)
        
        # Save CSV files (for app compatibility)
        self.save_to_csv(patient_data, 'patients.csv')
        
        # Save JSON files (for FHIR compliance)
        self.save_to_json(physician_data, 'practitioners.json')
        self.save_to_json(schedule_data, 'schedules.json')
        self.save_to_json(slot_data, 'slots.json')
        
        # Create empty appointments file
        self.save_to_json([], 'appointments.json')
        
        # Persist to vector stores (Chroma + lightweight local files)
        try:
            self._persist_to_vectorstores(patient_data, physician_data)
        except Exception as e:
            print(f"⚠️ Skipped vectorstore persistence due to error: {e}")

        print("\n📊 Data Generation Summary:")
        print(f"   • {len(patient_data)} patients")
        print(f"   • {len(physician_data)} physicians")
        print(f"   • {len(schedule_data)} schedules")
        print(f"   • {len(slot_data)} appointment slots")
        print(f"   • {weeks} weeks of availability")
        
        print(f"\n💾 Files saved to: {os.path.abspath(self.data_dir)}/")
        print("🎉 Healthcare data generation complete!")

    def _persist_to_vectorstores(self, patient_data, physician_data):
        """Create/update local vectorstore files and ChromaDB collections."""
        # 1) Build lightweight local vectorstore files from patients.csv (embeddings.npy/docs.json/ids.json)
        try:
            from src.prioritizer import build_vectorstore_from_csv, PERSIST_DIR, EMBEDDING_MODEL
        except Exception:
            # Fallback env/defaults to keep working even if import path differs
            import os as _os
            PERSIST_DIR = _os.getenv("CHROMA_DIR", "chroma_db")
            EMBEDDING_MODEL = _os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
            build_vectorstore_from_csv = None

        persist_dir = os.getenv("CHROMA_DIR", "chroma_db")
        os.makedirs(persist_dir, exist_ok=True)

        patients_csv_path = os.path.join(self.data_dir, 'patients.csv')
        docs_texts = None
        doc_ids = None
        doc_embs = None

        # Build or read local vectorstore artifacts
        try:
            if build_vectorstore_from_csv is not None:
                build_vectorstore_from_csv(patients_csv_path, persist_directory=persist_dir)
            # Load back artifacts
            docs_path = os.path.join(persist_dir, 'docs.json')
            ids_path = os.path.join(persist_dir, 'ids.json')
            emb_path = os.path.join(persist_dir, 'embeddings.npy')
            if os.path.exists(docs_path) and os.path.exists(ids_path) and os.path.exists(emb_path):
                with open(docs_path, 'r', encoding='utf-8') as f:
                    docs_texts = json.load(f)
                with open(ids_path, 'r', encoding='utf-8') as f:
                    doc_ids = json.load(f)
                doc_embs = np.load(emb_path)
        except Exception as e:
            print(f"⚠️ Local vectorstore build/load failed: {e}")

        # 2) Upsert into ChromaDB collections
        try:
            import chromadb
            from chromadb.config import Settings as _ChromaSettings
            from sentence_transformers import SentenceTransformer

            client = chromadb.Client(_ChromaSettings(chroma_db_impl="duckdb+parquet", persist_directory=persist_dir))

            # Helper to recreate or clear a collection
            def get_clean_collection(name: str):
                try:
                    coll = client.get_collection(name)
                    try:
                        existing = coll.get()
                        ids_to_delete = existing.get('ids') or []
                        if ids_to_delete:
                            coll.delete(ids=ids_to_delete)
                    except Exception:
                        pass
                    return coll
                except Exception:
                    try:
                        client.delete_collection(name)
                    except Exception:
                        pass
                    return client.create_collection(name)

            # a) General knowledge collection used by RAG queries
            if docs_texts is not None and doc_ids is not None and doc_embs is not None:
                coll_docs = get_clean_collection('visitiq_docs')
                # Ensure embeddings shape is list of lists
                embeddings_list = doc_embs.tolist() if not isinstance(doc_embs, list) else doc_embs
                coll_docs.add(ids=[str(i) for i in doc_ids], documents=docs_texts, embeddings=embeddings_list)
                print(f"✅ ChromaDB: Upserted {len(docs_texts)} docs into 'visitiq_docs'")
            else:
                print("ℹ️ Skipping 'visitiq_docs' upsert (no local docs/embeddings available)")

            # b) Patients collection for listing (with helpful metadata)
            try:
                coll_patients = get_clean_collection('patients')
                # Reuse patient docs/embeddings if available; otherwise compute lightweight embeddings
                if docs_texts is not None and doc_embs is not None and doc_ids is not None:
                    metadatas = []
                    for p in patient_data:
                        metadatas.append({
                            'patient_id': str(p.get('patient_id')),
                            'patient_name': p.get('name'),
                            'condition': p.get('condition')
                        })
                    coll_patients.add(
                        ids=[f"patient-{pid}" for pid in doc_ids],
                        documents=docs_texts,
                        embeddings=doc_embs.tolist() if not isinstance(doc_embs, list) else doc_embs,
                        metadatas=metadatas
                    )
                else:
                    # Compute quick embeddings for minimal viability
                    model = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
                    docs_texts = [
                        f"Patient ID: {p.get('patient_id')}. Name: {p.get('name')}. Age: {p.get('age')}. Condition: {p.get('condition')}" 
                        for p in patient_data
                    ]
                    embs = model.encode(docs_texts, show_progress_bar=False)
                    coll_patients.add(
                        ids=[f"patient-{p.get('patient_id')}" for p in patient_data],
                        documents=docs_texts,
                        embeddings=embs.tolist(),
                        metadatas=[{
                            'patient_id': str(p.get('patient_id')),
                            'patient_name': p.get('name'),
                            'condition': p.get('condition')
                        } for p in patient_data]
                    )
                print(f"✅ ChromaDB: Upserted {len(patient_data)} patients into 'patients'")
            except Exception as e:
                print(f"⚠️ Patients collection upsert failed: {e}")

            # c) Physicians collection with metadata
            try:
                coll_phys = get_clean_collection('physicians')
                model = None
                try:
                    model = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
                except Exception:
                    model = None
                phys_docs = [
                    f"{p.get('name')} - {p.get('specialty')} ({p.get('department')})"
                    for p in physician_data
                ]
                phys_ids = [p.get('id') for p in physician_data]
                phys_metas = [
                    {
                        'name': p.get('name'),
                        'specialty': p.get('specialty'),
                        'department': p.get('department')
                    } for p in physician_data
                ]
                if model is not None:
                    phys_embs = model.encode(phys_docs, show_progress_bar=False)
                    coll_phys.add(ids=phys_ids, documents=phys_docs, embeddings=phys_embs.tolist(), metadatas=phys_metas)
                else:
                    coll_phys.add(ids=phys_ids, documents=phys_docs, metadatas=phys_metas)
                print(f"✅ ChromaDB: Upserted {len(physician_data)} physicians into 'physicians'")
            except Exception as e:
                print(f"⚠️ Physicians collection upsert failed: {e}")

        except Exception as e:
            print(f"⚠️ ChromaDB persistence skipped: {e}")

def main():
    """Main function with CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate healthcare data for VisitIQ')
    parser.add_argument('--patients', type=int, default=50, 
                       help='Number of patients to generate (default: 50)')
    parser.add_argument('--physicians', type=int, default=12,
                       help='Number of physicians to generate (default: 12)')
    parser.add_argument('--weeks', type=int, default=4,
                       help='Number of weeks of slots to generate (default: 4)')
    parser.add_argument('--data-dir', type=str, default='data',
                       help='Directory to save data files (default: data)')
    
    args = parser.parse_args()
    
    # Create generator and generate data
    generator = DataGenerator(args.data_dir)
    generator.generate_all_data(args.patients, args.physicians, args.weeks)

if __name__ == '__main__':
    main()
