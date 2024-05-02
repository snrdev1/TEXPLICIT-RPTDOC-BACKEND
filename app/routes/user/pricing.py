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

        # Get country_name from ip
        ip_data = PricingService.get_ip_data()
        country_name = ip_data.get("country_name", "INDIA")
        
        # Get all prices
        prices = PricingService.get_prices()

        country_prices = PricingService.get_country_prices(country_name, prices)

        return Response.custom_response(country_prices, "Found pricing amounts", True, 200)

    except Exception as e:
        Common.exception_details("pricing.py: get_prices", e)
        return Response.server_error()
