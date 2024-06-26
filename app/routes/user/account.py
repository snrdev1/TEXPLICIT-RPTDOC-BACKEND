"""
    All User account related routes
"""
from datetime import datetime, timezone

from flask import Blueprint, request, send_file

from app.auth.userauthorization import authorized
from app.services import UserService
from app.utils import Response, Subscription, socket
from app.utils.common import Common
from app.utils.enumerator import Enumerator
from app.utils.messages import Messages
from app.utils.parser import Parser
from app.utils.validator import User

account = Blueprint("account", __name__, url_prefix="/account")

# Signup


@account.route("/signup", methods=["POST"])
def account_signup():
    """
    POST Method:
        The account_signup function is used to create a new user account.
        It takes in the following parameters:
            name - The full name of the user (required)
            mobileNumber - The mobile number of the user (optional)
            email - The email address of the user (required)
            password - The password of the user (required)
            role - The mode of use for this user (required). Values are either 'Personal' or 'Professional'
            subscription - The number of subscriptions to be created for this user (optional). Default = 1
        Args:

        Returns:
            A response object containing confirmation status
    """
    try:
        request_params = request.get_json()

        # Required parameters
        required_params = ["name", "email", "password"]

        # Check if all required parameters are present in the request params
        if not all(
            (key in request_params) and (request_params[key] not in [None, ""])
            for key in required_params
        ):
            return Response.missing_parameters()

        # Extract user data from request body
        user_data = User(
            name=request_params.get("name", ""),
            email=request_params.get("email", ""),
            passwordHash=Common.encrypt_password(request_params.get("password", "")),
            role=int(request_params.get("role", Enumerator.Role.Personal.value)),
            mobileNumber=request_params.get("mobileNumber", ""),
            companyName=request_params.get("companyName", ""),
            website=request_params.get("website", ""),
            subscription=int(request_params.get("subscription", 1)),
            permissions={
                "menu": request_params.get("menu", [])
            }
        )

        existing_user = UserService.get_user_by_email(user_data.dict().get("email"))

        if existing_user:
            return Response.custom_response([], Messages.DUPLICATE_EMAIL, False, 400)

        response = UserService.create_user(user_data)

        if response:
            return Response.custom_response(
                response, Messages.OK_USER_CREATED, True, 200
            )
        else:
            return Response.custom_response([], Messages.DUPLICATE_USER, True, 409)
    except Exception as e:
        Common.exception_details("account.py: account_signup", e)
        return Response.server_error()


# Login
@account.route("/login", methods=["POST"])
def account_login():
    """
    POST Method:
        The account_login function is used to log in a user.

        Args:

        Returns:
            Confirmation status with jwt token or error status.
    """
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

        # Check user is active
        if not UserService.active_user(existing_user):
            return Response.custom_response(
                [], Messages.ERROR_INACTIVE_USER, False, 400
            )

        # Check password
        match_password = Common.check_password(existing_user["passwordHash"], password)

        # If password doesn't match
        if not match_password:
            return Response.custom_response([], Messages.INVALID_LOGIN_INFO, False, 400)

        # If user found, generate token
        user_id = existing_user["_id"]
        token = Parser.get_encoded_token(user_id)

        response_data = {
            "token": token,
            "message": "Login Successful"
        }

        # If login is successful check if subscription is valid
        subscription = Subscription(user_id)
        subscription_valid = subscription.check_subscription_duration()
        if not subscription_valid:
            print("⚠️ Subscription duration exceeded! Please check plan details.")
            socket.emit_subscription_invalid_status(user_id, "Subscription duration exceeded! Please check plan details.")

        return Response.custom_response(response_data, Messages.OK_LOGIN, True, 200)

    except Exception as e:
        Common.exception_details("account.py: account_login", e)
        return Response.server_error()


# Update User Information
@account.route("/update", methods=["PATCH"])
@authorized
def account_update(logged_in_user):
    """
    PATCH Method:
        The account_update function is used to update the account information of a user.
        It takes in the logged_in_user as an argument and returns a response object with
        confirmation status of updating user information.

        Args:
            logged_in_user: Logged-In User object from authorization decorator.

        Returns:
            The account update status
    """
    try:
        user_id = logged_in_user["_id"]

        # Extract login data from request body
        request_params = request.get_json()

        # Required parameters
        required_params = ["name", "mobileNumber", "companyName", "website"]

        # Check if all required parameters are present in the request params
        if not any(
            (key in request_params) and (request_params[key] not in [None, ""])
            for key in required_params
        ):
            return Response.missing_parameters()

        # Constructing the update dictionary
        update_dict = {
            key: request_params[key]
            for key in request_params
            if (
                key in required_params
                and (request_params[key] and len(request_params[key]) > 0)
            )
        }

        response = UserService.update_user_info(user_id, update_dict)
        if response > -1:
            return Response.custom_response([], Messages.OK_USER_UPDATE, True, 200)
        else:
            return Response.custom_response([], Messages.ERROR_USER_UPDATE, True, 400)

    except Exception as e:
        Common.exception_details("account.py: account_update", e)
        return Response.server_error()


# Get User Data by Id
@account.route("/<string:user_id>", methods=["GET"])
def account_get_user_by_id(user_id):
    """
    GET Method:
        The account_get_user function is used to retrieve a single user from the database via id.
            Args:
                user_id (int): The id of the user to be retrieved.

        Args:
            user_id: Retrieve a single user from the database via id

        Returns:
            A json object containing the user details
    """
    try:
        user_data = UserService.get_user_by_id(user_id)
        if user_data:
            return Response.custom_response(
                user_data, Messages.OK_USER_RETRIEVAL, True, 200
            )
        else:
            return Response.custom_response([], Messages.NOT_FOUND_USER, False, 404)
    except Exception as e:
        Common.exception_details("account.py: account_get_user_by_id", e)
        return Response.server_error()


@account.route("/current-user", methods=["GET"])
@authorized
def account_get_current_user(logged_in_user):
    """
    The function `account_get_current_user` retrieves the current user's data based on their logged-in
    user object.

    Args:
      logged_in_user: The parameter "logged_in_user" is expected to be a dictionary object representing
    the logged-in user. It is assumed to have a key "_id" which represents the user's ID.

    Returns:
      a custom response object. If the user data is found, it returns a custom response with the user
    data, a success message, and a status code of 200. If the user data is not found, it returns a
    custom response with an empty list, a not found message, and a status code of 404. If an exception
    occurs, it returns a server error response
    """
    try:
        user_id = str(logged_in_user["_id"])
        user_data = UserService.get_user_by_id(user_id)
        if user_data:
            return Response.custom_response(
                user_data, Messages.OK_USER_RETRIEVAL, True, 200
            )
        else:
            return Response.custom_response([], Messages.NOT_FOUND_USER, False, 404)
    except Exception as e:
        Common.exception_details("account.py: account_get_user_by_id", e)
        return Response.server_error()


@account.route("/image/<image_name>", methods=["GET"])
def account_retrieve_user_image(image_name):
    """
    GET Method:
        The account_retrieve_user_image function retrieves the image of a user from the database.
            Args:
                image_name (str): The name of the user's profile picture.

        Args:
            image_name: Retrieve the image name from thr url

        Returns:
            The image of the user
    """
    try:
        image_path = UserService.get_image_path(image_name)
        return send_file(image_path, mimetype="image/gif")

        # path_to_private_key = './melodic-map-350806-76efa9752554.json'
        # client = storage.Client.from_service_account_json(json_credentials_path=path_to_private_key)

        # # The bucket on GCS in which to write the CSV file
        # bucket = client.bucket('test-bucket-python-ss')
        # blob = bucket.blob(image_name)
        # read_output = blob.download_as_string()
        # img = Image.open(BytesIO(read_output))
        # image_url = "https://storage.cloud.google.com/"+Environment().BUCKET_NAME+"/"+image_name
        # return image_url

    except Exception as e:
        Common.exception_details("account.py : account_retrieve_user_image", e)
        return Response.server_error()


# Update profile image
@account.route("/update-image", methods=["PUT"])
@authorized
def account_update_user_image(logged_in_user):
    """
    PUT Method:
        The account_update_user_image function is used to update the user image.
        It takes in a logged_in_user parameter and returns an updated confirmation status.


        Args:
            logged_in_user: Logged-In User object from authorization decorator.

        Returns:
            Update confirmation status
    """
    try:
        user_id = str(logged_in_user["_id"])
        request_files = request.files

        # Required parameters
        required_params = ["image"]

        # Check if all required parameters are present in the request params
        if not all(
            (key in request_files) and (request_files[key] not in [None, ""])
            for key in required_params
        ):
            return Response.missing_parameters()

        image = request_files["image"]
        response = UserService.save_or_update_image(user_id, image)
        if response:
            return Response.custom_response(
                response, Messages.OK_USER_IMAGE_UPDATE, True, 200
            )

        return Response.custom_response(
            [], Messages.ERROR_USER_IMAGE_UPDATE, False, 400
        )

    except Exception as e:
        Common.exception_details("account.py : account_update_user_image", e)
        return Response.server_error()


# Routes for reset / forgot password


@account.route("/reset-password/generatetoken", methods=["POST"])
def account_reset_password_generate_token():
    try:
        request_params = request.get_json()

        # required parameters check
        required_params = ["email"]
        check_response = Common.check_required_params(
            request_params, required_params)
        if check_response:
            return Response.missing_required_parameter(check_response)

        email = request_params["email"]

        # Check email in DB
        existing_user = UserService.get_user_by_email(email)

        # If user not found, return a response
        if not existing_user:
            return Response.custom_response([], Messages.INVALID_EMAIL, False, 400)

        success, token = UserService.send_forget_password_mail_with_reset_token(
            existing_user["_id"], existing_user["name"], existing_user["email"]
        )

        if success:
            return Response.custom_response(
                {"token": token}, Messages.OK_PASSWORD_RESET_EMAIL_SENT, True, 200
            )

        return Response.custom_response(
            [], Messages.ERROR_PASSWORD_RESET_EMAIL_SENT, False, 400
        )

    except Exception as e:
        Common.exception_details(
            "account.py: account_reset_password_generate_token", e)
        return Response.server_error()


@account.route("/reset-password/verify-token/<string:token>", methods=["GET"])
def account_reset_password_check_token_validity(token: str):
    """
    The function `account_forgot_password_check_token_validity` checks the validity of a token for a
    forgot password feature in an account system.

    Args:
      token: The `token` parameter is a string that represents a token used for password reset.

    Returns:
      a custom response with the validity of the token, along with a message and status code.
    """
    try:        
        if not token:
            return Response.custom_response(
                [{"validity": False}], Messages.MISSING_PARAMETER_TOKEN, False, 400
            )

        decoded_token = Parser.get_decoded_token(token)

        if not decoded_token:
            return Response.custom_response(
                [{"validity": False}], Messages.INVALID_TOKEN, False, 400
            )

        existing_user = UserService.get_user_by_id(decoded_token["id"])
        current_time = datetime.now(timezone.utc)
        expiry_time = datetime.fromtimestamp(decoded_token["exp"], timezone.utc)

        if not existing_user:
            return Response.custom_response(
                [{"validity": False}], Messages.NOT_FOUND_USER, False, 404
            )

        if current_time > expiry_time:
            return Response.custom_response(
                [{"validity": False}], Messages.ERROR_TOKEN_EXPIRED, False, 403
            )

        return Response.custom_response(
            [{"validity": True}], Messages.OK_TOKEN_VALID, True, 200
        )

    except Exception as e:
        Common.exception_details(
            "account.py: account_reset_password_check_token_validity", e
        )
        return Response.custom_response(
            [{"validity": False}], Messages.INVALID_TOKEN, False, 400
        )


@account.route("/reset-password/update-password", methods=["POST"])
def account_reset_password_update_password():
    """
    POST Method:
        The account_change_password function is used to change the password of a user.
        It takes in the logged_in_user as an argument and returns a response object with
        confirmation status of password update.

        Args:
            logged_in_user: Logged-In User object from authorization decorator.

        Returns:
            A confirmation status of the password update
    """
    try:
        request_params = request.get_json()

        # Required parameters
        required_params = ["token", "newPassword"]
        check_response = Common.check_required_params(
            request_params, required_params)
        if check_response:
            return Response.missing_required_parameter(check_response)

        token = request_params["token"]
        new_password = request_params["newPassword"]

        decoded_token = Parser.get_decoded_token(token)
        if decoded_token is None:
            return Response.custom_response(
                [{"token_validity": False}], Messages.INVALID_TOKEN, False, 400
            )

        existing_user = UserService.get_user_by_id(decoded_token["id"])

        if not existing_user:
            return Response.custom_response([], Messages.NOT_FOUND_USER, False, 404)

        user_id = existing_user["_id"]

        new_password_hash = Common.encrypt_password(new_password)

        # Old password and new password cannot be same
        current_password_hash = UserService.get_password(user_id)

        if Common.check_password(current_password_hash, new_password):
            return Response.custom_response(
                [], Messages.INVALID_NEW_PASSWORD, False, 400
            )

        response = UserService.update_password(user_id, new_password_hash)

        if response:
            return Response.custom_response([], Messages.OK_PASSWORD_UPDATE, True, 200)

        return Response.custom_response([], Messages.ERROR_PASSWORD_UPDATE, False, 400)

    except Exception as e:
        Common.exception_details(
            "account.py: account_reset_password_update_password", e
        )
        return Response.server_error()
