import requests
from flask import Blueprint
from app.auth.userauthorization import authorized
from app.config import Config
from app.utils.common import Common
from app.utils.messages import Messages
from app.utils import Response
from app.services import pricing_service as PricingService

pricing = Blueprint("pricing", __name__, url_prefix="/pricing")

@pricing.route("/get_prices", methods=["GET"])
def get_prices():
    try:       
        if not Config.IPSTACK_API_KEY:
            return Response.missing_api_key()
        
        ip_data = PricingService.get_ip_data()
        
        print("IP DATA : ", ip_data)
        
        prices = PricingService.get_prices()
        
        return Response.custom_response(prices, "Found pricing amounts", True, 200)

    except Exception as e:
        Common.exception_details("pricing.py: get_prices", e)
        return Response.server_error()