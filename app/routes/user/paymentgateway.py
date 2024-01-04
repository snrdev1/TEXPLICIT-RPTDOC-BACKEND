"""
    All Razopay Payment Gateway related routes
"""

import razorpay
from flask import Blueprint, request

from app.config import Config
from app.utils.common import Common
from app.utils.messages import Messages
from app.utils.response import Response

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

        amount = request_params.get("amount")

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
def capture_payment():
    # Get the payment data sent by Razorpay after payment completion
    request_params = request.get_json()
    
    print("request_params : ", request_params)

    # Required parameters
    required_params = ["razorpay_order_id", "razorpay_payment_id", "razorpay_signature"]

    # Check if all required parameters are present in the request params
    if not any(
        (key in request_params) and (request_params[key] not in [None, ""])
        for key in required_params
    ):
        return Response.missing_parameters()

    # Verify payment signature to ensure authenticity
    razorpay_order_id = request_params.get("razorpay_order_id")
    razorpay_payment_id = request_params.get("razorpay_payment_id")
    razorpay_signature = request_params.get("razorpay_signature")

    try:
        # Verify payment signature
        Config.razorpay_client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )

        # Capture payment
        captured_payment = Config.razorpay_client.payment.capture(
            razorpay_payment_id, amount=None
        )

        return Response.custom_response(
            {"captured_payment": captured_payment},
            Messages.OK_RAZROPAY_PAYMENT_CAPTURED,
            True,
            200,
        )

    except Exception as e:
        Common.exception_details("paymentgateway.py: capture_payment", e)
        return Response.server_error()
