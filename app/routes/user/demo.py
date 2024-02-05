"""
    All Customer-Demo request related routes
"""

from flask import Blueprint, request

from app.services.demoService import save_demo_request
from app.utils.common import Common
from app.utils.messages import Messages
from app.utils.response import Response

demo = Blueprint("demo", __name__, url_prefix='/demo')


@demo.route("", methods=["POST"])
def request_demo():
    try:
        request_params = request.get_json()

        # Required parameters
        required_params = ["email", "name"]

        # Check if all required parameters are present in the request params
        if not all(
            (key in request_params) and (request_params[key] not in [None, ""])
            for key in required_params
        ):
            return Response.missing_parameters()

        response = save_demo_request(request_params)

        if response:
            return Response.custom_response(
                response, Messages.OK_DEMO_REQUEST, True, 200
            )
        else:
            return Response.custom_response(
                response, Messages.ERROR_DEMO_REQUEST, False, 400
            )

    except Exception as e:
        Common.exception_details("demo.py: request_demo", e)
        return Response.server_error()
