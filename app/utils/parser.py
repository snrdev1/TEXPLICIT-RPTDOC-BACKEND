import datetime

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
            jwt_token = jwt.encode(jwt_payload, jwt_secret_key, algorithm=jwt_algorithm)

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
