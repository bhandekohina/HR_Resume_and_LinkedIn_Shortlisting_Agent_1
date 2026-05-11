from dataclasses import dataclass

@dataclass
class Candidate:
    name: str
    resume_text: str
    rubric: dict
    score: float