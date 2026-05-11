from core.parser import extract_resume_text

resume_path = "resumes/resume.pdf"

text = extract_resume_text(resume_path)

print(text)