"""
    All news related routes
"""

from flask import Blueprint, request

from app import socketio
from app.auth.userauthorization import authorized
from app.services.news_service import NewsService
from app.utils.common import Common
from app.utils.messages import Messages
from app.utils import Response

news = Blueprint("news", __name__)


@news.route("/get-news", methods=["GET"])
def new_get_news():
    """
    The new_get_news function is a socketio function that accepts news query parameters and returns the results to the client.

    Returns:
        A custom response
    """
    try:
        request_params = request.args
        query = request_params.get("query")
        engine = int(request_params.get("engine", 0))
        count = int(request_params.get("count", 10))
        start = int(request_params.get("start", 0))
        random_id = request_params.get("randomId")

        print("Random ID : ", random_id)

        search_results = NewsService.get_search_data(query, engine, count, start)
        news_event = random_id + "_" + query + "_news"
        print("Event : ", news_event)

        for data in NewsService.get_news(search_results, count):
            socketio.emit(news_event, data)
            print("Emitted data!")

        return Response.custom_response([], Messages.OK_FOUND_NEWS, True, 200)

    except Exception as e:
        Common.exception_details("news.py : get_news", e)


@news.route("/news-document", methods=["POST"])
@authorized
def convert_news_to_docx(logged_in_user):
    try:
        user_id = logged_in_user["_id"]
        request_params = request.get_json()
                
        # Required parameters
        required_params = ["news"]

        # Check if all required parameters are present in the request params
        if not any(
            (key in request_params) and (request_params[key] not in [None, ""])
            for key in required_params
        ):
            return Response.missing_parameters()
        
        news = request_params.get("news")
        folder = request_params.get("folder", None)
        response = NewsService.save_news_as_document(user_id, news, folder)

        if response:
            return Response.custom_response([], Messages.OK_NEWS_SHARED, True, 200)
        else:
            return Response.custom_response([], Messages.ERROR_NEW_SHARED, False, 400)

    except Exception as e:
        Common.exception_details("news.py : convert_news_to_docx", e)
