import base64
import json
import io
from bson import json_util

from app.utils.common import Common


def get_formatted_report_type(report_type: str) -> str:
    """Converts a report_type key to a proper titlecase string representation

    Args:
        report_type (str): report_type key value in report generation

    Returns:
        str: Titlecase string representation of report type
    """

    if not report_type:
        return ""

    return " ".join(word.title() for word in report_type.split("_"))


def get_formatted_response(response):
    """Converts a response object to python dictionary and avoid type errors

    Args:
        response (dict): Response object

    Returns:
        dict: Python dictionary representation of input Response
    """

    processed_response = json.loads(json_util.dumps(response, default=str))

    return processed_response


def cursor_to_dict(cursor):
    """Converts a cursor to python dictionary

    Args:
        cursor (Cursor): Cursor Object

    Returns:
        dict: Python dictionary representation of input Cursor
    """

    try:
        # iterate over cursor to get a list of dicts
        cursor_dict = [doc for doc in cursor]

        # serialize to json string
        cursor_dict_string = json.dumps(cursor_dict, default=json_util.default)

        # json from json string
        cursor_dict = json.loads(cursor_dict_string)

        return cursor_dict

    except Exception as e:
        Common.exception_details("common.py : cursor_to_dict", e)


def get_base64_encoding(file):
    try:
        if isinstance(file, io.BytesIO):
            file = file.getvalue()  # Convert BytesIO to bytes
        
        encoded_string = base64.b64encode(file)
        base64_message = encoded_string.decode("utf-8")

        return base64_message
    
    except Exception as e:
        Common.exception_details("get_base64_encoding", e)
        return None
