import datetime
from typing import Dict

from pydantic import BaseModel, Field

from ..enumerator import Enumerator


class ReportPermission(BaseModel):
    allowed: Dict[str, int] = {"total": 0}
    used: Dict[str, int] = {"total": 0}
    
    def __init__(self, **data):
        super().__init__(**data)
        for report_type in Enumerator.ReportType:
            self.used[report_type.value] = 0

class SubscriptionDuration(BaseModel):
    start_date: datetime = Field(default_factory=datetime.datetime.now(datetime.timezone.utc))
    end_date: datetime = Field(default_factory=datetime.datetime.now(datetime.timezone.utc))


class AllowedDocument(BaseModel):
    document_count: int = 0
    document_size: int = 0


class DocumentPermission(BaseModel):
    allowed: AllowedDocument = AllowedDocument()
    used: AllowedDocument = AllowedDocument()

class ChatCount(BaseModel):
    chat_count: int = 0

class ChatPermission(BaseModel):
    allowed: ChatCount = ChatCount()
    used: ChatCount = ChatCount()


class UserPermissions(BaseModel):
    menu: list = []
    subscription_duration: SubscriptionDuration = SubscriptionDuration()
    report: ReportPermission = ReportPermission()
    document: DocumentPermission = DocumentPermission()
    chat: ChatPermission = ChatPermission()


class User(BaseModel):
    name: str = ""
    mobileNumber: str = ""
    email: str = ""
    passwordHash: str = ""
    companyName: str = ""
    website: str = ""
    role: int = int(Enumerator.Role.Personal.value)
    subscription: int = 1
    image: str = ""
    invoices: str = ""
    isActive: bool = True
    createdOn: datetime = Field(default_factory=datetime.datetime.now(datetime.timezone.utc))
    permissions: UserPermissions = UserPermissions()
