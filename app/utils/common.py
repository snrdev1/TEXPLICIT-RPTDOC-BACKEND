"""
    Common functions accessible throughout the application
"""
import re
import traceback
from typing import Any
from urllib.parse import urlsplit
from werkzeug.security import generate_password_hash, check_password_hash

from app.config import Config


class Common:
    
    @staticmethod
    def encrypt_password(password):
        """Generates password hash from string password

        Args:
            password (string): User password

        Raises:
            Exception: Any

        Returns:
            _type_: Password hash from user password
        """
        try:
            return generate_password_hash(password)
        except Exception as e:
            raise Exception(e)

    @staticmethod
    def check_password(password_hash, password=""):
        """Checks stored password hash in db against input string password

        Args:
            password_hash (_type_): Stored password hash
            password (string, optional): Input password

        Returns:
            boolean: Returns true if input password matches stored password hash else false
        """
        try:
            return check_password_hash(password_hash, password)
        except ValueError:
            # Handle the specific exception that may be raised by check_password_hash function
            return False

    @staticmethod
    def get_field_value_or_default(dictionary: dict, field_name: str, default_value: Any) -> Any:
        """Returns the value of a field from a dict or the default value specified

        Args:
            dictionary(dict): the dictionary from which fields will be fetched
            field_name(str): name of the field
            default_value(Any): The default value to be returned if the field is not found

        Returns:
            The value of the field in the dict if found, or the default_value
        """

        if field_name in dictionary.keys():
            return dictionary[field_name]
        else:
            return default_value

    @staticmethod
    def validate_url(url):
        """
        Checks if URL looks valid.
        Returns validated URL, else returns None
        Modified from Django: https://docs.djangoproject.com/en/4.1/_modules/django/core/validators/#URLValidator
        """

        # Unicode letters range (must not be a raw string)
        ul = "\u00a1-\uffff"
        # IP patterns
        ipv4_re = (
            r"(?:0|25[0-5]|2[0-4][0-9]|1[0-9]?[0-9]?|[1-9][0-9]?)"
            r"(?:\.(?:0|25[0-5]|2[0-4][0-9]|1[0-9]?[0-9]?|[1-9][0-9]?)){3}"
        )
        ipv6_re = r"\[[0-9a-f:.]+\]"  # (simple regex, validated later)
        # Host patterns
        hostname_re = (
                r"[a-z" + ul + r"0-9](?:[a-z" + ul +
                r"0-9-]{0,61}[a-z" + ul + r"0-9])?"
        )
        # Max length for domain name labels is 63 characters per RFC 1034 sec. 3.1
        domain_re = r"(?:\.(?!-)[a-z" + ul + r"0-9-]{1,63}(?<!-))*"
        tld_re = (
                r"\."  # dot
                r"(?!-)"  # can't start with a dash
                r"(?:[a-z" + ul + "-]{2,63}"  # domain label
                                  r"|xn--[a-z0-9]{1,59})"  # or punycode label
                                  r"(?<!-)"  # can't end with a dash
                                  r"\.?"  # may have a trailing dot
        )
        host_re = "(" + hostname_re + domain_re + tld_re + ")"
        regex = re.compile(
            r"^[a-z0-9.+-]*://"
            r"(?:" + ipv4_re + "|" + ipv6_re + "|" + host_re + ")"
                                                               r"(?::[0-9]{1,5})?"  # port
                                                               r"(?:[/?#]\S*)?"  # resource path
                                                               r"\Z",
            re.IGNORECASE,
        )
        unsafe_chars = frozenset("\t\r\n")

        if not isinstance(url, str) or unsafe_chars.intersection(url):
            return None

        url = url.strip()

        # Check scheme
        scheme_split = url.split("://", maxsplit=1)
        scheme = scheme_split[0].lower()
        if scheme not in ["http", "https"]:
            if len(scheme_split) != 1:
                return None
            return Common.validate_url("https://" + url) or Common.validate_url("http://" + url)

        # Check full URL
        try:
            splitted_url = urlsplit(url)
        except ValueError:
            return None

        # Check the maximum length of a full host name is 253 characters
        if splitted_url.hostname is None or len(splitted_url.hostname) > 253:
            raise None

        regex_matches = regex.search(url)
        if regex_matches:
            # Verify IPv6 if any in the netloc part
            host_match = re.search(
                r"^\[(.+)](?::[0-9]{1,5})?$", splitted_url.netloc)
            if host_match:
                potential_ip = host_match[1]
                if not Common.is_valid_ipv6_address(potential_ip):
                    return None
            return url

        return None

    @staticmethod
    def exception_details(function_name, exception):
        """
        The function "exception_details" prints the details of an exception, including the function
        name, exception details, and traceback information.
        
        Args:
          function_name: The name of the function where the exception occurred.
          exception: The exception parameter is the exception object that was raised during the
        execution of the function. It contains information about the type of exception and any
        additional details that may be available.
        """
        # code to handle the exception
        print("=====================================================================================")
        print("🚩 Exception in function: ", function_name)
        print("-------------------------------------------------------------------------------------")
        print("⚠️ Exception details:", exception)
        print("-------------------------------------------------------------------------------------")
        print("🔽 Traceback information: ")
        traceback.print_exc()
        print("=====================================================================================")

    @staticmethod
    def allowed_file(filename):
        """Check if a file is an allowed file based on a set of allowed image extensions

        Args:
            filename (str): filename

        Returns:
            boolean: Returns the status of whether the file is an allowed file or not
        """

        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_IMAGE_EXTENSIONS

    @staticmethod
    def get_file_extension(filename):
        """Get the extension of a file

        Args:
            filename (str): The filename of the file whose extension is to be extracted

        Returns:
            str: The extension of the file
        """
        return filename.split('.')[-1]

    @staticmethod
    def check_required_params(request_params, params: list = []):
        """
        The function `check_required_params` checks if all required parameters are present in the
        request parameters and returns the first missing parameter if any, otherwise returns None.
        
        Args:
          request_params: A dictionary containing the request parameters.
          params (list): The `params` parameter is a list that contains the names of the required
        parameters.
        
        Returns:
          the first required parameter that is missing or empty in the request_params. If all required
        parameters are present and not empty, it returns None.
        """
    
        # Check if all required parameters are present in the request params
        for param in params:
        
            if param not in request_params or (request_params[param] in [None, ""]):
                return param
        
        return None
