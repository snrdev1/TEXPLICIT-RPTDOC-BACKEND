import json
import os

import requests
import sib_api_v3_sdk

from app.config import Config
from app.utils.common import Common


class EmailHelper:
    def send_mail(subject, htmlMailBody, recipients=[], sender=None):
        """
        The `send_mail` function sends an email using the Sendinblue API, with the specified subject,
        HTML mail body, recipients, and sender information.

        Args:
          subject: The subject of the email that you want to send.
          htmlMailBody: The `htmlMailBody` parameter is a string that represents the HTML content of the
        email you want to send. It should contain the actual content of the email, including any
        formatting, images, links, etc.
          recipients: The recipients parameter is a list of dictionaries, where each dictionary
        represents a recipient of the email. Each dictionary should have the following keys:
          sender: The `sender` parameter is an optional dictionary that contains the name and email
        address of the sender of the email. If the `sender` parameter is not provided, the function will
        use the sender name and email address specified in the environment variables `MAIL_SENDER_NAME`
        and `MAIL_SENDER_EMAIL

        Returns:
          a boolean value. If the email is sent successfully, it returns True. If there is an error or
        the email fails to send, it returns False.
        """
        try:
            # Configure API key authorization
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key["api-key"] = Config.MAIL_API_KEY

            # Create an instance of the API class
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
                sib_api_v3_sdk.ApiClient(configuration)
            )

            mailSender = {}
            mailSender["name"] = (
                Config.MAIL_SENDER_NAME if sender is None else sender["name"]
            )
            mailSender["email"] = (
                Config.MAIL_SENDER_EMAIL if sender is None else sender["email"]
            )

            # Create a send email object
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                sender=sib_api_v3_sdk.SendSmtpEmailSender(
                    email=mailSender["email"], name=mailSender["name"]
                ),
                to=[
                    sib_api_v3_sdk.SendSmtpEmailTo(
                        name=recipient["name"], email=recipient["email"]
                    )
                    for recipient in recipients
                ],
                subject=subject,
                html_content=htmlMailBody,
            )

            # Send the email
            api_response = api_instance.send_transac_email(send_smtp_email)

            if api_response:
                return True
            else:
                return False

        except Exception as e:
            print(
                "=================== EmailHelper.send_mail() =========================="
            )
            Common.exception_details("EmailHelper.send_mail", e)
            return False
