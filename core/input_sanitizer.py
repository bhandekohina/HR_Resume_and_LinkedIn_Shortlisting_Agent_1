"""
input_sanitizer.py
------------------
Handles:
  1. Prompt Injection Prevention  — strips known injection patterns from user input
  2. PII Masking                  — masks emails, phones, Aadhaar, PAN before logging
"""

import re

# ---------------------------------------------------------------------------
# 1. PROMPT INJECTION PREVENTION
# ---------------------------------------------------------------------------

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"forget\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"you\s+are\s+now\s+(?:a|an|the)\s+\w+",
    r"act\s+as\s+(?:a|an|the)\s+\w+",
    r"pretend\s+(you\s+are|to\s+be)",
    r"system\s*prompt\s*[:\-]",
    r"<\s*/?system\s*>",
    r"\[INST\]|\[\/INST\]",
    r"###\s*(instruction|system|human|assistant)",
    r"<\|im_start\|>|<\|im_end\|>",
    r"IGNORE AND PRINT",
    r"jailbreak",
    r"do anything now",
    r"DAN\s*mode",
]

_INJECTION_RE = re.compile(
    "|".join(INJECTION_PATTERNS),
    flags=re.IGNORECASE | re.DOTALL,
)

# ---------------------------------------------------------------------------
# 2. PII PATTERNS  (for log masking only — NOT applied to LLM input)
# ---------------------------------------------------------------------------

_PII_PATTERNS = [
    (re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"), "[EMAIL]"),
    (re.compile(r"(\+91[\-\s]?)?[6-9]\d{9}"), "[PHONE]"),
    (re.compile(r"\+?[\d\s\-\(\)]{10,15}"), "[PHONE]"),
    (re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"), "[AADHAAR]"),
    (re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"), "[PAN]"),
    (re.compile(r"\b[A-Z][0-9]{7}\b"), "[PASSPORT]"),
    (re.compile(r"https?://\S+"), "[URL]"),
]


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def sanitize_input(text: str, label: str = "input") -> str:
    """
    Sanitize text coming from the user (JD or resume text) before it is
    embedded in an LLM prompt.

    - Removes known prompt-injection phrases only.
    - Does NOT HTML-escape (that would garble text sent to the LLM).
    - Raises ValueError if more than 40% of lines were stripped
      (likely a pure injection attempt).

    Returns the cleaned text.
    """
    if not isinstance(text, str):
        raise TypeError(f"{label} must be a string")

    original_lines = text.splitlines()

    cleaned_lines = []
    removed = 0
    for line in original_lines:
        cleaned_line = _INJECTION_RE.sub("", line).strip()
        if cleaned_line != line.strip() and len(line.strip()) > 0:
            removed += 1
        cleaned_lines.append(cleaned_line)

    cleaned = "\n".join(cleaned_lines).strip()

    # If more than 40% of non-empty lines were mutated, treat as injection attack
    non_empty = [l for l in original_lines if l.strip()]
    if non_empty and removed / len(non_empty) > 0.40:
        raise ValueError(
            f"Potential prompt injection detected in {label}. "
            "Input rejected for safety."
        )

    return cleaned


def mask_pii(text: str) -> str:
    """
    Replace PII tokens with redacted placeholders.
    Use ONLY when writing user-supplied content to log files.
    Do NOT use on text going to the LLM.
    """
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def validate_score(value, field: str = "score") -> float:
    """
    Ensure a score value is a float between 0 and 10.
    Raises ValueError on invalid input (guards against hallucinated scores).
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be numeric, got: {value!r}")
    if not (0.0 <= v <= 10.0):
        raise ValueError(f"{field} must be between 0 and 10, got: {v}")
    return v