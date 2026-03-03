"""
ingest_service.py

Responsibilities
────────────────
1. Parse uploaded CSV / XLSX bytes into a pandas DataFrame.
2. Infer biological variable types for every column via a multi-step
   normalisation + dictionary lookup.
3. Persist a Dataset record (with mappings and a row preview) to the DB.
"""
from __future__ import annotations

import io
import math
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.study import Study

# ── Column alias dictionary ────────────────────────────────────────────────
# Maps every normalised alias → canonical biological variable name.
# Normalisation: lowercase, non-alnum → underscore, collapse, strip.

COLUMN_ALIASES: Dict[str, str] = {
    # ── Animal / subject identifiers ─────────────────────────────────────
    "id": "animal_id",
    "animal": "animal_id",
    "animal_id": "animal_id",
    "animalid": "animal_id",
    "animal_no": "animal_id",
    "subject": "animal_id",
    "subject_id": "animal_id",
    "subjectid": "animal_id",
    "subject_no": "animal_id",
    "rat_id": "animal_id",
    "mouse_id": "animal_id",

    # ── Group / cohort ────────────────────────────────────────────────────
    "group": "group",
    "grp": "group",
    "group_id": "group",
    "group_no": "group",
    "cohort": "group",
    "treatment_group": "group",
    "dose_group": "group",

    # ── Sex ───────────────────────────────────────────────────────────────
    "sex": "sex",
    "gender": "sex",

    # ── Dose / treatment ──────────────────────────────────────────────────
    "dose": "dose",
    "dose_level": "dose",
    "doselevel": "dose",
    "dose_mg_kg": "dose",
    "dose_mg": "dose",
    "dose_ug_kg": "dose",
    "dose_ul": "dose",
    "treatment": "dose",
    "compound_dose": "dose",
    "nominal_dose": "dose",
    "actual_dose": "dose",

    # ── Timepoint / study day ─────────────────────────────────────────────
    "timepoint": "timepoint",
    "time_point": "timepoint",
    "tp": "timepoint",
    "day": "timepoint",
    "study_day": "timepoint",
    "studyday": "timepoint",
    "day_of_study": "timepoint",
    "visit": "timepoint",
    "visit_day": "timepoint",
    "week": "timepoint",
    "study_week": "timepoint",
    "hour": "timepoint",
    "time_hr": "timepoint",
    "time_h": "timepoint",

    # ── Age ───────────────────────────────────────────────────────────────
    "age": "age",
    "age_weeks": "age",
    "age_days": "age",
    "age_wk": "age",

    # ── Body weight ───────────────────────────────────────────────────────
    "body_weight": "body_weight",
    "bodyweight": "body_weight",
    "bw": "body_weight",
    "b_w": "body_weight",
    "body_wt": "body_weight",
    "bodywt": "body_weight",
    "wt": "body_weight",
    "weight": "body_weight",
    "bw_g": "body_weight",
    "bw_kg": "body_weight",
    "body_weight_g": "body_weight",
    "body_weight_kg": "body_weight",

    # ── Tumor volume ──────────────────────────────────────────────────────
    "tumor_volume": "tumor_volume",
    "tumorvolume": "tumor_volume",
    "tumour_volume": "tumor_volume",
    "tumourvolume": "tumor_volume",
    "tv": "tumor_volume",
    "tv_mm3": "tumor_volume",
    "tumor_vol": "tumor_volume",
    "tumour_vol": "tumor_volume",
    "tumor_size": "tumor_volume",
    "tumour_size": "tumor_volume",

    # ── Food / water consumption ──────────────────────────────────────────
    "food_consumption": "food_consumption",
    "food_intake": "food_consumption",
    "food_con": "food_consumption",
    "fc": "food_consumption",
    "water_consumption": "water_consumption",
    "water_intake": "water_consumption",
    "water_con": "water_consumption",

    # ── Vital signs ───────────────────────────────────────────────────────
    "body_temperature": "body_temperature",
    "temp": "body_temperature",
    "temperature": "body_temperature",
    "core_temp": "body_temperature",
    "rectal_temp": "body_temperature",
    "heart_rate": "heart_rate",
    "hr": "heart_rate",
    "pulse": "heart_rate",
    "pulse_rate": "heart_rate",
    "blood_pressure": "blood_pressure",
    "bp": "blood_pressure",
    "systolic": "systolic_bp",
    "systolic_bp": "systolic_bp",
    "sbp": "systolic_bp",
    "diastolic": "diastolic_bp",
    "diastolic_bp": "diastolic_bp",
    "dbp": "diastolic_bp",
    "map": "mean_arterial_pressure",
    "mean_arterial_pressure": "mean_arterial_pressure",

    # ── Clinical chemistry ────────────────────────────────────────────────
    "alt": "alt",
    "alat": "alt",
    "alanine_aminotransferase": "alt",
    "alanine_transaminase": "alt",
    "sgpt": "alt",
    "ast": "ast",
    "asat": "ast",
    "aspartate_aminotransferase": "ast",
    "aspartate_transaminase": "ast",
    "sgot": "ast",
    "alp": "alp",
    "alkaline_phosphatase": "alp",
    "ap": "alp",
    "ggt": "ggt",
    "gamma_gt": "ggt",
    "gamma_glutamyl_transferase": "ggt",
    "ldh": "ldh",
    "lactate_dehydrogenase": "ldh",
    "bun": "bun",
    "blood_urea_nitrogen": "bun",
    "urea_nitrogen": "bun",
    "urea": "urea",
    "creatinine": "creatinine",
    "crea": "creatinine",
    "creat": "creatinine",
    "glucose": "glucose",
    "gluc": "glucose",
    "blood_glucose": "glucose",
    "fasting_glucose": "glucose",
    "cholesterol": "cholesterol",
    "total_cholesterol": "cholesterol",
    "chol": "cholesterol",
    "triglycerides": "triglycerides",
    "trig": "triglycerides",
    "tg": "triglycerides",
    "hdl": "hdl_cholesterol",
    "hdl_cholesterol": "hdl_cholesterol",
    "ldl": "ldl_cholesterol",
    "ldl_cholesterol": "ldl_cholesterol",
    "total_protein": "total_protein",
    "tp": "total_protein",
    "protein": "total_protein",
    "albumin": "albumin",
    "alb": "albumin",
    "globulin": "globulin",
    "total_bilirubin": "total_bilirubin",
    "tbili": "total_bilirubin",
    "t_bili": "total_bilirubin",
    "bilirubin": "total_bilirubin",
    "direct_bilirubin": "direct_bilirubin",
    "dbili": "direct_bilirubin",
    "indirect_bilirubin": "indirect_bilirubin",
    "sodium": "sodium",
    "na": "sodium",
    "potassium": "potassium",
    "k": "potassium",
    "chloride": "chloride",
    "cl": "chloride",
    "bicarbonate": "bicarbonate",
    "hco3": "bicarbonate",
    "calcium": "calcium",
    "ca": "calcium",
    "phosphorus": "phosphorus",
    "phosphate": "phosphorus",
    "phos": "phosphorus",
    "magnesium": "magnesium",
    "mg": "magnesium",
    "iron": "iron",
    "fe": "iron",
    "uric_acid": "uric_acid",
    "urate": "uric_acid",

    # ── Hematology ────────────────────────────────────────────────────────
    "wbc": "wbc",
    "white_blood_cell": "wbc",
    "white_blood_cells": "wbc",
    "leukocytes": "wbc",
    "leukocyte_count": "wbc",
    "rbc": "rbc",
    "red_blood_cell": "rbc",
    "red_blood_cells": "rbc",
    "erythrocytes": "rbc",
    "erythrocyte_count": "rbc",
    "hgb": "hemoglobin",
    "hb": "hemoglobin",
    "hemoglobin": "hemoglobin",
    "haemoglobin": "hemoglobin",
    "hct": "hematocrit",
    "hematocrit": "hematocrit",
    "haematocrit": "hematocrit",
    "pcv": "hematocrit",
    "packed_cell_volume": "hematocrit",
    "mcv": "mcv",
    "mean_corpuscular_volume": "mcv",
    "mch": "mch",
    "mean_corpuscular_hemoglobin": "mch",
    "mchc": "mchc",
    "plt": "platelet_count",
    "platelet": "platelet_count",
    "platelets": "platelet_count",
    "platelet_count": "platelet_count",
    "thrombocytes": "platelet_count",
    "neutrophils": "neutrophils",
    "neut": "neutrophils",
    "neutrophil": "neutrophils",
    "segs": "neutrophils",
    "polymorphonuclear": "neutrophils",
    "lymphocytes": "lymphocytes",
    "lymph": "lymphocytes",
    "lymphocyte": "lymphocytes",
    "monocytes": "monocytes",
    "mono": "monocytes",
    "monocyte": "monocytes",
    "eosinophils": "eosinophils",
    "eos": "eosinophils",
    "eosinophil": "eosinophils",
    "basophils": "basophils",
    "baso": "basophils",
    "basophil": "basophils",
    "reticulocytes": "reticulocytes",
    "retic": "reticulocytes",

    # ── Coagulation ───────────────────────────────────────────────────────
    "pt": "prothrombin_time",
    "prothrombin_time": "prothrombin_time",
    "aptt": "aptt",
    "activated_partial_thromboplastin_time": "aptt",
    "fibrinogen": "fibrinogen",

    # ── Urinalysis ────────────────────────────────────────────────────────
    "urine_volume": "urine_volume",
    "urine_vol": "urine_volume",
    "urine_ph": "urine_ph",
    "urine_protein": "urine_protein",
    "urine_glucose": "urine_glucose",
    "urine_ketones": "urine_ketones",
    "urine_creatinine": "urine_creatinine",
    "specific_gravity": "specific_gravity",

    # ── Organ weights ─────────────────────────────────────────────────────
    "liver_weight": "liver_weight",
    "liver_wt": "liver_weight",
    "kidney_weight": "kidney_weight",
    "kidney_wt": "kidney_weight",
    "spleen_weight": "spleen_weight",
    "spleen_wt": "spleen_weight",
    "brain_weight": "brain_weight",
    "brain_wt": "brain_weight",
    "heart_weight": "heart_weight",
    "heart_wt": "heart_weight",
    "lung_weight": "lung_weight",
    "lung_wt": "lung_weight",
    "thymus_weight": "thymus_weight",
    "thymus_wt": "thymus_weight",
    "adrenal_weight": "adrenal_weight",
    "adrenal_wt": "adrenal_weight",
    "testis_weight": "testis_weight",
    "ovary_weight": "ovary_weight",
    "uterus_weight": "uterus_weight",
    "prostate_weight": "prostate_weight",
    "thyroid_weight": "thyroid_weight",

    # ── Pharmacokinetics ──────────────────────────────────────────────────
    "auc": "auc",
    "cmax": "cmax",
    "tmax": "tmax",
    "t_half": "half_life",
    "half_life": "half_life",
    "clearance": "clearance",
    "cl": "clearance",
    "vd": "volume_of_distribution",
    "volume_of_distribution": "volume_of_distribution",
    "concentration": "concentration",
    "plasma_concentration": "concentration",
    "serum_concentration": "concentration",

    # ── Biomarkers / misc ─────────────────────────────────────────────────
    "tnf": "tnf_alpha",
    "tnf_alpha": "tnf_alpha",
    "il_6": "il_6",
    "il6": "il_6",
    "il_1b": "il_1beta",
    "il_1beta": "il_1beta",
    "crp": "crp",
    "c_reactive_protein": "crp",
    "insulin": "insulin",
    "cortisol": "cortisol",
}

# ── Normalisation helpers ──────────────────────────────────────────────────

# Common unit tokens that may be appended to a variable name
_UNIT_TOKENS = frozenset({
    "g", "kg", "mg", "ug", "ng", "pg",
    "ml", "ul", "l",
    "mm3", "cm3", "cm", "mm",
    "u_l", "iu_l", "iu", "u",
    "nmol", "umol", "mmol", "mol",
    "meq", "meql",
    "dl", "gdl",
    "percent", "pct",
    "hr", "h", "min", "s",
    "day", "wk", "week",
    "x10_3", "x10_6", "10_3_ul", "10_6_ul",
})

# Common study-specific prefix tokens (stripped before second-pass lookup)
_PREFIX_TOKENS = frozenset({"study", "test", "animal", "subject", "sample"})


def _normalize(name: str) -> str:
    """Lowercase, replace all non-alphanumeric chars with underscores, collapse."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s


def _candidate_keys(raw: str) -> List[str]:
    """
    Generate a ranked list of normalised lookup keys for *raw*.

    Strategy (tried in order):
    1. Full normalised string                       "body_weight_g"
    2. Strip trailing unit token(s)                 "body_weight"
    3. Strip leading prefix token                   "weight"  (if prefix in _PREFIX_TOKENS)
    4. First token only (for abbreviations)         "bw"  from "bw_day_14"
    5. Last significant token                       "weight" from "final_body_weight"
    """
    norm = _normalize(raw)
    candidates: List[str] = [norm]

    parts = norm.split("_")

    # 2. Strip trailing unit tokens (may need to strip more than one layer)
    trimmed = list(parts)
    while trimmed and trimmed[-1] in _UNIT_TOKENS:
        trimmed = trimmed[:-1]
        key = "_".join(trimmed)
        if key and key not in candidates:
            candidates.append(key)

    # 3. Strip leading prefix token
    if parts and parts[0] in _PREFIX_TOKENS and len(parts) > 1:
        key = "_".join(parts[1:])
        if key not in candidates:
            candidates.append(key)

    # 4. First token (handles "bw_day14" → "bw")
    if parts[0] not in candidates:
        candidates.append(parts[0])

    # 5. Last token of the trimmed form
    if trimmed and trimmed[-1] not in candidates:
        candidates.append(trimmed[-1])

    return candidates


# ── Public resolver ────────────────────────────────────────────────────────

def resolve_column(raw_name: str) -> Tuple[Optional[str], str]:
    """
    Map a raw column name to a canonical biological variable name.

    Returns
    -------
    (canonical_name, normalized_name)
        canonical_name is None when no match is found.
    """
    normalized = _normalize(raw_name)
    for key in _candidate_keys(raw_name):
        if key in COLUMN_ALIASES:
            return COLUMN_ALIASES[key], normalized
    return None, normalized


def infer_column_mappings(
    df: pd.DataFrame,
) -> Tuple[Dict[str, str], List[str]]:
    """
    Run resolver over every column in *df*.

    Returns
    -------
    (mappings, unmapped)
        mappings  : {original_col: canonical_name}  — only matched columns
        unmapped  : [original_col]                   — columns with no match
    """
    mappings: Dict[str, str] = {}
    unmapped: List[str] = []

    for col in df.columns:
        canonical, _ = resolve_column(str(col))
        if canonical is not None:
            mappings[col] = canonical
        else:
            unmapped.append(col)

    return mappings, unmapped


# ── File parsing ───────────────────────────────────────────────────────────

_SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def parse_upload(filename: str, content: bytes) -> pd.DataFrame:
    """
    Parse raw file bytes into a DataFrame.

    Raises
    ------
    ValueError  – unsupported extension or parse failure.
    """
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Accepted: "
            + ", ".join(sorted(_SUPPORTED_EXTENSIONS))
        )

    buf = io.BytesIO(content)
    try:
        if ext == ".csv":
            df = pd.read_csv(buf)
        else:  # .xlsx / .xls
            df = pd.read_excel(buf)
    except Exception as exc:
        raise ValueError(f"Failed to parse '{filename}': {exc}") from exc

    if df.empty:
        raise ValueError("The uploaded file contains no data rows.")

    return df


def _to_json_safe(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Convert a DataFrame slice to a list of JSON-serialisable dicts.

    Handles NaN / NaT → None and numpy scalar types → Python builtins.
    """
    import numpy as np

    records = df.where(pd.notnull(df), other=None).to_dict(orient="records")

    def _coerce(v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, float) and math.isnan(v):
            return None
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.floating,)):
            return None if math.isnan(float(v)) else float(v)
        if isinstance(v, (np.bool_,)):
            return bool(v)
        if isinstance(v, (pd.Timestamp,)):
            return v.isoformat()
        return v

    return [{k: _coerce(v) for k, v in row.items()} for row in records]


# ── Database write ─────────────────────────────────────────────────────────

# All rows are stored so the flag-review UI can retrieve surrounding context.
# Cap at 10 000 to guard against very large files; most preclinical datasets
# are well under this limit.
MAX_STORED_ROWS = 10_000
PREVIEW_ROWS = 20          # rows exposed in the dataset-detail preview endpoint


def create_dataset_from_upload(
    db: Session,
    study_id: int,
    filename: str,
    content: bytes,
) -> Tuple[Dataset, Dict[str, str], List[str]]:
    """
    Parse *content*, infer schema, persist a Dataset row, and return it.

    Raises
    ------
    ValueError  – propagated from parse_upload
    LookupError – study_id does not exist
    """
    study = db.get(Study, study_id)
    if study is None:
        raise LookupError(f"Study id={study_id} not found.")

    df = parse_upload(filename, content)
    mappings, unmapped = infer_column_mappings(df)
    # Store all rows (capped) so context windows work for any row_index
    preview = _to_json_safe(df.head(MAX_STORED_ROWS))

    dataset = Dataset(
        study_id=study_id,
        filename=filename,
        upload_status="complete",
        row_count=len(df),
        column_mappings=mappings,
        unmapped_columns=unmapped,
        preview_rows=preview,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return dataset, mappings, unmapped
