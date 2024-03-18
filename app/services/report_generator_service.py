import asyncio
import io
import os
import re
import urllib
from datetime import datetime, timedelta
from typing import List, Tuple, Union
from urllib.parse import unquote, urlparse, urlunparse

from bson import ObjectId

from app.config import Config
from app.models.mongoClient import MongoClient
from app.utils.email_helper import send_mail
from app.utils.files_and_folders import get_report_directory, get_report_path
from app.utils.formatter import cursor_to_dict, get_base64_encoding
from app.utils.llm_researcher.llm_researcher import research
from app.utils.socket import emit_report_status

from ..utils import (AudioGenerator, Common, Enumerator, Production, Response,
                     send_mail)
from . import user_service as UserService


def report_generate(
    user_id: Union[str, ObjectId],
    task: str,
    report_type: str,
    source: str,
    format: str,
    report_generation_id: Union[int, None],
    subtopics: list,
    urls: List[str]
) -> None:

    def transform_data(report_document, report_id: Union[ObjectId, str] = ""):
        report_document["_id"] = (
            str(report_id) if report_id else str(
                report_document.get("_id", ""))
        )

        if "createdBy" in report_document and "_id" in report_document["createdBy"]:
            report_document["createdBy"]["_id"] = str(
                report_document["createdBy"]["_id"]
            )

        if "createdOn" in report_document:
            # Convert UTC time to string in the desired format
            report_document["createdOn"] = (
                report_document["createdOn"].strftime(
                    "%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            )

        return report_document

    def emit_and_save_pending_report() -> str:
        document_data = {
            "status": {
                "value": int(Enumerator.ReportStep.Pending.value),
                "ref": "pending",
            },
            "task": task,
            "subtopics": subtopics,
            "report_type": report_type,
            "createdBy": {"_id": ObjectId(user_id), "ref": "user"},
            "createdOn": datetime.utcnow(),
            "source": source,
            "format": format,
            "urls": urls,
            "report_generation_id": report_generation_id,
            "tables": {
                "data": [],
                "path": ""
            },
        }
        insert_response = _insert_document_into_db(document_data)

        # Also emit the new document inserted as pending
        Response.socket_response(
            event=f"{user_id}_report_pending",
            data=transform_data(document_data),
            message="Report generation successfully started!",
            success=True,
            status=200,
        )

        return str(insert_response["inserted_id"])

    def run_research() -> Tuple[str, str]:
        return asyncio.run(
            research(
                user_id,
                task=task,
                report_type=report_type,
                source=source,
                format=format,
                report_generation_id=report_generation_id,
                subtopics=subtopics,
                urls=urls
            )
        )

    def generate_report_audio(
        report_text: str, report_folder: str
    ) -> dict[str, Union[bool, str]]:
        if (
            not len(report_folder)
            or not len(report_text)
            or report_type not in [
                Enumerator.ReportType.ResearchReport.value,
                Enumerator.ReportType.DetailedReport.value
            ]
        ):
            return {"exists": False, "text": "", "path": ""}

        print("🎵 Generating report audio...")
        emit_report_status(
            user_id, report_generation_id, "🎵 Generating report audio..."
        )

        audio_text = extract_text_before_h2(report_text)
        audio_generator = AudioGenerator(report_folder, audio_text)
        audio_path = audio_generator.tts()
        report_audio = {
            "exists": False,
            "text": audio_text,
            "path": urllib.parse.quote(audio_path),
        }
        if len(audio_path):
            report_audio["exists"] = True

        return report_audio

    def emit_and_save_report(
        report_id: Union[str, ObjectId],
        report: str,
        report_audio: dict[str, Union[bool, str]],
        report_path: str,
        tables: list,
        table_path: str,
        report_urls: set,
        report_generation_time: float,
        status: int,
    ) -> None:
        def prepare_report_document():

            document = {
                "task": task,
                "subtopics": subtopics,
                "report_path": report_path,
                "report": report,
                "report_type": report_type,
                "createdBy": {"_id": ObjectId(user_id), "ref": "user"},
                "createdOn": datetime.utcnow(),
                "source": source,
                "format": format,
                "urls": list(report_urls),
                "report_generation_id": report_generation_id,
                "report_generation_time": report_generation_time,
                "report_audio": report_audio,
                "tables": {
                    "data": tables,
                    "path": table_path
                },
            }

            if status == int(Enumerator.ReportStep.Success.value):
                document["status"] = {"value": status, "ref": "success"}
            else:
                document["status"] = {"value": status, "ref": "failure"}

            return document

        def update_report_document_in_db(report_document):
            update_response = _update_document_in_db(
                {"_id": ObjectId(report_id)}, report_document
            )

            return update_response["updated_count"]

        # Prepare report document for update
        report_document = prepare_report_document()
        # Update report document in db
        update_count = update_report_document_in_db(report_document)
        # Transform the report data to suitable format before emitting
        report_document_for_emitting = transform_data(
            report_document, report_id)

        if not update_count:
            Response.socket_response(
                event=f"{user_id}_report",
                data=report_document_for_emitting,
                message="Failed to update report in db!",
                success=False,
                status=400,
            )

        if status == int(Enumerator.ReportStep.Success.value):
            Response.socket_response(
                event=f"{user_id}_report",
                data=report_document_for_emitting,
                message="Report successfully generated!",
                success=True,
                status=200,
            )
        else:
            Response.socket_response(
                event=f"{user_id}_report",
                data=report_document_for_emitting,
                message="Failed to generate report!",
                success=False,
                status=400,
            )

    try:
        # Log start time of report generation
        start_time = datetime.utcnow()

        emit_report_status(
            user_id, report_generation_id, "✈️ Initiating report generation..."
        )

        report_id = emit_and_save_pending_report()
        report, report_path, tables, table_path, report_urls = run_research()

        # Log end time of report generation
        end_time = datetime.utcnow()
        report_generation_time = (end_time - start_time).total_seconds()
        report_audio = generate_report_audio(report, "")

        if len(report):
            report_folder = get_report_directory(report_path)
            print(f"🖫 Saved report to {report_folder}")
            report_audio = generate_report_audio(report, report_folder)
            emit_and_save_report(
                report_id,
                report,
                report_audio,
                report_path,
                tables,
                table_path,
                report_urls,
                report_generation_time,
                int(Enumerator.ReportStep.Success.value),
            )

            # Update user subscription
            UserService.update_report_subscription(user_id, report_type)
        else:
            emit_and_save_report(
                report_id,
                report,
                report_audio,
                report_path,
                tables,
                table_path,
                report_urls,
                report_generation_time,
                int(Enumerator.ReportStep.Failure.value),
            )

        print(f"📢 Emitted report!")

    except Exception as e:
        Common.exception_details("generate_report", e)
        Response.socket_response(
            event=f"{user_id}_report",
            data={"report_generation_id": report_generation_id},
            message="Failed to generate report!",
            success=False,
            status=500,
        )


def get_report_directory(url):
    # Parse the URL
    parsed_url = urlparse(url)

    # Decode the path component
    decoded_path = unquote(parsed_url.path)

    # Extract the directory part without the file at the end using os.path
    directory_part = os.path.dirname(decoded_path)

    # Reconstruct the URL with the decoded directory part
    reconstructed_url = urlunparse(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            directory_part,
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment,
        )
    )

    return reconstructed_url


def get_all_reports_from_db(
    user_id: Union[str, ObjectId],
    limit: int = 10,
    offset: int = 0,
    source: str = "",
    format: str = "",
    report_type: str = "",
):
    """
    The function `get_reports_from_db` retrieves reports from a MongoDB database based on various
    criteria such as user ID, limit, offset, source, format, and report type.

    Args:
      user_id (Union[str, ObjectId]): The user_id parameter is the ID of the user for whom you want to
    retrieve the reports. It can be either a string or an ObjectId.
      limit (int): The `limit` parameter specifies the maximum number of reports to retrieve from the
    database. By default, it is set to 10. Defaults to 10
      offset (int): The offset parameter is used to specify the number of documents to skip before
    starting to return the documents. It is used for pagination purposes. For example, if offset is set
    to 10, it means that the first 10 documents will be skipped and the result will start from the 11th
    document. Defaults to 0
      source (str): The "source" parameter is used to filter the reports based on their source. It is an
    optional parameter and can be a string representing the source of the reports.
      format (str): The "format" parameter is used to filter the reports based on their format. It is a
    string that specifies the desired format of the reports.
      report_type (str): The `report_type` parameter is used to filter the reports based on their type.
    It is an optional parameter and can be a string value.

    Returns:
      a list of reports from a database.
    """
    m_db = MongoClient.connect()

    # Filter stage to filter out the reports based on various criteria
    filter_stage = {
        "createdBy._id": ObjectId(user_id),
        "status.value": {
            "$nin": [
                int(Enumerator.ReportStep.Pending.value),
                int(Enumerator.ReportStep.Failure.value),
            ]
        },
    }
    if source not in [None, ""]:
        filter_stage["source"] = source
    if format not in [None, ""]:
        filter_stage["format"] = format
    if report_type not in [None, ""]:
        filter_stage["report_type"] = report_type

    response = m_db[Config.MONGO_REPORTS_MASTER_COLLECTION].aggregate(
        [
            {"$match": filter_stage},
            {"$sort": {"createdOn": -1}},
            {"$skip": offset},
            {"$limit": limit},
            {
                "$addFields": {
                    "_id": {"$toString": "$_id"},
                    "createdBy._id": {"$toString": "$createdBy._id"},
                    "createdOn": {"$dateToString": {"date": "$createdOn"}},
                }
            },
        ]
    )

    return cursor_to_dict(response)


def get_report_from_db(reportid: Union[str, ObjectId]):
    """
    The function `get_report_from_db` retrieves a report from a MongoDB database based on the
    provided report ID.

    Args:
      reportid: The `reportid` parameter is the unique identifier of the report that you want to
    retrieve from the database.

    Returns:
      a dictionary containing the report information retrieved from the database.
    """
    m_db = MongoClient.connect()
    response = m_db[Config.MONGO_REPORTS_MASTER_COLLECTION].aggregate(
        [
            {"$match": {"_id": ObjectId(reportid)}},
            {
                "$addFields": {
                    "_id": {"$toString": "$_id"},
                    "createdBy._id": {"$toString": "$createdBy._id"},
                    "createdOn": {"$dateToString": {"date": "$createdOn"}},
                }
            },
        ]
    )

    response = cursor_to_dict(response)
    if len(response) > 0:
        return response[0]
    else:
        return None


def get_multiple_reports_from_db(reportids: List[Union[str, ObjectId]]):
    """
    The function `get_reports_from_db` retrieves reports from a MongoDB database based on the
    provided list of report IDs.

    Args:
      reportids: A list of report IDs for the reports that you want to retrieve from the database.

    Returns:
      A list of dictionaries, each containing the report information retrieved from the database.
    """
    m_db = MongoClient.connect()
    response = m_db[Config.MONGO_REPORTS_MASTER_COLLECTION].aggregate(
        [
            {
                "$match": {
                    "_id": {"$in": [ObjectId(reportid) for reportid in reportids]}
                }
            },
            {
                "$addFields": {
                    "_id": {"$toString": "$_id"},
                    "createdBy._id": {"$toString": "$createdBy._id"},
                    "createdOn": {"$dateToString": {"date": "$createdOn"}},
                }
            },
        ]
    )

    response = cursor_to_dict(response)
    return response


def extract_text_before_h2(markdown_string: str):
    # Split the string into lines
    lines = markdown_string.split("\n")

    # Initialize variables to store the text
    text_before_first_h2 = ""
    text_before_second_h2 = ""

    # Flag to track if we have encountered the first h2 header
    first_h2_found = False

    # Iterate over the lines
    for line in lines:
        # Check if the line is an H1 or H2 header
        if re.match(r"^#{1,2} ", line):
            if not first_h2_found:
                if line.startswith("# "):  # H1 header
                    text_before_first_h2 = ""
                else:  # H2 header
                    text_before_first_h2 = text_before_first_h2.strip()
                    first_h2_found = True
            else:
                text_before_second_h2 = text_before_second_h2.strip()
                break
        else:
            # Append the line to the appropriate text variable
            if not first_h2_found:
                text_before_first_h2 += line + "\n"
            else:
                text_before_second_h2 += line + "\n"

    # Return the extracted text
    if text_before_first_h2.strip() == "":
        return text_before_second_h2.strip()
    else:
        return text_before_first_h2.strip()


def get_report_download_filename(report_type: str, report_task: str, report_created):
    try:
        processed_report_type = " ".join(
            word.capitalize() for word in report_type.split("_")
        )
        processed_report_task = report_task[:10]
        return f"{processed_report_type} - {processed_report_task}_{report_created}"

    except Exception as e:
        return ""


def get_report_audio_download_filename(
    report_type: str, report_task: str, report_created
):
    try:
        processed_report_type = " ".join(
            word.capitalize() for word in report_type.split("_")
        )
        processed_report_task = report_task[:10]
        return (
            f"{processed_report_type} - {processed_report_task}_AUDIO_{report_created}"
        )

    except Exception as e:
        return ""


def get_pending_reports_from_db(
    user_id: Union[str, ObjectId],
    limit: int = 10,
    offset: int = 0,
    source: str = "",
    format: str = "",
    report_type: str = "",
):
    # First clear the pending reports which have been pending for a certain amount of time
    _set_reports_as_failed_in_db(user_id)

    m_db = MongoClient.connect()

    # Filter stage to filter out the reports based on various criteria
    filter_stage = {
        "createdBy._id": ObjectId(user_id),
        "status.value": int(Enumerator.ReportStep.Pending.value),
    }
    if source not in [None, ""]:
        filter_stage["source"] = source
    if format not in [None, ""]:
        filter_stage["format"] = format
    if report_type not in [None, ""]:
        filter_stage["report_type"] = report_type

    response = m_db[Config.MONGO_REPORTS_MASTER_COLLECTION].aggregate(
        [
            {"$match": filter_stage},
            {"$sort": {"createdOn": -1}},
            {"$skip": offset},
            {"$limit": limit},
            {
                "$addFields": {
                    "_id": {"$toString": "$_id"},
                    "createdBy._id": {"$toString": "$createdBy._id"},
                    "createdOn": {"$dateToString": {"date": "$createdOn"}},
                }
            },
        ]
    )

    return cursor_to_dict(response)


def _set_reports_as_failed_in_db(user_id: Union[str, ObjectId]):
    try:
        m_db = MongoClient.connect()

        # Calculate the time threshold (1 hour ago from the current time)
        time_threshold = datetime.utcnow() - timedelta(hours=1)

        # Filter stage to filter out the reports based on various criteria
        query = {
            "createdBy._id": ObjectId(user_id),
            "createdOn": {"$lt": time_threshold},
            "status.value": int(Enumerator.ReportStep.Pending.value),
        }

        response = m_db[Config.MONGO_REPORTS_MASTER_COLLECTION].update_many(
            query,
            {
                "$set": {
                    "status": {
                        "value": int(Enumerator.ReportStep.Failure.value),
                        "ref": "failed",
                    }
                }
            },
        )

        return response.modified_count

    except Exception as e:
        print(f"Error updating document in the database: {e}")
        return {"updated_count": 0}


def _insert_document_into_db(report_document: dict) -> dict:
    """
    The function inserts a document into a MongoDB database and returns the inserted document's ID.

    Args:
      report_document (dict): A dictionary containing the data of the report document that needs to
    be inserted into the database.

    Returns:
      a dictionary with the key "inserted_id" and the value being the id of the document that was inserted.
    """
    m_db = MongoClient.connect()
    response = m_db[Config.MONGO_REPORTS_MASTER_COLLECTION].insert_one(
        report_document)

    print("Inserted _id : ", str(response.inserted_id))

    return {"inserted_id": str(response.inserted_id)}


def _update_document_in_db(query: dict, update_data: dict) -> dict:
    """
    The function updates a document in a MongoDB database based on the provided query and update data.

    Args:
      query (dict): A dictionary specifying the filter criteria for the document to be updated.
      update_data (dict): A dictionary containing the fields and values to be updated.

    Returns:
      a dictionary with the key "updated_count" and the value being the number of documents updated.
    """
    try:
        m_db = MongoClient.connect()
        result = m_db[Config.MONGO_REPORTS_MASTER_COLLECTION].update_one(
            query, {"$set": update_data}
        )

        if result.matched_count > 0:
            print(f"Updated {result.modified_count} document(s)")
            return {"updated_count": result.modified_count}
        else:
            print("No document matched the provided query.")
            return {"updated_count": 0}

    except Exception as e:
        print(f"Error updating document in the database: {e}")
        return {"updated_count": 0}


def delete_report_from_db(reportid: str) -> dict:
    """
    The function `_delete_report_from_db` deletes a report from a MongoDB database based on its
    report ID.

    Args:
      reportid (str): The `reportid` parameter is a string that represents the unique identifier of
    the report to be deleted from the database.

    Returns:
      a dictionary with the key "deleted_count" and the value being the number of documents deleted
    from the database.
    """
    m_db = MongoClient.connect()

    response = m_db[Config.MONGO_REPORTS_MASTER_COLLECTION].delete_one(
        {"_id": ObjectId(reportid)}
    )

    return {"deleted_count": response.deleted_count}


def get_failed_reports_from_db(user_id: Union[str, ObjectId]):
    m_db = MongoClient.connect()

    # Filter stage to filter out the reports based on various criteria
    filter_stage = {
        "createdBy._id": ObjectId(user_id),
        "status.value": int(Enumerator.ReportStep.Failure.value),
    }

    response = m_db[Config.MONGO_REPORTS_MASTER_COLLECTION].aggregate(
        [
            {"$match": filter_stage},
            {"$sort": {"createdOn": -1}},
            {
                "$addFields": {
                    "_id": {"$toString": "$_id"},
                    "createdBy._id": {"$toString": "$createdBy._id"},
                    "createdOn": {"$dateToString": {"date": "$createdOn"}},
                }
            },
        ]
    )

    return cursor_to_dict(response)


def delete_failed_reports_from_db(user_id: Union[str, ObjectId]) -> dict:
    try:
        m_db = MongoClient.connect()

        response = m_db[Config.MONGO_REPORTS_MASTER_COLLECTION].delete_many(
            {
                "createdBy._id": ObjectId(user_id),
                "status.value": int(Enumerator.ReportStep.Failure.value),
            }
        )

        return {"deleted_count": response.deleted_count}

    except Exception as e:
        return {"deleted_count": 0}


def get_file_contents(report_document):
    try:
        file_path = get_report_path(report_document)

        print(f"file_path : {file_path}")
        file_name = get_report_download_filename(
            report_document["report_type"],
            report_document["task"],
            report_document["createdOn"],
        )

        if Config.GCP_PROD_ENV:
            user_bucket = Production.get_users_bucket()
            blob = user_bucket.blob(file_path)
            bytes = blob.download_as_bytes()
            return io.BytesIO(bytes), file_name
        else:
            if os.path.exists(file_path):
                with open(file_path, 'rb') as file_handle:
                    file_bytes = file_handle.read()
                    return io.BytesIO(file_bytes), file_name

    except Exception as e:
        Common.exception_details(
            "report_generator_service.get_file_contents", e)
        return None, None


def share_reports_via_email(user_id, report_ids, email_ids, subject: str = "Sharing Report from TexplicitRW", message: str = "Check out these report(s) from TexplicitRW"):
    try:
        report_documents = get_multiple_reports_from_db(report_ids)
        user = UserService.get_user_by_id(user_id)
        report_details = [
            get_file_contents(report_document) for report_document in report_documents
        ]
        report_contents, report_names = zip(*report_details)
        attachments = [
            {
                "content": get_base64_encoding(report_content),
                "name": report_name + "." + ("pdf" if report_document["format"] == "pdf" else "docx")
            }
            for (report_content, report_name, report_document) in zip(report_contents, report_names, report_documents)
        ]

        recipients = [{"name": None, "email": email_id}
                      for email_id in email_ids]
        email_response = send_mail(
            subject=subject or Config.DEFAULT_REPORT_EMAIL_SUBJECT,
            htmlMailBody=message or Config.DEFAULT_REPORT_EMAIL_MESSAGE,
            recipients=recipients,
            sender={"name": user["name"], "email": user["email"]},
            attachments=attachments,
        )

        return email_response

    except Exception as e:
        Common.exception_details(
            "report_generator_service.share_reports_via_email", e)
        return None
