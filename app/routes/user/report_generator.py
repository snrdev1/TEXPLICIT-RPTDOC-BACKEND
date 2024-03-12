"""
    All Report Generator related routes
"""

import io
import os
import threading

from flask import Blueprint, request, send_file

from app.auth.userauthorization import authorized
from app.config import Config
from app.services.reportGeneratorService import (
    delete_failed_reports_from_db,
    get_all_reports_from_db,
    get_failed_reports_from_db,
    get_file_contents,
    get_pending_reports_from_db,
    get_report_audio_download_filename,
    get_report_from_db,
    report_generate,
    share_reports_via_email
)
from app.utils.common import Common
from app.utils.files_and_folders import get_report_audio_path
from app.utils.messages import Messages
from app.utils.production import Production
from app.utils import Response

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

        reports = get_all_reports_from_db(
            user_id, limit, offset, source, format, report_type
        )

        return Response.custom_response(reports, Messages.OK_REPORTS_FOUND, True, 200)

    except Exception as e:
        Common.exception_details("report-generator.py : retrieve_reports", e)
        return Response.server_error()


@report_generator.route("/pending", methods=["GET"])
@authorized
def retrieve_pending_reports(logged_in_user):
    try:
        user_id = str(logged_in_user["_id"])
        request_params = request.args.to_dict()
        limit = int(request_params.get("limit", 10))
        offset = int(request_params.get("offset", 0))
        source = request_params.get("source", "")
        format = request_params.get("format", "")
        report_type = request_params.get("report_type", "")

        reports = get_pending_reports_from_db(
            user_id, limit, offset, source, format, report_type
        )

        return Response.custom_response(reports, Messages.OK_REPORTS_FOUND, True, 200)

    except Exception as e:
        Common.exception_details("report-generator.py : retrieve_pending_reports", e)
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

            file_bytes, file_name = get_file_contents(report_document)

            return send_file(file_bytes, as_attachment=True, download_name=file_name)

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
                download_name=get_report_audio_download_filename(
                    report_document["report_type"],
                    report_document["task"],
                    report_document["createdOn"],
                ),
                mimetype="audio/wav",
            )
        else:
            if len(file_path) and os.path.exists(file_path):
                return send_file(
                    file_path,
                    as_attachment=True,
                    download_name=get_report_audio_download_filename(
                        report_document["report_type"],
                        report_document["task"],
                        report_document["createdOn"],
                    ),
                    mimetype="audio/wav",
                )

        return Response.custom_response([], Messages.MISSING_REPORT, False, 400)

    except Exception as e:
        Common.exception_details("mydocuments.py : download_report_audio", e)
        return Response.server_error()


@report_generator.route("/failed", methods=["GET"])
@authorized
def get_failed_reports(logged_in_user):
    try:
        user_id = str(logged_in_user["_id"])

        report_document = get_failed_reports_from_db(user_id)
        return Response.custom_response(report_document, "", True, 200)

    except Exception as e:
        Common.exception_details("mydocuments.py : get_failed_reports", e)
        return Response.server_error()


@report_generator.route("/failed/delete", methods=["DELETE"])
@authorized
def clear_failed_reports(logged_in_user):
    try:
        user_id = str(logged_in_user["_id"])

        report_document = delete_failed_reports_from_db(user_id).get("delete_count", 0)
        return Response.custom_response(
            [{"delete_count": report_document}], Messages.OK_REPORTS_DELETED, True, 200
        )

    except Exception as e:
        Common.exception_details("mydocuments.py : get_failed_reports", e)
        return Response.server_error()


@report_generator.route("/share", methods=["POST"])
@authorized
def share_report(logged_in_user):
    try:
        request_params = request.get_json()

        # Required parameters
        required_params = ["reportIds", "emailIds"]

        # Check if all required parameters are present in the request params
        if not all(
            (key in request_params) and (request_params[key] not in [None, ""])
            for key in required_params
        ):
            return Response.missing_parameters()

        report_ids = request_params.get("reportIds")
        email_ids = request_params.get("emailIds")
        subject = request_params.get("subject", "")
        message = request_params.get("message", "")

        user_id = logged_in_user["_id"]

        response = share_reports_via_email(
            user_id, report_ids, email_ids, subject, message
        )

        if response:
            return Response.custom_response(
                response, Messages.OK_MY_DOCUMENT_SHARED, True, 200
            )

        return Response.custom_response(
            0, Messages.ERROR_MY_DOCUMENT_SHARED, False, 400
        )

    except Exception as e:
        Common.exception_details("mydocuments.py : share_document", e)
        return Response.server_error()
