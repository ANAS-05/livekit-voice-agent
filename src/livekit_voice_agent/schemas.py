from pydantic import BaseModel


class Subject(BaseModel):
    code: str
    name: str
    credits: int
    grade: str


class StudentResult(BaseModel):
    hall_ticket: str
    name: str
    father_name: str
    course: str
    semester: int
    sgpa: float
    cgpa: float
    result: str
    subjects: list[Subject]
