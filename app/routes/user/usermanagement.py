"""
    All User Management related routes
"""
import math

from bson import ObjectId
from flask import Blueprint, request

from app.auth.userauthorization import authorized
from app.services import UserService
from app.services.user_management_service import UserManagementService
from app.utils import Response
from app.utils.common import Common
from app.utils.enumerator import Enumerator
from app.utils.messages import Messages

usermanagement = Blueprint("usermanagement", __name__,
                           url_prefix="/user-management")


# Manage Users


@usermanagement.route("/add-user", methods=["POST"])
@authorized
def add_user(logged_in_user):
    """
    Create a new child user for the logged in parent/professional user
    """
    try:
        user_id = logged_in_user.get("_id")
        request_body = request.get_json()
        print(request_body)
        user_data = {
            "name": request_body["name"],
            "email": request_body["email"],
            "passwordHash": "",
            "parentUserId": ObjectId(user_id),
            "companyName": logged_in_user["companyName"],
            "website": logged_in_user["website"],
            "role": int(Enumerator.Role.Child.value),
            "subscription": 1,
            "image": "",
            "permissions": {
                "menu": request_body["menus"]
            },
            "invoices": []
        }
        print("User Data:", user_data)

        existing_user = UserService.get_user_by_email(user_data["email"])

        if existing_user:
            return Response.custom_response([], Messages.DUPLICATE_USER, False, 400)

        response = UserManagementService().create_user(user_data)

        if response:
            print("Response:", response)
            user_id = response
            user_name = user_data["name"]
            user_email = user_data["email"]
            success, token = UserService.send_mail_with_reset_token(
                user_id, user_name, user_email
            )

            if success:
                print("User email sent successfully!")
            else:
                print("Failed to send email!")

            return Response.custom_response([], Messages.OK_USER_CREATED, True, 200)
        else:
            return Response.custom_response([], Messages.DUPLICATE_USER, True, 200)

    except Exception as e:
        Common.exception_details("usermanagement.py : add_user", e)


@usermanagement.route("/get-users", methods=["GET"])
@authorized
def get_child_users(logged_in_user):
    """
    Get all the child users for the logged in professional user
    """
    try:
        pageIndex = int(request.args.get('pageIndex'))
        pageSize = int(request.args.get('pageSize'))

        response, total_recs = UserManagementService().get_child_users(
            parent_user=logged_in_user["_id"], pageIndex=pageIndex, pageSize=pageSize
        )
        modified_response = {
            "users": response,
            "totalRecs": total_recs,
            "totalPageSize": math.ceil(total_recs / pageSize)
        }
        # print("\nModified response: ", modified_response)
        # print()
        if response:
            return Response.custom_response(
                modified_response, Messages.OK_USERS_RETRIEVAL, True, 200
            )
        else:
            return Response.custom_response([], Messages.NOT_FOUND_USERS, True, 200)

    except Exception as e:
        Common.exception_details("usermanagement.py : get_child_users", e)


@usermanagement.route("/get-user/<string:_id>", methods=["GET"])
@authorized
def get_child_user_by_id(logged_in_user, _id):
    """
    Get the child user from the user id
    """
    try:
        response = UserManagementService().get_child_users(
            parent_user=logged_in_user["_id"], user_id=_id)

        if response:
            return Response.custom_response(
                response, Messages.OK_USER_RETRIEVAL, True, 200
            )
        else:
            return Response.custom_response([], Messages.NOT_FOUND_USER, True, 400)

    except Exception as e:
        Common.exception_details("usermanagement.py : get_child_user_by_id", e)


@usermanagement.route("/edit-user/<string:_id>", methods=["PUT"])
@authorized
def edit_user(logged_in_user, _id):
    """
    Get the child user from the user id
    """
    try:
        request_body = request.get_json()
        # print("Request body : ", request_body)
        response = UserManagementService().edit_user(
            _id, request_body, logged_in_user["_id"]
        )

        if response:
            return Response.custom_response(
                response, Messages.OK_USER_UPDATE, True, 200
            )
        else:
            return Response.custom_response([], Messages.ERROR_USER_UPDATE, True, 400)

    except Exception as e:
        Common.exception_details("usermanagement.py : edit_user", e)


@usermanagement.route("/del-user/<string:user_id>", methods=["DELETE"])
@authorized
def del_user(logged_in_user, user_id):
    """
    Remove the child user with the user id
    """
    try:
        # request_body = request.get_json()
        # print("Request body : ", request_body)
        response = UserManagementService().delete_user(
            user_id, logged_in_user["_id"])

        if response:
            return Response.custom_response(
                response, Messages.OK_USER_DELETED, True, 200
            )
        else:
            return Response.custom_response([], Messages.ERROR_USER_DELETE, True, 400)

    except Exception as e:
        Common.exception_details("usermanagement.py : del_user", e)


# Utils

@usermanagement.route("/get-menu-names", methods=["GET"])
@authorized
def get_menus(logged_in_user):
    """
    Get all the menu names associated with the requested menu IDs
    """
    try:
        req = request.args
        menu_ids = [value for value in req.getlist("menuIds")]

        response = UserManagementService().get_user_menus(menu_ids)
        print("Response from get_user_menus : ", response)

        if response:
            return Response.custom_response(
                response, Messages.OK_MENU_NAMES_FOUND, True, 200
            )
        else:
            return Response.custom_response([], Messages.ERROR_MENU_NAMES, True, 400)

    except Exception as e:
        Common.exception_details("usermanagement.py : get_menus", e)
