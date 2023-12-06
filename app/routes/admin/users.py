"""
    All Admin routes for moderating users
"""
from flask import Blueprint, request

from app.auth.userauthorization import admin, authorized
from app.services.userService import UserService
from app.utils.common import Common
from app.utils.enumerator import Enumerator
from app.utils.messages import Messages
from app.utils.response import Response

admin_users = Blueprint("admin_users", __name__, url_prefix="/admin/user")


# List of users to approve
@admin_users.route("/all", methods=["GET"])
@authorized
@admin
def admin_users_for_approval(logged_in_user):
    try:
        response = UserService().get_base_users()
        return Response.custom_response(response, Messages.OK_USER_RETRIEVAL, True, 200)

    except Exception as e:
        Common.exception_details("admin users.py: user_approval", e)
        return Response.server_error()


# User approval
@admin_users.route("/user_status", methods=["POST"])
@authorized
@admin
def admin_user_status_change(logged_in_user):
    try:
        request_params = request.get_json()

        # Required parameters
        required_params = ["userId"]

        # Check if all required parameters are present in the request params
        if not all(
            (key in request_params) and (request_params[key] not in [None, ""])
            for key in required_params
        ):
            return Response.missing_parameters()

        user_id = request_params.get("userId")

        # Check if target user is existing
        existing_user = UserService().get_user_by_id(user_id)

        if not existing_user:
            return Response.custom_response([], Messages.NOT_FOUND_USER, False, 400)

        if existing_user["isActive"] == False:
            response = UserService().activate_user(user_id)
            if response:
                return Response.custom_response(
                    response, Messages.OK_USER_ACTIVATED, True, 200
                )
            else:
                return Response.custom_response(
                    response, Messages.ERROR_USER_ACTIVATED, False, 400
                )
        else:
            response = UserService().deactivate_user(user_id)
            if response:
                return Response.custom_response(
                    response, Messages.OK_USER_DEACTIVATED, True, 200
                )
            else:
                return Response.custom_response(
                    response, Messages.ERROR_USER_DEACTIVATED, False, 400
                )

    except Exception as e:
        Common.exception_details("admin users.py: admin_user_status_change", e)
        return Response.server_error()


@admin_users.route("/user-add-update", methods=["POST"])
@authorized
@admin
def admin_add_update_user(logged_in_user):
    try:
        request_params = request.get_json()
        # Required parameters
        required_params = ["userId", "email"]

        # Check if any of the required parameters are present in the request params
        if not any(
            (key in request_params) and (request_params[key] not in [None, ""])
            for key in required_params
        ):
            return Response.missing_parameters()

        print("Request params : ", request_params)

        user_info = {
            "name": request_params.get("name", ""),
            "email": request_params.get("email", ""),
            "mobileNumber": request_params.get("mobileNumber", ""),
            "companyName": request_params.get("companyName", ""),
            "website": request_params.get("website", ""),
            "domains": request_params.get("domains", []),
            "role": request_params.get("role", int(Enumerator.Role.Personal.value)),
            "permissions": {"menu": request_params.get("menu", [])},
            "subscription": request_params.get("subscription", 1)
        }

        if "userId" in request_params:
            # Update existing user
            target_user_id = request_params.get("userId")
            response = UserService().update_user_info(target_user_id, user_info)

            if response:
                return Response.custom_response([], Messages.OK_USER_UPDATE, True, 200)

        else:
            # Check if user exists with same email id
            existing_user = UserService().get_user_by_email(user_info["email"])

            if existing_user:
                return Response.custom_response(
                    [], Messages.DUPLICATE_EMAIL, False, 400
                )

            # Insert new user
            new_user_info = UserService.construct_user_data(
                name=user_info["name"],
                mobileNumber=user_info["mobileNumber"],
                email=user_info["email"],
                companyName=user_info["companyName"],
                website=user_info["website"],
                role=user_info["role"],
                subscription=user_info["subscription"],
                domains=user_info["domains"],
                menu=user_info["permissions"]["menu"],
            )
            response = UserService().create_user(new_user_info)

            if response:
                user_id = response
                user_name = user_info["name"]
                user_email = user_info["email"]
                success, token = UserService.send_mail_with_reset_token(
                    user_id, user_name, user_email
                )

                if success:
                    print("User email sent successfully!")
                else:
                    print("Failed to send email!")

                return Response.custom_response(
                    response, Messages.OK_USER_CREATED, True, 200
                )

        return Response.custom_response(
            response, Messages.ERROR_USER_UPDATE, False, 400
        )

    except Exception as e:
        Common.exception_details("admin users.py : admin_add_update_user",e)
        return Response.server_error()
