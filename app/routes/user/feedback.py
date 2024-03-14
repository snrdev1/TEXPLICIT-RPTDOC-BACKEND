"""
    All Customer-FeedBack related routes
"""

from flask import Blueprint, request

from app.services.feedback_service import FeedbackService
from app.utils.common import Common
from app.utils.messages import Messages
from app.utils import Response

feedback = Blueprint("feedback", __name__, url_prefix='/feedback')


@feedback.route("", methods=["POST"])
def save_user_feedback():
    try:
        request_params = request.get_json()

        # Required parameters
        required_params = ["email", "name", "comments"]

        # Check if all required parameters are present in the request params
        if not all(
            (key in request_params) and (request_params[key] not in [None, ""])
            for key in required_params
        ):
            return Response.missing_parameters()

        email_id = request_params.get("email")
        comments = request_params.get("comments")
        customer_name = request_params.get("name")

        phone_number = None
        if "phoneNumber" in request_params and (
            request_params.get("phoneNumber") != ""
        ):
            phone_number = int(request_params.get("phoneNumber"))

        feedback_object = {
            "emailId": email_id,
            "customerName": customer_name,
            "phoneNumber": phone_number,
            "comments": comments,
        }

        response = FeedbackService().save_user_feedback(feedback_object)

        if response:
            return Response.custom_response(
                response, Messages.OK_CUSTOMER_FEEDBACK_SAVE, True, 200
            )
        else:
            return Response.custom_response(
                response, Messages.ERROR_CUSTOMER_FEEDBACK_SAVE, False, 400
            )

    except Exception as e:
        Common.exception_details("feedback.py: save_user_feedback", e)
        return Response.server_error()
