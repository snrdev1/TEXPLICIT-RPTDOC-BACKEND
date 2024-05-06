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

from app.routes import (
    account,
    admin_account,
    admin_users,
    chat,
    demo,
    feedback,
    menu,
    mydocuments,
    news,
    payment_gateway,
    report_generator,
    summary,
    usermanagement,
    users,
    pricing
)

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
app.register_blueprint(demo)
app.register_blueprint(pricing)
