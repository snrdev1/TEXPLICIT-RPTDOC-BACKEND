import datetime
from functools import wraps

from flask import Response, request

from app.services.userService import UserService
from app.utils.common import Common
from app.utils.messages import Messages
from app.utils.parser import Parser
from app.utils.response import Response


def authorized(f):
    """
    The authorized function will check for the presence of a valid JWT in the request header.
    If it is present, it will decode and verify that token. If not, an unauthorized response
    will be returned.

    Args:
        f: Pass the function to be decorated

    Returns:
        A function that is then called by the route
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        """
        The decorated function will check for the presence of a valid JWT in the request header.
        If it is present, it will decode and verify that token. If not, an unauthorized response
        will be returned.

        Args:
            *args: Send a non-keyworded variable length argument list to the function
            **kwargs: Pass a keyworded, variable-length argument list

        Returns:
            A function

        """
        auth_type = None

        auth_token = request.headers.get("Authorization")
        if auth_token:
            auth_type = auth_token.split(" ")[0]

        # Check if token is present in request header
        if auth_token and auth_type == "Bearer":
            token = request.headers.get("Authorization").split(" ")[1]
        else:
            return Response.unauthorized()

        # Check for validity of token
        try:
            decoded_token = Parser.get_decoded_token(token)

            if decoded_token is None:
                return Response.custom_response(
                    [], Messages.ERROR_TOKEN_EXPIRED, False, 401
                )

            current_time = datetime.datetime.utcnow()
            expiry_time = datetime.datetime.utcfromtimestamp(decoded_token["exp"])

            if current_time > expiry_time:
                return Response.custom_response(
                    [], Messages.ERROR_TOKEN_EXPIRED, True, 401
                )

            logged_in_user = UserService().get_user_by_id(decoded_token["id"])

            if not logged_in_user:
                return Response.unauthorized()

        except Exception as e:
            Common.exception_details("authorized", e)
            return Response.custom_response([], f"{e}", False, 401)

        return f(logged_in_user, *args, **kwargs)

    return decorated


def anonymous(f):
    """
    The anonymous function will check for the presence of a valid JWT in the request header.
    If present, it will decode and verify it, then pass along the decoded payload to your function.
    If not present or invalid, None is passed instead.

    Args:
        f: Pass the function to be decorated

    Returns:
        A function that returns a function
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        """
        The decorated function will check for the presence of a valid JWT in the request header.
        If present, it will decode and verify it, then pass along the decoded payload to your function.
        If not present or invalid, None is passed instead.

        Args:
            *args: Send a non-keyworded variable length argument list to the function
            **kwargs: Pass a keyworded, variable-length argument list

        Returns:
            The result of the decorated function

        """
        auth_type = None

        auth_token = request.headers.get("Authorization")
        if auth_token:
            auth_type = auth_token.split(" ")[0]

        # Check if token is present in request header
        if auth_token and auth_type == "Bearer":
            token = request.headers.get("Authorization").split(" ")[1]
        else:
            return f(None, *args, **kwargs)

        logged_in_user = None
        # Check for validity of token
        try:
            decoded_token = Parser.get_decoded_token(token)

            if decoded_token is None:
                return f(None, *args, **kwargs)

            current_time = datetime.datetime.utcnow()
            expiry_time = datetime.datetime.utcfromtimestamp(decoded_token["exp"])

            if current_time > expiry_time:
                return f(None, *args, **kwargs)

            logged_in_user = UserService().get_user_by_id(decoded_token["id"])

        except Exception as e:
            Common.exception_details("anonymous", e)
            return Response.custom_response([], f"{e}", False, 500)

        finally:
            return f(logged_in_user, *args, **kwargs)

    return decorated


def admin(f):
    """
    The `admin` function is a decorator that checks if a user is an admin and if they are active before
    allowing them to access a protected route.
    
    Args:
      f: The parameter `f` is a function that will be decorated by the `admin` decorator.
    
    Returns:
      The function `admin` returns the decorated function `decorated`.
    """
    @wraps(f)
    def decorated(logged_in_user, *args, **kwargs):
        """
        The function `decorated` checks if the logged-in user is an admin and active, and then calls the
        function `f` with the logged-in user and any additional arguments and keyword arguments.
        
        Args:
          logged_in_user: The `logged_in_user` parameter is the user who is currently logged in and
        making the request.
        
        Returns:
          the result of calling the function `f` with the arguments `logged_in_user`, `*args`, and
        `**kwargs`.
        """
        try:
            # Check if user is admin
            if not UserService.check_user_admin(logged_in_user):
                return Response.custom_response(
                    [], Messages.UNAUTHORIZED_ADMIN, True, 401
                )

            # Check if user is active
            if not UserService.active_user(logged_in_user):
                return Response.custom_response(
                    [], Messages.ERROR_INACTIVE_USER, True, 401
                )

        except Exception as e:
            Common.exception_details("admin", e)
            return Response.custom_response([], f"{e}", False, 401)

        return f(logged_in_user, *args, **kwargs)

    return decorated
