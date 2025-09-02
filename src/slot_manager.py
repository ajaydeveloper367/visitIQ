"""
Slot Manager - Handles FHIR slot operations, persistence, and scheduling logic
"""

import json
import os
import pandas as pd
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import asdict

from .fhir_models import (
    FHIRPractitioner, FHIRSchedule, FHIRSlot, FHIRAppointment,
    SlotStatus, AppointmentStatus
)

class SlotManager:
    """
    Manages FHIR slots, practitioners, schedules, and appointments
    Provides persistence layer and business logic for slot operations
    """
    
    def __init__(self, data_dir: str = "data", vector_dir: Optional[str] = None):
        self.data_dir = data_dir
        self.vector_dir = vector_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # File paths
        self.practitioners_file = os.path.join(data_dir, "practitioners.json")
        self.schedules_file = os.path.join(data_dir, "schedules.json") 
        self.slots_file = os.path.join(data_dir, "slots.json")
        self.appointments_file = os.path.join(data_dir, "appointments.json")
        
        # In-memory storage
        self._practitioners: Dict[str, FHIRPractitioner] = {}
        self._schedules: Dict[str, FHIRSchedule] = {}
        self._slots: Dict[str, FHIRSlot] = {}
        self._appointments: Dict[str, FHIRAppointment] = {}
        
        # Load existing data
        self.load_data()
        
        # Check if data exists, otherwise suggest data generation
        if not self._practitioners:
            print("⚠️  No healthcare data found!")
            print("📋 Please run the data generator first:")
            print("    python tools/generate_data.py")
            print("🏥 This will create physicians, schedules, and appointment slots.")
    
    # ============ Data Persistence ============
    
    def save_data(self):
        """Save all data to JSON files"""
        # Practitioners
        with open(self.practitioners_file, 'w') as f:
            json.dump([p.to_dict() for p in self._practitioners.values()], f, indent=2)
        
        # Schedules
        with open(self.schedules_file, 'w') as f:
            json.dump([s.to_dict() for s in self._schedules.values()], f, indent=2)
        
        # Slots
        with open(self.slots_file, 'w') as f:
            json.dump([s.to_dict() for s in self._slots.values()], f, indent=2)
        
        # Appointments
        with open(self.appointments_file, 'w') as f:
            json.dump([a.to_dict() for a in self._appointments.values()], f, indent=2)
    
    def load_data(self):
        """Load data from vector DB metadatas.json if present, otherwise JSON files"""
        # Prefer vector metadata if available (vector-first)
        meta_path = None
        if self.vector_dir:
            candidate = os.path.join(self.vector_dir, "metadatas.json")
            if os.path.exists(candidate):
                meta_path = candidate

        if meta_path:
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    metas = json.load(f)

                # Practitioners
                practitioners = [m for m in metas if m.get('type') == 'physician']
                self._practitioners = {}
                for p in practitioners:
                    pid = p.get('id') or p.get('practitioner_id') or p.get('name')
                    if not pid:
                        continue
                    self._practitioners[str(pid)] = FHIRPractitioner(
                        id=str(pid),
                        name=p.get('name', 'Unknown'),
                        specialty=p.get('specialty', p.get('department', 'General')),
                        department=p.get('department', p.get('specialty', 'General'))
                    )
                # Fallback to JSON practitioners if vector metadata lacks them
                if not self._practitioners and os.path.exists(self.practitioners_file):
                    try:
                        with open(self.practitioners_file, 'r') as f:
                            data = json.load(f)
                            self._practitioners = {p['id']: FHIRPractitioner(**p) for p in data}
                    except Exception:
                        self._practitioners = {}

                # Slots
                from datetime import datetime
                self._slots = {}
                slots = [m for m in metas if m.get('type') == 'slot']
                for s in slots:
                    sid = str(s.get('id'))
                    try:
                        start = datetime.fromisoformat(str(s.get('start'))) if s.get('start') else datetime.now()
                        end = datetime.fromisoformat(str(s.get('end'))) if s.get('end') else start
                    except Exception:
                        start = end = datetime.now()

                    status_raw = str(s.get('status', 'free')).upper()
                    status = getattr(SlotStatus, status_raw, SlotStatus.free)

                    slot = FHIRSlot(
                        id=sid,
                        schedule_id=s.get('schedule_id', f"sched-{s.get('practitioner_id','unknown')}"),
                        practitioner_id=str(s.get('practitioner_id', '')),
                        start=start,
                        end=end,
                        status=status,
                        service_category=str(s.get('specialty', 'General')).lower(),
                        service_type=s.get('service_type', [s.get('specialty', 'General')]) if isinstance(s.get('service_type'), list) else [s.get('specialty', 'General')],
                        specialty=s.get('specialty', 'General'),
                    )
                    self._slots[sid] = slot

                # Schedules are optional here; keep empty if not provided
                self._schedules = {}

                # Appointments remain as-is (empty at startup)
                self._appointments = {}

                return
            except Exception as e:
                print(f"⚠️ Vector metadata load failed, falling back to JSON files: {e}")

        # Fallback: JSON files under data_dir
        # Practitioners
        if os.path.exists(self.practitioners_file):
            with open(self.practitioners_file, 'r') as f:
                data = json.load(f)
                self._practitioners = {p['id']: FHIRPractitioner(**p) for p in data}
        
        # Schedules
        if os.path.exists(self.schedules_file):
            with open(self.schedules_file, 'r') as f:
                data = json.load(f)
                self._schedules = {s['id']: FHIRSchedule(**s) for s in data}
        
        # Slots
        if os.path.exists(self.slots_file):
            with open(self.slots_file, 'r') as f:
                raw = json.load(f)
                data: List[Dict[str, Any]] = []
                for s in raw:
                    # ensure required fields exist
                    s = dict(s)
                    s.setdefault('schedule_id', f"sched-{s.get('practitioner_id','unknown')}")
                    s.setdefault('service_category', str(s.get('specialty','General')).lower())
                    s.setdefault('service_type', [s.get('specialty','General')])
                    if isinstance(s.get('status'), str):
                        try:
                            SlotStatus(s['status'])
                        except Exception:
                            s['status'] = 'free'
                    data.append(s)

                self._slots = {s['id']: FHIRSlot.from_dict(s) for s in data}
        
        # Appointments
        if os.path.exists(self.appointments_file):
            with open(self.appointments_file, 'r') as f:
                data = json.load(f)
                self._appointments = {a['id']: FHIRAppointment.from_dict(a) for a in data}
    

    
    # ============ Practitioner Operations ============
    
    def get_practitioners(self) -> List[FHIRPractitioner]:
        """Get all practitioners"""
        return list(self._practitioners.values())
    
    def get_practitioner(self, practitioner_id: str) -> Optional[FHIRPractitioner]:
        """Get practitioner by ID"""
        return self._practitioners.get(practitioner_id)
    
    def get_practitioners_by_specialty(self, specialty: str) -> List[FHIRPractitioner]:
        """Get practitioners by specialty"""
        return [p for p in self._practitioners.values() 
                if p.specialty.lower() == specialty.lower()]
    
    # ============ Slot Operations ============
    
    def get_available_slots(
        self, 
        practitioner_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        specialty: Optional[str] = None
    ) -> List[FHIRSlot]:
        """Get available slots with optional filters"""
        slots = list(self._slots.values())
        
        # Filter by availability
        slots = [s for s in slots if s.is_available]
        
        # Filter by practitioner
        if practitioner_id:
            slots = [s for s in slots if s.practitioner_id == practitioner_id]
        
        # Filter by date range
        if date_from:
            slots = [s for s in slots if s.start >= date_from]
        if date_to:
            slots = [s for s in slots if s.start <= date_to]
        
        # Filter by specialty
        if specialty:
            slots = [s for s in slots if s.specialty.lower() == specialty.lower()]
        
        # Sort by start time
        slots.sort(key=lambda x: x.start)
        
        return slots
    
    def get_slots_for_date(
        self, 
        target_date: date,
        practitioner_id: Optional[str] = None
    ) -> List[FHIRSlot]:
        """Get all slots for a specific date"""
        date_start = datetime.combine(target_date, datetime.min.time())
        date_end = datetime.combine(target_date, datetime.max.time())
        
        return self.get_available_slots(
            practitioner_id=practitioner_id,
            date_from=date_start, 
            date_to=date_end
        )
    
    def count_available_slots(
        self,
        practitioner_id: Optional[str] = None,
        target_date: Optional[date] = None,
        specialty: Optional[str] = None
    ) -> int:
        """Count available slots with filters"""
        date_from = None
        date_to = None
        
        if target_date:
            date_from = datetime.combine(target_date, datetime.min.time())
            date_to = datetime.combine(target_date, datetime.max.time())
        
        slots = self.get_available_slots(
            practitioner_id=practitioner_id,
            date_from=date_from,
            date_to=date_to, 
            specialty=specialty
        )
        
        return len(slots)
    
    # ============ Appointment Operations ============
    
    def book_appointment(
        self,
        slot_id: str,
        patient_id: str, 
        patient_name: str,
        reason_code: str,
        description: Optional[str] = None,
        priority: str = "routine"
    ) -> Optional[FHIRAppointment]:
        """Book an appointment in a specific slot"""
        
        # Check if slot exists and is available
        slot = self._slots.get(slot_id)
        if not slot or not slot.is_available:
            return None
        
        # Get practitioner info
        practitioner = self._practitioners.get(slot.practitioner_id)
        if not practitioner:
            return None
        
        # Create appointment
        appointment = FHIRAppointment(
            id=f"appt-{slot_id}-{patient_id}",
            status=AppointmentStatus.BOOKED,
            service_category=slot.service_category,
            service_type=slot.service_type,
            specialty=slot.specialty,
            appointment_type=slot.appointment_type,
            reason_code=reason_code,
            description=description,
            start=slot.start,
            end=slot.end,
            created=datetime.now(),
            patient_id=patient_id,
            patient_name=patient_name,
            practitioner_id=slot.practitioner_id,
            practitioner_name=practitioner.name,
            slot_id=slot_id,
            priority=priority,
            minutes_duration=slot.duration_minutes
        )
        
        # Update slot status
        slot.status = SlotStatus.BUSY
        
        # Store appointment
        self._appointments[appointment.id] = appointment
        
        # Save changes
        self.save_data()
        
        return appointment
    
    def cancel_appointment(self, appointment_id: str) -> bool:
        """Cancel an appointment and free up the slot"""
        appointment = self._appointments.get(appointment_id)
        if not appointment:
            return False
        
        # Update appointment status
        appointment.status = AppointmentStatus.CANCELLED
        
        # Free up the slot
        slot = self._slots.get(appointment.slot_id)
        if slot:
            slot.status = SlotStatus.FREE
        
        # Save changes
        self.save_data()
        
        return True
    
    def get_appointments(
        self,
        practitioner_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        target_date: Optional[date] = None,
        status: Optional[AppointmentStatus] = None
    ) -> List[FHIRAppointment]:
        """Get appointments with optional filters"""
        appointments = list(self._appointments.values())
        
        if practitioner_id:
            appointments = [a for a in appointments if a.practitioner_id == practitioner_id]
        
        if patient_id:
            appointments = [a for a in appointments if a.patient_id == patient_id]
        
        if target_date:
            appointments = [a for a in appointments if a.start.date() == target_date]
        
        if status:
            appointments = [a for a in appointments if a.status == status]
        
        appointments.sort(key=lambda x: x.start)
        return appointments
    
    # ============ Analytics and Reporting ============
    
    def get_slot_utilization(
        self, 
        practitioner_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get slot utilization statistics"""
        all_slots = list(self._slots.values())
        
        # Apply filters
        if practitioner_id:
            all_slots = [s for s in all_slots if s.practitioner_id == practitioner_id]
        if date_from:
            all_slots = [s for s in all_slots if s.start >= date_from]
        if date_to:
            all_slots = [s for s in all_slots if s.start <= date_to]
        
        total_slots = len(all_slots)
        available_slots = len([s for s in all_slots if s.status == SlotStatus.FREE])
        booked_slots = len([s for s in all_slots if s.status == SlotStatus.BUSY])
        
        utilization_rate = (booked_slots / total_slots * 100) if total_slots > 0 else 0
        
        return {
            "total_slots": total_slots,
            "available_slots": available_slots,
            "booked_slots": booked_slots,
            "utilization_rate": round(utilization_rate, 2)
        }
    
    def get_practitioner_schedule_summary(self, practitioner_id: str, target_date: date) -> Dict[str, Any]:
        """Get detailed schedule summary for a practitioner on a specific date"""
        practitioner = self.get_practitioner(practitioner_id)
        if not practitioner:
            return {}
        
        slots = self.get_slots_for_date(target_date, practitioner_id)
        appointments = self.get_appointments(practitioner_id=practitioner_id, target_date=target_date)
        
        available_slots = [s for s in slots if s.is_available]
        
        return {
            "practitioner": practitioner.to_dict(),
            "date": target_date.isoformat(),
            "total_slots": len(slots),
            "available_slots": len(available_slots),
            "booked_appointments": len(appointments),
            "available_slot_times": [s.start.strftime("%H:%M") for s in available_slots],
            "booked_appointment_times": [a.start.strftime("%H:%M") for a in appointments if a.status == AppointmentStatus.BOOKED]
        }

    # ============ Utility Methods ============
    
    def to_dataframe(self, entity_type: str) -> pd.DataFrame:
        """Convert entity data to pandas DataFrame for easier analysis"""
        if entity_type == "practitioners":
            return pd.DataFrame([p.to_dict() for p in self._practitioners.values()])
        elif entity_type == "slots":
            return pd.DataFrame([s.to_dict() for s in self._slots.values()])
        elif entity_type == "appointments":
            return pd.DataFrame([a.to_dict() for a in self._appointments.values()])
        else:
            return pd.DataFrame()
    
    def search_practitioners(self, query: str) -> List[FHIRPractitioner]:
        """Search practitioners by name or specialty"""
        query = query.lower()
        results = []
        
        for p in self._practitioners.values():
            if (query in p.name.lower() or 
                query in p.specialty.lower() or
                query in p.department.lower()):
                results.append(p)
        
        return results

# ============ Slot Manager Factory ============

_slot_manager_instance: Optional[SlotManager] = None
_slot_manager_config: Dict[str, Optional[str]] = {"data_dir": None, "vector_dir": None}

def get_slot_manager(data_dir: Optional[str] = None, vector_dir: Optional[str] = None) -> SlotManager:
    """Get singleton SlotManager; initialize with provided directories.
    If called with different directories than existing instance, reinitialize.
    """
    global _slot_manager_instance, _slot_manager_config

    # Defaults
    if data_dir is None:
        data_dir = "data"

    # Recreate if not exists or config changed
    if (
        _slot_manager_instance is None or
        _slot_manager_config.get("data_dir") != data_dir or
        _slot_manager_config.get("vector_dir") != vector_dir
    ):
        _slot_manager_instance = SlotManager(data_dir=data_dir, vector_dir=vector_dir)
        _slot_manager_config = {"data_dir": data_dir, "vector_dir": vector_dir}

    return _slot_manager_instance
