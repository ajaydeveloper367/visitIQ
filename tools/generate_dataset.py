#!/usr/bin/env python3
"""
Generate a realistic demo dataset:
- patients.csv (N patients)
- practitioners.json
- slots.json (optional)
- patient_documents/ (PDF-like text, notes as .txt, JSON vitals)

Usage:
  python tools/generate_dataset.py \
    --out ~/.visitiq/app/data \
    --patients 150 \
    --csv 50 --pdf 50 --notes 50

Notes:
- We generate text files instead of real PDFs to keep dependencies light; the
  app's document processor already supports .txt and .json in addition to PDFs.
"""

import argparse
import csv
import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path


FIRST_NAMES = [
    "John", "Jane", "Michael", "Emily", "Robert", "Sarah", "David", "Laura",
    "Daniel", "Olivia", "James", "Sophia", "William", "Ava", "Benjamin", "Mia"
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Lopez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Martin", "Jackson"
]

CONDITIONS = [
    "Type 2 Diabetes", "Type 1 Diabetes", "Hypertension", "Cardiovascular Disease",
    "Arthritis", "Fracture", "Asthma", "COPD", "Stroke History", "Chronic Kidney Disease"
]

SPECIALTIES = [
    ("Endocrinology", ["Type 1 Diabetes", "Type 2 Diabetes"]),
    ("Cardiology", ["Hypertension", "Cardiovascular Disease"]),
    ("Orthopedics", ["Arthritis", "Fracture"]),
    ("Pulmonology", ["Asthma", "COPD"]),
    ("Neurology", ["Stroke History"]),
    ("Nephrology", ["Chronic Kidney Disease"]),
    ("Family Medicine", CONDITIONS),
]


def rand_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def gen_practitioners(num=12):
    practitioners = []
    for i in range(1, num + 1):
        spec, _ = random.choice(SPECIALTIES)
        practitioners.append({
            "id": f"P{i:03d}",
            "name": f"Dr. {rand_name()}",
            "specialty": spec,
            "department": spec
        })
    return practitioners


def gen_slots(practitioners, days=5, per_day=6):
    slots = []
    sid = 1
    start_date = datetime.now().date() + timedelta(days=1)
    for d in range(days):
        for p in practitioners:
            for n in range(per_day):
                start = datetime.combine(start_date + timedelta(days=d), datetime.min.time()) + timedelta(hours=9 + n)
                end = start + timedelta(minutes=30)
                slots.append({
                    "id": f"S{sid:04d}",
                    "practitioner_id": p["id"],
                    "specialty": p["specialty"],
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "status": "free",
                    "service_type": [p["specialty"]]
                })
                sid += 1
    return slots


def gen_patient_row(pid: int):
    name = rand_name()
    age = random.randint(18, 85)
    condition = random.choice(CONDITIONS)
    glucose = random.choice([random.randint(90, 170), random.randint(180, 480)])
    bp_sys = random.choice([random.randint(110, 150), random.randint(160, 200)])
    bp_dia = random.choice([random.randint(70, 95), random.randint(96, 120)])
    hr = random.randint(60, 130)
    history = random.choice([
        "", "Family diabetes history", "CKD stage 2", "Ischemic heart disease",
        "Past fracture", "Mild asthma", "Smoking", "Obesity"
    ])
    return {
        "patient_id": f"{pid:03d}",
        "name": name,
        "age": age,
        "condition": condition,
        "glucose_mg_dL": glucose,
        "bp_systolic": bp_sys,
        "bp_diastolic": bp_dia,
        "heart_rate": hr,
        "history": history,
        "notes": ""
    }


def write_patients_csv(path: Path, rows):
    cols = [
        "patient_id", "name", "age", "condition", "glucose_mg_dL",
        "bp_systolic", "bp_diastolic", "heart_rate", "history", "notes"
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def write_documents(doc_root: Path, patient_ids, pdf_like=0, notes=0):
    doc_root.mkdir(parents=True, exist_ok=True)
    for pid in patient_ids:
        pdir = doc_root / f"patient_{str(pid).zfill(3)}"
        pdir.mkdir(parents=True, exist_ok=True)

        # Create JSON vitals always
        vitals = {
            "patient_id": str(pid).zfill(3),
            "timestamp": datetime.now().isoformat(),
            "vitals": {
                "glucose_mg_dL": random.randint(90, 480),
                "bp": f"{random.randint(110,200)}/{random.randint(70,120)}",
                "hr": random.randint(60, 130)
            }
        }
        (pdir / "vitals.json").write_text(json.dumps(vitals, indent=2), encoding="utf-8")

        # Optional PDF-like (use .txt; app supports OCR/text too)
        for i in range(max(0, pdf_like // max(1, len(patient_ids)))):
            (pdir / f"lab_report_{i+1}.txt").write_text(
                f"Patient {pid}\nHbA1c: {round(random.uniform(5.5, 13.5), 1)}%\nDoctor note: follow-up recommended.",
                encoding="utf-8"
            )

        # Optional clinical notes
        for i in range(max(0, notes // max(1, len(patient_ids)))):
            (pdir / f"doctor_note_{i+1}.txt").write_text(
                f"Subjective: {rand_name()} reports symptoms related to {random.choice(CONDITIONS)}.\nPlan: adjust meds.",
                encoding="utf-8"
            )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="Output directory (e.g., ~/.visitiq/app/data)")
    ap.add_argument("--patients", type=int, default=150)
    ap.add_argument("--csv", type=int, default=50, help="How many go into patients.csv")
    ap.add_argument("--pdf", type=int, default=50, help="How many get PDF-like lab reports")
    ap.add_argument("--notes", type=int, default=50, help="How many get doctor notes")
    ap.add_argument("--with-slots", action="store_true", help="Also generate slots.json")
    args = ap.parse_args()

    out_dir = Path(os.path.expanduser(args.out))
    out_dir.mkdir(parents=True, exist_ok=True)

    # Practitioners
    practitioners = gen_practitioners(num=12)
    (out_dir / "practitioners.json").write_text(json.dumps(practitioners, indent=2), encoding="utf-8")

    # Patients
    patients = [gen_patient_row(i+1) for i in range(args.patients)]
    csv_patients = patients[: args.csv]
    write_patients_csv(out_dir / "patients.csv", csv_patients)

    # Documents for remaining patients (and possibly some CSV ones)
    doc_patients = {p["patient_id"] for p in patients[args.csv:]} | {p["patient_id"] for p in csv_patients[: max(0, args.pdf + args.notes - (args.patients - args.csv))]}
    write_documents(out_dir / "patient_documents", sorted(doc_patients), pdf_like=args.pdf, notes=args.notes)

    # Slots
    if args.with_slots:
        slots = gen_slots(practitioners)
        (out_dir / "slots.json").write_text(json.dumps(slots, indent=2), encoding="utf-8")

    print(f"✅ Dataset generated at: {out_dir}")
    print("  - patients.csv")
    print("  - practitioners.json")
    print("  - slots.json (optional)")
    print("  - patient_documents/* (vitals.json, lab_report_*.txt, doctor_note_*.txt)")


if __name__ == "__main__":
    main()


