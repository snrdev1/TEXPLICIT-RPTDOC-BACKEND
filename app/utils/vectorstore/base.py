import os

from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate

from app.config import Config
from app.services.myDocumentsService import MyDocumentsService
from app.utils.common import Common
from app.utils.production import Production
from app.utils.vectorstore.retrievers import Retriever

from ..llm_utils import get_embeddings, load_fast_llm
from .prompts import get_document_prompt


class VectorStore:

    def delete_vectorindex(self, file_id, user_id):
        """
        The function `delete_vectorindex` deletes a vector index for a given file and user.

        Args:
          file_id: The `file_id` parameter is the unique identifier of the file that needs to be deleted
        from the vector index.
          user_id: The user ID is a unique identifier for a user in the system. It is used to identify
        which user's vector index needs to be deleted.
        """
        try:
            print("File id : ", file_id)
            file = MyDocumentsService().get_file(file_id)

            if Config.GCP_PROD_ENV:
                VectorStore._delete_vectorindex_production(file, user_id)
            else:
                VectorStore._delete_vectorindex_testing(file, user_id)

        except Exception as e:
            Common.exception_details("VectorStore.delete_vectorindex", e)

    def get_document_chat_response(self, user_id, query):
        try:
            embeddings = get_embeddings()
            llm = load_fast_llm()
            prompt = get_document_prompt()
            db = VectorStore().get_document_vectorstore(user_id, embeddings)
            retriever = Retriever(user_id, query, llm, prompt, db)
            response = retriever.vectorstore_retriever()
            
            # result = response["result"] or None
            # sources = (
            #     list(
            #         set(
            #             [
            #                 document.metadata["source"]
            #                 for document in response["source_documents"]
            #             ]
            #         )
            #     )
            #     or []
            # )
            # print("Sources : ", sources)

            # files = MyDocumentsService().get_all_files_by_virtual_name(user_id, sources)
            # original_sources = [file["originalFileName"] for file in files]

            return {"response": response, "sources": []}

        except Exception as e:
            Common.exception_details("VectorStore.get_document_chat_response", e)
            return None

    def get_document_vectorstore(self, user_id, embeddings=None):
        try:
            if Config.GCP_PROD_ENV:
                db = VectorStore._get_user_faiss_db_from_gcs(user_id)

            else:
                db_path = VectorStore._get_document_vectorstore_path(user_id)
                db = FAISS.load_local(db_path, embeddings)

            return db

        except Exception as e:
            return None

    def add_vectorindex(self, splits, user_id):
        try:
            embeddings = get_embeddings()
            db = FAISS.from_documents(splits, embeddings)
            db_path = VectorStore._get_document_vectorstore_path(user_id)

            if Config.GCP_PROD_ENV:
                bucket = Production.get_users_bucket()
                VectorStore._add_vectorindex_production(user_id, db, bucket)
            else:
                VectorStore._add_vectorindex_testing(user_id, db, embeddings, db_path)

        except Exception as e:
            Common.exception_details("Vectorstore.add_vectorindex", e)

    @staticmethod
    def _get_document_vectorstore_path(user_id):
        """
        The function `_get_document_vectorstore_path` returns the path to the document vector store for
        a given user ID.

        Args:
          user_id: The user_id parameter is a unique identifier for a user. It is used to create a
        folder path specific to that user and retrieve the document vectorstore path for that user.

        Returns:
          the path to the document vectorstore for a given user.
        """
        try:
            db_path = os.path.join(
                os.path.join(Config.USER_FOLDER, user_id), Config.USER_VECTORSTORE_PATH
            )

            return db_path

        except Exception as e:
            Common.exception_details("Vectorstore._get_document_vectorstore_path", e)
            return None

    @staticmethod
    def _get_user_faiss_db_from_gcs(user_id):
        """
        The function `_get_user_faiss_db_from_gcs` retrieves a Faiss database object for a specific user
        from Google Cloud Storage (GCS).

        Args:
          user_id: The `user_id` parameter is a unique identifier for a user. It is used to locate the
        user's folder and retrieve the Faiss database file associated with that user.

        Returns:
          the `db` object, which is the deserialized FAISS index loaded from a pickled object stored in
        Google Cloud Storage (GCS). If there is an exception during the process, it will return `None`.
        """
        try:
            embeddings = get_embeddings()
            bucket = Production.get_users_bucket()
            user_folder_path = f"{user_id}/"
            vectorstore_path = f"{user_folder_path}vectorstore/db_faiss/"

            blob = bucket.blob(vectorstore_path + "index.pkl")

            # Download the pickled object as bytes from GCS
            serialized_bytes = blob.download_as_bytes()

            # Load the index
            db = FAISS.deserialize_from_bytes(
                embeddings=embeddings, serialized=serialized_bytes
            )

            return db

        except Exception as e:
            Common.exception_details("VectorStore._get_user_faiss_db_from_gcs", e)
            return None

    @staticmethod
    def _upload_user_faiss_db_to_gcs(user_id, db):
        """
        The function `_upload_user_faiss_db_to_gcs` uploads a serialized Faiss index to a Google Cloud
        Storage bucket.

        Args:
          user_id: The user_id parameter is a unique identifier for a user. It is used to create a
        folder path in the Google Cloud Storage (GCS) bucket where the user's faiss database will be
        uploaded.
          db: The "db" parameter in the function `_upload_user_faiss_db_to_gcs` is a Faiss index object.
        Faiss is a library for efficient similarity search and clustering of dense vectors. The index
        object contains the data and metadata required for performing similarity search operations on
        the vectors.
        """
        try:
            bucket = Production.get_users_bucket()

            user_folder_path = f"{user_id}/"
            vectorstore_path = f"{user_folder_path}vectorstore/db_faiss/"
            db_blob = bucket.blob(vectorstore_path + "index.pkl")

            pkl = db.serialize_to_bytes()  # serializes the faiss index
            db_blob.upload_from_string(pkl)

        except Exception as e:
            Common.exception_details("VectorStore._upload_user_faiss_db_to_gcs", e)

    @staticmethod
    def _delete_vectorindex_production(file, user_id):
        """
        The function `_delete_vectorindex_production` deletes matching IDs from a Faiss database and
        saves the updated database to Google Cloud Storage.

        Args:
          file: The "file" parameter is a dictionary that contains information about the file to be
        deleted. It includes the "virtualFileName" key, which represents the path of the file to be
        deleted.
          user_id: The `user_id` parameter is a unique identifier for the user. It is used to retrieve
        and update the user's Faiss database.
        """
        try:
            file_path = file["virtualFileName"]
            print("delete_vectorindex File path : ", file_path)

            db = VectorStore._get_user_faiss_db_from_gcs(user_id)

            dbdict = db.docstore._dict

            matching_ids = [
                key
                for key, value in dbdict.items()
                if value.metadata.get("source") == file_path
            ]

            if len(matching_ids) > 0:
                print("Found matching IDs in vectorstore to delete! : ", matching_ids)

                print("Deleting existing ids!")
                db.delete(matching_ids)

            print("Saving new indices to cloud!")

            VectorStore._upload_user_faiss_db_to_gcs(user_id, db)
            print("Uploaded new index to GCS!")

        except Exception as e:
            Common.exception_details("VectorStore._delete_vectorindex_production", e)

    @staticmethod
    def _delete_vectorindex_testing(file, user_id):
        """
        The function `_delete_vectorindex_testing` deletes matching IDs from a vector store based on a
        file path and saves the updated indices.

        Args:
          file: The "file" parameter is the name or path of the file that you want to delete from the
        vector index.
          user_id: The `user_id` parameter is used to identify the user for whom the vector index is
        being deleted. It is likely a unique identifier assigned to each user in the system.
        """
        try:
            embeddings = get_embeddings()
            file_path = MyDocumentsService.get_file_path(file, user_id)
            print("delete_vectorindex File path : ", file_path)

            db_path = VectorStore._get_document_vectorstore_path(user_id)
            db = FAISS.load_local(db_path, embeddings)
            dbdict = db.docstore._dict

            matching_ids = [
                key
                for key, value in dbdict.items()
                if value.metadata.get("source") == file_path
            ]

            if len(matching_ids) > 0:
                print("Found matching IDs in vectorstore to delete! : ", matching_ids)

                print("Deleting existing ids!")
                db.delete(matching_ids)

            print("Saving new indices!")
            db.save_local(db_path)

        except Exception as e:
            Common.exception_details("VectorStore._delete_vectorindex_testing", e)

    @staticmethod
    def _add_vectorindex_production(user_id, db, bucket):
        """
        The function `_add_vectorindex_production` checks if a folder exists in a bucket, and if not,
        creates the folder and uploads a database to it. If the folder already exists, it merges the
        existing database with a new one and uploads the updated database.

        Args:
          user_id: The user_id parameter is a unique identifier for a user. It is used to create a
        folder path and to identify the user's vectorstore in the bucket.
          db: The `db` parameter in the `_add_vectorindex_production` function is a database object. It
        is used to store and manage vectors in the vector store.
          bucket: The "bucket" parameter refers to a storage bucket in a cloud storage service, such as
        Google Cloud Storage. It is used to interact with the bucket and perform operations like listing
        blobs, creating blobs, and uploading data to the bucket.
        """
        try:
            user_folder_path = f"{user_id}/"
            vectorstore_path = f"{user_folder_path}vectorstore/db_faiss/"
            print("Vectorstore path : ", vectorstore_path)

            # List objects with the specified folder prefix
            blobs = bucket.list_blobs(prefix=user_folder_path)

            # Check if any objects were found with the given prefix
            folder_exists = any(
                blob.name.startswith(vectorstore_path) for blob in blobs
            )

            if folder_exists:
                print(f"The folder '{vectorstore_path}' exists in the bucket.")
            else:
                print(f"The folder '{vectorstore_path}' does not exist in the bucket.")

            if not folder_exists:
                # Create an empty blob to represent the folder
                folder_blob = bucket.blob(vectorstore_path)

                # You don't need to upload any data, just create the blob to represent the folder
                folder_blob.upload_from_string("")
                print(f"Created folder: {vectorstore_path}")

                VectorStore._upload_user_faiss_db_to_gcs(user_id, db)

                print("Uploaded new vectorstore!")

            else:
                existing_db = VectorStore._get_user_faiss_db_from_gcs(user_id)
                existing_db.merge_from(db)
                VectorStore._upload_user_faiss_db_to_gcs(user_id, existing_db)

                print("Uploaded updated vectorstore!")

        except Exception as e:
            Common.exception_details("VectorStore._add_vectorindex_production", e)

    @staticmethod
    def _add_vectorindex_testing(user_id, db, embeddings, db_path):
        """
        The function `_add_vectorindex_testing` updates or creates a vector index in a database.

        Args:
          user_id: The user_id is a unique identifier for the user. It is used to determine the path
        where the vector index will be stored.
          db: The `db` parameter is a database object that contains vectors and their corresponding
        embeddings.
          embeddings: The "embeddings" parameter is a variable that represents the embeddings or vector
        representations of documents. It is used in the code to update or create an index in a vector
        store database.
        """
        try:
            if os.path.exists(db_path):
                print("Updating existing index!")
                existing_db = FAISS.load_local(db_path, embeddings)
                existing_db.merge_from(db)
                existing_db.save_local(db_path)

            else:
                print("Creating index!")
                db.save_local(db_path)

        except Exception as e:
            Common.exception_details("VectorStore._add_vectorindex_testing", e)
