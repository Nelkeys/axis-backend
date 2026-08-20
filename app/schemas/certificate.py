from pydantic import BaseModel
from datetime import datetime


class CertificateVerifyResponse(BaseModel):
    student_name: str
    course_title: str
    score: int
    verification_code: str
    issued_at: datetime