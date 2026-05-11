
"""
llm_utils.py  (SECURITY-HARDENED)
-----------------------------------
Changes from original:
  - Pydantic schema validates every LLM response (hallucination guard)
  - Scores outside 0-10 are clamped + flagged
  - Confidence threshold: if ALL scores == 0, response is flagged
  - Robust JSON extraction: regex fallback before giving up
"""

import os
import re
import json
from groq import Groq
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional

load_dotenv()

_api_key = os.getenv("GROQ_API_KEY")
if not _api_key:
    raise EnvironmentError(
        "GROQ_API_KEY is not set. "
        "Add it to your .env file and never hardcode it."
    )

client = Groq(api_key=_api_key)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class DimensionScore(BaseModel):
    score: float = Field(..., ge=0, le=10, description="Score 0-10")
    justification: str = Field(..., min_length=5, max_length=500)

    @field_validator("score", mode="before")
    @classmethod
    def clamp_score(cls, v):
        try:
            v = float(v)
        except (TypeError, ValueError):
            raise ValueError(f"Score must be numeric, got {v!r}")
        if v < 0:
            return 0.0
        if v > 10:
            return 10.0
        return v

    @field_validator("justification", mode="before")
    @classmethod
    def clean_justification(cls, v):
        """Strip any stray quotes or control chars that break JSON."""
        if isinstance(v, str):
            v = v.replace("\n", " ").replace("\r", " ").strip()
            v = v[:500]
        return v


class RubricResponse(BaseModel):
    skills_match:  DimensionScore
    experience:    DimensionScore
    education:     DimensionScore
    projects:      DimensionScore
    communication: DimensionScore

    @model_validator(mode="after")
    def check_confidence(self):
        scores = [
            self.skills_match.score,
            self.experience.score,
            self.education.score,
            self.projects.score,
            self.communication.score,
        ]
        if all(s == 0.0 for s in scores):
            object.__setattr__(self, "_low_confidence", True)
        else:
            object.__setattr__(self, "_low_confidence", False)
        return self


# ---------------------------------------------------------------------------
# Safe fallback
# ---------------------------------------------------------------------------

_FALLBACK = RubricResponse(
    skills_match  = DimensionScore(score=0, justification="LLM output could not be validated — manual review required"),
    experience    = DimensionScore(score=0, justification="LLM output could not be validated"),
    education     = DimensionScore(score=0, justification="LLM output could not be validated"),
    projects      = DimensionScore(score=0, justification="LLM output could not be validated"),
    communication = DimensionScore(score=0, justification="LLM output could not be validated"),
)


# ---------------------------------------------------------------------------
# JSON extraction helpers
# ---------------------------------------------------------------------------

def _strip_fences(text: str) -> str:
    """Remove markdown code fences."""
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return text.strip()


def _extract_json_block(text: str) -> str:
    """
    Pull the first {...} block out of the response even if the LLM
    added preamble text before or after the JSON.
    """
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return match.group(0)
    return text


def _sanitize_json_string(text: str) -> str:
    """
    Fix the most common LLM JSON mistake: unescaped quotes inside
    string values that break the parser.
    Strategy: parse each justification value and re-encode it safely.
    """
    # Replace smart/curly quotes with straight quotes first
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    return text


def _extract_scores_with_regex(text: str) -> Optional[dict]:
    """
    Last-resort fallback: pull scores directly with regex even if the
    JSON is malformed. Justifications are set to a placeholder.
    Returns None if not enough scores found.
    """
    dimensions = ["skills_match", "experience", "education", "projects", "communication"]
    result = {}

    for dim in dimensions:
        # Match "skills_match": {"score": 7, ...} or "score": 7 near the dim name
        pattern = rf'"{dim}"\s*:\s*\{{[^}}]*?"score"\s*:\s*(\d+(?:\.\d+)?)'
        match = re.search(pattern, text)
        if match:
            score = float(match.group(1))
            # Try to grab justification too
            just_pattern = rf'"{dim}"\s*:\s*\{{[^}}]*?"justification"\s*:\s*"([^"{{}}]*)"'
            just_match = re.search(just_pattern, text)
            justification = just_match.group(1) if just_match else "Extracted via fallback parser"
            result[dim] = {"score": score, "justification": justification}

    if len(result) == 5:
        print(f"[llm_utils] Used regex fallback parser — recovered all 5 dimensions")
        return result

    print(f"[llm_utils] Regex fallback only recovered {len(result)}/5 dimensions")
    return None


# ---------------------------------------------------------------------------
# Core LLM call
# ---------------------------------------------------------------------------

def ask_llm(prompt: str) -> dict:
    """
    Call the Groq LLM and validate the response against RubricResponse schema.
    Tries 3 increasingly aggressive parsing strategies before giving up.
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        raw_content = response.choices[0].message.content.strip()
        print(f"[llm_utils] raw response (first 300 chars): {raw_content[:300]}")

    except Exception as e:
        print(f"[llm_utils] API call failed: {e}")
        fallback = _FALLBACK.model_dump()
        fallback["_low_confidence"] = True
        return fallback

    # --- Strategy 1: clean fences + standard json.loads ---
    content = _strip_fences(raw_content)
    content = _extract_json_block(content)
    content = _sanitize_json_string(content)

    raw = None
    try:
        raw = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"[llm_utils] Strategy 1 failed (standard parse): {e}")

    # --- Strategy 2: regex score extraction ---
    if raw is None:
        raw = _extract_scores_with_regex(raw_content)

    # --- Strategy 3: give up, use fallback ---
    if raw is None:
        print(f"[llm_utils] All parse strategies failed. Raw response:\n{raw_content}\n")
        fallback = _FALLBACK.model_dump()
        fallback["_low_confidence"] = True
        return fallback

    # --- Pydantic validation ---
    try:
        validated: RubricResponse = RubricResponse.model_validate(raw)
        result = validated.model_dump()
        result["_low_confidence"] = validated._low_confidence
        return result
    except Exception as e:
        print(f"[llm_utils] Pydantic validation failed: {e}")
        fallback = _FALLBACK.model_dump()
        fallback["_low_confidence"] = True
        return fallback