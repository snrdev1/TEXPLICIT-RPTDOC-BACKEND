from .admin.account import admin_account
from .admin.users import admin_users
from .user.account import account
from .user.chat import chat
from .user.demo import demo
from .user.feedback import feedback
from .user.menu import menu
from .user.mydocuments import mydocuments
from .user.news import news
from .user.paymentgateway import payment_gateway
from .user.report_generator import report_generator
from .user.summary import summary
from .user.usermanagement import usermanagement
from .user.users import users
from .user.pricing import pricing

__all__ = [
    "account",
    "chat",
    "demo",
    "feedback",
    "menu",
    "mydocuments",
    "news",
    "payment_gateway",
    "report_generator",
    "summary",
    "usermanagement",
    "users",
    "pricing",
    "admin_account",
    "admin_users",
]
