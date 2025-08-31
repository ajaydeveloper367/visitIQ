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
        
        print("\n📊 Data Generation Summary:")
        print(f"   • {len(patient_data)} patients")
        print(f"   • {len(physician_data)} physicians")
        print(f"   • {len(schedule_data)} schedules")
        print(f"   • {len(slot_data)} appointment slots")
        print(f"   • {weeks} weeks of availability")
        
        print(f"\n💾 Files saved to: {os.path.abspath(self.data_dir)}/")
        print("🎉 Healthcare data generation complete!")

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
