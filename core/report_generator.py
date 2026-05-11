


import json
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter


# -----------------------------------
# JSON REPORT
# -----------------------------------
def generate_json_report(results, path="outputs/report.json"):
    with open(path, "w") as f:
        json.dump(results, f, indent=4)

# alias
save_json_report = generate_json_report


# -----------------------------------
# HTML REPORT
# -----------------------------------
def generate_html_report(results, path="outputs/report.html"):

    html = """
    <html>
    <head>
        <title>AI HR Screening Report</title>
        <style>
            body { font-family: Arial; margin: 40px; }
            h1 { color: #333; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ccc; padding: 12px; text-align: left; vertical-align: top; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
    <h1>AI HR Screening Report</h1>
    <table>
    <tr>
        <th>Rank</th>
        <th>Candidate</th>
        <th>Final Score</th>
        <th>Recommendation</th>
        <th>Skills</th>
        <th>Experience</th>
        <th>Education</th>
        <th>Projects</th>
        <th>Communication</th>
    </tr>
    """

    for i, r in enumerate(results, 1):
        ev = r.get('evaluation', r.get('rubric', {}))
        html += f"""
        <tr>
            <td>{i}</td>
            <td>{r['name']}</td>
            <td>{r['score']}/100</td>
            <td>{r.get('recommendation', '')}</td>
            <td><b>Score:</b> {ev.get('skills_match', {}).get('score', 0)}/10<br><br>{ev.get('skills_match', {}).get('justification', '')}</td>
            <td><b>Score:</b> {ev.get('experience', {}).get('score', 0)}/10<br><br>{ev.get('experience', {}).get('justification', '')}</td>
            <td><b>Score:</b> {ev.get('education', {}).get('score', 0)}/10<br><br>{ev.get('education', {}).get('justification', '')}</td>
            <td><b>Score:</b> {ev.get('projects', {}).get('score', 0)}/10<br><br>{ev.get('projects', {}).get('justification', '')}</td>
            <td><b>Score:</b> {ev.get('communication', {}).get('score', 0)}/10<br><br>{ev.get('communication', {}).get('justification', '')}</td>
        </tr>
        """

    html += "</table></body></html>"

    with open(path, "w") as f:
        f.write(html)

# alias
save_html_report = generate_html_report


# -----------------------------------
# PDF REPORT
# -----------------------------------
def generate_pdf_report(results, path="outputs/report.pdf"):

    doc = SimpleDocTemplate(path, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("AI HR Screening Report", styles["Heading1"]))
    elements.append(Spacer(1, 20))

    data = [["Rank", "Candidate", "Score", "Recommendation"]]

    for i, r in enumerate(results, 1):
        data.append([
            str(i),
            r["name"],
            f"{r['score']}/100",
            r.get("recommendation", "")
        ])

    table = Table(data, colWidths=[50, 200, 80, 100])
    table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#C2714A")),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.whitesmoke),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0),  12),
        ("BACKGROUND",    (0, 1), (-1, -1), colors.HexColor("#FFF8F2")),
        ("GRID",          (0, 0), (-1, -1), 1, colors.HexColor("#E8D5C0")),
    ]))

    elements.append(table)
    doc.build(elements)

# alias
save_pdf_report = generate_pdf_report
