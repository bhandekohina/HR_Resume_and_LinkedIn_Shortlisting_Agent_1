from core.ranker import rank_resumes

# -----------------------------------
# Sample JD
# -----------------------------------
job_description = """

Looking for an AI/ML Engineer with:

- Python
- NLP
- LangChain
- Deep Learning
- Flask
- RAG
- LLM experience

"""

# -----------------------------------
# Rank Resumes
# -----------------------------------
results = rank_resumes(
    "resumes",
    job_description
)

# -----------------------------------
# Print Ranked Candidates
# -----------------------------------
print("\n" + "="*60)
print("FINAL RANKINGS")
print("="*60)

for index, candidate in enumerate(results, start=1):

    print(f"\nRank #{index}")

    print(f"Resume: {candidate['file_name']}")

    print(f"Score: {candidate['score']}/100")

    print("\nEvaluation:\n")

    print(candidate["evaluation"])

    print("\n" + "-"*60)