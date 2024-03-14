import hashlib
import os
import urllib
from datetime import datetime
from typing import Union

from bson import ObjectId

from app.config import Config


def get_user_folder(user_id: Union[str, ObjectId]):
    """
    The function `get_user_folder` takes a user ID as input and returns the path to the user's folder.

    Args:
      user_id: The user_id parameter is the unique identifier for a user. It is used to create a folder
    path specific to that user.

    Returns:
      the path to the user's folder.
    """
    user_folder = os.path.join(Config.USER_FOLDER, str(user_id))

    return user_folder


def get_report_folder(question, source: str = "external"):
    """
    The function `get_report_folder` takes a question as input, creates a hashed folder path using
    the question, and returns the directory folder path.

    # The code snippet f"./outputs/{hashlib.sha1(question.encode()).hexdigest()}" is constructing a file path based on a hashed version of a 'question' string using the SHA-1 hashing algorithm.

    # - 'question' is a string that you want to hash. It could be any string, such as a question or some other data.
    # - 'question.encode()' converts the 'question' string into bytes. Hash functions typically operate on bytes, so this step is necessary to convert the string into a format that the hash function can process.
    # - 'hashlib.sha1(question.encode())' creates a SHA-1 hash object. The hashlib module in Python provides various hash functions, and in this case, it's using SHA-1.
    # - '.hexdigest()' is called on the SHA-1 hash object to get the hexadecimal representation of the hash. In other words, it converts the binary hash value into a human-readable hexadecimal string.
    # - 'f"./outputs/{hashlib.sha1(question.encode()).hexdigest()}"' uses an f-string to construct a file path. It places the hexadecimal representation of the SHA-1 hash at the end of the path, making it unique to the input 'question'.

    # So, this code generates a file path that is based on the SHA-1 hash of the 'question' string, which can be useful for creating unique filenames or directories associated with the input data.


    Args:
      question: The "question" parameter is a string that represents the question for which the
    report folder is being created.

    Returns:
      the directory path for the report folder.
    """
    # Create a hashed folder path using os.path.join
    current_time = datetime.utcnow()

    folder_name = f"{question.strip().lower()}_{source}_{current_time}"
    hashed_folder = hashlib.sha1(folder_name.encode()).hexdigest()

    if Config.GCP_PROD_ENV:
        directory_folder = f"report_outputs/{hashed_folder}"
    else:
        directory_folder = os.path.join('report_outputs', hashed_folder)

    return directory_folder


def get_report_directory(user_id: Union[str, ObjectId], question: str = "", source: str = "external", report_folder=None):
    """
    The function `get_report_directory` returns the path to a directory based on the user ID and
    question.

    Args:
      user_id: The user_id parameter is a unique identifier for a user. It could be a string or an
    integer that uniquely identifies a user in your system.
      question: The question parameter is a string that represents the question for which the report
    directory is being retrieved.

    Returns:
      the directory path where the report for the given user and question is stored.
    """
    if not report_folder:
        directory_folder = get_report_folder(question=question, source=source)
    else:
        directory_folder = urllib.parse.unquote(report_folder)

    if Config.GCP_PROD_ENV:
        user_folder_path = f"{user_id}"
        directory_path = f"{user_folder_path}/{directory_folder}"
    else:
        user_folder = get_user_folder(user_id)
        directory_path = os.path.join(user_folder, directory_folder)

    return directory_path


def get_report_path(report_document):
    print("report_document  : ", report_document)
    file_path = urllib.parse.unquote(report_document["report_path"])
    print("📡 file_path : ", file_path)

    return file_path


def get_report_audio_path(report_document):
    try:
        report_audio_path_quoted = report_document["report_audio"]["path"]
        report_audio_path = urllib.parse.unquote(report_audio_path_quoted)
        print("🎵 audio path : ", report_audio_path)

        return report_audio_path

    except Exception as e:
        return ""


def get_size(files: list) -> int:
    """
    This Python function calculates and returns the total size in bytes of a list of files.
    
    Args:
      files (list): The `get_size` function you provided takes a list of file objects as input and
    calculates the total size of all the files in bytes. The function iterates over each file in the
    list, moves to the end of the file to get its size, and then moves back to the beginning for further
    
    Returns:
      The function `get_size` returns the total size of all files in the input list in bytes.
    """
    total_size = 0
    for file in files:
        file.seek(0, 2)  # Move to the end of the file
        total_size += file.tell()  # Get the current position, which indicates the size
        # Move back to the beginning of the file for further processing
        file.seek(0)
        
    return total_size


def megabytes_to_bytes(file_size: int = 0) -> int:
    """
    Converts a file size in megabytes to bytes.

    Args:
        file_size (int): The file size in megabytes. Defaults to 0.

    Returns:
        int: The file size in bytes.
    """
    return int(file_size * 1024 * 1024)