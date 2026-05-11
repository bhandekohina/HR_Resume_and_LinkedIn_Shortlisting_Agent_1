

import PyPDF2
from docx import Document
import os
import json


# -----------------------------------
# PDF Parser
# -----------------------------------
def extract_text_from_pdf(pdf_file):
    text = ""
    with open(pdf_file, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text


# -----------------------------------
# DOCX Parser
# -----------------------------------
def extract_text_from_docx(docx_file):
    text = ""
    doc = Document(docx_file)
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text


# -----------------------------------
# TXT / LinkedIn Parser
# -----------------------------------
def extract_text_from_txt(txt_file):
    with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    print(f"TXT file content ({len(content)} chars): '{content[:300]}'")  
    # If it's a JSON file (LinkedIn export), flatten it to readable text
    try:
        data = json.loads(content)
        return flatten_linkedin_json(data)
    except (json.JSONDecodeError, ValueError):
        # Plain text — return as-is
        return content


def flatten_linkedin_json(data):
    """Convert LinkedIn JSON export into readable text for the LLM."""
    lines = []

    # Name
    name = f"{data.get('firstName', '')} {data.get('lastName', '')}".strip()
    if name:
        lines.append(f"Name: {name}")

    # Headline / summary
    if data.get('headline'):
        lines.append(f"Headline: {data['headline']}")
    if data.get('summary'):
        lines.append(f"\nSummary:\n{data['summary']}")

    # Experience
    positions = data.get('positions', {}).get('values', data.get('experience', []))
    if positions:
        lines.append("\nExperience:")
        for p in positions:
            title   = p.get('title', '')
            company = p.get('company', {}).get('name', p.get('companyName', ''))
            start   = p.get('startDate', {})
            end     = p.get('endDate', {})
            desc    = p.get('summary', p.get('description', ''))
            date_str = f"{start.get('year','')} - {end.get('year','Present') if end else 'Present'}"
            lines.append(f"  - {title} at {company} ({date_str})")
            if desc:
                lines.append(f"    {desc}")

    # Education
    education = data.get('educations', {}).get('values', data.get('education', []))
    if education:
        lines.append("\nEducation:")
        for e in education:
            school  = e.get('schoolName', '')
            degree  = e.get('degree', '')
            field   = e.get('fieldOfStudy', '')
            lines.append(f"  - {degree} in {field} from {school}")

    # Skills
    skills = data.get('skills', {}).get('values', data.get('skills', []))
    if skills:
        lines.append("\nSkills:")
        skill_names = []
        for s in skills:
            if isinstance(s, dict):
                skill_names.append(s.get('skill', {}).get('name', s.get('name', '')))
            elif isinstance(s, str):
                skill_names.append(s)
        lines.append("  " + ", ".join(filter(None, skill_names)))

    return "\n".join(lines)


# -----------------------------------
# Universal Resume Parser
# -----------------------------------
def extract_resume_text(file_path):
    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".pdf":
        return extract_text_from_pdf(file_path)

    elif extension == ".docx":
        return extract_text_from_docx(file_path)

    elif extension in (".txt", ".json"):
        return extract_text_from_txt(file_path)

    else:
        return "Unsupported File Format"