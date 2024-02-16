import os
from typing import Union

from bson import ObjectId
from langchain_community.vectorstores import FAISS

from app.config import Config
from app.services.myDocumentsService import MyDocumentsService
from app.utils.common import Common
from app.utils.production import Production
from app.utils.vectorstore.retrievers import Retriever

from ..llm_utils import get_embeddings, load_fast_llm
from .prompts import get_document_prompt


class VectorStore:
    
    def __init__(self, user_id: Union[str, ObjectId]):
        self.user_id = user_id

    def delete_vectorindex(self, file_id):
        """
        The function `delete_vectorindex` deletes a vector index file based on the provided file ID.
        
        :param file_id: The `file_id` parameter is the unique identifier of the file that needs to be
        deleted
        """
        try:
            print("File id : ", file_id)
            file = MyDocumentsService().get_file(file_id)

            if Config.GCP_PROD_ENV:
                self._delete_vectorindex_production(file)
            else:
                self._delete_vectorindex_testing(file)

        except Exception as e:
            Common.exception_details("VectorStore.delete_vectorindex", e)

    def get_document_chat_response(self, query):
        try:
            embeddings = get_embeddings()
            llm = load_fast_llm()
            prompt = get_document_prompt()
            db = self.get_document_vectorstore(embeddings)
            retriever = Retriever(self.user_id, query, llm, prompt, db)
            response, sources = retriever.rag_chain_with_sources()

            return {"response": response, "sources": sources}

        except Exception as e:
            Common.exception_details("VectorStore.get_document_chat_response", e)
            return None

    def get_document_vectorstore(self, embeddings=None):
        """
        The function `get_document_vectorstore` retrieves a vectorstore either from Google Cloud Storage
        (GCS) or from a local path, depending on the environment, and returns it.
        
        :param embeddings: The "embeddings" parameter is an optional argument that represents the
        pre-trained word embeddings or document embeddings. It is used to load the vectorstore with the
        specified embeddings. If no embeddings are provided, the vectorstore will be loaded without any
        embeddings
        :return: the variable "db" which represents the document vectorstore.
        """
        try:
            if Config.GCP_PROD_ENV:
                print("💁 Getting vectorstore from GCS")
                db = self._get_user_faiss_db_from_gcs()

            else:
                print("💁 Getting vectorstore from LOCAL")
                db_path = self._get_document_vectorstore_path()
                db = FAISS.load_local(db_path, embeddings)

            return db

        except Exception as e:
            return None

    def add_vectorindex(self, splits):
        """
        The function `add_vectorindex` adds vector indices to a database using embeddings.
        
        :param splits: The "splits" parameter is a list of documents that need to be added to the vector
        index. Each document in the list should be a string or a list of strings representing the text
        or content of the document
        """
        try:
            embeddings = get_embeddings()
            db = FAISS.from_documents(splits, embeddings)
            db_path = self._get_document_vectorstore_path()

            if Config.GCP_PROD_ENV:
                bucket = Production.get_users_bucket()
                self._add_vectorindex_production(db, bucket)
            else:
                self._add_vectorindex_testing(db, embeddings, db_path)

        except Exception as e:
            Common.exception_details("VectorStore.add_vectorindex", e)

    def _get_document_vectorstore_path(self):
        """
        The function `_get_document_vectorstore_path` returns the path to the document vector store for
        a specific user.
        :return: the path to the document vector store.
        """
        try:
            db_path = os.path.join(
                os.path.join(Config.USER_FOLDER, self.user_id), Config.USER_VECTORSTORE_PATH
            )

            return db_path

        except Exception as e:
            Common.exception_details("VectorStore._get_document_vectorstore_path", e)
            return None

    def _get_user_faiss_db_from_gcs(self):
        """
        The function `_get_user_faiss_db_from_gcs` downloads a pickled object from Google Cloud Storage
        (GCS), deserializes it using FAISS, and returns the deserialized object.
        :return: the variable `db`, which is the deserialized FAISS index object.
        """
        try:
            embeddings = get_embeddings()
            bucket = Production.get_users_bucket()
            user_folder_path = f"{self.user_id}/"
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

    def _upload_user_faiss_db_to_gcs(self, db):
        """
        The function `_upload_user_faiss_db_to_gcs` uploads a serialized Faiss index to Google Cloud
        Storage.
        
        :param db: The "db" parameter in the above code refers to a Faiss index object. Faiss is a
        library for efficient similarity search and clustering of dense vectors. The index object
        contains the data and metadata required for performing similarity search operations on the
        vectors
        """
        try:
            bucket = Production.get_users_bucket()

            user_folder_path = f"{self.user_id}/"
            vectorstore_path = f"{user_folder_path}vectorstore/db_faiss/"
            db_blob = bucket.blob(vectorstore_path + "index.pkl")

            pkl = db.serialize_to_bytes()  # serializes the faiss index
            db_blob.upload_from_string(pkl)

        except Exception as e:
            Common.exception_details("VectorStore._upload_user_faiss_db_to_gcs", e)

    def _delete_vectorindex_production(self, file):
        """
        The function `_delete_vectorindex_production` deletes matching IDs from a vectorstore database
        and saves the updated indices to a cloud storage.
        
        :param file: The `file` parameter is a dictionary that contains information about a file. It has
        a key called "virtualFileName" which represents the file path
        """
        try:
            file_path = file["virtualFileName"]
            print("delete_vectorindex File path : ", file_path)

            db = self._get_user_faiss_db_from_gcs()

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

            self._upload_user_faiss_db_to_gcs(db)
            print("Uploaded new index to GCS!")

        except Exception as e:
            Common.exception_details("VectorStore._delete_vectorindex_production", e)

    def _delete_vectorindex_testing(self, file):
        """
        The function `_delete_vectorindex_testing` deletes matching IDs from a vector store and saves
        the updated indices.
        
        :param file: The `file` parameter is the name or path of the file that you want to delete from
        the vector index
        """
        try:
            embeddings = get_embeddings()
            file_path = MyDocumentsService.get_file_path(file, self.user_id)
            print("delete_vectorindex File path : ", file_path)

            db_path = self._get_document_vectorstore_path()
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

    def _add_vectorindex_production(self, db, bucket):
        """
        The function `_add_vectorindex_production` checks if a folder exists in a bucket, and if not,
        creates the folder and uploads a database to it. If the folder already exists, it merges the
        existing database with a new one and uploads the updated database.
        
        :param db: The `db` parameter is a database object that represents the vector index data. It is
        used to store and retrieve vectors for similarity search operations
        :param bucket: The "bucket" parameter is the name of the Google Cloud Storage bucket where the
        vectorstore is stored
        """
        try:
            user_folder_path = f"{self.user_id}/"
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

                self._upload_user_faiss_db_to_gcs(db)

                print("Uploaded new vectorstore!")

            else:
                existing_db = self._get_user_faiss_db_from_gcs()
                existing_db.merge_from(db)
                self._upload_user_faiss_db_to_gcs(existing_db)

                print("Uploaded updated vectorstore!")

        except Exception as e:
            Common.exception_details("VectorStore._add_vectorindex_production", e)

    def _add_vectorindex_testing(self, db, embeddings, db_path):
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
