from datetime import datetime
from operator import itemgetter

from bson import ObjectId
from langchain.memory import ConversationBufferMemory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)
from langchain_core.runnables import (
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)

from app import socketio
from app.config import Config
from app.models.mongoClient import MongoClient
from app.services.myDocumentsService import MyDocumentsService
from app.utils.common import Common
from app.utils.enumerator import Enumerator
from app.utils.formatter import cursor_to_dict
from app.utils.llm_utils import load_fast_llm
from app.utils.timer import timeout_handler
from app.utils.vectorstore.base import VectorStore


class ChatService:
    def __init__(self, user_id):
        self.user_id = user_id

    def get_chat_response(self, chat_type: int, question: str, chatId: str):
        try:
            # Get chat memory
            memory = self.get_chat_memory()

            default_chat_response = "Sorry, I am unable to answer your question at the moment. Try again later."
            if chat_type == int(Enumerator.ChatType.External.value):
                response, sources = timeout_handler(
                    default_chat_response,
                    60,
                    self._get_external_chat_response,
                    question,
                    chatId,
                    memory,
                )
            else:
                response, sources = timeout_handler(
                    default_chat_response,
                    60,
                    self._get_document_chat_response,
                    question,
                    chatId,
                    memory,
                )

            # Prepare final chat_dict with complete response
            chat_dict = self._get_chat_dict(
                question=question,
                response=response,
                sources=sources,
                chatType=chat_type,
                chatId=chatId,
            )

            if response == default_chat_response:
                # Emit chat chunk through chat stream socket
                self._emit_chat_stream(chat_dict)

            # Update user chat history
            self._update_user_chat_info(chat_dict)

        except Exception as e:
            Common.exception_details("ChatSerice.get_chat_response", e)
            self._emit_chat_stream(
                {
                    "prompt": question,
                    "response": "Failed to get chat response....try again after some time...",
                    "sources": [],
                    "timestamp": datetime.utcnow().strftime("%d-%m-%Y %H:%M:%S"),
                    "chatType": int(Enumerator.ChatType.External.value),
                    "chatId": chatId,
                }
            )

    def get_chat_memory(self):
        memory = ConversationBufferMemory(return_messages=True)
        chats = self.get_all_user_related_chat(limit=10).get("chat", [])

        for user_chat, agent_chat in zip(chats[::2], chats[1::2]):
            memory.save_context(
                {"input": user_chat["content"]}, {"output": agent_chat["content"]}
            )

        return memory

    def _get_external_chat_response(
        self,
        question: str,
        chatId: str,
        memory: ConversationBufferMemory = ConversationBufferMemory(
            return_messages=True
        ),
    ):
        try:
            llm = load_fast_llm()
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are a helpful assistant. Answer all questions to the best of your ability in MARKDOWN.",
                    ),
                    MessagesPlaceholder(variable_name="history"),
                    ("human", "{input}"),
                ]
            )

            chain = (
                RunnablePassthrough.assign(
                    history=RunnableLambda(memory.load_memory_variables)
                    | itemgetter("history")
                )
                | prompt
                | llm
            )

            inputs = {"input": question}

            response = ""
            for chunk in chain.stream(inputs):
                # Keep on appending chunks to construct the entire response
                response = response + chunk.content
                print(chunk.content, end="", flush=True)

                # Prepare chat_dict
                chat_dict = self._get_chat_dict(
                    question=question,
                    response=chunk.content,
                    sources=[],
                    chatType=int(Enumerator.ChatType.External.value),
                    chatId=chatId,
                )

                # Emit chat chunk through chat stream socket
                self._emit_chat_stream(chat_dict)

            return response, []

        except Exception as e:
            Common.exception_details("ChatSerice._get_external_chat_response", e)
            return ""

    def _get_document_chat_response(
        self,
        question: str,
        chatId: str,
        memory: ConversationBufferMemory = ConversationBufferMemory(
            return_messages=True
        ),
    ):

        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        try:
            vectorstore = VectorStore(self.user_id)
            chat = load_fast_llm()
            prompt = self.get_document_prompt()
            db = vectorstore.get_document_vectorstore()

            rag_chain_from_docs = (
                RunnablePassthrough.assign(
                    context=(lambda x: format_docs(x["context"]))
                )
                | prompt
                | chat
                | StrOutputParser()
            )

            rag_chain_with_source = RunnableParallel(
                {"context": db.as_retriever(), "question": RunnablePassthrough()}
            ).assign(answer=rag_chain_from_docs)

            response = ""
            sources = []
            for chunk in rag_chain_with_source.stream(question):
                if "answer" in chunk.keys():
                    response = response + chunk["answer"]

                    # Prepare chat_dict
                    chat_dict = self._get_chat_dict(
                        question=question,
                        response=chunk["answer"],
                        sources=sources,
                        chatType=int(Enumerator.ChatType.Document.value),
                        chatId=chatId,
                    )

                    # Emit chat chunk through chat stream socket
                    self._emit_chat_stream(chat_dict)

                if "context" in chunk.keys():
                    virtual_source_names = [
                        doc.metadata.get("source", "") for doc in chunk["context"]
                    ]
                    sources = MyDocumentsService().get_all_files_by_virtual_name(
                        self.user_id, virtual_source_names
                    )

            return response, sources

        except Exception as e:
            Common.exception_details("ChatSerice._get_document_chat_response", e)
            return ""

    def _emit_chat_stream(self, chat_dict: dict):
        chat_event = "chat_" + str(self.user_id)
        socketio.emit(chat_event, [chat_dict])

        return chat_dict

    def _get_chat_dict(
        self, question: str, response: str, sources, chatType, chatId: str
    ):
        chat_dict = {
            "prompt": question,
            "response": response,
            "sources": sources,
            "timestamp": datetime.utcnow().strftime("%d-%m-%Y %H:%M:%S"),
            "chatType": chatType,
            "chatId": chatId,
        }

        return chat_dict

    def get_all_user_related_chat(self, limit=10, offset=0):
        """
        This function retrieves user-related chat messages from a MongoDB collection based on specified
        limits and offsets.

        Args:
          limit: The `limit` parameter in the `get_all_user_related_chat` function specifies the maximum
        number of chat documents to be returned in the result set. By default, it is set to 10 if not
        explicitly provided when calling the function. This parameter allows you to control the number
        of chat documents that. Defaults to 10
          offset: The `offset` parameter in the `get_all_user_related_chat` function is used to specify
        the number of documents to skip before returning the results. It helps in paginating through a
        large set of documents by allowing you to retrieve results starting from a specific position in
        the result set. Defaults to 0

        Returns:
          the first chat document related to the user specified by the user_id. If there are chat
        documents found based on the query criteria, the function returns the first chat document as a
        dictionary. If no chat documents are found or an exception occurs during the process, the
        function returns None.
        """
        try:
            m_db = MongoClient.connect()
            pipeline = [
                {"$match": {"user._id": ObjectId(self.user_id), "user.ref": "user"}},
                {"$sort": {"date": -1}},  # Sort by date in descending order
                {"$skip": offset},  # Skip offset number of documents
                {
                    "$limit": limit
                },  # Limit the result to the specified number of documents
                {"$sort": {"date": 1}},  # Re-Sort by date in correct order
                {"$project": {"chat": 1, "_id": 0}},
            ]

            result = m_db[Config.MONGO_CHAT_MASTER_COLLECTION].aggregate(pipeline)

            response = []
            if result:
                print("Found result!")
                response = cursor_to_dict(result)

            if len(response) > 0:
                return response[0]
            else:
                return None

        except Exception as e:
            Common.exception_details("chatService.get_all_user_related_chat", e)
            return None

    def delete_chats(self):
        """
        The delete_chats function deletes the chat history of a user.

        Args:
            self: Represent the instance of the class

        Returns:
            The response of the update_one function
        """
        m_db = MongoClient.connect()

        delete_filter = {"user._id": ObjectId(self.user_id)}
        delete_field = {"$unset": {"chat": 1}}
        response = m_db[Config.MONGO_CHAT_MASTER_COLLECTION].update_one(
            delete_filter, delete_field
        )

        if response:
            return True
        else:
            return False

    def _update_user_chat_info(self, chat_dict):
        """
        The function `_update_user_chat_info` updates the chat information for a user in a MongoDB
        database.

        Args:
          chat_dict: The `chat_dict` parameter is a dictionary that contains the following keys and
        values:

        Returns:
          the number of documents modified in the database.
        """
        try:
            m_db = MongoClient.connect()

            query = {"user._id": ObjectId(self.user_id), "user.ref": "user"}

            update_data = {
                "$push": {
                    "chat": {
                        "$each": [
                            {
                                "role": "user",
                                "content": chat_dict["prompt"],
                                "timestamp": chat_dict["timestamp"],
                                "chatType": chat_dict["chatType"],
                            },
                            {
                                "role": "system",
                                "content": chat_dict["response"],
                                "sources": chat_dict["sources"],
                                "timestamp": chat_dict["timestamp"],
                                "chatType": chat_dict["chatType"],
                            },
                        ]
                    }
                }
            }

            response = m_db[Config.MONGO_CHAT_MASTER_COLLECTION].update_one(
                query, update_data, upsert=True
            )

            if response:
                return response.modified_count

            return None

        except Exception as e:
            Common.exception_details("ChatSerice._update_user_chat_info", e)

    def get_document_prompt(self):
        prompt_template = """
        You are a helpful assistant. Answer all questions to the best of your ability based on the given context in MARKDOWN.

        The context and question are - 
        Context: {context}
        Question: {question}
        
        Answer:
        """

        prompt = PromptTemplate(
            template=prompt_template, input_variables=["context", "question"]
        )

        return prompt
