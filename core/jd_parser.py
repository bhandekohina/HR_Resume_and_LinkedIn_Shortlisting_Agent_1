import json
from core.llm_utils import llm  # your existing LLM wrapper

def parse_jd(jd_text: str):

    prompt = f"""
You are an HR AI system.

Extract structured information from this Job Description.

Return STRICT JSON ONLY:

{{
  "skills": [],
  "experience": "",
  "education": "",
  "certifications": [],
  "responsibilities": []
}}

JD:
{jd_text}
"""

    response = llm.invoke(prompt)

    try:
        return json.loads(response)
    except:
        return {
            "skills": [],
            "experience": "",
            "education": "",
            "certifications": [],
            "responsibilities": []
        }