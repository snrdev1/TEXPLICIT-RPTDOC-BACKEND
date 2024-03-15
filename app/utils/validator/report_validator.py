from pydantic import BaseModel, Field, root_validator
from typing import List
from ..enumerator import Enumerator
from ..messages import Messages


class ReportGenerationParameters(BaseModel):
    task: str = Field(..., min_length=1)
    report_type: str = Enumerator.ReportType.ResearchReport.value
    source: str = "external"
    format: str = "pdf"
    report_generation_id: str = ""
    websearch: bool = False
    subtopics: list = []
    urls: List[str] = []
    
    @root_validator
    def check_name_and_age(cls, values):
        if values['report_type'] not in Enumerator.ReportType:
            raise ValueError(Messages.INVALID_REPORT_TYPE)
        
        if values['format'] not in ["word", "pdf"]:
            raise ValueError("Output format not supported!")
        
        return values
