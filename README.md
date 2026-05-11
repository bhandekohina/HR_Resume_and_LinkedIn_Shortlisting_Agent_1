# 🤖 HR Resume Agent

AI-powered resume screening tool that scores and ranks candidates against a job description using a transparent, rubric-based evaluation.

---

## 1. Project Overview

An HR professional uploads resumes (PDF, DOCX, or TXT) and pastes a job description. The agent:

1. **Parses** each resume into plain text
2. **Scores** it across 5 weighted dimensions via LLM
3. **Ranks** candidates by composite score (0–100)
4. **Generates** exportable reports (JSON, HTML, PDF)
5. **Allows** HR score overrides with a full audit trail

Every score includes a plain-English justification. Low-confidence results and prompt-injection attempts are flagged visibly in the UI — never silently dropped.

---

## 2. Agent Architecture

**Pattern:** Plan-and-Execute — a fixed sequential pipeline orchestrated by Flask. No dynamic tool selection; the task has a deterministic flow that doesn't benefit from a ReAct loop.

```
HR Frontend (index.html)
        │  POST /api/analyze
        ▼
api_server.py  ── Auth (X-API-Key) · Rate limiting · Audit logging
        │
        ├─▶ parser.py            Extract text (PyPDF2 / python-docx / JSON flattener)
        │
        ├─▶ input_sanitizer.py   Strip prompt injection patterns
        │
        ├─▶ scorer.py            Build 2-step CoT prompt → call Groq LLM (temp=0)
        │
        ├─▶ llm_utils.py         Parse JSON (3-strategy fallback) → Pydantic validate
        │
        ├─▶ ranker.py            Weighted sum → ×10 scale → Hire / Maybe / No Hire
        │
        └─▶ report_generator.py  JSON · HTML · PDF output
                │
            audit_logger.py      Log events (no PII written to disk)
```

| Module | Responsibility |
|--------|----------------|
| `api_server.py` | Flask orchestrator, auth, rate limiting |
| `parser.py` | PDF / DOCX / TXT / LinkedIn JSON → plain text |
| `input_sanitizer.py` | Injection pattern stripping, length validation |
| `scorer.py` | Prompt construction, LLM call, score weighting |
| `llm_utils.py` | Groq SDK client, JSON fallback parser, Pydantic schema |
| `ranker.py` | Weighted formula, optional semantic blend, recommendation |
| `report_generator.py` | Exportable report generation |
| `audit_logger.py` | Security & operational event logging |

---

## 3. LLM & Framework Choice

### LLM

| | |
|---|---|
| **Model** | `llama-3.3-70b-versatile` |
| **Provider** | Groq |
| **Context window** | 128 000 tokens |
| **Temperature** | `0` (deterministic scoring) |

**Why Groq + Llama 3.3 70B:**
- **Speed:** Groq's LPU hardware is ~10× faster than standard GPU inference — critical when screening batches of resumes
- **Cost:** Free tier + low per-token pricing; practical for high-volume HR use
- **Open-weight:** No model vendor lock-in; Llama 3.3 70B reliably produces structured JSON when prompted correctly
- **vs GPT-4o / Claude:** Comparable quality on structured extraction tasks at significantly lower latency and cost
- **vs self-hosted:** Groq gives open-weight quality without GPU infrastructure overhead

### Framework

**Custom Flask pipeline** — no LangChain or AutoGen.

- The task is a fixed sequence (parse → sanitize → score → rank → report). A framework agent loop adds latency and complexity with no benefit.
- Direct Groq SDK calls give full control over the three-strategy JSON fallback parser and Pydantic validation layer — harder to implement cleanly inside framework abstractions.

---

## 4. Security Mitigations

| # | Mitigation | Implementation |
|---|------------|----------------|
| 1 | **API key auth** | All `/api/*` endpoints require `X-API-Key` header matching `HR_API_KEY` from `.env`. Missing/wrong key → `401`. Failures logged. |
| 2 | **Rate limiting** | Flask-Limiter: 200/day global; `/api/analyze` capped at 20/hr; LinkedIn at 10/hr. Violations → `429` + logged. |
| 3 | **Prompt injection guard** | `input_sanitizer.py` strips patterns like `IGNORE PREVIOUS`, `SYSTEM:`, `[INST]` before prompt construction. Detections set `_security_flag` visible in HR UI. |
| 4 | **Pydantic output validation** | Every LLM response validated against `RubricResponse` schema. Scores outside 0–10 are clamped. All-zero responses set `_low_confidence = True`. |
| 5 | **3-strategy JSON parser** | `llm_utils.py`: fence stripping → regex extraction → safe fallback. Malformed LLM output never crashes the pipeline. |
| 6 | **File upload hardening** | Whitelist: `{pdf, docx, txt}` only. `secure_filename` prevents path traversal. 50 MB limit. Temp files deleted in `finally` block. |
| 7 | **PII-safe audit logging** | `audit_logger.py` logs scores and events only — resume text and personal data are never written to disk. |
| 8 | **No hardcoded secrets** | All keys (`GROQ_API_KEY`, `HR_API_KEY`, `PROXYCURL_API_KEY`) loaded via `python-dotenv` from `.env`. Repo ships `.env.example` only. |
| 9 | **Debug mode off** | `app.run(debug=False)` — Flask's interactive debugger is never exposed. |

---

## 5. Setup Instructions

**Prerequisites:** Python 3.10+, a [Groq API key](https://console.groq.com/keys)

```bash
# 1. Clone
git clone https://github.com/your-org/hr-resume-agent.git
cd hr-resume-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure secrets
cp .env.example .env
# Fill in GROQ_API_KEY, HR_API_KEY, and optionally RAPIDAPI_KEY

# 4. Run
python api_server.py
# → http://localhost:8000
```

**`.env` variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ | Groq inference API key |
| `HR_API_KEY` | ✅ | Secret sent as `X-API-Key` header by the frontend |
| `PROXYCURL_API_KEY` | Optional | Enables LinkedIn profile ingestion |