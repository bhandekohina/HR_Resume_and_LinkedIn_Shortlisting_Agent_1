import os

# ── CHANGED: core/ imports ────────────────────────────────
from core.parser import extract_resume_text
from core.scorer import score_resume

try:
    from core.embedding_engine import compute_similarity
    HAS_EMBEDDING = True
except ImportError:
    HAS_EMBEDDING = False
    print("Warning: embedding_engine not found, using LLM scores only")

# -----------------------------------
# Scoring Rubric Configuration
# (Weights fixed per assignment rubric — do not change)
# -----------------------------------
RUBRIC_WEIGHTS = {
    "skills_match":  30,
    "experience":    25,
    "education":     15,
    "projects":      20,
    "communication": 10
}


def compute_rubric_score(rubric):
    """
    Calculate weighted total score from rubric dimensions.
    Skills(30%), Experience(25%), Education(15%), Projects(20%), Communication(10%)
    """
    try:
        total_weighted_score = 0

        for dimension, weight in RUBRIC_WEIGHTS.items():
            dimension_data = rubric.get(dimension, {})
            score = dimension_data.get("score", 0)

            if not isinstance(score, (int, float)):
                score = 0
            score = max(0, min(10, score))

            contribution = (score / 10) * weight
            total_weighted_score += contribution

        return round(total_weighted_score, 2)

    except Exception as e:
        import traceback
        traceback.print_exc()
        # ── FIXED: 'filename' was undefined here — replaced with generic message
        print(f"Error computing rubric score: {e}")
        return 0.0   # ── FIXED: was returning None, now returns 0.0 so callers don't crash


def get_recommendation(score):
    if score >= 75:
        return "Hire"
    elif score >= 50:
        return "Maybe"
    else:
        return "No Hire"


def format_rubric_output(rubric, final_score):
    output = {
        "total_score": final_score,
        "dimensions":  {}
    }

    for dimension, weight in RUBRIC_WEIGHTS.items():
        dim_data      = rubric.get(dimension, {})
        score         = dim_data.get("score", 0)
        justification = dim_data.get("justification", "No justification provided")

        if score <= 3:
            level = "Poor"
        elif score <= 6:
            level = "Average"
        else:
            level = "Excellent"

        output["dimensions"][dimension] = {
            "score":                score,
            "weight":               weight,
            "weighted_contribution": round((score / 10) * weight, 2),
            "level":                level,
            "justification":        justification
        }

    return output


def rank_resumes(resume_folder, job_description):
    results = []

    for file_name in os.listdir(resume_folder):
        if file_name.endswith((".pdf", ".docx")):
            file_path = os.path.join(resume_folder, file_name)
            print(f"Processing: {file_name}")

            resume_text    = extract_resume_text(file_path)
            rubric         = score_resume(job_description, resume_text)
            llm_score      = compute_rubric_score(rubric)
            detailed_output = format_rubric_output(rubric, llm_score)

            semantic_score = 0
            if HAS_EMBEDDING:
                try:
                    semantic_score = compute_similarity(job_description, resume_text)
                except Exception:
                    semantic_score = 0

            if HAS_EMBEDDING and semantic_score > 0:
                final_score = round(0.70 * llm_score + 0.30 * semantic_score, 2)
            else:
                final_score = llm_score

            recommendation = get_recommendation(final_score)

            results.append({
                "name":           file_name,
                "llm_score":      llm_score,
                "semantic_score": semantic_score,
                "final_score":    final_score,
                "recommendation": recommendation,
                "rubric":         rubric,
                "detailed_rubric": detailed_output
            })

    return sorted(results, key=lambda x: x["final_score"], reverse=True)