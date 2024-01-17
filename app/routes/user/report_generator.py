"""
    All Report Generator related routes
"""

import io
import os
import threading

from flask import Blueprint, request, send_file

from app.auth.userauthorization import authorized
from app.config import Config
from app.services.reportGeneratorService import report_generate, get_reports_from_db, get_report_from_db
from app.utils.common import Common
from app.utils.files_and_folders import get_report_path, get_report_audio_path
from app.utils.messages import Messages
from app.utils.production import Production
from app.utils.response import Response

report_generator = Blueprint("report_generator", __name__, url_prefix="/report")


@report_generator.route("/generate", methods=["POST"])
@authorized
def generate_report(logged_in_user):
    try:
        user_id = logged_in_user["_id"]
        request_params = request.get_json()

        # Required parameters
        required_params = ["task"]

        # Check if all required parameters are present in the request params
        if not any(
            (key in request_params) and (request_params[key] not in [None, ""])
            for key in required_params
        ):
            return Response.missing_parameters()

        task = request_params.get("task")
        report_type = request_params.get("report_type", "research_report")
        source = request_params.get("source", "external")
        format = request_params.get("format", "pdf")
        report_generation_id = request_params.get("report_generation_id", None)
        websearch = request_params.get("websearch", False)
        subtopics = request_params.get("subtopics", [])

        # Getting response and emitting it in a separate non-blocking thread
        t1 = threading.Thread(
            target=report_generate,
            args=(
                user_id,
                task,
                websearch,
                report_type,
                source,
                format,
                report_generation_id,
                subtopics,
            ),
        )
        t1.start()

        return Response.custom_response([], Messages.OK_REPORT_GENERATING, True, 200)

    except Exception as e:
        Common.exception_details("report-generator.py : generate_report", e)
        return Response.server_error()


@report_generator.route("/all", methods=["GET"])
@authorized
def retrieve_reports(logged_in_user):
    try:
        user_id = str(logged_in_user["_id"])
        request_params = request.args.to_dict()
        limit = int(request_params.get("limit", 10))
        offset = int(request_params.get("offset", 0))
        source = request_params.get("source", "")
        format = request_params.get("format", "")
        report_type = request_params.get("report_type", "")

        reports = get_reports_from_db(user_id, limit, offset, source, format, report_type)

        return Response.custom_response(reports, Messages.OK_REPORTS_FOUND, True, 200)

    except Exception as e:
        Common.exception_details("report-generator.py : retrieve_reports", e)
        return Response.server_error()


@report_generator.route("/download/<reportid>", methods=["GET"])
@authorized
def download_report(logged_in_user, reportid):
    try:
        user_id = str(logged_in_user["_id"])

        report_document = get_report_from_db(reportid)
        if report_document:
            if user_id != str(report_document["createdBy"]["_id"]):
                return Response.custom_response([], Messages.UNAUTHORIZED, False, 401)

            file_path = get_report_path(report_document)

            if Config.GCP_PROD_ENV:
                user_bucket = Production.get_users_bucket()
                blob = user_bucket.blob(file_path)
                bytes = blob.download_as_bytes()
                download_file = io.BytesIO(bytes)

                return send_file(
                    download_file,
                    as_attachment=True,
                    download_name=report_document["task"][:10],
                )
            else:
                if os.path.exists(file_path):
                    return send_file(
                        file_path,
                        as_attachment=True,
                        download_name=report_document["task"][:10],
                    )

        return Response.custom_response([], Messages.MISSING_REPORT, False, 400)

    except Exception as e:
        Common.exception_details("mydocuments.py : download_report", e)
        return Response.server_error()
    
@report_generator.route("/audio/download/<reportid>", methods=["GET"])
@authorized
def download_report_audio(logged_in_user, reportid):
    try:
        user_id = str(logged_in_user["_id"])

        report_document = get_report_from_db(reportid)
        if not report_document:
            return Response.custom_response([], Messages.MISSING_REPORT, False, 400)
        
        if user_id != str(report_document["createdBy"]["_id"]):
            return Response.custom_response([], Messages.UNAUTHORIZED, False, 401)

        file_path = get_report_audio_path(report_document)

        if Config.GCP_PROD_ENV:
            user_bucket = Production.get_users_bucket()
            blob = user_bucket.blob(file_path)
            bytes = blob.download_as_bytes()
            download_file = io.BytesIO(bytes)

            return send_file(
                download_file,
                as_attachment=True,
                download_name=f"{report_document['task'][:10]}_audio",
            )
        else:
            if len(file_path) and os.path.exists(file_path):
                return send_file(
                    file_path,
                    as_attachment=True,
                    download_name=f"{report_document['task'][:10]}_audio",
                )

        return Response.custom_response([], Messages.MISSING_REPORT, False, 400)

    except Exception as e:
        Common.exception_details("mydocuments.py : download_report_audio", e)
        return Response.server_error()
