from langchain_community.document_loaders import (
    GCSFileLoader,
    TextLoader,
    UnstructuredExcelLoader,
    UnstructuredPDFLoader,
    UnstructuredPowerPointLoader,
    UnstructuredWordDocumentLoader,
)
from langchain_community.document_loaders.csv_loader import UnstructuredCSVLoader
from app.utils.common import Common
from app.config import Config
from app.utils.llm_utils import split_text


class DocumentLoader:
    def __init__(self, user_id, file_id, file, filepath):
        self.user_id = user_id
        self.file_id = file_id
        self.file = file
        self.virtual_file_name = self.file["virtualFileName"]
        self.filepath = filepath
        self.file_extension = self.virtual_file_name.rsplit(".", 1)[-1]
        self.file_root = self.file["root"]

    def load_document(self):
        if Config.GCP_PROD_ENV:
            print("Loading document from gcs")
            data = self._load_document_from_gcs()
        else:
            data = self._load_document_from_local()

        if data:
            print("Found data!")
            splits = split_text(data)

            # Converting source files to virtual file name
            for split in splits:
                split.metadata["source"] = self.virtual_file_name

            if splits:
                from app.utils.vectorstore.base import VectorStore

                print("Adding vector index!")
                VectorStore().add_vectorindex(splits=splits, user_id=self.user_id)

    def _load_document_from_gcs(self):
        try:
            if self.file_root == f"/{self.user_id}/":
                blob = f"{self.user_id}/{self.virtual_file_name}"
            else:
                blob = f"{self.file_root[1:]}/{self.virtual_file_name}"

            loader = GCSFileLoader(
                project_name=Config.GCP_PROJECT_NAME,
                bucket=Config.GCP_BUCKET_USERS,
                blob=blob,
            )
            
            print("Config.GCP_PROJECT_NAME : ", Config.GCP_PROJECT_NAME)
            print("Config.GCP_BUCKET_USERS : ", Config.GCP_BUCKET_USERS)
            print("blob : ", blob)            
            
            print("Loader : ", loader)
            data = loader.load()

            print("Data from GCS : ", data)

            return data
        except Exception as e:
            Common.exception_details("DocumentLoader._load_document_from_gcs", e)
            return None

    def _load_document_from_local(self):
        try:
            # PDF
            if self.file_extension == "pdf":
                print("Loader : PDF")
                data = self.load_pdf()

            # WORD
            elif self.file_extension == "doc" or self.file_extension == "docx":
                print("Loader : DOCX")
                data = self.load_docx()

            # PPT
            elif self.file_extension == "pptx":
                print("Loader : PPTX")
                data = self.load_pptx()

            # TXT
            elif self.file_extension == "txt":
                print("Loader : TXT")
                data = self.load_txt()

            # CSV
            elif self.file_extension == "csv":
                print("Loader : CSV")
                data = self.load_csv()

            elif self.file_extension == "xls" or self.file_extension == "xlsx":
                print("Loader : Excel")
                data = self.load_excel()

            else:
                data = None

            return data

        except Exception as e:
            print(e)
            return None

    def load_pdf(self):
        loader = UnstructuredPDFLoader(self.filepath)
        docs = loader.load()

        return docs

    def load_docx(self):
        loader = UnstructuredWordDocumentLoader(self.filepath)
        docs = loader.load()

        return docs

    def load_pptx(self):
        loader = UnstructuredPowerPointLoader(self.filepath)
        docs = loader.load()

        return docs

    def load_txt(self):
        loader = TextLoader(self.filepath)
        docs = loader.load()

        return docs

    def load_excel(self):
        loader = UnstructuredExcelLoader(self.filepath, mode="elements")
        docs = loader.load()

        return docs

    def load_csv(self):
        loader = UnstructuredCSVLoader(self.filepath, mode="elements")
        docs = loader.load()

        return docs
