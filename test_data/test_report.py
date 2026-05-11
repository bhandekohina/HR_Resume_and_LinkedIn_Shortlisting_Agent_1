from core.ranker import rank_resumes

from core.report_generator import (
    save_json_report,
    save_html_report
)

# -----------------------------------
# Sample Job Description
# -----------------------------------
job_description = """

Looking for an AI/ML Engineer with:

- Python
- Machine Learning
- NLP
- LangChain
- Deep Learning
- Flask
- RAG
- LLM experience

"""

# -----------------------------------
# Rank Candidates
# -----------------------------------
results = rank_resumes(
    "resumes",
    job_description
)

# -----------------------------------
# Save Reports
# -----------------------------------
save_json_report(
    results,
    "outputs/report.json"
)

save_html_report(
    results,
    "outputs/report.html"
)

print("\nReports Generated Successfully!")