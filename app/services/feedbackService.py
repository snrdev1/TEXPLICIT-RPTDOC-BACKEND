import datetime
from datetime import datetime

from app.config import Config
from app.models.mongoClient import MongoClient
from app.utils.common import Common
import app.utils.constants as Constants


class FeedbackService:
    FEEDBACK_COLLECTION = Config.MONGO_CUSTOMER_FEEDBACK_COLLECTION

    def save_user_feedback(self, feedback_object):
        """
        The function saves user feedback by inserting it into a MongoDB collection and returns the
        inserted ID if successful.

        Args:
          feedback_object: The `feedback_object` parameter is a dictionary object that contains the
        feedback information to be saved. It should have the following keys:

        Returns:
          either the response from the insert operation (if it was acknowledged) or None.
        """
        feedback_object["created"] = datetime.utcnow()

        m_db = MongoClient.connect()

        insert_response = m_db[self.FEEDBACK_COLLECTION].insert_one(feedback_object)

        # mailBody = Constants..format(
        #     receiver=creator["name"],
        #     ki_title=ki["title"],
        #     reason=reason_text,
        #     sender=Config.MAIL_SENDER_NAME,
        # )

        # receivers = []
        # receivers.append({"name": creator["name"], "email": creator["email"]})

        # success = EmailHelper.send_mail(
        #     Constants.KI_REJECTED_MAILSUBJECT, mailBody, receivers, None
        # )

        if insert_response.acknowledged:
            return Common.process_response(insert_response.inserted_id)
        else:
            return None
