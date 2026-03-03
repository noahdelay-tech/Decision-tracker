"""
briefing/generator.py

Generates a plain-language study briefing using the Anthropic API.

Process
-------
1. Fetches structured pattern data by replicating the logic of
   GET /api/studies/{study_id}/briefing (sponsor patterns + column risk flags).
2. Formats the patterns into a concise prompt context block.
3. Calls the Anthropic API (claude-sonnet-4-20250514) with a system prompt that
   positions it as a senior CRO data manager writing a one-page onboarding
   briefing for a new data manager joining a study.
4. Stores the result in the `briefings` table (study_id, generated_at, model_used)
   so repeated calls are served from cache unless ?force=true is requested.
5. Returns the briefing as plain text.

API key is read from ANTHROPIC_API_KEY in the .env file via python-dotenv.
"""
from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.briefing import Briefing
from app.models.study import Study
from patterns.library import get_patterns_for_sponsor

# ── Load .env from the backend root (one level up from this file) ─────────────
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=False)

# ── Model config ──────────────────────────────────────────────────────────────
_MODEL = "claude-sonnet-4-20250514"
_MODEL_TAG = f"anthropic/{_MODEL}"

# ── System prompt ─────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """\
You are a senior CRO data manager with more than ten years of experience \
reviewing preclinical safety and efficacy datasets for pharmaceutical sponsors. \
You are writing a concise one-page onboarding briefing for a new data manager \
who is about to begin reviewing flagged data points for this study.

Your briefing MUST cover exactly the following sections, in order:

## 1. Study Overview
A short orientation: sponsor, study type, species, and any notable context.

## 2. Sponsor Data Quirks
Historical patterns that are specific to this sponsor — recurring transcription \
habits, instrument drift tendencies, unconventional coding practices, or any \
systematic behaviour the reviewer should anticipate before opening the data.

## 3. Column-Level Risk Flags
Which columns carry the highest quality risk and why, based on historical \
occurrence data. Name the columns explicitly and explain what kinds of errors \
tend to appear there.

## 4. Common Errors & How They Were Resolved
The most frequently encountered error types in prior reviews: what they were, \
how often they turned out to be genuine errors (vs. noise), and what the typical \
correction was. Keep this actionable — the reviewer needs to know what to do, \
not just what happened.

## 5. Reviewer Guidance
Practical, direct advice for this study: when to confirm vs. override vs. reject \
a flag, what to look out for on the first pass, and any sponsor-specific \
conventions the reviewer must respect.

Tone: professional but direct — brief a colleague, not a committee.
Format: markdown with the five headers above. Length: 350–500 words.
Do NOT reproduce raw statistics verbatim — synthesise them into natural-language \
guidance. Do NOT invent patterns that are not supported by the data provided.\
"""


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_column_risks(patterns: list) -> list[dict]:
    """
    Replicates the column-risk logic from GET /api/studies/{study_id}/briefing.
    Returns a list of dicts sorted high → medium → low.
    """
    col_groups: dict[str, list] = defaultdict(list)
    for p in patterns:
        col_groups[p.column_name].append(p)

    risks = []
    for column_name, col_patterns in col_groups.items():
        total_occ = sum(p.occurrence_count for p in col_patterns)
        pattern_cnt = len(col_patterns)
        dominant = max(col_patterns, key=lambda p: p.occurrence_count)

        if total_occ >= 10 or pattern_cnt >= 3:
            risk = "high"
        elif total_occ >= 5 or pattern_cnt >= 2:
            risk = "medium"
        else:
            risk = "low"

        risks.append(
            {
                "column_name": column_name,
                "risk_level": risk,
                "pattern_count": pattern_cnt,
                "total_occurrences": total_occ,
                "dominant_flag_type": dominant.flag_type,
            }
        )

    risk_order = {"high": 0, "medium": 1, "low": 2}
    risks.sort(key=lambda r: (risk_order[r["risk_level"]], -r["total_occurrences"]))
    return risks


def _build_prompt_context(study: Study, patterns: list, column_risks: list[dict]) -> str:
    """
    Format structured briefing data into a concise prompt context block
    that is injected into the user turn of the Anthropic API call.
    """
    # Column risk section
    if column_risks:
        col_lines = [
            f"  - {cr['column_name']}: {cr['risk_level'].upper()} risk "
            f"({cr['total_occurrences']} historical occurrences, "
            f"dominant issue: {cr['dominant_flag_type']}, "
            f"{cr['pattern_count']} distinct flag type(s))"
            for cr in column_risks
        ]
        col_section = "\n".join(col_lines)
    else:
        col_section = "  (No column-level risk data available — this appears to be a new sponsor context)"

    # Historical pattern section
    if patterns:
        pat_lines = []
        for p in patterns:
            conf_pct = int(p.confirmation_rate * 100)
            line = (
                f"  - [{p.column_name}] {p.flag_type}: "
                f"{p.occurrence_count} occurrence(s), "
                f"{conf_pct}% confirmed as genuine errors"
            )
            if p.common_override:
                line += f", typical correction → '{p.common_override}'"
            if p.example_reasonings:
                line += f"\n    Example reasoning: {p.example_reasonings[0]}"
            pat_lines.append(line)
        pat_section = "\n".join(pat_lines)
    else:
        pat_section = "  (No historical patterns found — new sponsor or first study)"

    return (
        f"STUDY CONTEXT\n"
        f"=============\n"
        f"Name        : {study.name}\n"
        f"Sponsor     : {study.sponsor_id}\n"
        f"Study type  : {study.study_type}\n"
        f"Species     : {study.species}\n"
        f"\n"
        f"COLUMN-LEVEL RISK FLAGS (from historical pattern library)\n"
        f"==========================================================\n"
        f"{col_section}\n"
        f"\n"
        f"HISTORICAL PATTERNS AND COMMON ERRORS\n"
        f"======================================\n"
        f"{pat_section}\n"
    )


def _call_anthropic(prompt_context: str) -> str:
    """
    Call the Anthropic API and return the raw briefing text.
    Raises RuntimeError if the key is missing or the API call fails.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. "
            "Add it to backend/.env before using the briefing generator."
        )

    try:
        import anthropic  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "The 'anthropic' package is not installed. "
            "Run: pip install anthropic"
        ) from exc

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Here is the structured study data pulled from the pattern library:\n\n"
                        + prompt_context
                        + "\nPlease write the briefing now."
                    ),
                }
            ],
        )
        return message.content[0].text
    except Exception as exc:
        raise RuntimeError(f"Anthropic API call failed: {exc}") from exc


# ── Public API ────────────────────────────────────────────────────────────────

def generate_study_briefing(
    db: Session,
    study_id: int,
    force: bool = False,
) -> Optional[tuple[str, int]]:
    """
    Generate (or return the cached) Anthropic-powered study briefing.

    Parameters
    ----------
    db:        SQLAlchemy session.
    study_id:  Primary key of the study.
    force:     If True, bypass the cache and regenerate from scratch.

    Returns
    -------
    (briefing_text, pattern_count) on success, or None if the study does not
    exist.  Raises RuntimeError if the Anthropic API is unavailable.
    """
    study = db.get(Study, study_id)
    if study is None:
        return None

    # Return cached briefing unless the caller requests a fresh one
    if not force:
        cached = (
            db.execute(
                select(Briefing)
                .where(
                    Briefing.study_id == study_id,
                    Briefing.model_used == _MODEL_TAG,
                )
                .order_by(Briefing.generated_at.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        if cached:
            return cached.briefing_text, cached.pattern_count

    # ── Fetch structured pattern data (replicates GET /api/studies/{id}/briefing)
    patterns = get_patterns_for_sponsor(db, study.sponsor_id)
    column_risks = _build_column_risks(patterns)

    # ── Format prompt context block
    prompt_context = _build_prompt_context(study, patterns, column_risks)

    # ── Call Anthropic API
    briefing_text = _call_anthropic(prompt_context)

    # ── Persist to briefings table
    row = Briefing(
        study_id=study_id,
        briefing_text=briefing_text,
        model_used=_MODEL_TAG,
        pattern_count=len(patterns),
        generated_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return briefing_text, len(patterns)
