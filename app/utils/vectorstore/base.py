import os

from langchain.chains import RetrievalQA
from langchain.document_loaders import GCSFileLoader
from langchain.llms import OpenAI
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain.schema.document import Document
from langchain.vectorstores import FAISS

from app.config import Config
from app.services.myDocumentsService import MyDocumentsService
from app.utils.common import Common
from app.utils.production import Production

from .document_loaders import load_docx, load_pdf, load_pptx, load_txt
from .llm_utils import get_embeddings, get_text_splitter, load_llm, split_text
from .prompts import get_custom_document_prompt, get_custom_knowledgeitem_prompt


class VectorStore:
    PRODUCTION_CHECK = Config.GCP_PROD_ENV

    def update_document_vectorstore(self, user_id, file_id, path):
        """
        The function `update_document_vectorstore` updates the vector store index with the contents of a
        file specified by its path.

        Args:
          user_id: The user ID is a unique identifier for the user who owns the document. It is used to
        associate the document with the correct user in the database.
          file_id: The `file_id` parameter is the unique identifier of the file in the database.
          path: The `path` parameter is the path where the file is saved on the server.
        """

        try:
            print("Update vector store index")
            print("File path : ", path)

            # Get virtual filename from DB
            file = MyDocumentsService().get_file(file_id)
            virtual_file_name = file["virtualFileName"]
            data = None

            # Extract file extension
            print("File : ", file)

            filename = file["virtualFileName"]
            print("Filename : ", filename)

            file_extension = filename.rsplit(".", 1)[-1]
            print("File extension : ", file_extension)

            root = file["root"]
            print("File root : ", root)

            if self.PRODUCTION_CHECK:
                print("Loading file from gcp!")
                data = VectorStore._load_file_from_gcs(user_id, root, virtual_file_name)

            else:
                # Get path of file saved on server
                file_save_path = MyDocumentsService().get_file_save_path(
                    virtual_file_name, user_id, path
                )

                data = VectorStore._load_file_from_local(file_save_path, file_extension)

            if data:
                splits = split_text(data)

                # Converting source files to virtual file name
                for split in splits:
                    split.metadata["source"] = filename

                if splits:
                    self._add_vectorindex(
                        splits=splits,
                        user_id=user_id,
                        db_path=VectorStore._get_document_vectorstore_path(user_id),
                        bucket=Production.get_users_bucket(),
                    )

        except Exception as e:
            Common.exception_details("Vectorstore.update_document_vectorstore", e)

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

            if self.PRODUCTION_CHECK:
                VectorStore._delete_vectorindex_production(file, user_id)
            else:
                VectorStore._delete_vectorindex_testing(file, user_id)

        except Exception as e:
            Common.exception_details("VectorStore.delete_vectorindex", e)

    def get_document_chat_response(self, user_id, query):
        """
        The function `get_document_chat_response` retrieves a response and sources based on a user query
        using vector embeddings and a retrieval question-answering chain.

        Args:
          user_id: The user_id parameter is a unique identifier for the user who is making the chat
        request. It is used to retrieve the user's specific document vector store and Faiss database.
          query: The query parameter is the user's input or question that they want to ask the document
        chatbot.

        Returns:
          a dictionary with two keys: "response" and "sources". The value associated with the "response"
        key is the result of the chat query, and the value associated with the "sources" key is a list
        of original file names related to the chat query.
        """
        try:
            embeddings = get_embeddings()
            llm = load_llm()

            db = self.get_document_vectorstore(user_id, embeddings)
            qa_prompt = get_custom_document_prompt()
            qa_chain = VectorStore._retrieval_qa_chain(llm, qa_prompt, db)
            response = qa_chain({"query": query})

            result = response["result"] or None
            sources = (
                list(
                    set(
                        [
                            document.metadata["source"]
                            for document in response["source_documents"]
                        ]
                    )
                )
                or []
            )
            print("Sources : ", sources)

            files = MyDocumentsService().get_all_files_by_virtual_name(user_id, sources)
            original_sources = [file["originalFileName"] for file in files]

            return {"response": result, "sources": original_sources}

        except Exception as e:
            Common.exception_details("VectorStore.get_document_chat_response", e)
            return None

    def get_document_vectorstore(self, user_id, embeddings=None):
        try:
            if self.PRODUCTION_CHECK:
                db = VectorStore._get_user_faiss_db_from_gcs(user_id)
                
            else:
                db_path = VectorStore._get_document_vectorstore_path(user_id)
                db = FAISS.load_local(db_path, embeddings)

            return db
        
        except Exception as e:
            return None

    def get_knowledgeitem_chat_response(self, query):
        """
        The function `get_knowledgeitem_chat_response` retrieves a response and sources based on a given
        query using a knowledge item vector store.

        Args:
          query: The `query` parameter is a string that represents the user's input or question. It is
        used as input to retrieve a response from the knowledge item chatbot.

        Returns:
          The function `get_knowledgeitem_chat_response` returns a dictionary with two keys: "response"
        and "sources". The value associated with the "response" key is the result of the chat response,
        which can be a string or None. The value associated with the "sources" key is a list of sources,
        which can be empty if there are no source documents associated with the chat response.
        """
        try:
            embeddings = get_embeddings()

            if self.PRODUCTION_CHECK:
                db = VectorStore._get_knowledgeitem_faiss_db_from_gcs()

            else:
                db_path = Config.KNOWLEDGEITEM_VECTORSTORE_PATH
                db = FAISS.load_local(db_path, embeddings)

            llm = load_llm()
            qa_prompt = get_custom_knowledgeitem_prompt()
            qa_chain = VectorStore._retrieval_qa_chain(llm, qa_prompt, db)
            response = qa_chain({"query": query})

            result = response["result"] or None
            print("Response : ", result)

            sources = (
                list(
                    set(
                        [
                            document.metadata["source"]
                            for document in response["source_documents"]
                        ]
                    )
                )
                or []
            )
            print("Sources : ", sources)

            return {"response": result, "sources": sources}

        except Exception as e:
            Common.exception_details("VectorStore.get_knowledgeitem_chat_response", e)
            return None

    def update_knowledgeitem_vectorstore(self, ki_id, ki_description):
        """
        The function `update_knowledgeitem_vectorstore` updates the vector store with the description of
        a knowledge item.

        Args:
          ki_id: The `ki_id` parameter is the identifier of the knowledge item. It is used as the source
        metadata for the document in the vector store.
          ki_description: The `ki_description` parameter is a string that represents the description of
        a knowledge item.
        """
        try:
            text_splitter = get_text_splitter()
            splits = [
                Document(page_content=x, metadata={"source": str(ki_id)})
                for x in text_splitter.split_text(ki_description)
            ]

            if splits:
                self._add_vectorindex(
                    splits=splits,
                    user_id=None,
                    db_path=Config.KNOWLEDGEITEM_VECTORSTORE_PATH,
                    bucket=Production.get_knowledgeitems_bucket(),
                )

        except Exception as e:
            Common.exception_details("VectorStore.update_knowledgeitem_vectorstore", e)

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
            user_folder_path = os.path.join(Config.USER_FOLDER, user_id)
            db_path = os.path.join(
                user_folder_path, Config.USER_VECTORSTORE_PATH
            )

            return db_path

        except Exception as e:
            Common.exception_details("Vectorstore._get_document_vectorstore_path", e)
            return None

    @staticmethod
    def _retrieval_qa_chain(llm, prompt, db):
        """
        The function `_retrieval_qa_chain` retrieves a question-answering chain using a language model,
        a prompt, and a database.

        Args:
          llm: The "llm" parameter is an instance of a language model. It is used for language modeling
        tasks such as generating text or predicting the next word in a sequence.
          prompt: The `prompt` parameter is a string that represents the question or query for which you
        want to retrieve an answer. It is used as input to the retrieval QA chain to find relevant
        information from the database (`db`) and generate an answer.
          db: The `db` parameter is an object that represents a database. It is used as a retriever in
        the `ContextualCompressionRetriever` to perform search operations. The `as_retriever` method is
        called on the `db` object to convert it into a retriever that can

        Returns:
          a retrieval QA chain object.
        """
        try:
            # Including a compressor for more better results
            llm = load_llm()
            compressor = LLMChainExtractor.from_llm(llm)

            # Combining compressor and retriever into a single retriever
            compression_retriever = ContextualCompressionRetriever(
                base_compressor=compressor,
                base_retriever=db.as_retriever(search_type="mmr"),
            )

            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=compression_retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": prompt},
            )

            return qa_chain

        except Exception as e:
            Common.exception_details("VectorStore._retrieval_qa_chain", e)
            return None

    @staticmethod
    def _load_file_from_local(file_save_path, file_extension):
        """
        The function `_load_file_from_local` loads a file from a local path based on its file extension
        and returns the loaded data.

        Args:
          file_save_path: The file_save_path parameter is the path where the file is saved on the local
        system. It should be a string representing the file path, including the file name and extension.
        For example, "C:/Documents/myfile.pdf".
          file_extension: The `file_extension` parameter is a string that represents the extension of
        the file that needs to be loaded. It can have values such as "pdf", "doc", "docx", "pptx", or
        "txt" depending on the type of file you want to load.

        Returns:
          the loaded data from the file, or None if there was an exception.
        """
        try:
            data = None

            # Use dataloaders to load the docs based on file type
            # PDF
            if file_extension == "pdf":
                print("Loader : PDF")
                data = load_pdf(file_save_path)

            # WORD
            elif file_extension == "doc" or file_extension == "docx":
                print("Loader : DOCX")
                data = load_docx(file_save_path)

            # PPT
            elif file_extension == "pptx":
                print("Loader : PPTX")
                data = load_pptx(file_save_path)

            # TXT
            elif file_extension == "txt":
                print("Loader : TXT")
                data = load_txt(file_save_path)

            return data

        except Exception as e:
            Common.exception_details("VectorStore._load_file_from_local", e)
            return None

    @staticmethod
    def _load_file_from_gcs(user_id, file_root, virtual_file_name):
        try:
            data = None

            if file_root == f"/{user_id}/":
                blob = f"{user_id}/{virtual_file_name}"
            else:
                blob = f"{file_root[1:]}/{virtual_file_name}"

            print("Blob name : ", blob)

            # bucket = .get_bucket(Config.GCP_BUCKET_USERS"])
            loader = GCSFileLoader(
                project_name="Texplicit-02",
                bucket=Config.GCP_BUCKET_USERS,
                blob=blob,
            )
            data = loader.load()

            print("Data : ", data)

            return data

        except Exception as e:
            Common.exception_details("VectorStore._load_file_from_gcs", e)
            return None

    @staticmethod
    def _get_knowledgeitem_faiss_db_from_gcs():
        try:
            embeddings = get_embeddings()
            bucket = Production.get_knowledgeitems_bucket()
            vectorstore_path = f"vectorstore/db_faiss/"

            blob = bucket.blob(vectorstore_path + "index.pkl")

            # Download the pickled object as bytes from GCS
            serialized_bytes = blob.download_as_bytes()

            # Load the index
            db = FAISS.deserialize_from_bytes(
                embeddings=embeddings, serialized=serialized_bytes
            )

            return db

        except Exception as e:
            Common.exception_details(
                "VectorStore._get_knowledgeitem_faiss_db_from_gcs", e
            )
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

    def _add_vectorindex(self, splits, user_id=None, db_path=None, bucket=None):
        """
        The function `_add_vectorindex` adds a vector index to a database using the given splits, user
        ID, database path, and bucket.

        Args:
          splits: The "splits" parameter is a list of documents that will be used to create the vector
        index. Each document in the list should be a string or a list of strings representing the text
        or features of the document.
          user_id: The user_id parameter is an optional parameter that represents the ID of the user for
        whom the vector index is being added.
          db_path: The `db_path` parameter is the path to the directory where the vector index database
        will be stored.
          bucket: The "bucket" parameter is used to specify the name of the bucket where the vector
        index will be stored. It is typically used when working with cloud storage services like Amazon
        S3 or Google Cloud Storage.
        """
        try:
            embeddings = get_embeddings()
            db = FAISS.from_documents(splits, embeddings)

            if self.PRODUCTION_CHECK:
                VectorStore._add_vectorindex_production(user_id, db, bucket)
            else:
                VectorStore._add_vectorindex_testing(user_id, db, embeddings, db_path)

        except Exception as e:
            Common.exception_details("Vectorstore._add_vectorindex", e)
