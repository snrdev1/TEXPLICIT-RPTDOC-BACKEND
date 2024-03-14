from datetime import datetime
from typing import Dict

from pydantic import BaseModel, Field

from ..enumerator import Enumerator


class Permission(BaseModel):
    total: int = 0
    report_permissions: Dict[str, int] = {}

    def __init__(self, **data):
        super().__init__(**data)
        if not self.report_permissions:
            self.report_permissions = {
                report_type.value: 0 for report_type in Enumerator.ReportType}


class SubscriptionDuration(BaseModel):
    start_date: datetime = Field(default_factory=datetime.utcnow)
    end_date: datetime = Field(default_factory=datetime.utcnow)


class AllowedDocument(BaseModel):
    document_count: int = 0
    document_size: int = 0


class DocumentPermission(BaseModel):
    allowed: AllowedDocument = AllowedDocument()
    used: AllowedDocument = AllowedDocument()


class ChatPermission(BaseModel):
    allowed: Dict[str, int] = {"chat_count": 0}
    used: Dict[str, int] = {"chat_count": 0}


class UserPermissions(BaseModel):
    menu: list = []
    subscription_duration: SubscriptionDuration = SubscriptionDuration()
    report: Permission = Permission()
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
    createdOn: datetime = Field(default_factory=datetime.utcnow)
    permissions: UserPermissions = UserPermissions()
