"""
FHIR-compliant data models for healthcare scheduling
Based on FHIR R4 specification for Slot, Appointment, Practitioner, and Schedule resources
"""

from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import json
import uuid

class SlotStatus(Enum):
    BUSY = "busy"
    FREE = "free"
    BUSY_UNAVAILABLE = "busy-unavailable"
    BUSY_TENTATIVE = "busy-tentative"
    ENTERED_IN_ERROR = "entered-in-error"

class AppointmentStatus(Enum):
    PROPOSED = "proposed"
    PENDING = "pending"
    BOOKED = "booked"
    ARRIVED = "arrived"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    NOSHOW = "noshow"

@dataclass
class FHIRPractitioner:
    """FHIR Practitioner resource"""
    id: str
    name: str
    specialty: str
    department: str
    qualification: List[str] = field(default_factory=list)
    active: bool = True
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass 
class FHIRSchedule:
    """FHIR Schedule resource - defines when a practitioner is available"""
    id: str
    practitioner_id: str
    service_category: str  # e.g., "endocrinology", "cardiology"
    service_type: List[str]  # e.g., ["consultation", "follow-up"]
    specialty: str
    planning_horizon: int = 30  # days ahead scheduling is allowed
    comment: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class FHIRSlot:
    """FHIR Slot resource - specific time slot when service can be provided"""
    id: str
    schedule_id: str
    practitioner_id: str
    status: SlotStatus
    start: datetime
    end: datetime
    service_category: str
    service_type: List[str]
    specialty: str
    appointment_type: str = "routine"  # routine, urgent, walk-in
    comment: Optional[str] = None
    overbooked: bool = False
    
    @property
    def duration_minutes(self) -> int:
        """Duration of slot in minutes"""
        return int((self.end - self.start).total_seconds() / 60)
    
    @property 
    def is_available(self) -> bool:
        """Check if slot is available for booking"""
        return self.status == SlotStatus.FREE and self.start > datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['start'] = self.start.isoformat()
        data['end'] = self.end.isoformat() 
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FHIRSlot':
        """Create FHIRSlot from dictionary"""
        data['start'] = datetime.fromisoformat(data['start'])
        data['end'] = datetime.fromisoformat(data['end'])
        data['status'] = SlotStatus(data['status'])
        return cls(**data)

@dataclass
class FHIRAppointment:
    """FHIR Appointment resource - booked appointment"""
    id: str
    status: AppointmentStatus
    service_category: str
    service_type: List[str]
    specialty: str
    appointment_type: str
    reason_code: str  # e.g., "diabetes-followup", "hypertension-check"
    description: Optional[str]
    start: datetime
    end: datetime
    created: datetime
    
    # Participants
    patient_id: str
    patient_name: str
    practitioner_id: str
    practitioner_name: str
    slot_id: str
    
    # Priority and scheduling (fields with default values must come last)
    comment: Optional[str] = None
    priority: str = "routine"  # routine, urgent, asap, stat
    minutes_duration: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['start'] = self.start.isoformat()
        data['end'] = self.end.isoformat()
        data['created'] = self.created.isoformat()
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FHIRAppointment':
        data['start'] = datetime.fromisoformat(data['start'])
        data['end'] = datetime.fromisoformat(data['end'])
        data['created'] = datetime.fromisoformat(data['created'])
        data['status'] = AppointmentStatus(data['status'])
        return cls(**data)

class FHIRSlotGenerator:
    """Utility class to generate FHIR-compliant slots for practitioners"""
    
    @staticmethod
    def generate_daily_slots(
        practitioner: FHIRPractitioner,
        schedule: FHIRSchedule,
        date: datetime,
        start_time: str = "09:00",
        end_time: str = "17:00", 
        slot_duration_minutes: int = 30,
        lunch_break: Optional[tuple] = ("12:00", "13:00")
    ) -> List[FHIRSlot]:
        """Generate slots for a practitioner on a specific date"""
        
        slots = []
        start_dt = datetime.combine(date.date(), datetime.strptime(start_time, "%H:%M").time())
        end_dt = datetime.combine(date.date(), datetime.strptime(end_time, "%H:%M").time())
        
        current_time = start_dt
        slot_duration = timedelta(minutes=slot_duration_minutes)
        
        while current_time + slot_duration <= end_dt:
            # Skip lunch break if specified
            if lunch_break:
                lunch_start = datetime.combine(date.date(), datetime.strptime(lunch_break[0], "%H:%M").time())
                lunch_end = datetime.combine(date.date(), datetime.strptime(lunch_break[1], "%H:%M").time())
                
                if current_time >= lunch_start and current_time < lunch_end:
                    current_time = lunch_end
                    continue
            
            slot = FHIRSlot(
                id=f"slot-{practitioner.id}-{current_time.strftime('%Y%m%d-%H%M')}",
                schedule_id=schedule.id,
                practitioner_id=practitioner.id,
                status=SlotStatus.FREE,
                start=current_time,
                end=current_time + slot_duration,
                service_category=schedule.service_category,
                service_type=schedule.service_type,
                specialty=schedule.specialty
            )
            
            slots.append(slot)
            current_time += slot_duration
            
        return slots

    @staticmethod
    def generate_weekly_slots(
        practitioner: FHIRPractitioner,
        schedule: FHIRSchedule,
        start_date: datetime,
        working_days: List[int] = [0, 1, 2, 3, 4],  # Monday-Friday
        **daily_slot_kwargs
    ) -> List[FHIRSlot]:
        """Generate slots for a week"""
        all_slots = []
        
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            if current_date.weekday() in working_days:
                daily_slots = FHIRSlotGenerator.generate_daily_slots(
                    practitioner, schedule, current_date, **daily_slot_kwargs
                )
                all_slots.extend(daily_slots)
                
        return all_slots

# Sample data generators
def create_sample_practitioners() -> List[FHIRPractitioner]:
    """Create sample practitioners for diabetes care"""
    return [
        FHIRPractitioner(
            id="prac-001",
            name="Dr. Sarah Chen",
            specialty="Endocrinology",
            department="Internal Medicine",
            qualification=["MD", "Board Certified Endocrinologist"],
            contact_phone="+1-555-0101",
            contact_email="s.chen@hospital.com"
        ),
        FHIRPractitioner(
            id="prac-002", 
            name="Dr. Michael Rodriguez",
            specialty="Family Medicine",
            department="Primary Care",
            qualification=["MD", "Family Medicine Board Certified"],
            contact_phone="+1-555-0102",
            contact_email="m.rodriguez@clinic.com"
        ),
        FHIRPractitioner(
            id="prac-003",
            name="Dr. Priya Patel",
            specialty="Cardiology", 
            department="Cardiovascular Medicine",
            qualification=["MD", "Interventional Cardiology"],
            contact_phone="+1-555-0103",
            contact_email="p.patel@cardio.com"
        )
    ]

def create_sample_schedules() -> List[FHIRSchedule]:
    """Create sample schedules for practitioners"""
    return [
        FHIRSchedule(
            id="sched-001",
            practitioner_id="prac-001",
            service_category="endocrinology",
            service_type=["diabetes-consultation", "hormone-therapy", "follow-up"],
            specialty="Endocrinology",
            comment="Diabetes and hormone specialist"
        ),
        FHIRSchedule(
            id="sched-002", 
            practitioner_id="prac-002",
            service_category="primary-care",
            service_type=["general-consultation", "preventive-care", "chronic-disease"],
            specialty="Family Medicine",
            comment="Primary care and chronic disease management"
        ),
        FHIRSchedule(
            id="sched-003",
            practitioner_id="prac-003", 
            service_category="cardiology",
            service_type=["cardiac-consultation", "echo-study", "stress-test"],
            specialty="Cardiology",
            comment="Cardiac care for diabetic complications"
        )
    ]
