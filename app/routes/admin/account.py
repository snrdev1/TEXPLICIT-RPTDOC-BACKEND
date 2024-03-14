from flask import Blueprint, request

from app.services import UserService
from app.utils.common import Common
from app.utils.messages import Messages
from app.utils.parser import Parser
from app.utils import Response

admin_account = Blueprint("admin_account", __name__, url_prefix="/admin")


# Login
@admin_account.route("/login", methods=["POST"])
def admin_login():
    try:
        # Extract login data from request body
        request_params = request.get_json()

        # Required parameters
        required_params = ["email", "password"]

        # Check if all required parameters are present in the request params
        if not all(key in request_params for key in required_params):
            return Response.missing_parameters()

        email = request_params["email"]
        password = request_params["password"]

        # Check email in DB
        existing_user = UserService.get_user_by_email(email)

        # If user not found
        if not existing_user:
            return Response.custom_response([], Messages.INVALID_LOGIN_INFO, False, 400)

        id = existing_user["_id"]

        # Check user is active
        if not UserService.active_user(existing_user):
            return Response.custom_response(
                [], Messages.ERROR_INACTIVE_USER, False, 400
            )

        # Check if user is admin
        if not UserService.check_user_admin(existing_user):
            return Response.custom_response([], Messages.UNAUTHORIZED_ADMIN, False, 400)

        # Check password
        match_password = Common.check_password(existing_user["passwordHash"], password)

        # If password doesn't match
        if not match_password:
            return Response.custom_response([], Messages.INVALID_LOGIN_INFO, False, 400)

        # If user found, generate token
        token = Parser.get_encoded_token(id)

        return Response.custom_response({"token": token}, Messages.OK_LOGIN, True, 200)

    except Exception as e:
        Common.exception_details("adminroutes account.py: admin_login", e)
        return Response.server_error()
