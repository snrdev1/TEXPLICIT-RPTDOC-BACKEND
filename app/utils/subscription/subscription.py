from datetime import datetime
from typing import Union

from bson import ObjectId

from ...services import user_service as UserService
from ..enumerator import Enumerator


class Subscription:
    def __init__(self, user_id: Union[str, ObjectId]):
        self.user_id = user_id
        self.user_data = UserService.get_user_by_id(user_id)
        self.user_permissions = self.user_data.get("permissions", {})

    def check_subscription_duration(self) -> bool:
        try:
            current_date = datetime.utcnow()
            subscription_duration = self.user_permissions.get(
                "subscription_duration", {})
            start_date = datetime.strptime(subscription_duration.get(
                "start_date")['$date'], '%Y-%m-%dT%H:%M:%S.%fZ')
            end_date = datetime.strptime(subscription_duration.get("end_date")[
                                         '$date'], '%Y-%m-%dT%H:%M:%S.%fZ')

            # print("check_subscription_duration : ", start_date <= current_date <= end_date)

            return start_date <= current_date <= end_date

        except Exception as e:
            return False

    def check_subscription_chat(self) -> bool:
        try:
            subscription_chat = self.user_permissions.get("chat", {})
            allowed_chat_count = subscription_chat.get(
                "allowed", {}).get("chat_count", 0)
            used_chat_count = subscription_chat.get(
                "used", {}).get("chat_count", 0)

            # print("check_subscription_chat : ", used_chat_count < allowed_chat_count)

            return used_chat_count < allowed_chat_count

        except Exception as e:
            return False

    def check_subscription_report(self, report_type: str) -> bool:
        try:
            subscription_report = self.user_permissions.get("report", {})
            allowed_report_total_count = subscription_report.get(
                "allowed", {}).get("total", 0)
            used_report_total_count = subscription_report.get(
                "used", {}).get("total", 0)

            if report_type == Enumerator.ReportType.ResearchReport.value or report_type == Enumerator.ReportType.DetailedReport.value:
                report_value = 0.5
            else:
                report_value = 1

            return allowed_report_total_count - (used_report_total_count + report_value) >= 0

        except Exception as e:
            return False

    def check_subscription_document(self) -> bool:
        try:
            subscription_document = self.user_permissions.get("document", {})
            allowed_document_size = subscription_document.get(
                "allowed", {}).get("document_size", 0)
            used_document_size = subscription_document.get(
                "used", {}).get("document_size", 0)

            # print("check_subscription_document : ", allowed_document_size > used_document_size)

            return allowed_document_size > used_document_size

        except Exception as e:
            return False

    def check_subscription_new_document(self, upload_documents_size: int = 0) -> bool:
        try:
            subscription_document = self.user_permissions.get("document", {})
            allowed_document_size = subscription_document.get(
                "allowed", {}).get("document_size", 0)
            used_document_size = subscription_document.get(
                "used", {}).get("document_size", 0)

            # print("check_subscription_new_document : ", allowed_document_size > used_document_size + upload_documents_size)

            return allowed_document_size > used_document_size + upload_documents_size

        except Exception as e:
            return False
