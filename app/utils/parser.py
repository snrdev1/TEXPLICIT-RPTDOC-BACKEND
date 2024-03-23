import datetime
from typing import Union

import jwt

from app.config import Config
from app.utils.common import Common


class Parser:

    @staticmethod
    def get_encoded_token(user_id, days=1):
        """Generates JWT token

        Args:
            user_id (string): User Id

        Raises:
            Exception: Any

        Returns:
            _type_: Jwt Token
        """
        try:
            # Generate a JWT token
            jwt_payload = {
                "id": str(user_id),
                # CHANGE NUMBER OF DAYS LATER
                "exp": datetime.datetime.utcnow() + datetime.timedelta(days),
            }
            jwt_secret_key = Config.JWT_SECRET_KEY
            jwt_algorithm = "HS256"  # Use the desired JWT algorithm
            jwt_token = jwt.encode(
                jwt_payload, jwt_secret_key, algorithm=jwt_algorithm)

            return jwt_token
        except Exception as e:
            raise Exception(e)

    @staticmethod
    def get_decoded_token(jwt_token):
        """
        The function `get_decoded_token` decodes a JWT token using a secret key and returns the decoded
        output, or None if an exception occurs.

        Args:
          jwt_token: The `jwt_token` parameter is the JSON Web Token (JWT) that needs to be decoded.

        Returns:
          the decoded token if it is successfully decoded using the provided secret key and algorithm.
        If there is an exception during the decoding process, the function returns None.
        """
        try:
            jwt_secret_key = Config.JWT_SECRET_KEY
            jwt_algorithm = "HS256"
            output = jwt.decode(
                jwt_token, key=jwt_secret_key, algorithms=[jwt_algorithm]
            )

            return output
        except Exception as e:
            Common.exception_details("Parser.get_decoded_token", e)
            return None

    @staticmethod
    def convert_to_datetime(date, current_date=datetime.datetime.utcnow()):
        """
        The function `convert_to_datetime` converts a date string or dictionary to a datetime object,
        using the current date if no date is provided.
        
        Args:
          date: The `date` parameter in the `convert_to_datetime` function can be either a string, a
        dictionary, or a datetime object.
          current_date: The `current_date` parameter in the `convert_to_datetime` function is a datetime
        object representing the current date and time. If no value is provided for `current_date` when
        calling the function, it defaults to the current UTC date and time obtained using
        `datetime.datetime.utcnow()`.
        
        Returns:
          The function `convert_to_datetime` returns a datetime object. The function first checks if the
        input `date` is a string or a dictionary. If it is a string, it converts it to a datetime object
        using the `fromisoformat` method. If it is a dictionary, it extracts the date string and
        converts it to a datetime object using `strptime`. If the input `date`
        """
        if isinstance(date, str):
            return datetime.datetime.fromisoformat(date.replace('Z', '+00:00'))
        elif isinstance(date, dict):
            return datetime.datetime.strptime(date["$date"], '%Y-%m-%dT%H:%M:%SZ')
        else:
            return date if date else current_date
