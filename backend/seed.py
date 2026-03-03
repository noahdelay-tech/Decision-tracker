"""
seed.py — insert representative development data into the local SQLite DB.

Usage (from the backend/ directory):
    python seed.py            # idempotent: skips insert if data already exists
    python seed.py --reset    # drops all rows first, then re-seeds
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Bootstrap sys.path so the app package is importable when run from backend/
# ---------------------------------------------------------------------------
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.study import Study
from app.models.dataset import Dataset
from app.models.flag import Flag
from app.models.decision import Decision

DB_URL = "sqlite:///./data/decisiontracker.db"

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

STUDY = dict(
    name="GLP-001: 28-Day Oral Toxicology in Sprague-Dawley Rats",
    sponsor_id="SPONSOR-XYZ-42",
    study_type="Repeated-dose toxicology",
    species="Rat (Sprague-Dawley)",
)

DATASET = dict(
    filename="GLP001_clinical_pathology_wk4.xlsx",
    upload_status="complete",
    row_count=320,
)

FLAGS = [
    dict(
        row_index=14,
        column_name="ALT",
        raw_value="312",
        proposed_value="31.2",
        flag_type="unit_error",
        severity="high",
        biological_reasoning=(
            "ALT value of 312 U/L is ~10× the normal range for this strain/sex/age "
            "group (25–50 U/L). Pattern is consistent with a ×10 transcription error "
            "rather than a genuine hepatotoxic signal; adjacent animals in the same "
            "dose group show values of 28–46 U/L with no histopathological correlate."
        ),
        status="confirmed",
    ),
    dict(
        row_index=47,
        column_name="body_weight_g",
        raw_value="22.4",
        proposed_value=None,
        flag_type="outlier",
        severity="medium",
        biological_reasoning=(
            "Body weight of 22.4 g is 3.2 SD below the group mean (M = 310 g, "
            "SD = 18 g). Likely a units issue (g vs. kg) or mis-keyed animal ID. "
            "Requires verification against raw paper records before correction."
        ),
        status="pending",
    ),
    dict(
        row_index=88,
        column_name="WBC",
        raw_value="0.9",
        proposed_value="9.0",
        flag_type="decimal_shift",
        severity="high",
        biological_reasoning=(
            "WBC of 0.9 × 10³/µL would indicate severe leukopenia incompatible with "
            "the animal's clinical observation of 'no findings'. Group mean is 8.7 "
            "(SD 1.1). Decimal shift of one place (→ 9.0) aligns with group data and "
            "the source instrument printout."
        ),
        status="overridden",
    ),
    dict(
        row_index=103,
        column_name="creatinine_umol_L",
        raw_value="55",
        proposed_value=None,
        flag_type="reference_range_exceedance",
        severity="low",
        biological_reasoning=(
            "Creatinine of 55 µmol/L is marginally above the historical control "
            "upper limit of 53 µmol/L for male rats aged 8–10 weeks. Minimal "
            "biological significance; no other renal biomarkers (BUN, GFR proxy) "
            "are elevated. Flag retained for auditor visibility."
        ),
        status="rejected",
    ),
    dict(
        row_index=201,
        column_name="platelet_count",
        raw_value="1850",
        proposed_value="850",
        flag_type="transcription_error",
        severity="medium",
        biological_reasoning=(
            "Platelet count of 1850 × 10³/µL exceeds physiological maximum for "
            "Sprague-Dawley rats (~1200 × 10³/µL) and is inconsistent with the "
            "CBC pattern (no reactive thrombocytosis markers). Manual comparison "
            "with the analyzer output suggests leading '1' was erroneously prepended; "
            "corrected value of 850 falls within normal range."
        ),
        status="pending",
    ),
]

# One decision record for the already-resolved flags
DECISIONS = [
    # confirmed flag (row 14 ALT)
    dict(
        flag_index=0,  # index into FLAGS list
        reviewer_name="Dr. Sarah Okonkwo",
        action="confirmed",
        override_value=None,
        notes="Cross-checked against original analyzer printout. Correction validated.",
        decided_at=datetime.utcnow() - timedelta(days=2),
    ),
    # overridden flag (row 88 WBC)
    dict(
        flag_index=2,
        reviewer_name="Dr. Marcus Lim",
        action="overridden",
        override_value="8.7",
        notes=(
            "Instrument printout shows 8.7, not 9.0 as proposed. Corrected to "
            "match source document rather than algorithmic proposal."
        ),
        decided_at=datetime.utcnow() - timedelta(days=1),
    ),
    # rejected flag (row 103 creatinine)
    dict(
        flag_index=3,
        reviewer_name="Dr. Sarah Okonkwo",
        action="rejected",
        override_value=None,
        notes="Within acceptable biological variability. No correction warranted.",
        decided_at=datetime.utcnow() - timedelta(hours=6),
    ),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def reset_tables(session: Session) -> None:
    """Delete all rows in reverse FK order."""
    for model in (Decision, Flag, Dataset, Study):
        session.query(model).delete()
    session.commit()
    print("All seed tables cleared.")


def already_seeded(session: Session) -> bool:
    return session.query(Study).filter_by(sponsor_id=STUDY["sponsor_id"]).first() is not None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def seed(reset: bool = False) -> None:
    engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

    # Ensure all tables exist (safe no-op if they already do)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        if reset:
            reset_tables(session)

        if already_seeded(session):
            print("Seed data already present. Run with --reset to reload.")
            return

        # ── Study ─────────────────────────────────────────────────────────
        study = Study(**STUDY)
        session.add(study)
        session.flush()
        print(f"  [+] Study:   id={study.id}  {study.name[:60]}")

        # ── Dataset ───────────────────────────────────────────────────────
        dataset = Dataset(study_id=study.id, **DATASET)
        session.add(dataset)
        session.flush()
        print(f"  [+] Dataset: id={dataset.id}  {dataset.filename}")

        # ── Flags ─────────────────────────────────────────────────────────
        flag_objects: list[Flag] = []
        for f in FLAGS:
            flag = Flag(dataset_id=dataset.id, **f)
            session.add(flag)
            session.flush()
            print(
                f"  [+] Flag:    id={flag.id}  row={flag.row_index:>3}  "
                f"col={flag.column_name:<25}  severity={flag.severity:<6}  "
                f"status={flag.status}"
            )
            flag_objects.append(flag)

        # ── Decisions ─────────────────────────────────────────────────────
        for d in DECISIONS:
            flag_obj = flag_objects[d["flag_index"]]
            decision = Decision(
                flag_id=flag_obj.id,
                reviewer_name=d["reviewer_name"],
                action=d["action"],
                override_value=d["override_value"],
                notes=d["notes"],
                decided_at=d["decided_at"],
            )
            session.add(decision)
            session.flush()
            print(
                f"  [+] Decision: id={decision.id}  flag_id={decision.flag_id}  "
                f"action={decision.action}  reviewer={decision.reviewer_name}"
            )

        session.commit()
        print("\nSeed complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the decision-tracker dev database.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear all existing seed data before inserting.",
    )
    args = parser.parse_args()
    seed(reset=args.reset)
