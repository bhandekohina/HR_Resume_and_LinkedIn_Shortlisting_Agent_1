# -----------------------------------
# Parse LinkedIn JSON
# -----------------------------------
def parse_linkedin(data):

    return {
        "name": data.get("name", ""),
        "skills": data.get("skills", []),
        "experience": data.get("experience", ""),
        "education": data.get("education", ""),
        "projects": data.get("projects", [])
    }


# -----------------------------------
# Convert LinkedIn Profile to Text
# -----------------------------------
def linkedin_to_text(profile):

    return f"""
Name:
{profile['name']}

Skills:
{', '.join(profile['skills'])}

Experience:
{profile['experience']}

Education:
{profile['education']}

Projects:
{', '.join(profile['projects'])}
"""