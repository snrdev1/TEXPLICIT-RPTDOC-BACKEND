import asyncio
import os
import re
import urllib
from datetime import datetime
from typing import Tuple, Union
from urllib.parse import unquote, urlparse, urlunparse

from bson import ObjectId
from app.utils.formatter import cursor_to_dict
from app.config import Config
from app.models.mongoClient import MongoClient
from app.utils.audio import tts
from app.utils.common import Common
from app.utils.enumerator import Enumerator
from app.utils.files_and_folders import get_report_directory
from app.utils.llm_researcher.llm_researcher import research
from app.utils.response import Response
from app.utils.socket import emit_report_status


def report_generate(
    user_id: Union[str, ObjectId],
    task: str,
    websearch: bool,
    report_type: str,
    source: str,
    format: str,
    report_generation_id: Union[int, None],
    subtopics: list,
) -> None:
    def create_and_insert_report_document() -> str:
        document_data = {
            "status": {"value": 0, "ref": "pending"},
            "task": task,
            "websearch": websearch,
            "subtopics": subtopics,
            "report_type": report_type,
            "createdBy": {"_id": ObjectId(user_id), "ref": "user"},
            "createdOn": datetime.now(),
            "source": source,
            "format": format,
            "report_generation_id": report_generation_id,
        }
        insert_response = _insert_document_into_db(document_data)
        return str(insert_response["inserted_id"])

    def run_research() -> Tuple[str, str]:
        return asyncio.run(
            research(
                user_id,
                task=task,
                websearch=websearch,
                report_type=report_type,
                source=source,
                format=format,
                report_generation_id=report_generation_id,
                subtopics=subtopics,
            )
        )

    def generate_report_audio(
        report_text: str, report_folder: str
    ) -> dict[str, Union[bool, str]]:
        if len(report_text) and report_type in ["research_report", "detailed_report"]:
            print("🎵 Generating report audio...")
            emit_report_status(user_id, report_generation_id, "🎵 Generating report audio...")

            audio_text = extract_text_before_h2(report_text)
            audio_path = tts(report_folder, audio_text)
            report_audio = {
                "exists": False,
                "text": audio_text,
                "path": urllib.parse.quote(audio_path),
            }
            if len(audio_path):
                report_audio["exists"] = True

            return report_audio
        else:
            return {"exists": False, "text": "", "path": ""}

    def emit_and_save_report(
        report_id: Union[str, ObjectId],
        report: str,
        report_audio: dict[str, Union[bool, str]],
        report_path: str,
        report_generation_time: float,
        status: int,
    ) -> None:
        def transform_data(report_document):
            report_document["_id"] = str(report_id)
            report_document["createdBy"]["_id"] = str(
                report_document["createdBy"]["_id"]
            )
            report_document["createdOn"] = str(report_document["createdOn"])

            return report_document

        def prepare_report_document():
            document = {
                "task": task,
                "websearch": websearch,
                "subtopics": subtopics,
                "report_path": report_path,
                "report": report,
                "report_type": report_type,
                "createdBy": {"_id": ObjectId(user_id), "ref": "user"},
                "createdOn": datetime.now(),
                "source": source,
                "format": format,
                "report_generation_id": report_generation_id,
                "report_generation_time": report_generation_time,
                "report_audio": report_audio,
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
        report_document_for_emitting = transform_data(report_document)

        if not len(update_count):
            Response.socket_reponse(
                event=f"{user_id}_report",
                data=report_document_for_emitting,
                message="Failed to update report in db!",
                success=False,
                status=400,
            )

        if status == int(Enumerator.ReportStep.Success.value):
            Response.socket_reponse(
                event=f"{user_id}_report",
                data=report_document_for_emitting,
                message="Report successully generated!",
                success=True,
                status=200,
            )
        else:
            Response.socket_reponse(
                event=f"{user_id}_report",
                data=report_document_for_emitting,
                message="Failed to generate report!",
                success=False,
                status=400,
            )

    try:
        start_time = datetime.now()

        emit_report_status(
            user_id, report_generation_id, "✈️ Initiaing report generation..."
        )

        report_id = create_and_insert_report_document()
        report, report_path = run_research()
        end_time = datetime.now()
        report_generation_time = (end_time - start_time).total_seconds()
        report_audio = generate_report_audio(report, report_folder)

        if len(report):
            print(f"🖫 Saved report to {report_folder}")
            report_folder = get_report_directory(report_path)
            emit_and_save_report(
                report_id,
                report,
                report_audio,
                report_path,
                report_generation_time,
                int(Enumerator.ReportStep.Success.value),
            )
        else:
            emit_and_save_report(
                report_id,
                report,
                report_audio,
                report_path,
                report_generation_time,
                int(Enumerator.ReportStep.Failure.value),
            )

        print(f"📢 Emitted report!")

    except Exception as e:
        Common.exception_details("generate_report", e)
        Response.socket_reponse(
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


def get_reports_from_db(
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


def get_report_from_db(reportid):
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


def extract_text_before_h2(markdown_text):
    # Use regular expression to find the content before the first H2 heading
    match = re.match(r"^(.*?)(?=\n## )", markdown_text, re.DOTALL)

    if match:
        # Return the content before the first H2 heading
        return match.group(1)
    else:
        # If no H2 heading found, return the entire text
        return markdown_text


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
    response = m_db[Config.MONGO_REPORTS_MASTER_COLLECTION].insert_one(report_document)

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


def _delete_document_from_db(reportid: str) -> dict:
    """
    The function `_delete_document_from_db` deletes a document from a MongoDB database based on its
    report ID.

    Args:
      reportid (str): The `reportid` parameter is a string that represents the unique identifier of
    the document to be deleted from the database.

    Returns:
      a dictionary with the key "deleted_count" and the value being the number of documents deleted
    from the database.
    """
    m_db = MongoClient.connect()

    response = m_db[Config.MONGO_REPORTS_MASTER_COLLECTION].delete_one(
        {"_id": ObjectId(reportid)}
    )

    return {"deleted_count": response.deleted_count}
