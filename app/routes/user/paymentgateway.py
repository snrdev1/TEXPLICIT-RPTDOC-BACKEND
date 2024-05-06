"""
    All Razopay Payment Gateway related routes
"""

import razorpay
from flask import Blueprint, request

from app.auth.userauthorization import authorized
from app.config import Config
from app.services import payment_gateway_service as PaymentGatewayService
from app.services import user_service as UserService
from app.utils import Response
from app.utils.common import Common
from app.utils.messages import Messages

payment_gateway = Blueprint("payment_gateway", __name__, url_prefix="/payment")


@payment_gateway.route("/create_order", methods=["POST"])
def create_order():
    try:
        request_params = request.get_json()

        # Required parameters
        required_params = ["amount"]

        # Check if all required parameters are present in the request params
        if not any(
            (key in request_params) and (request_params[key] not in [None, ""])
            for key in required_params
        ):
            return Response.missing_parameters()

        amount = int(request_params.get("amount"))

        # Create a Razorpay order
        order_payload = {
            "amount": amount * 100,  # Razorpay expects the amount in paise
            "currency": "INR",  # Change this according to your currency
        }

        order = Config.razorpay_client.order.create(data=order_payload)
        order_id = order["id"]

        return Response.custom_response(
            {"order_id": order_id}, Messages.OK_RAZORPAY_ORDERID_GENERATED, True, 200
        )

    except Exception as e:
        Common.exception_details("paymentgateway.py: create_order", e)
        return Response.server_error()


@payment_gateway.route("/capture_payment", methods=["POST"])
@authorized
def capture_payment(logged_in_user):
    try:
        user_id = logged_in_user["_id"]

        # Get the payment data sent by Razorpay after payment completion
        request_params = request.get_json()

        # Verify payment signature to ensure authenticity
        razorpay_order_id = request_params.get("razorpay_order_id")
        razorpay_payment_id = request_params.get("razorpay_payment_id")
        razorpay_signature = request_params.get("razorpay_signature")
        selected_plan = request_params.get("selected_plan")

        print("Selected plan : ", selected_plan)

        # Verify payment signature
        signature_verification = PaymentGatewayService.verify_payment_signature(
            razorpay_order_id, razorpay_payment_id, razorpay_signature)

        # If signature verification fails return failure response
        if not signature_verification:
            return Response.custom_response(
                [],
                Messages.ERROR_RAZORPAY_PAYMENT_VERIFICATION,
                False,
                401
            )

        # If signature verification succeeds then update records in DB
        PaymentGatewayService.add_payment_history(user_id, request_params)

        # After payment history has been updated then modify the subscription of the user

        report_count = selected_plan.get("report_plan").get("count")
        chat_count = selected_plan.get("chat_plan").get("count")
        document_size_amount = selected_plan.get("document_plan").get("amount").get("value")
        document_size_unit = selected_plan.get("document_plan").get("amount").get("unit")

        # convert the document size amount to bytes
        if document_size_unit == "GB":
            document_size = float(document_size_amount) * 1024 * 1024 * 1024
        else:
            document_size = float(document_size_amount) * 1024 * 1024

        user_subscription_update = UserService.update_user_subscription(
            user_id,
            report_count,
            chat_count,
            document_size
        )

        if not user_subscription_update:
            return Response.custom_response(
                [],
                "Failed to update existing subscription!",
                False,
                400,
            )

        # Return success response
        return Response.custom_response(
            [],
            "Successfully verified payment and modified existing subscription!",
            True,
            200,
        )

    except Exception as e:
        Common.exception_details("paymentgateway.py: capture_payment", e)
        return Response.server_error()


@payment_gateway.route("/payment-history", methods=["GET"])
@authorized
def get_payment_history(logged_in_user):
    try:
        user_id = logged_in_user["_id"]

        # Get payment history
        payment_history = PaymentGatewayService.get_payment_history(user_id)

        return Response.custom_response(
            payment_history,
            "Successfully retrieved payment history!",
            True,
            200,
        )

    except Exception as e:
        Common.exception_details("paymentgateway.py: get_payment_history", e)
        return Response.server_error()
