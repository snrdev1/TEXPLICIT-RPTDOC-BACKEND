from datetime import datetime

from app.config import Config
from app.models.mongoClient import MongoClient
from app.utils import constants as Constants
from app.utils.common import Common
from app.utils.email_helper import EmailHelper
from app.utils.formatter import get_formatted_response

# Demo request


def save_demo_request(demo_data: dict):
    """
    The function `save_demo_request` saves a demo request in a MongoDB collection and returns a
    formatted response.

    :param demo_data: The `demo_data` parameter is a dictionary that contains the data for the demo
    request. It should have the necessary fields and values required for the demo request
    :type demo_data: dict
    :return: either a formatted response containing the inserted ID if the insertion was acknowledged,
    or None if there was an exception or if the insertion was not acknowledged.
    """
    try:
        demo_data["created"] = datetime.utcnow()

        m_db = MongoClient.connect()

        insert_response = m_db[Config.MONGO_DEMO_REQUEST_COLLECTION].insert_one(demo_data)

        if insert_response.acknowledged:
            # If insert into db is acknowledged then also send an email to the one in charge
            # send_email_to_admin(demo_data)

            # And also to the user
            send_email_to_user(demo_data)

            return get_formatted_response(insert_response.inserted_id)
        else:
            return None

    except Exception as e:
        Common.exception_details("demoService.save_demo_request", e)
        return None


def send_email_to_admin(demo_data: dict):
    try:
        mailBody = Constants.DEMO_REQUEST_MAILBODY.format(
            name=demo_data.get("name"),
            email=demo_data.get("email"),
            phone=demo_data.get("phone", ""),
            comments=demo_data.get("comments", ""),
        )

        receivers = []
        receivers.append(
            {"name": Config.MAIL_SENDER_NAME, "email": Config.MAIL_SENDER_EMAIL}
        )

        success = EmailHelper.send_mail(
            Constants.DEMO_REQUEST_MAILSUBJECT, mailBody, receivers, None
        )

    except Exception as e:
        Common.exception_details("demoService.send_email_to_admin", e)


def send_email_to_user(demo_data: dict):
    try:
        mailBody = Constants.DEMO_REQUEST_CONFIRMATION_MAILBODY.format(
            name=demo_data.get("name")
        )

        receivers = []
        receivers.append({"name": demo_data["name"], "email": demo_data["email"]})

        success = EmailHelper.send_mail(
            Constants.DEMO_REQUEST_CONFIRMATION_MAILSUBJECT, mailBody, receivers, None
        )

    except Exception as e:
        Common.exception_details("demoService.send_email_to_user", e)
