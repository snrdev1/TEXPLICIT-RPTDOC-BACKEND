import sib_api_v3_sdk

from app.config import Config
from app.utils.common import Common


def send_mail(subject, htmlMailBody, recipients=[], sender=None, attachments=[]):
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
            attachment=attachments,
        )

        # Send the email
        api_response = api_instance.send_transac_email(send_smtp_email)

        if api_response:
            return True
        else:
            return False

    except Exception as e:
        Common.exception_details("send_mail", e)
        return False
