from app.config import Config
from datetime import datetime
from typing import Union
from app.models.mongoClient import MongoClient
from bson import ObjectId
from app.utils.common import Common

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
            "createdOn": datetime.utcnow(),
            "payment_details": payment_details
        })
            
    except Exception as e:
        Common.exception_details("payment_gateway_service.add_payment_history", e)
    