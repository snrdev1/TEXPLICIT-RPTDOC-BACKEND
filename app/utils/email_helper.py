import sib_api_v3_sdk

from app.config import Config
from app.utils.common import Common


def send_mail(subject, htmlMailBody, recipients=[], sender=None, attachments=[]):
    """
    The function `send_mail` sends transactional emails with optional attachments using the Sendinblue
    API.
    
    Args:
      subject: The `subject` parameter in the `send_mail` function is used to specify the subject line
    of the email that will be sent. It typically contains a brief summary or description of the email
    content.
      htmlMailBody: The `htmlMailBody` parameter in the `send_mail` function is used to specify the HTML
    content of the email that will be sent. This content will be displayed in the email body when the
    recipient receives the email. It should be a string containing the HTML markup for the email
    content, including
      recipients: The `recipients` parameter in the `send_mail` function is a list of dictionaries
    containing information about the recipients of the email. Each dictionary in the list represents a
    recipient and typically includes the recipient's name and email address.
      sender: The `sender` parameter in the `send_mail` function is used to specify the sender of the
    email. It can be provided as a dictionary with keys "name" and "email" to define the name and email
    address of the sender. If the `sender` parameter is not provided (i
      attachments: Attachments parameter in the `send_mail` function is used to include any files or
    documents that need to be sent along with the email. These attachments could be files like images,
    PDFs, documents, etc. The function allows for attaching multiple files by providing a list of
    attachment paths or objects.
    
    Returns:
      The function `send_mail` returns a boolean value - `True` if the email was sent successfully, and
    `False` if there was an error or the email sending failed.
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
        
        if attachments:
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
                attachment=attachments
            )
        else:
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
        Common.exception_details("send_mail", e)
        return False
