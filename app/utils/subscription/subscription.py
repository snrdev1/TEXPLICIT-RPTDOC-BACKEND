from datetime import datetime
from typing import Union

from bson import ObjectId

from ...services import userService as UserService


class Subscription:

    def __init__(self, user_id: Union[str, ObjectId]):
        self.user_id = user_id
        self.user_info = UserService.get_user_by_id(user_id)

    def check_subscription_duration(self) -> bool:
        """
        The function `check_subscription_duration` checks if a user's subscription is active based on the
        start and end dates.

        Args:
        user_id (Union[str, ObjectId]): The `user_id` parameter in the `check_subscription_duration`
        function is expected to be a string or an `ObjectId` type. It is used to identify a specific user
        for whom we want to check the subscription duration.

        Returns:
        The function `check_subscription_duration` returns a boolean value. It returns `True` under the
        following conditions:
        1. If the user information is retrieved successfully and the subscription duration is valid (current
        date falls within the start and end dates of the subscription).
        2. If the subscription duration is missing, it updates the user information and returns `True`.
        """
        # Get the current date
        current_date = datetime.utcnow()

        if not self.user_info:
            return False

        subscription_duration = self.user_info.get(
            "subscription_duration", None)

        if not subscription_duration:
            self.update_user_permissions()
            return True

        start_date = subscription_duration.get("start_date", None)
        end_date = subscription_duration.get("end_date", None)
        if start_date and end_date:
            if current_date >= start_date and current_date <= end_date:
                return True

        return False

    def check_subscription_chat(self) -> bool:
        if not self.user_info:
            return False

        subscription_chat = self.user_info.get("chat", None)

        if not subscription_chat:
            self.update_user_permissions()
            return True

        allowed_chat_count = subscription_chat.get(
            "allowed", {}).get("count", 0)
        used_chat_count = subscription_chat.get("used", {}).get("count", 0)

        if used_chat_count < allowed_chat_count:
            return True

        return False

    def check_subscription_report(self, report_type: str) -> bool:
        if not self.user_info:
            return False

        subscription_report = self.user_info.get("report", None)

        if not subscription_report:
            self.update_user_permissions()
            return True

        allowed_report_total_count = subscription_report.get(
            "allowed", {}).get("total", 0)
        allowed_report_type_count = subscription_report.get(
            "allowed", {}).get(report_type, 0)
        used_report_total_count = subscription_report.get(
            "used", {}).get("total", 0)
        used_report_type_count = subscription_report.get(
            "used", {}).get(report_type, 0)

        if allowed_report_total_count - used_report_total_count > 0 and allowed_report_type_count - used_report_type_count > 0:
            return True

        return False

    def update_user_permissions(self):
        print("Updating user permissions!")

        self.user_info["permissions"] = UserService.create_new_user_permission(
            self.user_info["permissions"]["menu"]
        )
        self.user_info.pop('_id', None)
        UserService.update_user_info(self.user_id, self.user_info)
