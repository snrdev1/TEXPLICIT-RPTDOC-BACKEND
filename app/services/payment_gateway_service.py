from datetime import datetime, timezone
from typing import Union

from bson import ObjectId

from app.config import Config
from app.models.mongoClient import MongoClient
from app.utils.common import Common
from app.utils.formatter import cursor_to_dict


def verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
    signature_verification = Config.razorpay_client.utility.verify_payment_signature(
        {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        }
    )

    return signature_verification


def add_payment_history(user_id: Union[ObjectId, str], payment_details: dict):
    try:
        m_db = MongoClient.connect()
        response = m_db[Config.MONGO_PAYMENT_HISTORY_COLLECTION].insert_one({
            "createdBy": {"_id": ObjectId(user_id), "ref": "user"},
            "createdOn": datetime.now(timezone.utc),
            "payment_details": payment_details
        })

        return response.inserted_id

    except Exception as e:
        Common.exception_details(
            "payment_gateway_service.add_payment_history", e)


def get_payment_history(user_id: Union[ObjectId, str]):
    try:
        m_db = MongoClient.connect()

        pipeline = [
            {
                "$match": {
                    "createdBy": {"_id": ObjectId(user_id), "ref": "user"}
                }
            },
            {
                "$sort": {
                    "createdOn": -1
                }
            },
            {
                "$addFields": {
                    "createdOn": {"$dateToString": {"date": "$createdOn"}},
                }
            },
            {
                "$unset": ["createdBy", "_id"]
            }
        ]

        response = m_db[Config.MONGO_PAYMENT_HISTORY_COLLECTION].aggregate(
            pipeline
        )

        return cursor_to_dict(response)

    except Exception as e:
        Common.exception_details(
            "payment_gateway_service.add_payment_history", e)
        return None
