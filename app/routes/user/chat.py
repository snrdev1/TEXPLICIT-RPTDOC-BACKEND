"""
    All Chat related routes
"""

import threading

from flask import Blueprint, request

from app.auth.userauthorization import authorized
from app.services.chatService import ChatService
from app.utils.common import Common
from app.utils.enumerator import Enumerator
from app.utils.messages import Messages
from app.utils.response import Response

chat = Blueprint("chat", __name__, url_prefix="/chat")

@chat.route("", methods=["POST"])
@authorized
def get_chat(logged_in_user):
    """
        The get_chat function is used to get the chat response from the user.
        The function takes in a logged_in_user as an argument and returns a custom response object.


    Args:
        logged_in_user: Get the user id of the logged in user

    Request Args:
            prompt: The user prompt to the system
            chatType: The type of chat the user wants:
                       0: External
                       1: Documents

    """
    user_id = logged_in_user["_id"]

    request_body = request.get_json()
    prompt = Common.get_field_value_or_default(
        request_body.get("params"), "prompt", None
    )
    chat_type = Common.get_field_value_or_default(
        request_body.get("params"), "chatType", int(Enumerator.ChatType.External.value)
    )

    # Getting chat response and emitting it in a separate non-blocking thread
    chatService = ChatService(user_id)
    t1 = threading.Thread(
        target=chatService.get_chat_response,
        args=(chat_type, prompt),
    )
    t1.start()

    return Response.custom_response([], Messages.OK_CHAT_PROCESSING, True, 200)


@chat.route("", methods=["GET"])
@authorized
def get_chat_history(logged_in_user):
    """
    The function `get_chat_history` retrieves the chat history for a logged-in user, with options to
    specify the limit and offset of the results.

    Args:
      logged_in_user: The logged_in_user parameter is an object that represents the user who is
    currently logged in. It contains information about the user, such as their ID and image.

    Returns:
      a custom response with the chat history, along with a success message and a status code of 200.
    """
    try:
        user_id = logged_in_user["_id"]
        request_params = request.args.to_dict()
        limit = int(request_params.get("limit", 10))
        offset = int(request_params.get("offset", 0))

        response = ChatService(user_id).get_all_user_related_chat(limit, offset)

        return Response.custom_response(
            [response, logged_in_user["image"]],
            Messages.OK_CHAT_HISTORY_FOUND,
            True,
            200,
        )

    except Exception as e:
        Common.exception_details("chat.py : get_chat_history", e)
        return Response.server_error()


@chat.route("", methods=["DELETE"])
@authorized
def delete_chats(logged_in_user):
    try:
        user_id = logged_in_user["_id"]
        response = ChatService(user_id).delete_chats()

        if response:
            return Response.custom_response(
                response, Messages.OK_CHAT_DELETE, True, 200
            )
        else:
            return Response.custom_response(
                response, Messages.ERROR_CHAT_DELETE, False, 400
            )

    except Exception as e:
        Common.exception_details("chat.py : delete_chats", e)
        return Response.server_error()
