from datetime import datetime, timezone

from pydantic import BaseModel, Field

from ..enumerator import Enumerator


class TotalReportCount(BaseModel):
    total: int = 0


class ReportPermission(BaseModel):
    allowed: TotalReportCount = TotalReportCount()


class SubscriptionDuration(BaseModel):
    start_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    end_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))


class AllowedDocument(BaseModel):
    document_size: int = 0


class DocumentPermission(BaseModel):
    allowed: AllowedDocument = AllowedDocument()


class ChatCount(BaseModel):
    chat_count: int = 0


class ChatPermission(BaseModel):
    allowed: ChatCount = ChatCount()


class UserPermissions(BaseModel):
    menu: list = []
    subscription_duration: SubscriptionDuration = SubscriptionDuration()
    report: ReportPermission = ReportPermission()
    document: DocumentPermission = DocumentPermission()
    chat: ChatPermission = ChatPermission()


class AdminUserPermissions(BaseModel):
    name: str = ""
    mobileNumber: str = ""
    email: str = ""
    companyName: str = ""
    website: str = ""
    role: int = int(Enumerator.Role.Personal.value)
    subscription: int = 1
    permissions: UserPermissions = UserPermissions()
