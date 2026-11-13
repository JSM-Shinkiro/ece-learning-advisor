"""Dated public references for reading enrollment conditions alongside the catalog."""

from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field

from .models import StrictModel

REFERENCE_PATH = Path("data/catalog/ece_enrollment_references_2026_2027.json")
DEPARTMENT_COURSES = "https://ecse.engineering.arizona.edu/undergrad-programs/courses/"
ADVISED_PLAN = "https://engineering.arizona.edu/pdfs/4-year-degree-plans/2026/ElectricalComputerEngineering26-27r.pdf"
PUBLIC_CLASS_SEARCH = "https://studentcenter.arizona.edu/app/ui/public/select-campus"
CourseCode = Annotated[str, Field(pattern=r"^ECE[1-4]\d{2}[A-Z]{0,2}$")]


class EnrollmentReference(StrictModel):
    course_id: str = Field(pattern=r"^\d{7}$")
    requirement_reference: str = Field(pattern=r"^\d{1,12}$")
    department_summary: str = Field(min_length=1, max_length=500)
    plan_summary: str | None = Field(default=None, min_length=1, max_length=500)


class EnrollmentReferences(StrictModel):
    catalog_version: str = Field(pattern=r"^20\d{2}-20\d{2}$")
    reviewed_on: date
    courses: dict[CourseCode, EnrollmentReference] = Field(min_length=1)

    def for_course(self, code, course_url, requirement_reference, catalog_version):
        reference = self.courses.get(code)
        if (reference is not None and self.catalog_version == catalog_version
                and course_url == "https://catalog.arizona.edu/courses/" + reference.course_id
                and requirement_reference == reference.requirement_reference):
            return reference
        return None


@lru_cache(maxsize=4)
def load_enrollment_references(path=Path(__file__).resolve().parents[1] / REFERENCE_PATH):
    return EnrollmentReferences.model_validate_json(Path(path).read_bytes())
