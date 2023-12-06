import asyncio
import urllib
from datetime import datetime
from typing import Union

from bson import ObjectId

from app.config import Config
from app.models.mongoClient import MongoClient
from app.utils.common import Common
from app.utils.files_and_folders import get_report_folder
from app.utils.llm_researcher.llm_researcher import research
from app.utils.response import Response


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
    try:
        start_time = datetime.now()
        report, report_path = asyncio.run(
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
        report_folder = urllib.parse.quote(get_report_folder(task, source))
        print(f"🖫 Saved report to {report_folder}")
        end_time = datetime.now()

        report_generation_time = (end_time - start_time).total_seconds()

        # Once report is ready emit it using socket and store it in the db
        if len(report):
            _save_and_emit(
                task=task,
                websearch=websearch,
                subtopics=subtopics,
                user_id=user_id,
                report_folder=report_folder,
                report_path=report_path,
                report=report,
                report_type=report_type,
                source=source,
                format=format,
                report_generation_id=report_generation_id,
                report_generation_time=report_generation_time,
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
    filter_stage = {"createdBy._id": ObjectId(user_id)}
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

    return Common.cursor_to_dict(response)


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

    response = Common.cursor_to_dict(response)
    if len(response) > 0:
        return response[0]
    else:
        return None


def _save_and_emit(
    task: str,
    websearch: bool,
    subtopics: list,
    user_id: Union[str, ObjectId],
    report_folder: str,
    report_path: str,
    report: str,
    report_type: str,
    source: str,
    format: str,
    report_generation_id: Union[str, None],
    report_generation_time: float,
) -> None:
    try:
        report_document = {
            "task": task,
            "websearch": websearch,
            "subtopics": subtopics,
            "report_folder": report_folder,
            "report_path": report_path,
            "report": report,
            "report_type": report_type,
            "createdBy": {"_id": ObjectId(user_id), "ref": "user"},
            "createdOn": datetime.now(),
            "source": source,
            "format": format,
            "report_generation_id": report_generation_id,
            "report_generation_time": report_generation_time,
        }

        insert_response = _insert_document_into_db(report_document)

        report_document["_id"] = str(insert_response["inserted_id"])
        report_document["createdBy"]["_id"] = str(report_document["createdBy"]["_id"])
        report_document["createdOn"] = str(report_document["createdOn"])
        Response.socket_reponse(
            event=f"{user_id}_report",
            data=report_document,
            message="Report successully generated!",
            success=True,
            status=200,
        )

    except Exception as e:
        Common.exception_details("_save_and_emit", e)


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
