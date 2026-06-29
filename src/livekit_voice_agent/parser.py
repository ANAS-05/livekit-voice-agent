import re

from bs4 import BeautifulSoup

from .schemas import StudentResult, Subject


# Map of Roman numerals used in semester labels to integers.
_ROMAN_TO_INT = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
}


def _cell_text(cell) -> str:
    # Collapse all whitespace into single spaces for clean text extraction.
    return re.sub(r"\s+", " ", cell.get_text(" ", strip=True)).strip()


def _rows(table) -> list[list[str]]:
    # Convert a table into a list of cell-text rows, dropping empty ones.
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells = [_cell_text(c) for c in tr.find_all(["td", "th"])]
        if any(cells):
            rows.append(cells)
    return rows


def _personal_details(outer) -> dict[str, str]:
    # AutoNumber3 holds the personal details in a 2-column label/value layout.
    table = outer.find("table", id="AutoNumber3")
    if not table:
        return {}

    out: dict[str, str] = {}
    for cells in _rows(table):
        # First label/value pair.
        if len(cells) >= 2:
            out[cells[0]] = cells[1]
        # Second label/value pair on the same row.
        if len(cells) >= 4:
            out[cells[2]] = cells[3]

    return {
        "name": out.get("Name", ""),
        "father_name": out.get("Father's Name", ""),
        "course": out.get("Course", ""),
    }


def _subjects(outer) -> list[Subject]:
    # AutoNumber4 holds the marks table: code, name, credits, grade.
    table = outer.find("table", id="AutoNumber4")
    if not table:
        return []

    subjects: list[Subject] = []
    for cells in _rows(table):
        if len(cells) < 4:
            continue
        # Skip the header row ("Sub Code", "Subject Name", ...).
        if cells[0].lower() == "sub code":
            continue
        code = cells[0]
        name = cells[1]
        credits = int(re.sub(r"\D", "", cells[2]) or 0)
        grade = cells[3]
        if code and name and grade:
            subjects.append(Subject(code=code, name=name, credits=credits, grade=grade))

    return subjects


def _result_block(outer) -> tuple[int, str, float, float]:
    # AutoNumber5 holds the semester summary: semester, result+SGPA, CGPA.
    table = outer.find("table", id="AutoNumber5")
    if not table:
        return 0, "", 0.0, 0.0

    semester = 0
    result_text = ""
    cgpa = 0.0

    for cells in _rows(table):
        # Skip the header row.
        if cells[0].lower() == "semester":
            continue
        if len(cells) >= 3:
            # Parse semester as Roman (e.g., "VIII") first, fall back to digits.
            semester_raw = cells[0]
            roman_match = re.search(r"(VIII|VII|VI|IV|V|IX|X|III|II|I)\b", semester_raw, re.IGNORECASE)
            if roman_match:
                semester = _ROMAN_TO_INT[roman_match.group(1).upper()]
            else:
                num_match = re.search(r"\d+", semester_raw)
                semester = int(num_match.group(0)) if num_match else 0

            # The middle cell is "PASSED-9.14" — split status and SGPA later.
            result_cell = cells[1]
            if re.search(r"([\d.]+)", result_cell):
                result_text = result_cell
            cgpa_match = re.search(r"([\d.]+)", cells[2])
            if cgpa_match:
                cgpa = float(cgpa_match.group(1))

    # Split the combined "STATUS-SGPA" cell into separate fields.
    result = ""
    sgpa = 0.0
    if result_text:
        status_match = re.match(r"\s*([A-Z]+)", result_text)
        sgpa_match = re.search(r"([\d.]+)", result_text)
        if status_match:
            result = status_match.group(1)
        if sgpa_match:
            sgpa = float(sgpa_match.group(1))

    return semester, result, sgpa, cgpa


def parse_result(html: str, hall_ticket: str) -> StudentResult:
    # The response has one outer wrapper (#AutoNumber2) with three inner tables.
    soup = BeautifulSoup(html, "html.parser")
    outer = soup.find("table", id="AutoNumber2")
    if not outer:
        raise ValueError("Result table (#AutoNumber2) not found")

    # Pull each section from its dedicated sub-table.
    personal = _personal_details(outer)
    subjects = _subjects(outer)
    semester, result, sgpa, cgpa = _result_block(outer)

    return StudentResult(
        hall_ticket=hall_ticket,
        name=personal.get("name", ""),
        father_name=personal.get("father_name", ""),
        course=personal.get("course", ""),
        semester=semester,
        sgpa=sgpa,
        cgpa=cgpa,
        result=result,
        subjects=subjects,
    )
