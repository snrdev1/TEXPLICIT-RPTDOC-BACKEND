import os
import openai
from dotenv import load_dotenv

# load environment variables from .env file
load_dotenv()


class Config(object):
    ## 1. ENVIRONMENT variables

    # MONGO Database
    MONGO_CONNECTION_STRING = os.getenv(
        "MONGO_CONNECTION_STRING", "mongodb://localhost:27017"
    )

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")

    # SerpAPI
    SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
    SERPAPI_NO_CACHE = False

    # Google API
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
    GOOGLEBOOKS_API_KEY = os.getenv("GOOGLEBOOKS_API_KEY", "")

    # SCOPUS API for ScienceDirect
    SCOPUS_API_KEY = os.getenv("SCOPUS_API_KEY", "")

    # Spotify
    SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")

    # OPENAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    openai.api_key = OPENAI_API_KEY

    # Email Configuration
    MAIL_API_KEY = os.getenv("MAIL_API_KEY", "")
    MAIL_SENDER_EMAIL = os.getenv("MAIL_SENDER_EMAIL", "noreply@texplicit2.com")
    MAIL_SENDER_NAME = os.getenv("MAIL_SENDER_NAME", "Texplicit2 Admin")

    # Constant variable for environment
    GCP_PROD_ENV = eval(os.getenv("GCP_PROD_ENV", False))

    # REPORT GENERATION
    REPORT_DEBUG_MODE = False
    REPORT_ALLOW_DOWNLOADS = False

    REPORT_WEB_BROWSER = os.getenv("USE_WEB_BROWSER", "chrome")
    REPORT_LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ChatOpenAI")
    REPORT_FAST_LLM_MODEL = os.getenv("FAST_LLM_MODEL", "gpt-3.5-turbo-1106")
    REPORT_SMART_LLM_MODEL = os.getenv("SMART_LLM_MODEL", "gpt-4-1106-preview")
    REPORT_FAST_TOKEN_LIMIT = int(os.getenv("FAST_TOKEN_LIMIT", 2000))
    REPORT_SMART_TOKEN_LIMIT = int(os.getenv("SMART_TOKEN_LIMIT", 4000))
    REPORT_BROWSE_CHUNK_MAX_LENGTH = int(os.getenv("BROWSE_CHUNK_MAX_LENGTH", 8192))
    REPORT_SUMMARY_TOKEN_LIMIT = int(os.getenv("SUMMARY_TOKEN_LIMIT", 700))

    REPORT_TEMPERATURE = float(os.getenv("TEMPERATURE", "1"))

    REPORT_USER_AGENT = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
    )

    REPORT_MEMORY_BACKEND = os.getenv("MEMORY_BACKEND", "local")

    # MongoDB
    MONGO_DATABASE = "TEXPLICIT2_B2C_RPTDOC"
    MONGO_USER_MASTER_COLLECTION = "USER_MASTER"
    MONGO_DOCUMENT_MASTER_COLLECTION = "DOCUMENTS_MASTER"
    MONGO_CUSTOMER_FEEDBACK_COLLECTION = "CUSTOMER_FEEDBACK_COLLECTION"
    MONGO_EMBEDDING_MASTER_COLLECTION = "EMBEDDING_MASTER"
    MONGO_CHAT_MASTER_COLLECTION = "CHAT_MASTER"
    MONGO_MENU_MASTER_COLLECTION = "MENU_MASTER"
    MONGO_REPORTS_MASTER_COLLECTION = "REPORTS_MASTER"

    # Media related configurations
    ALLOWED_IMAGE_EXTENSIONS = ["jpg", "png", "jpeg"]
    USER_IMAGE_UPLOAD_FOLDER = os.getcwd() + "\\assets\\users"
    GROUP_IMAGE_UPLOAD_FOLDER = os.getcwd() + "\\assets\\groups"
    USER_DOCUMENTS_UPLOAD_FOLDER = os.getcwd() + "\\assets\\documents"

    # File paths for downloaded files
    USER_SUMMARY_DOCX_DOWNLOAD_FOLDER = os.getcwd() + "\\assets\\summary\\docx"
    USER_SUMMARY_XLSX_DOWNLOAD_FOLDER = os.getcwd() + "\\assets\\summary\\xlsx"
    USER_SUMMARY_PPTX_DOWNLOAD_FOLDER = os.getcwd() + "\\assets\\summary\\ppt"

    # User related folders and files
    USER_FOLDER = os.getcwd() + "\\assets\\users"
    USER_VECTORSTORE_PATH = "vectorstore\\db_faiss"

    # Vectorstore
    KNOWLEDGEITEM_VECTORSTORE_PATH = "app\\vectorstores\\knowledgeitems-faiss"

    # Summary
    SUMMARY_DEFAULT_NUM_SENTENCES = 10

    # GCP Bucket Names
    GCP_BUCKET_USERS = "texplicit-02-users"
    GCP_BUCKET_KNOWLEDGEITEMS = "texplicit-02-knowledgeitems"