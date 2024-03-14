from flask import Blueprint

from app.auth.userauthorization import authorized
from app.services import UserService
from app.utils.common import Common
from app.utils.messages import Messages
from app.utils import Response

users = Blueprint("users", __name__, url_prefix="/users")


# List of users
@users.route("/all", methods=["GET"])
@authorized
def users_get_all(logged_in_user):
    try:
        response = UserService.get_all_users()

        return Response.custom_response(
            response, Messages.OK_USERS_RETRIEVAL, True, 200
        )
    except Exception as e:
        Common.exception_details("users.py: users_get_all", e)
        return Response.server_error()
