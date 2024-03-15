from typing import List, Union

from pydantic import BaseModel, Field, root_validator
from .mongo_objectid_validator import PydanticObjectId
from ..enumerator import Enumerator
from ..messages import Messages


class ReportGenerationParameters(BaseModel):
    user_id: Union[str, PydanticObjectId]
    task: str = Field(..., min_length=1)
    report_type: str = Enumerator.ReportType.ResearchReport.value
    source: str = "external"
    format: str = "pdf"
    report_generation_id: str = ""
    websearch: bool = False
    subtopics: list = []
    urls: List[str] = []
    check_existing_report: bool = False
    
    @root_validator
    def check_name_and_age(cls, values):
        report_type_values = [report_type.value for report_type in Enumerator.ReportType.__members__.values()]
        if values['report_type'] not in report_type_values:
            raise ValueError(Messages.INVALID_REPORT_TYPE)
        
        if values['format'] not in ["word", "pdf"]:
            raise ValueError("Output format not supported!")
        
        return values
