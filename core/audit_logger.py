
"""
audit_logger.py  (SECURITY-HARDENED)
--------------------------------------
Changes from original:
  - PII is masked before anything is written to the log file
  - Candidate name is partially redacted in log (keeps first 3 chars)
  - Structured JSON logging with security_event field
"""

import json
import os
from datetime import datetime
from core.input_sanitizer import mask_pii

LOG_FILE = "outputs/audit_log.json"

# Ensure outputs dir exists
os.makedirs("outputs", exist_ok=True)


def _redact_name(name: str) -> str:
    """Partially redact a candidate name for the log: 'John Doe.pdf' → 'Joh***'"""
    if not name:
        return "[unknown]"
    visible = name[:3]
    return visible + "*" * max(3, len(name) - 3)


def log_override(candidate: str, old_score: float, new_score: float, reason: str):
    """
    Log an HR override event with PII masking applied to the reason field.
    The candidate filename is partially redacted.
    """
    log = {
        "event":        "hr_override",
        "candidate":    _redact_name(candidate),       # partial redaction
        "old_score":    old_score,
        "new_score":    new_score,
        "reason":       mask_pii(reason),              # mask any PII in free-text reason
        "timestamp":    str(datetime.now()),
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log) + "\n")


def log_analysis_event(candidate: str, score: float, recommendation: str,
                       low_confidence: bool = False, security_flag: str = None):
    """
    Log a resume analysis event.  No resume text or PII is written to the log —
    only the derived score and recommendation.
    """
    log = {
        "event":          "resume_analyzed",
        "candidate":      _redact_name(candidate),
        "score":          score,
        "recommendation": recommendation,
        "low_confidence": low_confidence,
        "timestamp":      str(datetime.now()),
    }

    if security_flag:
        log["security_flag"] = mask_pii(security_flag)

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log) + "\n")


def log_security_event(event_type: str, detail: str, endpoint: str = None):
    """
    Log a security-relevant event (rate limit hit, injection attempt, auth failure).
    PII is masked in the detail field.
    """
    log = {
        "event":     "security_event",
        "type":      event_type,
        "detail":    mask_pii(str(detail)[:300]),      # cap length + mask PII
        "endpoint":  endpoint,
        "timestamp": str(datetime.now()),
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log) + "\n")

        