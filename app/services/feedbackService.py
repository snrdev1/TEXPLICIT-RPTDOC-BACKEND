import datetime
from datetime import datetime

from app.config import Config
from app.models.mongoClient import MongoClient
from app.utils.formatter import get_formatted_response


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

        if insert_response.acknowledged:
            return get_formatted_response(insert_response.inserted_id)
        else:
            return None
