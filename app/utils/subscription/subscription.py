from datetime import datetime
from typing import Union

from bson import ObjectId

from ...services import user_service as UserService
from ..enumerator import Enumerator
from ...utils.common import Common

class Subscription:
    def __init__(self, user_id: Union[str, ObjectId]):
        self.user_id = user_id
        self.user_data = UserService.get_user_by_id(user_id)
        self.user_permissions = self.user_data.get("permissions", {})

    def check_subscription_duration(self) -> bool:
        """
        The function `check_subscription_duration` checks if the current date falls within a specified
        subscription duration.
        
        Returns:
          The function `check_subscription_duration` is returning a boolean value. It checks if the
        current date falls within the subscription duration specified by the start date and end date,
        and returns `True` if it does, and `False` if there is an exception or if the current date is
        outside the subscription duration.
        """
        try:
            current_date = datetime.utcnow()
            subscription_duration = self.user_permissions.get("subscription_duration", {})
            start_date = datetime.strptime(subscription_duration.get("start_date", current_date)["$date"], '%Y-%m-%dT%H:%M:%S.%fZ')
            end_date = datetime.strptime(subscription_duration.get("end_date", current_date)["$date"], '%Y-%m-%dT%H:%M:%S.%fZ')

            # print("check_subscription_duration : ", start_date <= current_date < end_date)

            return start_date <= current_date < end_date

        except Exception as e:
            Common.exception_details("Subscription.check_subscription_duration", e)
            return False

    def check_subscription_chat(self) -> bool:
        """
        The function `check_subscription_chat` checks if a user has remaining chat counts based on their
        subscription permissions.
        
        Returns:
          The function `check_subscription_chat` is returning a boolean value. It checks if the used
        chat count is less than the allowed chat count for a subscription and returns `True` if it is,
        otherwise it returns `False`. If any exception occurs during the process, it will also return
        `False`.
        """
        try:
            subscription_chat = self.user_permissions.get("chat", {})
            allowed_chat_count = subscription_chat.get(
                "allowed", {}).get("chat_count", 0)
            used_chat_count = subscription_chat.get(
                "used", {}).get("chat_count", 0)

            # print("check_subscription_chat : ", used_chat_count < allowed_chat_count)

            return used_chat_count < allowed_chat_count

        except Exception as e:
            Common.exception_details("Subscription.check_subscription_chat", e)
            return False

    def check_subscription_report(self, report_type: str) -> bool:
        """
        This function checks if a user has enough remaining report credits based on their subscription
        permissions.
        
        Args:
          report_type (str): The `report_type` parameter in the `check_subscription_report` method is a
        string that specifies the type of report being checked. It can have values such as
        "ResearchReport" or "DetailedReport".
        
        Returns:
          a boolean value indicating whether the user has enough remaining report credits to generate
        the specified type of report.
        """
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
            Common.exception_details("Subscription.check_subscription_report", e)
            return False


    def check_subscription_document(self, upload_documents_size: int = 0) -> bool:
        """
        The function `check_subscription_document` checks if the upload of a document is allowed based
        on subscription limits.
        
        Args:
          upload_documents_size (int): The `upload_documents_size` parameter in the
        `check_subscription_document` method represents the size of the document that the user is trying
        to upload. This method is used to check if the user's subscription allows them to upload a
        document of the given size based on their subscription limits. Defaults to 0
        
        Returns:
          The function `check_subscription_document` returns a boolean value indicating whether the sum
        of the used document size and the size of the documents being uploaded is less than the allowed
        document size for the subscription.
        """
        try:
            subscription_document = self.user_permissions.get("document", {})
            allowed_document_size = subscription_document.get(
                "allowed", {}).get("document_size", 0)
            used_document_size = subscription_document.get(
                "used", {}).get("document_size", 0)

            return allowed_document_size >= (used_document_size + upload_documents_size)

        except Exception as e:
            Common.exception_details("Subscription.check_subscription_document", e)
            return False
