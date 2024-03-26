"""
    All Documents related routes
"""

import datetime
import io
import os
import threading

from flask import Blueprint, request, send_file

from app import socketio
from app.auth.userauthorization import authorized
from app.config import Config
from app.services.my_documents_service import MyDocumentsService
from app.utils import Subscription, Messages, Common
from app.utils import Response, files_and_folders
from app.utils.vectorstore.base import VectorStore

mydocuments = Blueprint("mydocuments", __name__, url_prefix="/my-documents")


@mydocuments.route("/create-folder", methods=["POST"])
@authorized
def create_folder(logged_in_user):
    try:
        user_id = logged_in_user.get("_id")
        request_body = request.get_json()
        path = request_body.get("path")
        folder_name = request_body.get("folderName")
        # print("Folder name : ", folder_name)
        response = MyDocumentsService().create_folder(folder_name, path, user_id)
        print(response)
        if response:
            return Response.custom_response([], Messages.OK_FOLDER_CREATED, True, 200)
        else:
            return Response.custom_response([], Messages.OK_FOLDER_EXISTS, True, 200)

    except Exception as e:
        Common.exception_details("mydocuments.py : create_folder", e)


@mydocuments.route("/delete-folder/<string:_id>", methods=["DELETE"])
@authorized
def delete_folder(logged_in_user, _id):
    """
    Delete a folder and all the files and sub folders in it

    Args:
            logged_in_user: Logged-In User object from authorization decorator.

    Returns:
        A custom response

    """
    try:
        user_id = logged_in_user["_id"]
        response = MyDocumentsService().delete_folder(_id, user_id)

        print("Response: ", response)

        if response:
            return Response.custom_response(
                response, Messages.OK_FOLDER_DELETED, True, 200
            )
        else:
            return Response.custom_response(
                response, Messages.ERROR_FOLDER_DELETE, False, 400
            )

    except Exception as e:
        Common.exception_details("mydocuments.py : delete_folder", e)
        return Response.server_error()


@mydocuments.route("/folder-content/<string:_id>", methods=["GET"])
@authorized
def folder_content(logged_in_user, _id):
    """
    Display all documents inside folder

    Args:
        logged_in_user: Logged-In User object from authorization decorator.

    Returns:
        A custom response
    """
    try:
        # print("FOLDER Id : ", _id)
        user_id = logged_in_user["_id"]
        docs = MyDocumentsService().get_folder_contents(user_id, _id)

        if docs:
            return Response.custom_response(docs, Messages.OK_FILE_RETRIEVE, True, 200)
        else:
            return Response.custom_response(
                [], Messages.ERROR_FILE_RETRIEVE, False, 200
            )

    except Exception as e:
        Common.exception_details("mydocuments.py : get_documents", e)
        return Response.server_error()


@mydocuments.route("/upload-documents", methods=["POST"])
@authorized
def upload_documents(logged_in_user):
    """
    The upload_document function posts the details of a document to the server

    Args:
        logged_in_user: Logged-In User object from authorization decorator.

    Returns:
        A custom response
    """
    try:
        files = request.files.getlist("files")
        path = request.form.get("path")
        upload_id = request.form.get("uploadId")
        user_id = logged_in_user["_id"]
          
        # Check User Subscription
        subscription = Subscription(user_id)
        subscription_validity = subscription.check_subscription_duration()
        if not subscription_validity:
            return Response.subscription_invalid()
        
        # Check if under current subscription the new files can be uploaded
        upload_files_size = files_and_folders.get_size(files)
        subscription_validity = subscription.check_subscription_document(upload_files_size)
        if not subscription_validity:
            return Response.subscription_invalid(Messages.INVALID_SUBSCRIPTION_DOCUMENT)

        # Upload files
        MyDocumentsService.upload_documents(logged_in_user, files, path, upload_id)

        return Response.custom_response([], Messages.OK_FILE_UPLOAD_STARTED, True, 200)

    except Exception as e:
        Common.exception_details("mydocuments.py : upload_documents", e)
        return Response.server_error()


@mydocuments.route("/display-documents", methods=["GET"])
@authorized
def get_documents(logged_in_user):
    """
    Display all uploaded documents

    Args:
        logged_in_user: Logged-In User object from authorization decorator.

    Returns:
        A custom response
    """
    try:
        folder_name = request.args.get("root")
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
        user_id = logged_in_user["_id"]
        docs = MyDocumentsService().get_all_files(user_id, folder_name, limit, offset)

        if docs and len(docs) > 0:
            return Response.custom_response(
                docs[0], Messages.OK_FILE_RETRIEVE, True, 200
            )
        else:
            return Response.custom_response(
                [], Messages.ERROR_FILE_RETRIEVE, False, 200
            )

    except Exception as e:
        Common.exception_details("mydocuments.py : get_documents", e)
        return Response.server_error()


@mydocuments.route("/display-folders", methods=["GET"])
@authorized
def get_folders(logged_in_user):
    """
    Display all folders

    Args:
        logged_in_user: Logged-In User object from authorization decorator.

    Returns:
        A custom response
    """
    try:
        user_id = logged_in_user["_id"]
        folders = MyDocumentsService().get_all_folders(user_id)

        return Response.custom_response(folders, Messages.OK_FOLDER_RETRIEVE, True, 200)

    except Exception as e:
        Common.exception_details("mydocuments.py : get_folders", e)
        return Response.server_error()


@mydocuments.route("/move-files", methods=["PUT"])
@authorized
def move_file(logged_in_user):
    try:
        request_body = request.get_json()
        file = Common.get_field_value_or_default(request_body, "file", None)
        folder = Common.get_field_value_or_default(request_body, "folder", None)
        # print("FILE : ", file)
        # print(file["_id"], "\t", folder["_id"])
        # print("FOLDER : ", folder)

        response = MyDocumentsService().move_file_to_folder(
            file, folder, logged_in_user["_id"]
        )

        if response:
            return Response.custom_response([], Messages.OK_FILE_MOVED, True, 200)
        else:
            return Response.custom_response([], Messages.ERROR_FILE_MOVE, False, 400)

    except Exception as e:
        Common.exception_details("mydocuments.py : move_file", e)
        return Response.server_error()


@mydocuments.route("/<string:document_id>", methods=["GET"])
@authorized
def get_document(logged_in_user, document_id):
    try:
        response = MyDocumentsService().get_file(document_id)

        print("Response : ", response)

        if response:
            return Response.custom_response(
                response, Messages.OK_FILE_RETRIEVE, True, 200
            )
        else:
            return Response.custom_response(
                [], Messages.ERROR_FILE_RETRIEVE, False, 400
            )

    except Exception as e:
        Common.exception_details("mydocuments.py : get_document", e)
        return Response.server_error()


@mydocuments.route("/<string:file_id>", methods=["DELETE"])
@authorized
def delete_document(logged_in_user, file_id):
    try:
        user_id = logged_in_user["_id"]

        vectorstore_obj = VectorStore(user_id)
        t1 = threading.Thread(
            target=vectorstore_obj.delete_vectorindex, args=(file_id,)
        )
        t1.start()

        delete_response = MyDocumentsService().delete_file(file_id, user_id)

        if delete_response:
            return Response.custom_response(
                delete_response, Messages.OK_MY_DOCUMENT_DELETED, True, 200
            )
        else:
            return Response.custom_response(
                delete_response, Messages.ERROR_MY_DOCUMENT_DELETED, False, 400
            )

    except Exception as e:
        Common.exception_details("mydocuments.py : delete_file", e)
        return Response.server_error()


@mydocuments.route("", methods=["DELETE"])
@authorized
def delete_mutliple_docs(logged_in_user):
    try:
        user_id = logged_in_user["_id"]
        params = request.args.getlist("filesIds")
        print("Parameters : ", params)
        response = MyDocumentsService().delete_files(params, user_id)
        # response = 1
        print("Response: ", response)

        if response:
            return Response.custom_response(
                response, Messages.OK_MY_DOCUMENT_DELETED, True, 200
            )
        else:
            return Response.custom_response(
                response, Messages.ERROR_MY_DOCUMENT_DELETED, False, 400
            )

    except Exception as e:
        Common.exception_details("mydocuments.py : delete_mutliple_docs", e)
        return Response.server_error()


@mydocuments.route("/summary/itemized", methods=["POST"])
@authorized
def my_documents_itemized_summary(logged_in_user):
    summary_response = []
    try:
        request_body = request.get_json()
        request_params = request.args.to_dict()

        sentence_count = Common.get_field_value_or_default(
            request_params, "sentenceCount", Config.SUMMARY_DEFAULT_NUM_SENTENCES
        )

        document_ids = Common.get_field_value_or_default(
            request_body, "documentIds", []
        )

        for (
            summary,
            idx,
            title,
            date,
            success,
        ) in MyDocumentsService().my_documents_summarize_gpt(
            document_ids, sentence_count
        ):
            response = {
                "data": {
                    "documentId": document_ids[idx],
                    "sequenceNumber": idx + 1,
                    "summary": summary,
                    "title": title,
                    "createdOn": date,
                },
                "message": (
                    Messages.OK_GENERATE_SUMMARY if success else Messages.NOT_FOUND_KI
                ),
                "success": success,
            }
            print()
            print("Document summary : ", summary)
            print()
            print("Document title : ", title)
            if idx == 0:
                socketio.sleep(1)
            socketio.emit("server_emit_document_summary", response)
            print()
            print(f"Emitted data! - {idx + 1}/{len(document_ids)}")
            socketio.sleep(1)
            summary_response.append(
                {
                    "fileId": document_ids[idx],
                    "itemizedSummary": summary,
                    "title": title,
                    "createdOn": date,
                }
            )

        return Response.custom_response(
            summary_response, Messages.OK_GENERATE_SUMMARY, True, 200
        )

    except Exception as e:
        Common.exception_details("summary.py : my_documents_itemized_summary", e)
        return Response.server_error()


@mydocuments.route("/summary/highlights", methods=["POST"])
@authorized
def get_highlights_by_file_ids(logged_in_user):
    try:
        print(request)
        request_body = request.get_json()
        request_params = request.args.to_dict()

        print("Request Body : ", request_body)
        print("Request params : ", request_params)

        file_ids = Common.get_field_value_or_default(request_body, "fileIds", [])

        for key_phrase_obj, title, idx in MyDocumentsService().highlights(file_ids):
            response = {
                "data": {
                    "fileId": file_ids[idx],
                    "title": title,
                    "sequenceNumber": idx + 1,
                    "highlights": key_phrase_obj["out"],
                },
                "message": (
                    Messages.OK_GENERATE_HIGHLIGHTS
                    if key_phrase_obj["suc"]
                    else Messages.NOT_FOUND_KI
                ),
                "success": key_phrase_obj["suc"],
            }

            if idx == 0:
                socketio.sleep(1)
            socketio.emit("server_emit_highlight", response)
            print()
            print(f"Emitted highlight! - {idx + 1}/{len(file_ids)}")
            socketio.sleep(1)

        return Response.custom_response([], Messages.OK_GENERATE_HIGHLIGHTS, True, 200)

    except Exception as e:
        Common.exception_details("mydocuments.py : get_highlights_by_file_ids", e)
        return Response.server_error()


@mydocuments.route("/summary/itemized/downloadppt", methods=["POST"])
@authorized
def get_my_documents_itemized_summary_ppt(logged_in_user):
    """Return a document's description's summary based on the file's id

    Returns:
        Summary of the file's description
    """
    try:
        request_body = request.get_json()
        request_params = request.args.to_dict()

        sentence_count_itemized = Common.get_field_value_or_default(
            request_params,
            "sentenceCountItemized",
            Config.SUMMARY_DEFAULT_NUM_SENTENCES,
        )
        print("Request body : ", request_body)

        file_path = MyDocumentsService().create_itemized_summary_ppt(request_body)

        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"itemized_summary_{datetime.datetime.utcnow().isoformat()}",
        )

    except Exception as e:
        Common.exception_details(
            "mydocuments.py : get_my_documents_itemized_summary_ppt", e
        )
        return Response.server_error()


@mydocuments.route("/summary/itemized/downloadexcel", methods=["POST"])
@authorized
def get_my_documents_itemized_summary_excel(logged_in_user):
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

        file_path = MyDocumentsService().create_itemized_summary_excel(request_body)

        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"itemized_summary_{datetime.datetime.utcnow().isoformat()}",
        )

    except Exception as e:
        Common.exception_details(
            "mydocuments.py : get_my_documents_itemized_summary_excel", e
        )
        return Response.server_error()


@mydocuments.route("/summary/highlights/downloadppt", methods=["POST"])
@authorized
def get_my_documents_highlights_summary_ppt(logged_in_user):
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

        file_path = MyDocumentsService().create_highlights_summary_ppt(request_body)

        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"highlights_summary_{datetime.datetime.utcnow().isoformat()}",
        )

    except Exception as e:
        Common.exception_details(
            "mydocuments.py : get_my_documents_highlights_summary_ppt", e
        )
        return Response.server_error()


@mydocuments.route("/summary/highlights/downloadexcel", methods=["POST"])
@authorized
def get_my_documents_highlights_summary_excel(logged_in_user):
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

        file_path = MyDocumentsService().create_highlights_summary_excel(request_body)

        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"highlights_summary_{datetime.datetime.utcnow().isoformat()}",
        )

    except Exception as e:
        Common.exception_details(
            "mydocuments.py : get_my_documents_highlights_summary_excel", e
        )
        return Response.server_error()


@mydocuments.route("/download/<virtual_document_name>", methods=["GET"])
@authorized
def my_documents_download(logged_in_user, virtual_document_name):
    try:
        file, name = MyDocumentsService().get_file_contents(virtual_document_name)
        if file and name:
            return send_file(file, as_attachment=True, download_name=name)
        else:
            return Response.custom_response([], Messages.ERROR_FILE_RETRIEVE, False, 400)

    except Exception as e:
        Common.exception_details("mydocuments.py : my_documents_download", e)
        return Response.server_error()


@mydocuments.route("/share", methods=["POST"])
@authorized
def share_document(logged_in_user):
    try:
        request_params = request.get_json()

        # Required parameters
        required_params = ["documentIds"]

        # Check if all required parameters are present in the request params
        if not all(
            (key in request_params) and (request_params[key] not in [None, ""])
            for key in required_params
        ):
            return Response.missing_parameters()

        document_ids = request_params.get("documentIds")
        targets_user_ids = request_params.get("usersWithAccess", [])
        share_type = request_params.get("shareType", "internal")
        email_ids = request_params.get("emailIds", [])
        subject = request_params.get("subject", "")
        message = request_params.get("message", "")

        user_id = logged_in_user["_id"]

        # Add the target_user_id to the "shared" field of the document
        my_documents_service = MyDocumentsService()
        if share_type == "internal":
            response = my_documents_service.modify_document_shared_users(
                user_id, document_ids, targets_user_ids
            )
        else:
            response = my_documents_service.share_document_via_email(
                user_id, document_ids, email_ids, subject, message
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


@mydocuments.route("/rename/<string:_id>", methods=["PUT"])
@authorized
def rename_docs(logged_in_user, _id):
    try:
        user_id = str(logged_in_user["_id"])
        request_params = request.get_json()
        rename_value = request_params["renameValue"]
        
        # Check if rename_value is present in the request params
        if rename_value == "" or rename_value == None or rename_value == []:
            return Response.missing_parameters()

        response = MyDocumentsService().rename_document(_id, rename_value, user_id)

        if response:
            return Response.custom_response(
                response, Messages.OK_DOCUMENT_RENAMED, True, 200
            )
        else:
            return Response.custom_response(
                response, Messages.ERROR_DOCUMENT_RENAMED, False, 400
            )

    except Exception as e:
        Common.exception_details("mydocuments.py : rename_docs", e)
        return Response.server_error()
