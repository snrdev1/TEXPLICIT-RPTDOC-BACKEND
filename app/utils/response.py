"""
    Common responses used throughout the application, with provisions for 
    creating custom response within a specified structure
"""

from flask import jsonify

from app import socketio
from app.utils.messages import Messages


def custom_response(data="", message="", success=True, status=200):
    """Generates a custom response
    Args:
        data (str, optional): Data to pass in the response. Defaults to "".
        message (str, optional): Response message. Defaults to "".
        success (bool, optional): Response indicating success of api call. Defaults to True.
        status (int, optional): Http status code. Defaults to 200.
    Returns:
        json: Custom response
    """
    return jsonify({"data": data, "message": message, "success": success}), status


def socket_response(
    event: str,
    data: any = [],
    message: str = "",
    success: bool = True,
    status: int = 200,
) -> None:
    """
    The function `socket_response` emits a socket event with a message, data, success status, and
    status code.
    Args:
      event (str): The event parameter is a string that represents the name of the event that you
    want to emit to the socket clients.
      data (any): The `data` parameter is used to pass any data that you want to send along with the
    socket response. It can be of any type, such as a string, integer, list, dictionary, etc.
      message (str): The "message" parameter is a string that represents a message or description
    related to the response. It can be used to provide additional information or context about the
    response.
      success (bool): The "success" parameter is a boolean value that indicates whether the
    operation was successful or not. It is set to True by default. Defaults to True
      status (int): The `status` parameter is an integer that represents the HTTP status code of the
    response. It is set to 200 by default, which indicates a successful response. However, you can
    change it to any other valid HTTP status code based on your requirements. Defaults to 200
    """
    socketio.emit(
        event,
        {"message": message, "data": data, "success": success, "status": status},
    )


def unauthorized():
    """Generates an unauthorized response
    Returns:
        json: Unauthorized response(401)
    """
    return (
        jsonify({"data": [], "message": Messages.UNAUTHORIZED, "success": False}),
        401,
    )


def missing_parameters():
    """Generates a response for missing parameters
    Returns:
        json: Response for missing parameters(400)
    """
    return (
        jsonify(
            {
                "data": [],
                "message": Messages.MISSING_REQUIRED_PARAMETERS,
                "success": False,
            }
        ),
        400,
    )


def missing_required_parameter(param=""):
    """Generates a response for a missing parameter
    Returns:
        json: Response for a missing parameter(400)
    """
    return (
        jsonify(
            {
                "data": [],
                "message": Messages.MISSING_REQUIRED_PARAMETER + str(param),
                "success": False,
            }
        ),
        400,
    )


def server_error():
    """Generates a response for server error
    Returns:
        json: Response for internal server error(500)
    """
    return (
        jsonify(
            {
                "data": [],
                "message": Messages.ERROR_INTERNAL_SERVER,
                "success": False,
            }
        ),
        500,
    )


def subscription_invalid(message: str = ""):
    """
    The function `subscription_invalid` returns a JSON response with a message indicating an invalid
    subscription.
    
    Args:
      message (str): The `message` parameter in the `subscription_invalid` function is a string
    parameter that represents a custom message to be included in the response. If no message is
    provided, it will default to a predefined message constant `Messages.INVALID_SUBSCRIPTION`.
    
    Returns:
      A tuple is being returned containing a JSON response with data, message, and success fields, along
    with an HTTP status code of 400.
    """
    return (
        jsonify(
            {
                "data": [],
                "message": message or Messages.INVALID_SUBSCRIPTION,
                "success": False,
            }
        ),
        400,
    )

def missing_api_key(api: str):
    """Generates a response for missing api key
    Returns:
        json: Response for missing api key(403)
    """
    return (
        jsonify(
            {
                "data": [],
                "message": Messages.MISSING_API_KEY + api,
                "success": False,
            }
        ),
        403,
    )