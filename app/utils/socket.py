from typing import Union

from bson import ObjectId

from app import socketio
from app.utils import Response

# On connection


@socketio.on("connect")
def connect():
    """
    The connect function is used to connect the socket to a remote address.
    The function takes no arguments and returns nothing.

    Args:

    Returns:
        Nothing.
    """
    try:
        print("Socket Connected!")
    except Exception as e:
        print("Error: ", e)


# On disconnection


@socketio.on("disconnect")
def disconnect():
    """
    The disconnect function is used to disconnect the socket from the server.

    Args:

    Returns:
        Nothing.
    """
    try:
        print("Socket Disconnected!")
    except Exception as e:
        print("Error: ", e)


# Common socket events


# Error
def socket_error(userid: Union[str, ObjectId], msg: str) -> None:
    print(f"🔌 socket_error: {msg}")
    socketio.emit(f"{userid}_error", msg)


# Success
def socket_success(userid: Union[str, ObjectId], msg: str) -> None:
    print(f"🔌 socket_success: {msg}")
    socketio.emit(f"{userid}_success", msg)


# Info
def socket_info(userid: Union[str, ObjectId], msg: str) -> None:
    print(f"🔌 socket_info: {msg}")
    socketio.emit(f"{userid}_info", msg)


def emit_report_status(
    user_id: Union[str, ObjectId], report_generation_id: str, message: str
) -> None:
    print(f"🔌 Emitting Report Generation Status : {message}\n")

    Response.socket_response(
        event=f"{user_id}_report_{report_generation_id}_status",
        data=[],
        message=message,
    )


def emit_document_upload_status(
    user_id: Union[str, ObjectId], upload_id: str, message: str, progress: int = 0
) -> None:
    print(f"🔌 Emitting Document Upload Status : {message}\n")
    
    print(f"Event name : {user_id}_{upload_id}_document_upload_status")

    Response.socket_response(
        event=f"{user_id}_{upload_id}_document_upload_status",
        data=[{"progress": progress}],
        message=message,
    )
    
    
def emit_subscription_invalid_status(
    user_id: Union[str, ObjectId], message: str
) -> None:
    print(f"🔌 Emitting Subscription Invalid Status")
    event_name = f"{user_id}_subscription_status"
    print(f"Event name : {event_name}")
    
    Response.socket_response(
        event=event_name,
        data=[],
        message=message,
    )
