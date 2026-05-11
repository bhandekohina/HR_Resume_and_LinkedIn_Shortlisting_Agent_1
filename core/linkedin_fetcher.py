
import requests
import os
from dotenv import load_dotenv

load_dotenv()

PROXYCURL_API_KEY = os.getenv("PROXYCURL_API_KEY")


def extract_username(url):
    url = url.strip().rstrip('/')
    if '/in/' in url:
        return url.split('/in/')[-1].split('/')[0].split('?')[0]
    return None


def fetch_linkedin_profile(url):
    username = extract_username(url)
    if not username:
        raise ValueError(f"Could not extract LinkedIn username from URL: {url}")

    if not PROXYCURL_API_KEY:
        raise ValueError("PROXYCURL_API_KEY is not set in .env")

    print(f"Fetching LinkedIn profile for: {username}")

    response = requests.get(
        "https://nubela.co/proxycurl/api/v2/linkedin",
        headers={"Authorization": f"Bearer {PROXYCURL_API_KEY}"},
        params={"url": f"https://www.linkedin.com/in/{username}/"},
        timeout=15
    )

    if response.status_code != 200:
        raise ValueError(f"Proxycurl API error {response.status_code}: {response.text[:200]}")

    data = response.json()

    if not data:
        raise ValueError("Empty response from Proxycurl API")

    print(f"[linkedin] response keys: {list(data.keys())}")
    return flatten_linkedin_profile(data, url)


def flatten_linkedin_profile(data, original_url=""):
    lines = []

    # Name
    first = data.get('first_name', '')
    last  = data.get('last_name', '')
    name  = f"{first} {last}".strip()
    if name:
        lines.append(f"Name: {name}")

    if original_url:
        lines.append(f"LinkedIn: {original_url}")

    # Headline / summary
    if data.get('headline'):
        lines.append(f"Headline: {data['headline']}")

    if data.get('summary'):
        lines.append(f"\nAbout:\n{data['summary']}")

    # Location
    city    = data.get('city', '')
    country = data.get('country_full_name', '')
    loc     = ', '.join(filter(None, [city, country]))
    if loc:
        lines.append(f"Location: {loc}")

    # Experience
    experiences = data.get('experiences', [])
    if experiences:
        lines.append("\nExperience:")
        for e in experiences:
            title   = e.get('title', '')
            company = e.get('company', '')
            start   = e.get('starts_at', {})
            end     = e.get('ends_at', {})
            desc    = e.get('description', '')

            start_yr = start.get('year', '') if isinstance(start, dict) else ''
            end_yr   = end.get('year', 'Present') if isinstance(end, dict) and end else 'Present'

            lines.append(f"  - {title} at {company} ({start_yr} - {end_yr})")
            if desc:
                lines.append(f"    {desc[:300]}")

    # Education
    education = data.get('education', [])
    if education:
        lines.append("\nEducation:")
        for e in education:
            school = e.get('school', '')
            degree = e.get('degree_name', '')
            field  = e.get('field_of_study', '')
            lines.append(f"  - {degree} in {field} from {school}".strip(" in from"))

    # Skills
    skills = data.get('skills', [])
    if skills:
        lines.append("\nSkills:")
        lines.append("  " + ", ".join(filter(None, skills)))

    # Certifications
    certs = data.get('certifications', [])
    if certs:
        lines.append("\nCertifications:")
        for c in certs:
            if isinstance(c, dict):
                lines.append(f"  - {c.get('name', '')}")
            elif isinstance(c, str):
                lines.append(f"  - {c}")

    return "\n".join(lines)

