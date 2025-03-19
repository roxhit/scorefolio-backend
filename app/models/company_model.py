from pydantic import BaseModel
from typing import Optional
from typing import List


class Eligibility(BaseModel):
    minScore: int
    backlogsAllowed: int


# Data model for a company
class CompanyDetails(BaseModel):
    name: str
    industry: str
    logo: Optional[str]
    recruitmentDate: str
    ctc: str
    roles: List[str]
    status: str
    eligibility: Eligibility
    additionalInfo: Optional[str]
