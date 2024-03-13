"""
    All Report Generator related routes
"""

import io
import os
import threading

from flask import Blueprint, request, send_file

from app.config import Config

from ...auth import authorized
from ...services import reportGeneratorService as ReportGeneratorService
from ...utils import Common, Messages, Production, Response, Subscription, Enumerator
from ...utils.files_and_folders import get_report_audio_path

report_generator = Blueprint(
    "report_generator", __name__, url_prefix="/report")


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
        report_type = request_params.get("report_type", Enumerator.ReportType.ResearchReport.value)
        source = request_params.get("source", "external")
        format = request_params.get("format", "pdf")
        report_generation_id = request_params.get("report_generation_id", None)
        websearch = request_params.get("websearch", False)
        subtopics = request_params.get("subtopics", [])
                
        # Check if the report_type is valid
        if report_type not in [item.value for item in Enumerator.ReportType]:
            return Response.custom_response([], Messages.INVALID_REPORT_TYPE, False, 400) 

        # Check subscription validity before generating report
        subscription = Subscription(user_id)
        subscription_validity = subscription.check_subscription_duration() and subscription.check_subscription_report(report_type)
        if not subscription_validity:
            return Response.subscription_invalid()

        # Getting response and emitting it in a separate non-blocking thread
        t1 = threading.Thread(
            target=ReportGeneratorService.report_generate,
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

        reports = ReportGeneratorService.get_all_reports_from_db(
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

        reports = ReportGeneratorService.get_pending_reports_from_db(
            user_id, limit, offset, source, format, report_type
        )

        return Response.custom_response(reports, Messages.OK_REPORTS_FOUND, True, 200)

    except Exception as e:
        Common.exception_details(
            "report-generator.py : retrieve_pending_reports", e)
        return Response.server_error()


@report_generator.route("/download/<reportid>", methods=["GET"])
@authorized
def download_report(logged_in_user, reportid):
    try:
        user_id = str(logged_in_user["_id"])

        report_document = ReportGeneratorService.get_report_from_db(reportid)
        if report_document:
            if user_id != str(report_document["createdBy"]["_id"]):
                return Response.custom_response([], Messages.UNAUTHORIZED, False, 401)

            file_bytes, file_name = ReportGeneratorService.get_file_contents(
                report_document)

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

        report_document = ReportGeneratorService.get_report_from_db(reportid)
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
                download_name=ReportGeneratorService.get_report_audio_download_filename(
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
                    download_name=ReportGeneratorService.get_report_audio_download_filename(
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

        report_document = ReportGeneratorService.get_failed_reports_from_db(
            user_id)
        return Response.custom_response(report_document, "", True, 200)

    except Exception as e:
        Common.exception_details("mydocuments.py : get_failed_reports", e)
        return Response.server_error()


@report_generator.route("/failed/delete", methods=["DELETE"])
@authorized
def clear_failed_reports(logged_in_user):
    try:
        user_id = str(logged_in_user["_id"])

        report_document = ReportGeneratorService.delete_failed_reports_from_db(
            user_id).get("delete_count", 0)
        return Response.custom_response(
            [{"delete_count": report_document}
             ], Messages.OK_REPORTS_DELETED, True, 200
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

        response = ReportGeneratorService.share_reports_via_email(
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
