from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from .config import Config


def create_app():
    """
    The create_app function wraps the creation of a new Flask object, and returns it after it's loaded up with
    configuration settings using app.config.from_object(Config). (For those unfamiliar, a decorator is just a fancy
    way to wrap a function and modify its behavior.)

    Args:

    Returns:
        The app object
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    # Handling CORS
    CORS(app)

    # SocketIO documentation : https://flask-socketio.readthedocs.io/en/latest/api.html
    socketio = SocketIO(
        app, cors_allowed_origins="*", async_mode="threading", async_handlers=True
    )

    return app, socketio


app, socketio = create_app()

from app.routes.admin.account import admin_account
from app.routes.admin.users import admin_users
from app.routes.user.account import account
from app.routes.user.chat import chat
from app.routes.user.feedback import feedback
from app.routes.user.menu import menu
from app.routes.user.mydocuments import mydocuments
from app.routes.user.news import news
from app.routes.user.report_generator import report_generator
from app.routes.user.summary import summary
from app.routes.user.usermanagement import usermanagement
from app.routes.user.users import users
from app.routes.user.paymentgateway import payment_gateway

# Admin routes
app.register_blueprint(admin_account)
app.register_blueprint(admin_users)

# User routes
app.register_blueprint(account)
app.register_blueprint(chat)
app.register_blueprint(feedback)
app.register_blueprint(mydocuments)
app.register_blueprint(news)
app.register_blueprint(summary)
app.register_blueprint(usermanagement)
app.register_blueprint(users)
app.register_blueprint(menu)
app.register_blueprint(report_generator)
app.register_blueprint(payment_gateway)
