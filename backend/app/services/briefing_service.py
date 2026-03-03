"""
briefing_service.py

Generates plain-language study briefings from the pattern library.

LLM Backends (tried in order)
──────────────────────────────
1. Anthropic Claude  — if ANTHROPIC_API_KEY is set
2. OpenAI            — if OPENAI_API_KEY is set
3. Template fallback — always available, no network required

The fallback produces a deterministic, readable briefing from structured
pattern data so the feature works out of the box in air-gapped CRO
environments.
"""
from __future__ import annotations

import os
import textwrap
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.briefing import Briefing
from app.models.pattern import Pattern
from app.models.study import Study
from app.services.pattern_service import get_patterns_for_study

# ── LLM dispatch ────────────────────────────────────────────────────────────

def _llm_generate(prompt: str) -> Optional[tuple[str, str]]:
    """
    Try each available LLM backend in priority order.
    Returns (briefing_text, model_name) or None on failure / no keys.
    """
    # ── Anthropic ──────────────────────────────────────────────────────────
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            import anthropic  # type: ignore
            client = anthropic.Anthropic(api_key=anthropic_key)
            msg = client.messages.create(
                model="claude-3-5-haiku-latest",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text, "anthropic/claude-3-5-haiku"
        except Exception:
            pass

    # ── OpenAI ─────────────────────────────────────────────────────────────
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            import openai as oai  # type: ignore
            client = oai.OpenAI(api_key=openai_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a preclinical data quality expert writing concise study briefings for data managers."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1024,
            )
            return resp.choices[0].message.content or "", "openai/gpt-4o-mini"
        except Exception:
            pass

    return None


def _template_briefing(study: Study, patterns: List[Pattern]) -> str:
    """
    Deterministic fallback briefing built from structured pattern data.
    No LLM required.
    """
    lines = [
        f"## Study Briefing: {study.name}",
        f"**Sponsor:** {study.sponsor_id}  |  **Type:** {study.study_type}  |  **Species:** {study.species}",
        "",
    ]

    if not patterns:
        lines += [
            "### Prior Decision Patterns",
            "_No historical patterns found for this sponsor × study type combination._",
            "This appears to be a new context. All flags should be reviewed independently.",
        ]
    else:
        lines += [
            f"### Prior Decision Patterns ({len(patterns)} rules learned)",
            "",
            "The following rules have been distilled from past review sessions:",
            "",
        ]
        for p in patterns:
            conf_bar = "▓" * int(p.confidence * 10) + "░" * (10 - int(p.confidence * 10))
            lines.append(f"- **{p.flag_type}** [{conf_bar} {int(p.confidence*100)}%]  ")
            lines.append(f"  {p.rule_text}")
            lines.append("")

    lines += [
        "### Reviewer Guidance",
        "- Review high-severity flags first.",
        "- Where a pattern confidence exceeds 80%, consider following the suggested action unless clinical context differs.",
        "- All overrides require a value and are logged for audit purposes.",
        "",
        f"_Briefing generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} by decision-tracker/1.0 (template mode)._",
    ]
    return "\n".join(lines)


def _build_llm_prompt(study: Study, patterns: List[Pattern]) -> str:
    pattern_block = "\n".join(f"- {p.rule_text}" for p in patterns) or "  (none yet)"
    return textwrap.dedent(f"""
        You are a preclinical data quality expert writing a concise study briefing for a data manager.

        STUDY CONTEXT
        =============
        Name       : {study.name}
        Sponsor    : {study.sponsor_id}
        Study type : {study.study_type}
        Species    : {study.species}

        LEARNED PATTERNS FROM PRIOR REVIEWS
        ====================================
        {pattern_block}

        TASK
        ====
        Write a 3–5 paragraph plain-English briefing for a data manager about to begin
        reviewing this study's flagged data points. Include:
        1. A short study context summary.
        2. Key historical patterns the reviewer should keep in mind (drawn from the rules above).
        3. Any caveats or flag types that may need extra care.
        4. A reminder about the override workflow.

        Use markdown headers and bullet points.  Keep it under 400 words.
        Do not include the raw pattern percentages verbatim — synthesise them naturally.
    """).strip()


# ── Public API ───────────────────────────────────────────────────────────────

def generate_briefing(db: Session, study_id: int, force_regenerate: bool = False) -> Optional[Briefing]:
    study = db.get(Study, study_id)
    if study is None:
        return None

    # Return cached briefing unless caller requests a fresh one
    if not force_regenerate:
        cached = (
            db.execute(
                select(Briefing)
                .where(Briefing.study_id == study_id)
                .order_by(Briefing.generated_at.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        if cached:
            return cached

    # Gather relevant patterns
    patterns = get_patterns_for_study(db, study)

    # Try LLM, fall back to template
    llm_result = _llm_generate(_build_llm_prompt(study, patterns))
    if llm_result:
        briefing_text, model_used = llm_result
    else:
        briefing_text = _template_briefing(study, patterns)
        model_used = "template"

    briefing = Briefing(
        study_id=study_id,
        briefing_text=briefing_text,
        model_used=model_used,
        pattern_count=len(patterns),
        generated_at=datetime.utcnow(),
    )
    db.add(briefing)
    db.commit()
    db.refresh(briefing)
    return briefing


def list_briefings(db: Session, study_id: int) -> List[Briefing]:
    return list(
        db.execute(
            select(Briefing)
            .where(Briefing.study_id == study_id)
            .order_by(Briefing.generated_at.desc())
        )
        .scalars()
        .all()
    )
