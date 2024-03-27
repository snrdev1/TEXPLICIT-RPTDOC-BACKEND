import datetime

import jwt
from dateutil import parser

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
    def convert_to_datetime(date=datetime.datetime.now(datetime.timezone.utc)):
        """
        The function `convert_to_datetime` converts a date string or dictionary to a datetime object
        using the `isoparse` method from the `dateutil.parser` module.
        
        Args:
          date: The `date` parameter in the `convert_to_datetime` function is a datetime object with the
        current date and time in UTC timezone by default. If a dictionary is passed instead of a
        datetime object, it extracts the value associated with the key "" from the dictionary and
        converts it to a datetime
        
        Returns:
          The function `convert_to_datetime` returns a datetime object parsed from the input date
        content. If the input date is in dictionary format, it extracts the date value from the key
        "" before parsing it.
        """
        date_content = date
        if isinstance(date, dict):
            date_content = date["$date"]
        
        return parser.isoparse(date_content)
