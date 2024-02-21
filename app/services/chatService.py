from datetime import datetime

import openai
from bson import ObjectId
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

from app import socketio
from app.config import Config
from app.models.mongoClient import MongoClient
from app.utils.common import Common
from app.utils.enumerator import Enumerator
from app.utils.formatter import cursor_to_dict
from app.utils.llm_utils import load_fast_llm
from app.utils.pipelines import PipelineStages
from app.utils.vectorstore.base import VectorStore
from app.utils.timer import timeout_handler
from langchain.memory import ConversationBufferWindowMemory


openai.api_key = Config.OPENAI_API_KEY


class ChatService:
    def __init__(self, user_id):
        self.user_id = user_id

    def get_chat_response(self, chat_type, question: str, chatId: str):
        try:
            default_chat_response = "Sorry, I am unable to answer your question at the moment. Try again later."
            if chat_type == int(Enumerator.ChatType.External.value):
                response = timeout_handler(
                    default_chat_response, 
                    60, 
                    self._get_external_chat_response, 
                    question, 
                    chatId
                )
            else:
                response = timeout_handler(
                    default_chat_response, 
                    60, 
                    self._get_document_chat_response, 
                    question, 
                    chatId
                )
            
            # Prepare final chat_dict with complete response
            chat_dict = self._get_chat_dict(
                question=question,
                response=response,
                sources = [],
                chatType=int(Enumerator.ChatType.External.value),
                chatId=chatId
            )
            
            if response == default_chat_response:
                # Emit chat chunk through chat stream socket
                self._emit_chat_stream(
                    chat_dict
                )
                    
            # Update user chat history
            self._update_user_chat_info(chat_dict)

        except Exception as e:
            Common.exception_details("ChatSerice.get_chat_response", e)
            self._emit_chat_stream({
                "prompt": question,
                "response": "Failed to get chat response....try again after some time...",
                "sources": [],
                "timestamp": datetime.utcnow().strftime("%d-%m-%Y %H:%M:%S"),
                "chatType": int(Enumerator.ChatType.External.value),
                "chatId": chatId
            })

    def _get_external_chat_response(self, question: str, chatId: str):
        try:
            chat = load_fast_llm()            
            template = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant. Answer all questions to the best of your ability in MARKDOWN."),
                ("human", "{question}"),
            ])
            messages = template.format_messages(
                question=question
            )

            response = ""
            for chunk in chat.stream(messages):
                # Keep on appending chunks to construct the entire response
                response = response + chunk.content
                print(chunk.content, end="", flush=True)
                
                # Prepare chat_dict
                chat_dict = self._get_chat_dict(
                    question=question,
                    response=chunk.content,
                    sources=[],
                    chatType=int(Enumerator.ChatType.External.value),
                    chatId=chatId
                )
                
                # Emit chat chunk through chat stream socket
                self._emit_chat_stream(
                    chat_dict
                )
                
            return response
        
        except Exception as e:
            Common.exception_details("ChatSerice._get_external_chat_response", e)
            return ""
            
    def _get_document_chat_response(self, question: str, chatId: str):
        try:  
            vectorstore = VectorStore(self.user_id)
            chat = load_fast_llm()
            prompt = self.get_document_prompt()
            db = vectorstore.get_document_vectorstore()
            rag_chain = (
                {"context": db.as_retriever(), "question": RunnablePassthrough()}
                | prompt
                | chat
                | StrOutputParser()
            )
            response = ""
            for chunk in rag_chain.stream(question):
                # Keep on appending chunks to construct the entire response
                response = response + chunk
                print(chunk, end="", flush=True)
                
                # Prepare chat_dict
                chat_dict = self._get_chat_dict(
                    question=question,
                    response=chunk,
                    sources=[],
                    chatType=int(Enumerator.ChatType.Document.value),
                    chatId=chatId
                )
                
                # Emit chat chunk through chat stream socket
                self._emit_chat_stream(
                    chat_dict
                )
                
            return response
        
        except Exception as e:
            Common.exception_details("ChatSerice._get_document_chat_response", e)
            return ""
            
    def _emit_chat_stream(self, chat_dict: dict):       
        chat_event = "chat_" + str(self.user_id)
        socketio.emit(chat_event, [chat_dict])
        
        return chat_dict
    
    def _get_chat_dict(self, question: str, response: str, sources, chatType, chatId: str):
        chat_dict = {
            "prompt": question,
            "response": response,
            "sources": sources,
            "timestamp": datetime.utcnow().strftime("%d-%m-%Y %H:%M:%S"),
            "chatType": chatType,
            "chatId": chatId
        }
        
        return chat_dict

    def get_all_user_related_chat(self, limit=10, offset=0):
        """
        The function `get_all_user_related_chat` retrieves chat data related to a specific user from a
        MongoDB database.

        Args:
          limit: The `limit` parameter specifies the maximum number of chat records to retrieve. By
        default, it is set to 10, but you can change it to any positive integer value to retrieve a
        different number of records. Defaults to 10
          offset: The offset parameter is used to specify the starting point of the query results. It
        determines how many documents to skip before returning the results. By default, the offset is
        set to 0, meaning it starts from the beginning of the collection. Defaults to 0

        Returns:
          a dictionary containing the chat related to the specified user. If no chat is found, it
        returns None.
        """
        try:
            m_db = MongoClient.connect()
            project_keys = ["chat"]
            unset_keys = ["_id"]
            pipeline = [
                PipelineStages.stage_match(
                    {"user._id": ObjectId(self.user_id), "user.ref": "user"}
                ),
                PipelineStages.stage_project(project_keys),
                PipelineStages.stage_unset(unset_keys),
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
        You are a helpful Artificial Intelligence Question and Answer bot who answers questions based on context.

        Example Number 1:
        - Context: The Theory of Relativity was developed by Albert Einstein
        - Question: Who developed the Theory of Relativity?
        - AI Response: The Theory of Relativity was developed by Albert Einstein.

        Example Number 2:
        - Context: Marketing is the activity, set of institutions, and processes for creating, communicating, delivering, and exchanging offerings that have value for customers, clients, partners, and society at large.
        - Question: How do you manage your finance?
        - AI Response: I don't know.

        Example Number 3:
        - Context: Water boils at 100 degrees Celsius at sea level
        - Question: What is the boiling point of water at sea level?
        - AI Response: The boiling point of water at sea level is 100 degrees Celsius.

        Example Number 4:
        - Context: Artificial intelligence is the ability of machines to perform tasks that are typically associated with human intelligence.
        - Question: What is the safety measure taken in Steel?
        - AI Response: I don't know.

        Example Number 5:
        - Context: 
        - Question: How to get over depression?
        - AI Response: I don't know.

        Since the context does not contain the answer to the question in Examples 2 and 4, and since the context was empty in Example 5, the AI Response is "I don't know". In a similar way, if the context is not related to the answer or the context is empty, the final answer should be "I don't know".

        Remember the following points before providing any answer:
        - If the answer is not present in the "context", then just say "I don't know"; don't try to make up an answer.
        - If the "context" is empty, do not answer; say "I don't know", even if you know the answer.
        - Only return the helpful answer below and nothing else.
        - ALWAYS answer in MARKDOWN!

        The context and question are - 
        Context: {context}
        Question: {question}

        Helpful answer:

        """

        prompt = PromptTemplate(
            template=prompt_template, input_variables=["context", "question"]
        )

        return prompt