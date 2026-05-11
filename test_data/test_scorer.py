from parser import extract_resume_text
from scorer import score_resume

# -----------------------------------
# Load Resume
# -----------------------------------
resume_text = extract_resume_text(
    "resumes/resume.pdf"
)

# -----------------------------------
# Sample Job Description
# -----------------------------------
job_description = """

Looking for an AI/ML Engineer with:

- Python
- Machine Learning
- Deep Learning
- NLP
- LangChain
- RAG
- LLM experience
- Flask
- Strong projects in AI

"""

# -----------------------------------
# Score Resume
# -----------------------------------
result = score_resume(
    job_description,
    resume_text
)

# -----------------------------------
# Print Result
# -----------------------------------
print(result)