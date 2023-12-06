"""
    All Menu related routes
"""


from flask import Blueprint, request

from app.services.menuService import MenuService
from app.utils.common import Common
from app.utils.messages import Messages
from app.utils.response import Response

menu = Blueprint("menu", __name__, url_prefix="/menu")


@menu.route("", methods=["POST"])
def get_menu():
    try:
        # Extract data from request body
        request_params = request.get_json()

        menu_ids = request_params.get("menu_ids", [])
        menu = MenuService().get_menu_items(menu_ids)

        return Response.custom_response(menu, Messages.OK_MENU_RETRIEVAL, True, 200)

    except Exception as e:
        Common.exception_details("menu get_menu : ", e)
        return Response.server_error()
