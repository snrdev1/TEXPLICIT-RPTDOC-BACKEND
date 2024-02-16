import os
import openai
from dotenv import load_dotenv
import razorpay

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

    # OPENAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    openai.api_key = OPENAI_API_KEY

    # Email Configuration
    MAIL_API_KEY = os.getenv("MAIL_API_KEY", "")
    MAIL_SENDER_EMAIL = os.getenv("MAIL_SENDER_EMAIL", "noreply@texplicit2.com")
    MAIL_SENDER_NAME = os.getenv("MAIL_SENDER_NAME", "Texplicit2 Admin")

    # Constant variable for environment
    GCP_PROD_ENV = eval(os.getenv("GCP_PROD_ENV", "False"))
    TESTING = eval(os.getenv("TESTING", "False"))
    
    # LLM models used
    FAST_LLM_MODEL = os.getenv("FAST_LLM_MODEL", "gpt-3.5-turbo-1106")
    SMART_LLM_MODEL = os.getenv("SMART_LLM_MODEL", "gpt-4-1106-preview")

    # REPORT GENERATION
    REPORT_DEBUG_MODE = False
    REPORT_ALLOW_DOWNLOADS = False

    REPORT_WEB_SCRAPER = os.getenv("USE_WEB_SCRAPER", "newspaper") # selenium / newspaper
    REPORT_WEB_BROWSER = os.getenv("USE_WEB_BROWSER", "chrome")
    REPORT_LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ChatOpenAI")
    REPORT_FAST_TOKEN_LIMIT = int(os.getenv("FAST_TOKEN_LIMIT", 2000))
    REPORT_SMART_TOKEN_LIMIT = int(os.getenv("SMART_TOKEN_LIMIT", 4000))
    REPORT_BROWSE_CHUNK_MAX_LENGTH = int(os.getenv("BROWSE_CHUNK_MAX_LENGTH", 8192))
    REPORT_SUMMARY_TOKEN_LIMIT = int(os.getenv("SUMMARY_TOKEN_LIMIT", 700))
    REPORT_TEMPERATURE = float(os.getenv("TEMPERATURE", "0.55"))
    REPORT_USER_AGENT = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
    )
    REPORT_MEMORY_BACKEND = os.getenv("MEMORY_BACKEND", "local")
    REPORT_TOTAL_WORDS = int(os.getenv('TOTAL_WORDS', 1000))
    REPORT_FORMAT = os.getenv('REPORT_FORMAT', "APA")
    REPORT_MAX_ITERATIONS = int(os.getenv('MAX_ITERATIONS', 3))
    REPORT_AGENT_ROLE = os.getenv('AGENT_ROLE', None)
    REPORT_MAX_SEARCH_RESULTS_PER_QUERY = int(os.getenv('MAX_SEARCH_RESULTS_PER_QUERY', 5))
    REPORT_TOTAL_WORDS = int(os.getenv('TOTAL_WORDS', 1000))
    REPORT_SEARCH_RETRIEVER = os.getenv("SEARCH_RETRIEVER", "serpapi")

    # MongoDB
    MONGO_DATABASE = "TEXPLICIT2_B2C_RPTDOC"
    MONGO_USER_MASTER_COLLECTION = "USER_MASTER"
    MONGO_DOCUMENT_MASTER_COLLECTION = "DOCUMENTS_MASTER"
    MONGO_CUSTOMER_FEEDBACK_COLLECTION = "CUSTOMER_FEEDBACK_COLLECT"
    MONGO_MENU_MASTER_COLLECTION = "MENU_MASTER"
    MONGO_CHAT_MASTER_COLLECTION = "CHAT_MASTER"
    MONGO_REPORTS_MASTER_COLLECTION = "REPORTS_MASTER"
    MONGO_PAYMENT_HISTORY_COLLECTION = "PAYMENT_HISTORY"
    MONGO_DEMO_REQUEST_COLLECTION = "DEMO_MASTER"

    # Media related configurations
    ALLOWED_IMAGE_EXTENSIONS = ["jpg", "png", "jpeg"]
    USER_IMAGE_UPLOAD_FOLDER = os.getcwd() + "\\assets\\users"
    USER_DOCUMENTS_UPLOAD_FOLDER = os.getcwd() + "\\assets\\documents"

    # File paths for downloaded files
    USER_SUMMARY_DOCX_DOWNLOAD_FOLDER = os.getcwd() + "\\assets\\summary\\docx"
    USER_SUMMARY_XLSX_DOWNLOAD_FOLDER = os.getcwd() + "\\assets\\summary\\xlsx"
    USER_SUMMARY_PPTX_DOWNLOAD_FOLDER = os.getcwd() + "\\assets\\summary\\ppt"

    # User related folders and files
    USER_FOLDER = os.getcwd() + "\\assets\\users"
    USER_MY_DATASOURCES_FOLDER = "mydatasources"
    USER_VECTORSTORE_PATH = "vectorstore\\db_faiss"

    # Summary
    SUMMARY_DEFAULT_NUM_SENTENCES = 10

    # GCP Bucket Names
    GCP_BUCKET_USERS = "texplicit-rw-users"
    
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", 'stoked-forest-413805')  # Replace with your GCP project ID
    GCP_PROJECT_NAME = os.getenv("GCP_PROJECT_NAME", "My First Project")  # Replace with your GCP project Name
    GCP_SERVICE_ACCOUNT_FILE = os.getenv("GCP_SERVICE_ACCOUNT_FILE")
    # GCP_REPORT_QUEUE = os.getenv("GCP_REPORT_QUEUE", 'texplicit02-reports')  # Replace with your queue name
    # GCP_REPORT_QUEUE_LOCATION = os.getenv("GCP_REPORT_QUEUE_LOCATION", 'asia-south1')  # Replace with your queue location
    # GCP_REPORT_CLOUD_RUN_URL = os.getenv("GCP_REPORT_CLOUD_RUN_URL", 'https://texplicit.com/api/report/execute_report') # GCP Cloud Run url for report execution from google cloud task
    
    # Payment Gateway
    
    # Razorpay
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
    # Initialize Razorpay client with your API keys
    razorpay_client = razorpay.Client(
        auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    )
    
    # Admin email details
    ADMIN_EMAIL_ADDRESSES = [
        {"name": "Prabir Aditya", "email": "prabir@springandriver.com"},
        {"name": "Prateep Kumar Guha", "email": "prateep.guha@springandriver.com"}
    ]