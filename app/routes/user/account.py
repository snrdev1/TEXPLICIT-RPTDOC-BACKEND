"""
    All User account related routes
"""
import os
from datetime import datetime

from flask import Blueprint, request, send_file
from app.config import Config
from app.auth.userauthorization import authorized
from app.services.domainService import DomainService
from app.services.userService import UserService
from app.utils.common import Common
from app.utils.enumerator import Enumerator
from app.utils.messages import Messages
from app.utils.parser import Parser
from app.utils.production import Production
from app.utils.response import Response

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
        required_params = ["name", "email", "password", "domains", "role"]

        # Check if all required parameters are present in the request params
        if not all(
            (key in request_params) and (request_params[key] not in [None, ""])
            for key in required_params
        ):
            return Response.missing_parameters()

        # Extract user data from request body
        user_data = UserService.construct_user_data(
            name=request_params.get("name", ""),
            mobileNumber=request_params.get("mobileNumber", ""),
            email=request_params.get("email", ""),
            passwordHash=Common.encrypt_password(request_params.get("password", "")),
            companyName=request_params.get("companyName", ""),
            website=request_params.get("website", ""),
            role=int(Enumerator.Role.Personal.value),
            subscription=request_params.get("subscription", 1),
            domains=request_params.get("domains", []),
            menu=request_params.get("menu", []),
        )

        existing_user = UserService().get_user_by_email(user_data["email"])

        if existing_user:
            return Response.custom_response([], Messages.DUPLICATE_USER, False, 400)

        response = UserService().create_user(user_data)

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
        existing_user = UserService().get_user_by_email(email)

        # If user not found
        if not existing_user:
            return Response.custom_response([], Messages.INVALID_LOGIN_INFO, False, 400)

        id = existing_user["_id"]

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
        token = Parser.get_encoded_token(id)

        response_data = {
            "token":token,
            "message": "Login Successful"
        }
        return Response.custom_response(response_data,Messages.OK_LOGIN, True, 200)
        # =================================================================
        # Folder Creation
        PRODUCTION_CHECK = Config.GCP_PROD_ENV
        if PRODUCTION_CHECK:
            bucket = Production.get_users_bucket()

            # Name of the folder you want to create
            folder_name = str(id) + "/"

            # Check if the folder already exists
            folder_flag = False
            prefix = folder_name if folder_name.endswith("/") else folder_name + "/"
            blobs = bucket.list_blobs(prefix=prefix)

            for blob in blobs:
                if blob.name.startswith(prefix):
                    folder_flag = True
                else:
                    folder_flag = False
            if folder_flag == True:
                print("Folder already exists!")
            else:
                # Create an empty blob to represent the folder (blobs are like objects in GCS)
                folder_blob = bucket.blob(folder_name)
                # Upload an empty string to create an empty folder
                folder_blob.upload_from_string("")

                # print(f"Created folder {folder_name} in bucket {bucket_name}!")

        else:
            # Creating folder if folder doesn't exist for this user
            folder_path = os.getcwd() + "\\assets\\users"
            folder_path = os.path.join(folder_path, str(id))
            isExist = os.path.exists(folder_path)
            # print(isExist)
            if isExist == False:
                os.makedirs(folder_path, exist_ok=True)
                print("Folder created for user : ", id)

        return Response.custom_response({"token": token}, Messages.OK_LOGIN, True, 200)

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

        response = UserService().update_user_info(user_id, update_dict)
        if response:
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
        user_data = UserService().get_user_by_id(user_id)
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
        user_data = UserService().get_user_by_id(user_id)
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
        response = UserService().save_or_update_image(user_id, image)
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


@account.route("/domains", methods=["GET"])
@authorized
def domains_get_user_domains(logged_in_user):
    """
    The function `domains_get_user_domains` retrieves the domains associated with a logged-in user and
    returns a response containing the retrieved domains.

    Args:
      logged_in_user: The parameter "logged_in_user" is expected to be an object representing a
    logged-in user. It is used to retrieve the "domains" array from the user object.

    Returns:
      a custom response object.
    """
    try:
        user = logged_in_user
        # Get the domains array from the user object
        domains = user["domains"]

        print("Domains : ", domains)

        response = DomainService().get_domains_by_ids(domains)
        return Response.custom_response(
            response, Messages.OK_DOMAINS_RETRIEVAL, True, 200
        )

    except Exception as e:
        Common.exception_details("domains.py: domains_get_user_domains", e)
        return Response.server_error()


# Routes for reset / forgot password


@account.route("/reset-password/generatetoken", methods=["POST"])
def account_reset_password_generate_token():
    try:
        request_params = request.get_json()

        # required parameters check
        required_params = ["email"]
        check_response = Common.check_required_params(request_params, required_params)
        if check_response:
            return Response.missing_required_parameter(check_response)

        email = request_params["email"]

        # Check email in DB
        existing_user = UserService().get_user_by_email(email)

        # If user not found, return a response
        if not existing_user:
            return Response.custom_response([], Messages.INVALID_EMAIL, False, 400)

        success, token = UserService.send_mail_with_reset_token(
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
        Common.exception_details("account.py: account_reset_password_generate_token", e)
        return Response.server_error()


@account.route("/reset-password/verify-token/<string:token>", methods=["GET"])
def account_reset_password_check_token_validity(token):
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

        if decoded_token is None:
            return Response.custom_response(
                [{"validity": False}], Messages.INVALID_TOKEN, False, 400
            )

        existing_user = UserService().get_user_by_id(decoded_token["id"])
        current_time = datetime.utcnow()
        expiry_time = datetime.utcfromtimestamp(decoded_token["exp"])

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
        check_response = Common.check_required_params(request_params, required_params)
        if check_response:
            return Response.missing_required_parameter(check_response)

        token = request_params["token"]
        new_password = request_params["newPassword"]

        decoded_token = Parser.get_decoded_token(token)
        if decoded_token is None:
            return Response.custom_response(
                [{"token_validity": False}], Messages.INVALID_TOKEN, False, 400
            )

        existing_user = UserService().get_user_by_id(decoded_token["id"])

        if not existing_user:
            return Response.custom_response([], Messages.NOT_FOUND_USER, False, 404)

        user_id = existing_user["_id"]

        new_password_hash = Common.encrypt_password(new_password)

        # Old password and new password cannot be same
        current_password_hash = UserService().get_password(user_id)

        if Common.check_password(current_password_hash, new_password):
            return Response.custom_response(
                [], Messages.INVALID_NEW_PASSWORD, False, 400
            )

        response = UserService().update_password(user_id, new_password_hash)

        if response:
            return Response.custom_response([], Messages.OK_PASSWORD_UPDATE, True, 200)

        return Response.custom_response([], Messages.ERROR_PASSWORD_UPDATE, False, 400)

    except Exception as e:
        Common.exception_details(
            "account.py: account_reset_password_update_password", e
        )
        return Response.server_error()
