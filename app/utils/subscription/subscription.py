from datetime import datetime
from typing import Union

from bson import ObjectId

from ...services import userService as UserService


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
        
        # print("check_subscription_report : ", allowed_report_total_count - used_report_total_count > 0 and \
            #    allowed_report_type_count - used_report_type_count > 0)
        
        return allowed_report_total_count - used_report_total_count > 0

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
            new_permissions = UserService.create_user_permission(self.user_permissions.get("menu", {}))
            new_permissions.pop('_id', None)
            self.user_permissions["permissions"] = new_permissions
            UserService.update_user_info(self.user_id, self.user_permissions)
