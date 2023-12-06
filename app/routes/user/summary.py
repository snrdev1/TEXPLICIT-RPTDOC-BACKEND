"""
    All Summary-related routes
"""

import datetime

from flask import Blueprint, request, send_file
from flask_socketio import emit

from app import socketio
from app.config import Config
from app.auth.userauthorization import authorized
from app.services.summaryService import SummaryService
from app.utils.common import Common
from app.utils.messages import Messages
from app.utils.response import JSONEncoder, Response

summary = Blueprint("summary", __name__, url_prefix="/summary")


@summary.route("/itemized", methods=["POST"])
@authorized
def get_summary_by_ki_ids(logged_in_user):
    """Return a specific Knowledge Item's description's summary based on the Knowledge Item's id

    Returns:
        Summary of the Knowledge Item's description
    """
    try:
        request_body = request.get_json()
        request_params = request.args.to_dict()

        sentence_count = Common.get_field_value_or_default(
            request_params, "sentenceCount", Config.SUMMARY_DEFAULT_NUM_SENTENCES
        )

        ki_ids = Common.get_field_value_or_default(request_body, "kiIds", [])

        summary_response = []
        for summary, idx, title, success in SummaryService().itemized_summary_gpt(
            ki_ids, sentence_count
        ):
            print("ID: ", idx)
            # print("KI[IDX] : ", ki_ids[idx])
            print()
            response = {
                "data": {
                    "kiId": str(idx),
                    "title": title,
                    "summary": summary,
                },
                "message": Messages.OK_GENERATE_SUMMARY
                if success
                else Messages.NOT_FOUND_KI,
                "success": success,
            }
            print("Response : ", response)
            # print("KI summary : ", summary)
            if idx == 0:
                socketio.sleep(1)
            socketio.emit("server_emit_summary", response)
            print()
            # print(f'Emitted data! - {idx + 1}/{len(ki_ids)}')
            socketio.sleep(1)
            summary_response.append(response["data"])

        return Response.custom_response(
            summary_response, Messages.OK_GENERATE_SUMMARY, True, 200
        )

    except Exception as e:
        Common.exception_details("summary.py : get_summary_by_ki_ids", e)
        return Response.server_error()


@summary.route("/consolidated", methods=["POST"])
@authorized
def get_consolidated_summary_by_ki_ids(logged_in_user):
    """Return a specific Knowledge Item's description's summary based on the Knowledge Item's id

    Returns:
        Summary of the Knowledge Item's description
    """
    try:
        request_body = request.get_json()
        request_params = request.args.to_dict()

        sentence_count_itemized = Common.get_field_value_or_default(
            request_params,
            "sentenceCountItemized",
            Config.SUMMARY_DEFAULT_NUM_SENTENCES,
        )

        verbose = bool(
            Common.get_field_value_or_default(request_params, "verbose", False)
        )

        ki_ids = Common.get_field_value_or_default(request_body, "kiIds", [])

        num_required_words = Common.get_field_value_or_default(
            request_params, "numRequiredWords", 200
        )

        response = SummaryService.consolidated_summary(
            ki_ids, sentence_count_itemized, num_required_words, verbose
        )
        print(response["paragraphs"])

        return Response.custom_response(
            response, Messages.OK_GENERATE_SUMMARY, True, 200
        )

    except Exception as e:
        Common.exception_details("summary.py : get_consolidated_summary_by_ki_ids", e)
        return Response.server_error()


@summary.route("/highlights", methods=["POST"])
@authorized
def get_highlights_by_ki_ids(logged_in_user):
    try:
        request_body = request.get_json()

        ki_ids = Common.get_field_value_or_default(request_body, "kiIds", [])

        for key_phrase_obj, idx in SummaryService().highlights(ki_ids):
            response = {
                "data": {
                    "kiId": ki_ids[idx],
                    "sequenceNumber": idx + 1,
                    "highlights": key_phrase_obj["out"],
                },
                "message": Messages.OK_GENERATE_HIGHLIGHTS
                if key_phrase_obj["suc"]
                else Messages.NOT_FOUND_KI,
                "success": key_phrase_obj["suc"],
            }
            print()
            print("KI highlights : ", key_phrase_obj)
            if idx == 0:
                socketio.sleep(1)
            socketio.emit("server_emit_highlight", response)
            print()
            print(f"Emitted highlight! - {idx + 1}/{len(ki_ids)}")
            socketio.sleep(1)

        return Response.custom_response([], Messages.OK_GENERATE_HIGHLIGHTS, True, 200)

    except Exception as e:
        Common.exception_details("summary.py : get_highlights_by_ki_ids", e)
        return Response.server_error()


@summary.route("/consolidated/downloadppt", methods=["POST"])
@authorized
def get_consolidated_summary_ppt(logged_in_user):
    """Return a specific Knowledge Item's description's highlights based on the Knowledge Item's id

    Returns:
        Highlights of the Knowledge Item's description
    """
    try:
        request_body = request.get_json()
        request_params = request.args.to_dict()

        sentence_count_itemized = Common.get_field_value_or_default(
            request_params,
            "sentenceCountItemized",
            Config.SUMMARY_DEFAULT_NUM_SENTENCES,
        )

        # ki_ids = Common.get_field_value_or_default(
        #     request_body,
        #     "kiIds",
        #     []
        # )

        file_path = SummaryService().create_consolidated_ppt(request_body)

        # cache = Cache()
        # cache.clear()

        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"consolidated_summary_{datetime.datetime.utcnow().isoformat()}",
        )

    except Exception as e:
        Common.exception_details("summary.py : get_highlights_by_ki_ids", e)
        return Response.server_error()


@summary.route("/consolidated/downloaddocx", methods=["POST"])
@authorized
def get_consolidated_summary_docx(logged_in_user):
    try:
        request_body = request.get_json()
        request_params = request.args.to_dict()

        sentence_count_itemized = Common.get_field_value_or_default(
            request_params,
            "sentenceCountItemized",
            Config.SUMMARY_DEFAULT_NUM_SENTENCES,
        )

        file_path = SummaryService().create_consolidated_docx(request_body)

        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"consolidated_summary_{datetime.datetime.utcnow().isoformat()}",
        )

    except Exception as e:
        Common.exception_details("summary.py : get_highlights_by_ki_ids", e)
        return Response.server_error()


@summary.route("/consolidated/downloadexcel", methods=["POST"])
@authorized
def get_consolidated_summary_excel(logged_in_user):
    """Converts the consolidated summary content into an Excel file

    Returns:
        Summary of the Knowledge Item's description
    """
    try:
        request_body = request.get_json()
        request_params = request.args.to_dict()

        sentence_count_itemized = Common.get_field_value_or_default(
            request_params,
            "sentenceCountItemized",
            Config.SUMMARY_DEFAULT_NUM_SENTENCES,
        )

        file_path = SummaryService().create_consolidated_summary_excel(request_body)

        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"consolidated_summary_{datetime.datetime.utcnow().isoformat()}",
        )

    except Exception as e:
        Common.exception_details("summary.py : get_itemized_summary_excel", e)
        return Response.server_error()


@summary.route("/itemized/downloadppt", methods=["POST"])
@authorized
def get_itemized_summary_ppt(logged_in_user):
    """Return a specific Knowledge Item's description's summary based on the Knowledge Item's id

    Returns:
        Summary of the Knowledge Item's description
    """
    try:
        request_body = request.get_json()
        request_params = request.args.to_dict()

        sentence_count_itemized = Common.get_field_value_or_default(
            request_params,
            "sentenceCountItemized",
            Config.SUMMARY_DEFAULT_NUM_SENTENCES,
        )

        file_path = SummaryService().create_itemized_summary_ppt(request_body)

        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"itemized_summary_{datetime.datetime.utcnow().isoformat()}",
        )

    except Exception as e:
        Common.exception_details("summary.py : get_itemized_summary_ppt", e)
        return Response.server_error()


@summary.route("/itemized/downloaddocx", methods=["POST"])
@authorized
def get_itemized_summary_docx(logged_in_user):
    try:
        request_body = request.get_json()
        request_params = request.args.to_dict()

        sentence_count_itemized = Common.get_field_value_or_default(
            request_params,
            "sentenceCountItemized",
            Config.SUMMARY_DEFAULT_NUM_SENTENCES,
        )

        file_path = SummaryService().create_itemized_summary_docx(request_body)

        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"itemized_summary_{datetime.datetime.utcnow().isoformat()}",
        )

    except Exception as e:
        Common.exception_details("summary.py : get_itemized_summary_docx", e)
        return Response.server_error()


@summary.route("/itemized/downloadexcel", methods=["POST"])
@authorized
def get_itemized_summary_excel(logged_in_user):
    """Return a specific Knowledge Item's description's summary based on the Knowledge Item's id

    Returns:
        Summary of the Knowledge Item's description
    """
    try:
        request_body = request.get_json()
        request_params = request.args.to_dict()

        sentence_count_itemized = Common.get_field_value_or_default(
            request_params,
            "sentenceCountItemized",
            Config.SUMMARY_DEFAULT_NUM_SENTENCES,
        )

        file_path = SummaryService().create_itemized_summary_excel(request_body)

        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"itemized_summary_{datetime.datetime.utcnow().isoformat()}",
        )

    except Exception as e:
        Common.exception_details("summary.py : get_itemized_summary_excel", e)
        return Response.server_error()


@summary.route("/highlights/downloadppt", methods=["POST"])
@authorized
def get_highlights_summary_ppt(logged_in_user):
    """Return a specific Knowledge Item's description's summary based on the Knowledge Item's id

    Returns:
        Summary of the Knowledge Item's description
    """
    try:
        request_body = request.get_json()
        request_params = request.args.to_dict()

        sentence_count_itemized = Common.get_field_value_or_default(
            request_params,
            "sentenceCountItemized",
            Config.SUMMARY_DEFAULT_NUM_SENTENCES,
        )

        file_path = SummaryService().create_highlights_summary_ppt(request_body)

        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"highlights_summary_{datetime.datetime.utcnow().isoformat()}",
        )

    except Exception as e:
        Common.exception_details("summary.py : get_highlights_summary_ppt", e)
        return Response.server_error()


@summary.route("/highlights/downloaddocx", methods=["POST"])
@authorized
def get_highlights_summary_docx(logged_in_user):
    """Return a specific Knowledge Item's description's summary based on the Knowledge Item's id

    Returns:
        Summary of the Knowledge Item's description
    """
    try:
        request_body = request.get_json()
        request_params = request.args.to_dict()

        sentence_count_itemized = Common.get_field_value_or_default(
            request_params,
            "sentenceCountItemized",
            Config.SUMMARY_DEFAULT_NUM_SENTENCES,
        )

        file_path = SummaryService().create_highlights_summary_docx(request_body)

        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"highlights_summary_{datetime.datetime.utcnow().isoformat()}",
        )

    except Exception as e:
        Common.exception_details("summary.py : get_highlights_summary_docx", e)
        return Response.server_error()


@summary.route("/highlights/downloadexcel", methods=["POST"])
@authorized
def get_highlights_summary_excel(logged_in_user):
    """Return a specific Knowledge Item's description's summary based on the Knowledge Item's id

    Returns:
        Summary of the Knowledge Item's description
    """
    try:
        request_body = request.get_json()
        request_params = request.args.to_dict()

        sentence_count_itemized = Common.get_field_value_or_default(
            request_params,
            "sentenceCountItemized",
            Config.SUMMARY_DEFAULT_NUM_SENTENCES,
        )

        file_path = SummaryService().create_highlights_summary_excel(request_body)

        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"itemized_summary_{datetime.datetime.utcnow().isoformat()}",
        )

    except Exception as e:
        Common.exception_details("summary.py : get_highlights_summary_excel", e)
        return Response.server_error()
