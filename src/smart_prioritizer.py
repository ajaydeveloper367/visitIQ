"""
Smart Prioritizer - Enhanced prioritization that considers available slots
Integrates with FHIR slots and provides slot-aware patient prioritization
"""

import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from .prioritizer import rag_prioritize_row, rule_based_priority_row, rag_prioritize_batch
from .slot_manager import get_slot_manager, SlotManager, FHIRSlot, FHIRPractitioner
from .fhir_models import SlotStatus

class SmartPrioritizer:
    """
    Enhanced prioritizer that considers available slots when prioritizing patients
    """
    
    def __init__(self, slot_manager: Optional[SlotManager] = None):
        self.slot_manager = slot_manager or get_slot_manager()
        
        # Priority weights for slot matching
        self.priority_weights = {
            'Emergency': 100,
            'High': 75,
            'Medium': 50, 
            'Low': 25
        }
        
        # Specialty matching weights
        self.specialty_matching = {
            'diabetes': ['Endocrinology', 'Family Medicine'],
            'cardiovascular': ['Cardiology', 'Family Medicine'],
            'general': ['Family Medicine', 'Internal Medicine']
        }
    
    def prioritize_patients_for_slots(
        self,
        patients: List[Dict[str, Any]],
        practitioner_id: Optional[str] = None,
        target_date: Optional[date] = None,
        max_patients: Optional[int] = None,
        consider_specialty_match: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Prioritize patients considering available slots
        Returns up to the number of available slots (or max_patients if specified)
        """
        
        # Get available slot count
        if max_patients is None:
            available_slots = self.slot_manager.count_available_slots(
                practitioner_id=practitioner_id,
                target_date=target_date
            )
            max_patients = available_slots
        
        if max_patients <= 0:
            return []
        
        # Get practitioner info for specialty matching
        practitioner = None
        if practitioner_id:
            practitioner = self.slot_manager.get_practitioner(practitioner_id)
        
        # 🚀 OPTIMIZED: Batch process all patients for 5-10x performance improvement
        
        # LLM-FIRST medical prioritization with FAST batch processing!
        # Use LLM batch processing (1 call for all patients), fallback to rules if batch fails
        try:
            # ⚡ FAST: Process all patients in one batch LLM call
            priority_results = rag_prioritize_batch(patients)
            
            # Add reasoning source to all results from successful batch
            for result in priority_results:
                result['reasoning_source'] = '🧠 LLM Medical Intelligence'
            
            print(f"✅ LLM Batch Processing: {len(priority_results)} patients in 1 call")
            llm_success_count = len(priority_results)
            rule_fallback_count = 0
            
        except Exception as e:
            # Fallback: Use rule-based for all patients if LLM batch fails
            print(f"⚠️ LLM batch processing failed: {e}")
            print("🔄 Falling back to rule-based scoring for all patients")
            
            priority_results = []
            for patient in patients:
                priority_result = rule_based_priority_row(patient)
                priority_result['reasoning_source'] = '📋 Clinical Rules (LLM Batch Failed)'
                priority_results.append(priority_result)
            
            llm_success_count = 0
            rule_fallback_count = len(priority_results)
        
        print(f"🧠 LLM Medical Intelligence: {llm_success_count} patients")
        print(f"📋 Rule-based Fallback: {rule_fallback_count} patients")
        
        # Process all patients in vectorized operations where possible
        prioritized_patients = []
        for i, (patient, priority_result) in enumerate(zip(patients, priority_results)):
            # Enhanced patient record with slot-aware scoring
            enhanced_patient = {
                **patient,
                'base_priority_level': priority_result.get('priority_level', 'Low'),
                'base_score': priority_result.get('score', 0),
                'base_reasons': priority_result.get('reasons', []),
                'reasoning_source': priority_result.get('reasoning_source', '❓ Unknown'),
                'slot_aware_score': 0,
                'specialty_match_score': 0,
                'final_score': 0,
                'recommended_for_booking': False
            }
            
            # Calculate slot-aware score
            base_weight = self.priority_weights.get(enhanced_patient['base_priority_level'], 25)
            enhanced_patient['slot_aware_score'] = base_weight + enhanced_patient['base_score']
            
            # Add specialty matching score
            if consider_specialty_match and practitioner:
                specialty_score = self._calculate_specialty_match_score(patient, practitioner)
                enhanced_patient['specialty_match_score'] = specialty_score
                enhanced_patient['slot_aware_score'] += specialty_score
            
            # Add urgency modifiers
            urgency_modifier = self._calculate_urgency_modifier(patient, target_date)
            enhanced_patient['slot_aware_score'] += urgency_modifier
            
            enhanced_patient['final_score'] = enhanced_patient['slot_aware_score']
            
            prioritized_patients.append(enhanced_patient)
        
        # Sort by medical priority FIRST, then by final score
        # This ensures Emergency/High patients are always ranked higher than Low/Medium
        priority_order = {'Emergency': 4, 'High': 3, 'Medium': 2, 'Low': 1}
        prioritized_patients.sort(
            key=lambda x: (
                priority_order.get(x['base_priority_level'], 0),  # Medical priority first
                x['final_score']  # Then by calculated score
            ), 
            reverse=True
        )
        
        # Select top N patients for available slots
        selected_patients = prioritized_patients[:max_patients]
        
        # Mark selected patients as recommended for booking
        for patient in selected_patients:
            patient['recommended_for_booking'] = True
            
            # Add slot booking reasons
            booking_reasons = []
            if patient['base_priority_level'] in ['Emergency', 'High']:
                booking_reasons.append(f"High medical priority ({patient['base_priority_level']})")
            if patient.get('specialty_match_score', 0) > 0:
                booking_reasons.append("Good specialty match")
            if target_date and self._is_overdue_patient(patient):
                booking_reasons.append("Overdue for follow-up")
            
            patient['booking_reasons'] = booking_reasons
        
        return selected_patients
    
    def recommend_optimal_practitioner(
        self,
        patient: Dict[str, Any],
        target_date: Optional[date] = None,
        consider_availability: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Recommend optimal practitioners for a patient based on specialty match and availability
        """
        practitioners = self.slot_manager.get_practitioners()
        recommendations = []
        
        for practitioner in practitioners:
            # Calculate specialty match score
            specialty_score = self._calculate_specialty_match_score(patient, practitioner)
            
            # Get availability info
            available_slots = 0
            if consider_availability:
                available_slots = self.slot_manager.count_available_slots(
                    practitioner_id=practitioner.id,
                    target_date=target_date
                )
            
            # Calculate overall recommendation score
            recommendation_score = specialty_score
            if available_slots > 0:
                recommendation_score += min(available_slots * 5, 25)  # Bonus for availability
            
            recommendation = {
                'practitioner_id': practitioner.id,
                'practitioner_name': practitioner.name,
                'specialty': practitioner.specialty,
                'department': practitioner.department,
                'specialty_match_score': specialty_score,
                'available_slots': available_slots,
                'recommendation_score': recommendation_score,
                'recommended': recommendation_score > 50
            }
            
            recommendations.append(recommendation)
        
        # Sort by recommendation score
        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        
        return recommendations
    
    def get_slot_allocation_summary(
        self,
        patients: List[Dict[str, Any]],
        practitioner_id: Optional[str] = None,
        target_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Get summary of slot allocation for given patients and constraints
        """
        available_slots = self.slot_manager.count_available_slots(
            practitioner_id=practitioner_id,
            target_date=target_date
        )
        
        prioritized_patients = self.prioritize_patients_for_slots(
            patients, practitioner_id, target_date
        )
        
        # Count by priority levels
        priority_counts = {}
        for patient in prioritized_patients:
            level = patient.get('base_priority_level', 'Low')
            priority_counts[level] = priority_counts.get(level, 0) + 1
        
        # Identify waitlisted patients
        all_prioritized = self.prioritize_patients_for_slots(
            patients, practitioner_id, target_date, max_patients=len(patients)
        )
        waitlisted = all_prioritized[available_slots:] if available_slots < len(all_prioritized) else []
        
        practitioner_info = {}
        if practitioner_id:
            practitioner = self.slot_manager.get_practitioner(practitioner_id)
            if practitioner:
                practitioner_info = practitioner.to_dict()
        
        return {
            'total_patients': len(patients),
            'available_slots': available_slots,
            'patients_to_book': len(prioritized_patients),
            'patients_waitlisted': len(waitlisted),
            'priority_breakdown': priority_counts,
            'practitioner_info': practitioner_info,
            'utilization_rate': min(100, (len(prioritized_patients) / available_slots * 100)) if available_slots > 0 else 0,
            'waitlisted_patients': [
                {
                    'patient_id': p['patient_id'], 
                    'name': p['name'],
                    'priority': p['base_priority_level'],
                    'score': p['final_score']
                } for p in waitlisted[:10]  # Top 10 waitlisted
            ]
        }
    
    def _calculate_specialty_match_score(
        self, 
        patient: Dict[str, Any], 
        practitioner: FHIRPractitioner
    ) -> float:
        """Calculate how well a patient matches with practitioner's specialty"""
        patient_condition = str(patient.get('condition', '')).lower()
        patient_history = str(patient.get('history', '')).lower()
        practitioner_specialty = practitioner.specialty.lower()
        
        match_score = 0
        
        # Diabetes conditions
        if any(term in patient_condition for term in ['diabetes', 'diabetic']):
            if practitioner_specialty in ['endocrinology']:
                match_score += 30
            elif practitioner_specialty in ['family medicine', 'internal medicine']:
                match_score += 20
        
        # Cardiovascular conditions  
        if any(term in patient_history for term in ['heart', 'cardiac', 'stroke', 'hypertension']):
            if practitioner_specialty in ['cardiology']:
                match_score += 30
            elif practitioner_specialty in ['family medicine', 'internal medicine']:
                match_score += 15
        
        # Kidney/renal conditions
        if any(term in patient_history for term in ['ckd', 'kidney', 'renal']):
            if practitioner_specialty in ['nephrology']:
                match_score += 30
            elif practitioner_specialty in ['endocrinology', 'internal medicine']:
                match_score += 20
        
        # Pregnancy-related
        if 'gestational' in patient_condition:
            if practitioner_specialty in ['obstetrics', 'maternal-fetal medicine']:
                match_score += 30
            elif practitioner_specialty in ['endocrinology', 'family medicine']:
                match_score += 20
        
        # General medicine fallback
        if match_score == 0 and practitioner_specialty in ['family medicine', 'internal medicine']:
            match_score += 10
        
        return match_score
    
    def _calculate_urgency_modifier(
        self, 
        patient: Dict[str, Any], 
        target_date: Optional[date] = None
    ) -> float:
        """Calculate urgency modifiers based on patient condition and timing"""
        modifier = 0
        
        # Glucose-based urgency
        try:
            glucose = float(patient.get("glucose_mg_dL", 0) or 0)
            if glucose >= 400:  # Hyperglycemic emergency
                modifier += 50
            elif glucose >= 300:  # Very high
                modifier += 25
        except (ValueError, TypeError):
            pass
        
        # BP-based urgency
        try:
            sys_bp = float(patient.get("bp_systolic", 0) or 0)
            dia_bp = float(patient.get("bp_diastolic", 0) or 0)
            if sys_bp >= 180 or dia_bp >= 110:  # Hypertensive emergency
                modifier += 40
        except (ValueError, TypeError):
            pass
        
        # Age-based urgency
        try:
            age = int(patient.get("age", 0) or 0)
            if age >= 70:
                modifier += 15
            elif age >= 65:
                modifier += 10
        except (ValueError, TypeError):
            pass
        
        # History-based urgency
        history = str(patient.get("history", "")).lower()
        if any(term in history for term in ['stroke', 'heart attack', 'mi']):
            modifier += 20
        if 'ckd' in history:
            modifier += 15
        
        return modifier
    
    def _is_overdue_patient(self, patient: Dict[str, Any]) -> bool:
        """Check if patient is overdue for follow-up (placeholder logic)"""
        # This would typically check against last visit date
        # For now, use high-risk conditions as proxy
        condition = str(patient.get('condition', '')).lower()
        history = str(patient.get('history', '')).lower()
        
        # High-risk patients who should be seen regularly
        return any(term in condition + ' ' + history for term in [
            'type 1 diabetes', 'insulin', 'ckd', 'stroke', 'heart'
        ])

# ============ Convenience Functions ============

def prioritize_for_appointment_booking(
    patients_csv_path: str,
    practitioner_id: Optional[str] = None,
    target_date: Optional[date] = None,
    max_appointments: Optional[int] = None
) -> pd.DataFrame:
    """
    Convenience function to prioritize patients from CSV for appointment booking
    """
    # Load patients
    df = pd.read_csv(patients_csv_path)
    patients = df.to_dict('records')
    
    # Initialize smart prioritizer
    prioritizer = SmartPrioritizer()
    
    # Get prioritized patients for slots
    prioritized = prioritizer.prioritize_patients_for_slots(
        patients=patients,
        practitioner_id=practitioner_id,
        target_date=target_date,
        max_patients=max_appointments
    )
    
    # Convert back to DataFrame
    return pd.DataFrame(prioritized)

def get_practitioner_recommendations(
    patients_csv_path: str,
    target_date: Optional[date] = None
) -> pd.DataFrame:
    """
    Get practitioner recommendations for all patients
    """
    df = pd.read_csv(patients_csv_path)
    patients = df.to_dict('records')
    
    prioritizer = SmartPrioritizer()
    all_recommendations = []
    
    for patient in patients:
        recommendations = prioritizer.recommend_optimal_practitioner(
            patient, target_date
        )
        
        # Add patient info to each recommendation
        for rec in recommendations[:3]:  # Top 3 recommendations per patient
            rec.update({
                'patient_id': patient.get('patient_id'),
                'patient_name': patient.get('name'),
                'patient_condition': patient.get('condition')
            })
            all_recommendations.append(rec)
    
    return pd.DataFrame(all_recommendations)
