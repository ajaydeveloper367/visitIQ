#!/usr/bin/env python3
"""
Generate standardized patient JSON reports for embeddings ingestion.

Default output layout (vector-first friendly):
  <data_dir>/patient_documents/patient_<ID>/vitals/<YYYY-MM-DD>_vitals.json

Each JSON includes identity and vitals in a schema the processor understands:
{
  "patient_id": "001",
  "patient_name": "John Doe",
  "physician": "Dr. Sarah Lee",
  "visit_date": "2025-09-02",
  "vitals": {
    "glucose": 210,
    "bp_systolic": 145,
    "bp_diastolic": 92,
    "heart_rate": 88,
    "temperature": 98.7,
    "oxygen_saturation": 97,
    "hba1c": 8.2,
    "weight": 78.5,
    "height": 175
  },
  "primary_condition": "Type 2 Diabetes",
  "secondary_conditions": ["Hypertension"],
  "glucose": 210,
  "bp_systolic": 145,
  "bp_diastolic": 92,
  "heart_rate": 88,
  "temperature": 98.7
}

This works with MedicalDocumentProcessor._process_json_report() and the embeddings builder.
"""

import argparse
import os
import sys
import json
import random
from datetime import date, timedelta
from typing import List


# Ensure src is importable when run from repo or installed app
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_PATH = os.path.join(ROOT, 'src')
if SRC_PATH not in sys.path:
    sys.path.append(SRC_PATH)

try:
    from config import DATA_DIR as DEFAULT_DATA_DIR
except Exception:
    DEFAULT_DATA_DIR = os.path.join(os.path.expanduser("~"), ".visitiq", "app", "data")


FIRST_NAMES = [
    "John", "Jane", "Alex", "Maria", "Michael", "Sarah", "David", "Emily",
    "Robert", "Linda", "Daniel", "Sophia", "James", "Olivia", "Ethan", "Ava"
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson"
]
PHYSICIANS = [
    "Dr. Sarah Lee", "Dr. Robert King", "Dr. Emily Carter", "Dr. Daniel Ortiz",
    "Dr. Michael Chen", "Dr. Olivia Patel", "Dr. Ethan Brooks", "Dr. Linda Park"
]
CONDITIONS = [
    "Type 2 Diabetes", "Hypertension", "Hyperlipidemia", "Asthma", "COPD",
    "Coronary Artery Disease", "CKD", "Arrhythmia"
]


def zero_pad(n: int) -> str:
    return str(n).zfill(3)


def generate_patient_name(rng: random.Random) -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def generate_vitals(rng: random.Random) -> dict:
    # Broad, realistic ranges with occasional outliers to exercise triage
    glucose = int(rng.normalvariate(160, 60))  # mg/dL
    glucose = max(70, min(glucose, 450))
    bp_sys = int(rng.normalvariate(135, 25))
    bp_sys = max(90, min(bp_sys, 220))
    bp_dia = int(rng.normalvariate(85, 15))
    bp_dia = max(50, min(bp_dia, 140))
    hr = int(rng.normalvariate(80, 18))
    hr = max(45, min(hr, 160))
    temp = round(rng.normalvariate(98.4, 0.9), 1)
    o2 = int(rng.normalvariate(97, 2))
    o2 = max(85, min(o2, 100))
    hba1c = round(rng.normalvariate(7.5, 1.2), 1)
    weight = round(rng.normalvariate(78, 12), 1)
    height = int(rng.normalvariate(170, 10))
    return {
        "glucose": glucose,
        "bp_systolic": bp_sys,
        "bp_diastolic": bp_dia,
        "heart_rate": hr,
        "temperature": temp,
        "oxygen_saturation": o2,
        "hba1c": hba1c,
        "weight": weight,
        "height": height,
    }


def write_json(path: str, obj: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=10, help="Number of patients to generate")
    parser.add_argument("--start-id", type=int, default=1, help="Starting numeric patient id")
    parser.add_argument("--out-data-dir", default=DEFAULT_DATA_DIR, help="Base data directory")
    parser.add_argument("--reports-per-patient", type=int, default=1, help="Number of JSON vitals reports per patient")
    parser.add_argument("--standalone", action="store_true", help="Write standalone JSONs under <out>/reports instead of patient_documents")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    out_dir = os.path.abspath(args.out_data_dir)

    if args.standalone:
        base_reports_dir = os.path.join(out_dir, "reports")
    else:
        base_reports_dir = os.path.join(out_dir, "patient_documents")

    created_files: List[str] = []

    for i in range(args.start_id, args.start_id + args.count):
        pid = zero_pad(i)
        name = generate_patient_name(rng)
        physician = rng.choice(PHYSICIANS)
        primary_condition = rng.choice(CONDITIONS)
        secondary = [c for c in rng.sample(CONDITIONS, k=2) if c != primary_condition]

        for r in range(args.reports_per_patient):
            day_offset = rng.randint(0, 60)
            report_date = date.today() - timedelta(days=day_offset)
            vitals = generate_vitals(rng)

            report = {
                "patient_id": pid,
                "patient_name": name,
                "physician": physician,
                "visit_date": report_date.isoformat(),
                "vitals": vitals,
                "primary_condition": primary_condition,
                "secondary_conditions": secondary,
                # Flattened keys for robust extraction by regex/mapping
                "glucose": vitals["glucose"],
                "bp_systolic": vitals["bp_systolic"],
                "bp_diastolic": vitals["bp_diastolic"],
                "heart_rate": vitals["heart_rate"],
                "temperature": vitals["temperature"],
                "hba1c": vitals["hba1c"],
            }

            if args.standalone:
                file_dir = os.path.join(base_reports_dir, f"patient_{pid}")
                file_name = f"{report_date.isoformat()}_vitals.json"
            else:
                file_dir = os.path.join(base_reports_dir, f"patient_{pid}", "vitals")
                file_name = f"{report_date.isoformat()}_vitals.json"

            file_path = os.path.join(file_dir, file_name)
            write_json(file_path, report)
            created_files.append(file_path)

        # Also write a simple per-patient profile.json (used by ingestion to enrich metadata)
        if not args.standalone:
            profile = {
                "id": pid,
                "name": name,
                "age": int(random.normalvariate(55, 12)),
                "gender": rng.choice(["male", "female"]),
                "condition": primary_condition,
            }
            profile_path = os.path.join(base_reports_dir, f"patient_{pid}", "profile.json")
            write_json(profile_path, profile)
            created_files.append(profile_path)

    print(f"✅ Created {len(created_files)} JSON files under {base_reports_dir}")


if __name__ == "__main__":
    main()



