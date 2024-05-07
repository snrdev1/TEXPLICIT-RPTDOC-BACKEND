import os
from typing import Union
from urllib.parse import urljoin

from bson import ObjectId
from flask import request

from app.config import Config
from app.models.mongoClient import MongoClient
from app.utils import constants as Constants
from app.utils.email_helper import send_mail
from app.utils.formatter import cursor_to_dict

from ..utils import Common, Enumerator, Parser, PipelineStages, Production


def get_image_path(image_name):
    """
    The get_image_path function takes in an image name and returns the path to that image.
        This function is used by the get_image_url function below.

    Args:
        image_name: Get the image name from the database

    Returns:
            The path of the image
    """

    image_path = os.path.join(Config.USER_IMAGE_UPLOAD_FOLDER, image_name)
    return image_path


# ADMIN ROUTES


def check_user_admin(user_details):
    """
    The function `check_user_admin` checks if a user is an admin based on their role in the user
    details.

    Args:
      user_details: The user_details parameter is a dictionary that contains information about a
    user. It is expected to have a key called "role" which represents the role of the user.

    Returns:
      a boolean value. It returns True if the user details exist and the role is equal to the
    integer value of the Enumerator Role Admin, and False otherwise.
    """
    try:
        if user_details and user_details["role"] == int(Enumerator.Role.Admin.value):
            return True
        else:
            return False

    except Exception as e:
        Common.exception_details("UserService.check_user_admin", e)
        return False


def activate_user(user_id):
    """
    The `approve_user` function updates the `isActive` field of a user in the database to True and
    returns the number of modified documents.

    Args:
      user_id: The user_id parameter is the unique identifier of the user that needs to be approved.

    Returns:
      either the number of documents modified (as a string) if the update operation was successful,
    or None if the update operation was not successful. If an exception occurs, it will return
    False.
    """
    try:
        m_db = MongoClient.connect()

        query = {"_id": ObjectId(user_id)}
        new_values = {"$set": {"isActive": True}}
        response = m_db[Config.MONGO_USER_MASTER_COLLECTION].update_one(
            query, new_values
        )

        if response:
            return str(response.modified_count)

        return None

    except Exception as e:
        Common.exception_details("UserService.approve_user", e)
        return False


def deactivate_user(user_id):
    """
    The `deactivate_user` function deactivates a user by updating their `isActive` field to `False`
    in the user master collection.

    Args:
      user_id: The user_id parameter is the unique identifier of the user that needs to be
    deactivated.

    Returns:
      the number of documents modified in the database if the deactivation is successful. If the
    deactivation is not successful or an exception occurs, it returns None or False respectively.
    """
    try:
        m_db = MongoClient.connect()

        query = {"_id": ObjectId(user_id)}
        new_values = {"$set": {"isActive": False}}
        response = m_db[Config.MONGO_USER_MASTER_COLLECTION].update_one(
            query, new_values
        )

        if response:
            return str(response.modified_count)

        return None

    except Exception as e:
        Common.exception_details("UserService.deactivate_user", e)
        return False


def create_or_update_user(user_info):
    try:
        query = {"email": user_info["email"]}
        m_db = MongoClient.connect()
        response = m_db[Config.MONGO_USER_MASTER_COLLECTION].update_one(
            query, user_info, upsert=True
        )

        # If new user was created then send him a mail with generated token for password reset
        if response.upserted_id:
            print("Inserted new user!")
            user_id = response.upserted_id
            user_name = user_info["name"]
            user_email = user_info["email"]
            success, token = send_mail_with_reset_token(
                user_id, user_name, user_email
            )

            return {
                "response": response.upserted_id,
                "modified_count": 0,
                "user_email_sent": success,
                "token": token,
            }

        return {
            "response": None,
            "modified_count": response.modified_count,
            "user_email_sent": None,
            "token": None,
        }

    except Exception as e:
        Common.exception_details("UserService.create_or_update_user : ", e)
        return None


# USER ROUTES


def active_user(user_details):
    """
    The function "active_user" checks if a user is active based on their details.

    Args:
      user_details: The parameter "user_details" is expected to be a dictionary containing
    information about a user. It is used to determine if the user is active or not. The dictionary
    should have a key "isActive" which should have a boolean value indicating the user's active
    status.

    Returns:
      a boolean value. If the "user_details" parameter is not empty and the value of the "isActive"
    key is True, then the function returns True. Otherwise, it returns False.
    """
    try:
        if user_details and user_details["isActive"]:
            return True
        else:
            return False

    except Exception as e:
        Common.exception_details("UserService.active_user", e)
        return False


def send_mail_with_token(user_id, user_name, user_email, subject, body_template, link_path):
    """
    Helper function to send an email with a token to the user.

    Args:
        user_id: The user ID of the user for whom the token is being generated.
        user_name: The name of the user.
        user_email: The email address of the user.
        subject: The subject line of the email.
        body_template: The template for the email body.
        link_path: The path to be appended to the reset link.

    Returns:
        A tuple containing the success status (bool) and the generated token (str).
    """
    try:
        token = Parser.get_encoded_token(user_id)
        origin = request.environ["HTTP_ORIGIN"]
        reset_password_link = urljoin(origin, f"/{link_path}/{token}")
        mail_body = body_template.format(
            name=user_name,
            link=reset_password_link,
            sender=Config.MAIL_SENDER_NAME,
        )
        receivers = [{"name": user_name, "email": user_email}]
        success = send_mail(subject, mail_body, receivers)
        return success, token
    except Exception as e:
        Common.exception_details("UserService.send_mail_with_token : ", e)
        return None, None


def send_forget_password_mail_with_reset_token(user_id, user_name, user_email):
    """
    The function `send_forget_password_mail_with_reset_token` sends an email to a user
    with a password reset token and returns a success status and the generated token.

    Args:
        user_id: The user ID of the user for whom the password reset token is being generated.
        user_name: The name of the user who requested the password reset.
        user_email: The email address of the user who needs to reset their password.

    Returns:
        The function `send_forget_password_mail_with_reset_token` returns two values:
        `success` and `token`.
    """
    return send_mail_with_token(
        user_id,
        user_name,
        user_email,
        Constants.PASSWORD_RESET_REQUEST_MAILSUBJECT,
        Constants.PASSWORD_RESET_REQUEST_MAILBODY,
        "reset-password",
    )


def send_mail_with_reset_token(user_id, user_name, user_email):
    """
    The function `send_mail_with_reset_token` sends an email to a user with a password
    reset token and returns a success status and the generated token.

    Args:
        user_id: The user ID of the user for whom the password reset token is being generated.
        user_name: The name of the user who requested the password reset.
        user_email: The email address of the user who needs to reset their password.

    Returns:
        The function `send_mail_with_reset_token` returns two values: `success` and `token`.
    """
    return send_mail_with_token(
        user_id,
        user_name,
        user_email,
        Constants.NEW_ACCOUNT_MAILSUBJECT,
        Constants.NEW_ACCOUNT_MAILBODY,
        "reset-password",
    )


def get_all_users():
    """
    The get_all_users function returns a list of all users in the database.
        :return: A list of dictionaries containing user information.

    Args:
        self: Refer to the object itself

    Returns:
        A list of dictionaries

    """
    m_db = MongoClient.connect()

    pipeline = [PipelineStages.stage_find_all()] + _common_user_pipeline()
    response = m_db[Config.MONGO_USER_MASTER_COLLECTION].aggregate(pipeline)

    return cursor_to_dict(response)


def get_base_users():
    try:
        m_db = MongoClient.connect()

        pipeline = [
            PipelineStages.stage_match(
                {
                    "role": {
                        "$in": [
                            # int(Enumerator.Role.Admin.value),
                            int(Enumerator.Role.Personal.value),
                            int(Enumerator.Role.Professional.value),
                        ]
                    }
                }
            ),
            PipelineStages.stage_sort({"_id": -1}),
        ] + _common_user_pipeline()
        response = m_db[Config.MONGO_USER_MASTER_COLLECTION].aggregate(
            pipeline)

        return cursor_to_dict(response)

    except Exception as e:
        Common.exception_details("UserService.get_base_users : ", e)
        return None


def get_users_for_approval():
    """
    The get_users_for_approval function returns a list of all users in the database with
    isActive = False, i.e. the users that need to be approved.
        :return: A list of dictionaries containing user information.

    Args:
        self: Refer to the object itself

    Returns:
        A list of dictionaries

    """
    m_db = MongoClient.connect()

    pipeline = [
        PipelineStages.stage_match(
            {
                "isActive": False,
            }
        ),
    ] + _common_user_pipeline()
    response = m_db[Config.MONGO_USER_MASTER_COLLECTION].aggregate(pipeline)

    return cursor_to_dict(response)


def get_user_by_id(user_id):
    """
    The get_user_by_id function takes in a user_id and returns the corresponding user object.

    Args:
        self: Represent the instance of the class
        user_id (str): The id of the desired User object.

    Returns:
        A dictionary with the user's information
    """
    try:
        m_db = MongoClient.connect()

        pipeline = [
            PipelineStages.stage_match({"_id": ObjectId(user_id)})
        ] + _common_user_pipeline()

        response = m_db[Config.MONGO_USER_MASTER_COLLECTION].aggregate(
            pipeline)

        return cursor_to_dict(response)[0]

    except Exception as e:
        Common.exception_details("user_service.get_user_by_id", e)
        return None


def get_user_by_ids(ids):
    m_db = MongoClient.connect()

    pipeline = [
        PipelineStages.stage_match({"_id": {"$in": ids}, "isActive": True})
    ] + _common_user_pipeline()

    response = m_db[Config.MONGO_USER_MASTER_COLLECTION].aggregate(pipeline)

    return cursor_to_dict(response)


def get_password(user_id):
    """
    The get_password function takes a user_id as an argument and returns the passwordHash for that user.
    The function uses the MongoClient to connect to the database, then finds one document in
    Config.MONGO_USER_MASTER_COLLECTION where _id is equal to ObjectId(user_id). It then returns response["passwordHash"].

    Args:
        self: Represent the instance of the class
        user_id: Find the user in the database

    Returns:
        The password hash of the user
    """
    m_db = MongoClient.connect()

    response = m_db[Config.MONGO_USER_MASTER_COLLECTION].find_one(
        {"_id": ObjectId(user_id)}
    )

    return response["passwordHash"]


def get_user_by_email(email):
    """
    The get_user_by_email function takes in an email address and returns the user object associated with that email.

    Args:
        self: Represent the instance of the class
        email: Find the user in the database

    Returns:
        A dictionary object
    """
    try:
        m_db = MongoClient.connect()

        response = m_db[Config.MONGO_USER_MASTER_COLLECTION].find_one({
                                                                      "email": email})

        return response

    except Exception as e:
        Common.exception_details("user_service.get_user_by_email", e)
        return None


def create_user(user_data):
    """
    The create_user function creates a new user in the database.

    Args:
        self: Represent the instance of the class
        user_data (dict): A dictionary containing all the information for a single user.

    Returns:
        The id of the user created
    """

    m_db = MongoClient.connect()

    response = m_db[Config.MONGO_USER_MASTER_COLLECTION].insert_one(user_data)

    if response:
        id = str(response.inserted_id)
        if Config.GCP_PROD_ENV:
            bucket = Production.get_users_bucket()

            # Name of the folder you want to create
            folder_name = id + "/"

            # Create an empty blob to represent the folder (blobs are like objects in GCS)
            folder_blob = bucket.blob(folder_name)
            # Upload an empty string to create an empty folder
            folder_blob.upload_from_string("")

            # print(f"Created folder {folder_name} in bucket {bucket_name}!")
        else:
            folder_path = os.path.join(Config.USER_FOLDER, id)
            os.makedirs(folder_path, exist_ok=True)
            print("Folder created for user : ", id)

        return id

    return None


def update_user_info(user_id, update_dict) -> int:
    """
    The function `update_user_info` updates user information in a MongoDB database and returns the count
    of modified documents.

    Args:
      user_id: The `user_id` parameter in the `update_user_info` function is the unique identifier of
    the user whose information you want to update in the database. It is used to locate the specific
    user document in the database based on its ObjectId.
      update_dict: The `update_dict` parameter is a dictionary containing the fields and values that you
    want to update for a specific user in the database. The keys in the dictionary represent the fields
    you want to update, and the corresponding values are the new values you want to set for those
    fields.

    Returns:
      The function `update_user_info` is returning the number of documents that were modified in the
    MongoDB collection as a result of the update operation.
    """
    try:
        m_db = MongoClient.connect()
        query = {"_id": ObjectId(user_id)}
        new_values = {"$set": update_dict}
        response = m_db[Config.MONGO_USER_MASTER_COLLECTION].update_one(
            query, new_values
        )

        return response.modified_count

    except Exception as e:
        Common.exception_details("user_service.update_user_info : ", e)
        return -1


def update_password(user_id, new_password_hash):
    """
    The update_password function updates the passwordHash field in the user_master collection.
        The function takes two parameters:
            1) user_id - a string representing an ObjectId of a document in the user_master collection.
            2) new_password - a string representing an encrypted version of the new password for this account.

    Args:
        self: Represent the instance of the class
        user_id: Identify the user in the database
        new_password_hash: Update the password hash in the database

    Returns:
        The number of documents modified
    """
    m_db = MongoClient.connect()

    query = {"_id": ObjectId(user_id), "isActive": True}
    new_values = {"$set": {"passwordHash": new_password_hash}}
    response = m_db[Config.MONGO_USER_MASTER_COLLECTION].update_one(
        query, new_values)

    if response:
        return str(response.modified_count)

    return None


def save_or_update_image(user_id, image):
    """
    The save_or_update_image function saves or updates a user's profile image.
        Args:
            user_id (str): The id of the user whose profile image is being saved or updated.
            image (file): The file object containing the new profile picture to be uploaded.

    Args:
        self: Represent the instance of the class
        user_id: Identify the user whose profile image is being uploaded
        image: Store the image uploaded by the user

    Returns:
        The modified count as a string

    """
    # Ensure that the user image upload folder exists
    os.makedirs(Config.USER_IMAGE_UPLOAD_FOLDER, exist_ok=True)

    if image and Common.allowed_file(image.filename):
        file_extension = Common.get_file_extension(image.filename)
        filename = str(user_id) + "__profile_image__" + "." + file_extension
        print("filename : ", filename)
        print(
            "COnfig.USER_IMAGE_UPLOAD_FOLDER : ",
            Config.USER_IMAGE_UPLOAD_FOLDER,
        )
        image_path = os.path.join(Config.USER_IMAGE_UPLOAD_FOLDER, filename)
        print("Image path: " + image_path)
        image.save(image_path)
        m_db = MongoClient.connect()

        query = {"_id": ObjectId(user_id), "isActive": True}
        value = {"$set": {"image": str(filename)}}
        response = m_db[Config.MONGO_USER_MASTER_COLLECTION].update_one(
            query, value)

        if response:
            return str(response.modified_count)

        return None


def update_report_subscription(user_id: Union[ObjectId, str], report_type: str) -> int:
    """
    The function `update_report_subscription` updates a user's report subscription in a MongoDB database
    based on the report type and returns the modified count.

    Args:
      user_id (Union[ObjectId, str]): The `user_id` parameter is the unique identifier of the user for
    whom you want to update the report subscription. It can be either an `ObjectId` or a string that
    represents the user's ID in the MongoDB database.
      report_type (str): The `report_type` parameter in the `update_report_subscription` function is a
    string that specifies the type of report for which the user's subscription is being updated. It can
    have values like "ResearchReport" or "DetailedReport" based on the report types defined in the
    Enumerator class.

    Returns:
      The function `update_report_subscription` is returning an integer value, which represents the
    modified count after updating the user document in the MongoDB database. If the update operation is
    successful, it returns the modified count. If any exceptions occur during the database operation, it
    returns 0.
    """
    try:
        # Connect to the MongoDB database
        m_db = MongoClient.connect()

        # Prepare the query to find the user document
        query = {"_id": ObjectId(user_id)}

        # Determine the value to add to the used total based on the report type
        if report_type == Enumerator.ReportType.ResearchReport.value or report_type == Enumerator.ReportType.DetailedReport.value:
            total = 0.5
        else:
            total = 1

        # Prepare the pipeline to update the user document
        pipeline = [
            {
                "$set": {
                    "permissions.report.used.total": {"$sum": ["$permissions.report.used.total", total]},
                    f"permissions.report.used.{report_type}": {"$sum": [f"$permissions.report.used.{report_type}", 1]},
                }
            }
        ]

        # Update the user document in the database
        response = m_db[Config.MONGO_USER_MASTER_COLLECTION].update_one(
            query,
            pipeline,
            upsert=True  # Add this option to enable upsert
        )

        return response.modified_count

    except Exception as e:
        Common.exception_details("user_service.update_report_subscription", e)
        # Handle any exceptions that may occur during the database operation
        return -1


def update_chat_subscription(user_id: Union[ObjectId, str]) -> int:
    """
    The function `update_chat_subscription` updates the chat count for a user in a MongoDB collection
    and returns the number of modified documents.

    Args:
      user_id (Union[ObjectId, str]): The `user_id` parameter in the `update_chat_subscription` function
    is used to identify the user whose chat subscription needs to be updated. It can be either an
    `ObjectId` or a `str` type, representing the unique identifier of the user in the database.

    Returns:
      The function `update_chat_subscription` is returning an integer value, which is the modified count
    from the update operation on the MongoDB collection. If the update operation is successful, it will
    return the number of documents that were modified. If there is an exception during the update
    operation, it will return 0.
    """
    try:

        m_db = MongoClient.connect()
        query = {"_id": ObjectId(user_id)}

        pipeline = [
            {
                "$set": {
                    "permissions.chat.used.chat_count": {"$sum": ["$permissions.chat.used.chat_count", 1]}
                }
            }
        ]

        response = m_db[Config.MONGO_USER_MASTER_COLLECTION].update_one(
            query,
            pipeline,
            upsert=True  # Add this option to enable upsert
        )

        return response.modified_count

    except Exception as e:
        Common.exception_details("user_service.update_report_subscription", e)
        return -1


def update_document_subscription(user_id: Union[ObjectId, str], document_size: int = 0) -> int:
    try:

        m_db = MongoClient.connect()
        query = {"_id": ObjectId(user_id)}

        pipeline = [
            {
                "$set": {
                    "permissions.document.used.document_size": {"$sum": ["$permissions.document.used.document_size", document_size]},
                }
            }
        ]

        response = m_db[Config.MONGO_USER_MASTER_COLLECTION].update_one(
            query,
            pipeline,
            upsert=True  # Add this option to enable upsert
        )

        return response.modified_count

    except Exception as e:
        Common.exception_details("user_service.update_report_subscription", e)
        return -1


def update_user_subscription(
    user_id: Union[ObjectId, str],
    report_count: int,
    chat_count: int,
    document_size: int,
    subscription_duration: int = 180
):
    """
    This Python function updates a user's subscription details in a MongoDB collection by incrementing
    report count, chat count, document size, and extending the subscription duration.

    Args:
      user_id (Union[ObjectId, str]): The `user_id` parameter is the unique identifier of the user whose
    subscription needs to be updated. It can be either an `ObjectId` or a string representing the user's
    ID.
      report_count (int): The `report_count` parameter in the `update_user_subscription` function
    represents the number of reports that will be added to the user's total allowed reports. This value
    will be used to update the user's permissions for reports in the database.
      chat_count (int): The `chat_count` parameter in the `update_user_subscription` function represents
    the number of chat messages allowed for the user's subscription. It is used to update the total chat
    count allowed for the user in the database.
      document_size (int): The `document_size` parameter in the `update_user_subscription` function
    represents the size of documents that the user is allowed to access or store as part of their
    subscription. This parameter is used to update the user's permissions related to document access or
    storage based on the provided `document_size` value.
      subscription_duration (int): The `subscription_duration` parameter in the
    `update_user_subscription` function represents the duration in days for which the user's
    subscription will be extended. By default, it is set to 180 days if no value is provided when
    calling the function. Defaults to 180 (6 months)

    Returns:
      The function `update_user_subscription` returns the number of documents that were modified by the
    update operation. This count is returned as the result of the `response.modified_count` attribute.
    If the update operation is successful, this count represents the number of documents that were
    updated with the new subscription information. If an error occurs during the update process, the
    function returns -1.
    """
    try:
        m_db = MongoClient.connect()
        query = {"_id": ObjectId(user_id)}

        pipeline = [
            {
                "$set": {
                    "permissions.report.allowed.total": {"$sum": ["$permissions.report.allowed.total", report_count]},
                    "permissions.chat.allowed.chat_count": {"$sum": ["$permissions.chat.allowed.chat_count", chat_count]},
                    "permissions.document.allowed.document_size": {"$sum": ["$permissions.document.allowed.document_size", document_size]},
                    "permissions.subscription_duration.end_date": {
                        "$add": [
                            "$permissions.subscription_duration.end_date",
                            # Convert days to milliseconds
                            {"$multiply": [
                                subscription_duration, 24 * 60 * 60 * 1000]}
                        ]
                    }
                }
            }
        ]

        response = m_db[Config.MONGO_USER_MASTER_COLLECTION].update_one(
            query,
            pipeline,
            upsert=True  # Add this option to enable upsert
        )

        return response.modified_count

    except Exception as e:
        Common.exception_details("user_service.update_report_subscription", e)
        return -1


def _common_user_pipeline() -> list:
    """
    The _common_user_pipeline function is used to create a pipeline for the user collection.
    It will be used in many different places, so it's best to have it as a function.
    The pipeline removes the passwordHash field from all documents and adds an _id field that is converted into a string.

    Args:

    Returns:
        A list of stages
    """
    user_image_route = request.host_url + "account/image/"

    pipeline = [
        PipelineStages.stage_add_fields(
            {
                "_id": {"$toString": "$_id"},
                "createdOn": {"$toString": "$createdOn"},
                "image": {
                    "$cond": {
                        "if": {"$ne": ["$image", ""]},
                        "then": {"$concat": [user_image_route, "$image"]},
                        "else": "$image",
                    }
                },
                "permissions.subscription_duration": {
                    "$cond": {
                        "if": {
                            "$and": [
                                {"$ifNull": ["$permissions", False]},
                                {"$ifNull": [
                                    "$permissions.subscription_duration", False]}
                            ]
                        },
                        "then": {
                            "start_date": {
                                "$toString": "$permissions.subscription_duration.start_date"
                            },
                            "end_date": {
                                "$toString": "$permissions.subscription_duration.end_date"
                            }
                        },
                        "else": "$permissions.subscription_duration"
                    }
                }
            }
        ),
        PipelineStages.stage_unset(["passwordHash"]),
    ]

    return pipeline
