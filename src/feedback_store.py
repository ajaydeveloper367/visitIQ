"""
Lightweight persistent store for clinician feedback on patient prioritization.

Stores JSONL at <DATA_DIR>/patient_feedback.jsonl with entries like:
{
  "timestamp": "2025-09-02T12:00:00Z",
  "patient_id": "001",
  "status": "ignore_not_available"|"ignore_already_visited"|"ignore_not_interested"|"ignore_appointment_done"|"none",
  "priority_override": "Emergency"|"High"|"Medium"|"Low"|null,
  "score_delta": 10|-15|0,
  "comment": "Clinician rationale..."
}

The latest record per patient is used. Reading is resilient if file is missing.
"""

from __future__ import annotations

import os
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List

try:
    from .config import DATA_DIR
except Exception:
    from config import DATA_DIR  # type: ignore


DEFAULT_FEEDBACK_FILENAME = "patient_feedback.jsonl"


@dataclass
class PatientFeedback:
    patient_id: str
    status: str = "none"
    priority_override: Optional[str] = None
    score_delta: int = 0
    comment: str = ""
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp or datetime.now(timezone.utc).isoformat(),
            "patient_id": str(self.patient_id),
            "status": self.status,
            "priority_override": self.priority_override,
            "score_delta": int(self.score_delta or 0),
            "comment": self.comment or "",
        }


class FeedbackStore:
    def __init__(self, data_dir: Optional[str] = None, filename: str = DEFAULT_FEEDBACK_FILENAME) -> None:
        self.data_dir = data_dir or DATA_DIR
        self.file_path = os.path.join(self.data_dir, filename)
        os.makedirs(self.data_dir, exist_ok=True)

    def _iter_records(self) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        if not os.path.exists(self.file_path):
            return records
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        continue
        except Exception:
            pass
        return records

    def load_latest_map(self) -> Dict[str, PatientFeedback]:
        latest: Dict[str, PatientFeedback] = {}
        for rec in self._iter_records():
            pid = str(rec.get("patient_id", "")).strip()
            if not pid:
                continue
            latest[pid] = PatientFeedback(
                patient_id=pid,
                status=str(rec.get("status", "none")),
                priority_override=rec.get("priority_override"),
                score_delta=int(rec.get("score_delta") or 0),
                comment=str(rec.get("comment", "")),
                timestamp=str(rec.get("timestamp", "")),
            )
        return latest

    def add_feedback(
        self,
        patient_id: str,
        status: str = "none",
        comment: str = "",
        priority_override: Optional[str] = None,
        score_delta: int = 0,
    ) -> None:
        fb = PatientFeedback(
            patient_id=str(patient_id),
            status=status,
            priority_override=priority_override,
            score_delta=int(score_delta or 0),
            comment=comment or "",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(fb.to_dict(), ensure_ascii=False) + "\n")

    # Convenience helpers
    def get_ignored_patient_ids(self) -> List[str]:
        latest = self.load_latest_map()
        ignored_statuses = {
            "ignore_not_available",
            "ignore_already_visited",
            "ignore_not_interested",
            "ignore_appointment_done",
        }
        return [pid for pid, fb in latest.items() if fb.status in ignored_statuses]

    def get_adjustments(self) -> Dict[str, Dict[str, Any]]:
        latest = self.load_latest_map()
        adjustments: Dict[str, Dict[str, Any]] = {}
        for pid, fb in latest.items():
            adj: Dict[str, Any] = {}
            if fb.priority_override:
                adj["priority_override"] = fb.priority_override
            if fb.score_delta:
                adj["score_delta"] = int(fb.score_delta)
            if fb.comment:
                adj["comment"] = fb.comment
            if adj:
                adjustments[pid] = adj
        return adjustments


