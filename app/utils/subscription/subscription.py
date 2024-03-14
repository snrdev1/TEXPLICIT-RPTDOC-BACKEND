from datetime import datetime
from typing import Union

from bson import ObjectId

from ...services import user_service as UserService
from ..enumerator import Enumerator


class Subscription:
    def __init__(self, user_id: Union[str, ObjectId]):
        self.user_id = user_id
        self.user_permissions = UserService.get_user_by_id(user_id).get("permissions", {})
        self.check_existing_permissions()

    def check_subscription_duration(self) -> bool:
        current_date = datetime.utcnow()
        subscription_duration = self.user_permissions.get("subscription_duration", {})
        start_date = datetime.strptime(subscription_duration.get("start_date")['$date'], '%Y-%m-%dT%H:%M:%S.%fZ')
        end_date = datetime.strptime(subscription_duration.get("end_date")['$date'], '%Y-%m-%dT%H:%M:%S.%fZ')
        
        # print("check_subscription_duration : ", start_date <= current_date <= end_date)
        
        return start_date <= current_date <= end_date
        
    def check_subscription_chat(self) -> bool:
        subscription_chat = self.user_permissions.get("chat", {})
        allowed_chat_count = subscription_chat.get("allowed", {}).get("chat_count", 0)
        used_chat_count = subscription_chat.get("used", {}).get("chat_count", 0)
        
        # print("check_subscription_chat : ", used_chat_count < allowed_chat_count)
        
        return used_chat_count < allowed_chat_count

    def check_subscription_report(self, report_type: str) -> bool:
        subscription_report = self.user_permissions.get("report", {})
        allowed_report_total_count = subscription_report.get("allowed", {}).get("total", 0)
        used_report_total_count = subscription_report.get("used", {}).get("total", 0)
            
        if report_type == Enumerator.ReportType.ResearchReport.value or report_type == Enumerator.ReportType.DetailedReport.value:
            report_value = 0.5
        else:
            report_value = 1
        
        return allowed_report_total_count - (used_report_total_count + report_value) >= 0

    def check_subscription_document(self) -> bool:
        subscription_document = self.user_permissions.get("document", {})
        allowed_document_size = subscription_document.get("allowed", {}).get("document_size", 0)
        used_document_size = subscription_document.get("used", {}).get("document_size", 0)
        
        # print("check_subscription_document : ", allowed_document_size > used_document_size)
        
        return allowed_document_size > used_document_size

    def check_subscription_new_document(self, upload_documents_size: int = 0) -> bool:
        subscription_document = self.user_permissions.get("document", {})
        allowed_document_size = subscription_document.get("allowed", {}).get("document_size", 0)
        used_document_size = subscription_document.get("used", {}).get("document_size", 0)
        
        # print("check_subscription_new_document : ", allowed_document_size > used_document_size + upload_documents_size)
        
        return allowed_document_size > used_document_size + upload_documents_size

    def check_existing_permissions(self):
        existing_permissions = (
            self.user_permissions,
            self.user_permissions.get("document"),
            self.user_permissions.get("chat"),
            self.user_permissions.get("report"),
            self.user_permissions.get("subscription_duration")
        )
        if not all(existing_permissions):
            new_permissions = UserService.create_user_permission(
                menu=self.user_permissions.get("menu", []),
                start_date=self.user_permissions.get("subscription_duration", {}).get("start_date", datetime.utcnow()),
                end_date=self.user_permissions.get("subscription_duration", {}).get("end_date", datetime.utcnow()),
                allowed_report_count=self.user_permissions.get("report", {}).get("allowed", {}).get("total", 0),
                used_report_count=self.user_permissions.get("report", {}).get("used", {}).get("total", 0),
                allowed_document_size=self.user_permissions.get("document", {}).get("allowed", {}).get("document_size", 0),
                allowed_document_count=self.user_permissions.get("document", {}).get("allowed", {}).get("document_count", 0),
                used_document_size=self.user_permissions.get("document", {}).get("used", {}).get("document_size", 0),
                used_document_count=self.user_permissions.get("document", {}).get("used", {}).get("document_count", 0),
                allowed_chat_count=self.user_permissions.get("chat", {}).get("allowed", {}).get("chat_count", 0),
                used_chat_count=self.user_permissions.get("chat", {}).get("used", {}).get("chat_count", 0)
            )
            new_permissions.pop('_id', None)
            self.user_permissions["permissions"] = new_permissions
            UserService.update_user_info(self.user_id, self.user_permissions)
