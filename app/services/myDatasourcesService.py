import csv
import os
import re
import shutil
import sys
from datetime import datetime

import langchain
import pymongo
from bson import ObjectId
from langchain.prompts import PromptTemplate
from langchain.sql_database import SQLDatabase
from langchain.llms import OpenAI
from langchain.llms.openai import OpenAI
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain.prompts import PromptTemplate
from openpyxl import Workbook
from pymongo import MongoClient
from pympler import asizeof

from app.config import Config
from app.models.mongoClient import MongoClient
from app.utils.common import Common
from app.utils.datasources.base import get_connection_string
from app.utils.datasources.mongodb.base import (check_mongo_connection,
                                                create_mongodb_agent,
                                                execute_pipeline)
from app.utils.datasources.sql.base import excute_sql_query, execute_query
from app.utils.enumerator import Enumerator
from app.utils.pipelines import PipelineStages
from app.utils.files_and_folders import get_user_folder


# Use this for debugging purposes of langchain agents
langchain.verbose = True


class MyDatasourcesService:
    DATASOURCES_COLLECTION = Config.MONGO_DATASOURCES_COLLECTION
    DATASOURCES_TYPE_COLLECTION = Config.MONGO_DATASOURCE_TYPE
    ERROR_RESPONSE = (
        "Unable to execute query! Please try after some time or try a different query."
    )

    def connect_to_database(self, database_connection_info):
        """
        The function `connect_to_database` connects to a database using the provided connection
        information and returns True if the connection is successful, otherwise it returns False.

        Args:
          database_connection_info: The parameter `database_connection_info` is a dictionary that
        contains information about the database connection. It typically includes the following keys:

        Returns:
          a boolean value. If the connection to the database is successfully established, it returns
        True. Otherwise, it returns False.
        """
        try:
            connection_string = get_connection_string(database_connection_info)
            print("Connection string: ", connection_string)
            # Datasource type
            datasource_type = database_connection_info["type"]

            # MongoDB
            if datasource_type == int(Enumerator.DatasourceTypes.MONGODB.value):
                print("Detected MongoDB database!")
                # If MongoDB client is connected then return True
                client = pymongo.MongoClient(connection_string)
                print("Client : ", client)

                if client:
                    # As an extra step check if connection has truly been established
                    # by trying to retrieve the collections in the database
                    db_connection = check_mongo_connection(
                        client, database_connection_info["database"]
                    )
                    if db_connection:
                        return True

            else:
                print("Detected SQL database!")
                # If Sql database is connected then return True
                db = SQLDatabase.from_uri(connection_string)
                if db:
                    return True

            return False
        except Exception as e:
            print("Connection error: ", e)
            return False

    def get_datasource_information(self, user_id, database_connection_info):
        """
        The function `get_datasource_information` retrieves information about a specific datasource for
        a given user from a MongoDB database.

        Args:
          user_id: The user_id parameter is the unique identifier of the user for whom we want to
        retrieve the datasource information.
          database_connection_info: The `database_connection_info` parameter is a dictionary that
        contains information about the database connection. It includes the following keys:

        Returns:
          the target datasource information, which includes the username and password for the given user
        and database connection information.
        """
        try:
            m_db = MongoClient.connect()
            datasource_name = database_connection_info["name"]

            match_pipeline = [
                PipelineStages.stage_match(
                    {
                        "user._id": ObjectId(user_id),
                        "datasources": {"$elemMatch": {"name": datasource_name}},
                    }
                )
            ]

            user_datasource_response = m_db[self.DATASOURCES_COLLECTION].aggregate(
                match_pipeline
            )
            user_datasource_response = Common.cursor_to_dict(user_datasource_response)[
                0
            ]["datasources"]
            target_datasource = [
                item
                for item in user_datasource_response
                if item["name"] == datasource_name
            ][0]
            target_datasource["username"] = database_connection_info["username"]
            target_datasource["password"] = database_connection_info["password"]

            return target_datasource
        except Exception as e:
            print("Exception in get_datasource_information : ", e)
            return None

    def update_database_connection_info(self, user_id, database_connection_info):
        """
        The function `update_database_connection_info` updates the database connection information for a
        specific user in a MongoDB collection.

        Args:
          user_id: The user_id parameter is the unique identifier of the user for whom the database
        connection information needs to be updated.
          database_connection_info: The `database_connection_info` parameter is a dictionary that
        contains the following information:

        Returns:
          the number of documents modified in the database.
        """
        try:
            datasource_query = {"user._id": ObjectId(user_id)}
            m_db = MongoClient.connect()
            documents = m_db[self.DATASOURCES_COLLECTION].find_one(datasource_query)

            existing_connections = documents["datasources"]
            datasource_name = database_connection_info["name"].strip()

            new_datasource_connection_info = {
                "name": datasource_name,
                "type": database_connection_info["type"],
                "host": database_connection_info["host"],
                "port": database_connection_info["port"],
                "database": database_connection_info["database"],
                "ssl": database_connection_info["ssl"],
                "lastEditedOn": datetime.utcnow(),
            }

            # Find the index of the target data source
            target_datasource_object = None
            for index, datasource in enumerate(existing_connections):
                if datasource["name"] == datasource_name:
                    target_datasource_object = datasource
                    break

            # Extract createdOn from target datasource object
            createdOn = target_datasource_object["createdOn"]
            new_datasource_connection_info["createdOn"] = createdOn

            # Update the data source details if found
            if index is not None:
                existing_connections[index].update(new_datasource_connection_info)

            update_operation = {"$set": {"datasources": existing_connections}}

            response = m_db[self.DATASOURCES_COLLECTION].update_one(
                datasource_query, update_operation
            )

            return response.modified_count

        except Exception as e:
            Common.exception_details(
                "myDatasourcesService update_database_connection_info", e
            )
            return None

    def save_database_connection_info(self, user_id, database_connection_info):
        """
        The function `save_database_connection_info` saves the database connection information for a
        user in a MongoDB collection.

        Args:
          user_id: The user_id parameter is the unique identifier of the user for whom the database
        connection information is being saved.
          database_connection_info: The `database_connection_info` parameter is a dictionary that
        contains the following keys:

        Returns:
          the response from the database operation. If the operation is successful, it returns the
        response as a dictionary. If there is an exception or error, it returns None.
        """
        try:
            new_database_connection = {
                "name": database_connection_info["name"].strip(),
                "type": database_connection_info["type"],
                "host": database_connection_info["host"],
                "port": database_connection_info["port"],
                "database": database_connection_info["database"],
                "ssl": database_connection_info["ssl"],
                "createdOn": datetime.utcnow(),
            }

            m_db = MongoClient.connect()

            match_pipeline = [
                PipelineStages.stage_match({"user._id": ObjectId(user_id)})
            ]

            user_datasource_response = m_db[self.DATASOURCES_COLLECTION].aggregate(
                match_pipeline
            )
            user_datasource_response = Common.cursor_to_dict(user_datasource_response)

            print("User Datasource Exists Response : ", user_datasource_response)

            # If no such document exists then create and insert it
            if not user_datasource_response:
                user_datasource_info = {
                    "user": {"_id": ObjectId(user_id), "ref": "user"},
                    "datasources": [new_database_connection],
                    "queries": [],
                }

                insert_response = m_db[self.DATASOURCES_COLLECTION].insert_one(
                    user_datasource_info
                )
                print("User Datasource Insert Response : ", insert_response)
                return Common.cursor_to_dict(insert_response)

            else:
                query = {
                    "user._id": ObjectId(user_id),
                    "datasources": {
                        "$elemMatch": {"name": {"$ne": new_database_connection["name"]}}
                    },
                }
                update_response = m_db[self.DATASOURCES_COLLECTION].update_one(
                    query, {"$push": {"datasources": new_database_connection}}
                )

                print("User Datasource Update Response : ", update_response)
                return Common.cursor_to_dict(update_response)

        except Exception as e:
            Common.exception_details(
                "myDatasourcesService save_database_connection_info", e
            )
            return None

    def get_all_connections(self, user_id):
        """
        The function `get_all_connections` retrieves all connections for a given user from a MongoDB
        database.

        Args:
          user_id: The `user_id` parameter is the unique identifier of the user for whom you want to
        retrieve all connections.

        Returns:
          the result of the aggregation query performed on the MongoDB collection. The result is
        converted to a dictionary format using the `cursor_to_dict` function from the `Common` class.
        The function returns the first element of the resulting dictionary.
        """
        try:
            m_db = MongoClient.connect()

            connections_pipeline = [
                PipelineStages.stage_match({"user._id": ObjectId(user_id)}),
                PipelineStages.stage_add_fields(
                    {
                        "_id": {"$toString": "$_id"},
                        "user._id": {"$toString": "$user._id"},
                        "datasources": {
                            "$map": {
                                "input": "$datasources",
                                "in": {
                                    "$mergeObjects": [
                                        "$$this",
                                        {
                                            "createdOn": {
                                                "$dateToString": {
                                                    "date": "$$this.createdOn"
                                                }
                                            }
                                        },
                                    ]
                                },
                            }
                        },
                    }
                ),
                PipelineStages.stage_unset(["queries"]),
            ]

            connections_response = m_db[self.DATASOURCES_COLLECTION].aggregate(
                connections_pipeline
            )

            connections_response = Common.cursor_to_dict(connections_response)
            if len(connections_response) > 0:
                return Common.cursor_to_dict(connections_response)[0]
            else:
                return []

        except Exception as e:
            Common.exception_details("myDatasourcesService get_all_connections", e)
            return None

    def get_datasource_types(self):
        """
        The function `get_datasource_types` retrieves all the datasource types from a MongoDB collection
        and returns them as a dictionary.

        Returns:
          the result of the aggregation query on the datasource types collection. The result is
        converted to a dictionary using the `cursor_to_dict` method from the `Common` class. If an
        exception occurs, `None` is returned.
        """
        try:
            m_db = MongoClient.connect()
            datasource_pipeline = [
                PipelineStages.stage_find_all(),
                PipelineStages.stage_add_fields({"_id": {"$toString": "$_id"}}),
            ]
            datasource_types = m_db[self.DATASOURCES_TYPE_COLLECTION].aggregate(
                datasource_pipeline
            )

            return Common.cursor_to_dict(datasource_types)

        except Exception as e:
            print("myDatasourcesService : get_datasource_types", e)
            return None

    def get_query_response(
        self, user_id, query, db_connection, datasource_name, datasource_information
    ):
        """
        The function `get_query_response` takes in user information, a query, database connection
        information, and datasource information, and executes the query, storing the response if it
        meets certain criteria.

        Args:
          user_id: The user ID is a unique identifier for the user who is making the query. It is used
        to associate the query and its response with the specific user.
          query: The `query` parameter is a string that represents the query to be executed on the given
        datasource. It can be a SQL query or a MongoDB query, depending on the type of the datasource.
          db_connection: The `db_connection` parameter is the connection string or object used to
        connect to the database. It is used to establish a connection to the database and execute
        queries.
          datasource_name: The `datasource_name` parameter is the name of the data source that the query
        is being executed on. It is used to identify the specific data source in the database.
          datasource_information: The `datasource_information` parameter is a dictionary that contains
        information about the data source. It includes details such as the type of data source (e.g.,
        MongoDB, SQL), the connection details (e.g., host, port, username, password), and any other
        relevant information needed to establish a

        Returns:
          a dictionary with the following keys:
        - "output_saved": a boolean indicating whether the response output was saved in the database or
        not.
        - "output": the response from the query execution.
        - "file_name": the name of the CSV file where the response was saved, if applicable.
        """
        try:
            # Check if the given query already exists
            m_db = MongoClient.connect()
            print("db_connection : ", db_connection)
            query_object = {
                "user._id": ObjectId(user_id),
                "queries.query": re.compile(query, re.IGNORECASE),
                "queries.datasource_name": datasource_name,
            }

            datasource_type = datasource_information["type"]
            database_executable_query = None
            response = None
            existing_datasource_object = m_db[self.DATASOURCES_COLLECTION].find_one(
                query_object
            )
            if existing_datasource_object:
                print("Executing exisitng query!")
                response = self._execute_existing_query(
                    query,
                    existing_datasource_object,
                    db_connection,
                    datasource_information,
                )

            if not response:
                # If the query is new then create the agent and run the query
                # making sure to store it for subsequent uses
                if datasource_type == int(Enumerator.DatasourceTypes.MONGODB.value):
                    agent = create_mongodb_agent(db_connection)
                    response = agent(query)["output"]
                else:
                    sql_query, response = execute_query(query, datasource_information)

                if datasource_type == int(Enumerator.DatasourceTypes.MONGODB.value):
                    (
                        pipeline,
                        collection,
                    ) = MyDatasourcesService._get_final_pipeline_collection()

                    database_executable_query = {
                        "pipeline": str(pipeline),
                        "collection": str(collection),
                    }
                else:
                    database_executable_query = {"sql": sql_query}

                # response = self._format_agent_response(response)

            # # If we get a proper response then store the response
            response_output_db_saved = False
            file_name = None
            if response and response != self.ERROR_RESPONSE:
                # Insert the response only if the size of the response is less than the maximum acceptable response size
                response_size = asizeof.asizeof(response)
                if response_size <= Config.MAX_DATASOURCE_RESPONSE_SIZE:
                    output_db_save_response = MyDatasourcesService().save_query(
                        user_id,
                        query,
                        response,
                        datasource_name,
                        datasource_type,
                        database_executable_query,
                    )

                    if output_db_save_response:
                        response_output_db_saved = True

                else:
                    # Save the response in a csv
                    file_name = MyDatasourcesService()._create_response_csv(
                        response, user_id
                    )

            if file_name:
                return {
                    "output_saved": response_output_db_saved,
                    "output": [],
                    "file_name": file_name,
                }
            else:
                return {
                    "output_saved": response_output_db_saved,
                    "output": response,
                    "file_name": None,
                }

        except Exception as e:
            print("Exception in get_query_response : ", e)
            return {None, None, None}

    def save_query(
        self,
        user_id,
        user_query,
        response,
        datasource_name,
        datasource_type,
        database_executable_query=None,
    ):
        """
        The `save_query` function saves a user query and its response to a MongoDB collection, either as
        a new query or as a response to an existing query.

        Args:
          user_id: The user ID is a unique identifier for the user who is saving the query. It is used
        to associate the query with the user in the database.
          user_query: The user's query that needs to be saved in the database.
          response: The "response" parameter is the response to the user's query. It is the information
        or data that is returned as a result of the query.
          datasource_name: The name of the data source that the query is associated with.
          datasource_type: The parameter "datasource_type" is used to specify the type of the data
        source. It could be a database, API, file, or any other type of data source.
          database_executable_query: The parameter "database_executable_query" is an optional parameter
        that represents the executable query that can be used to retrieve data from the database. It is
        used when saving a new query to the database.

        Returns:
          the number of modified documents in the database.
        """
        try:
            m_db = MongoClient.connect()

            # Constructing query object to find exisiting query
            query = {
                "user._id": ObjectId(user_id),
                "queries.query": re.compile(user_query, re.IGNORECASE),
                "queries.datasource_name": datasource_name,
            }

            existing_query = m_db[self.DATASOURCES_COLLECTION].find_one(query)

            # If the query already exists then save the new response
            if existing_query:
                print("Saving response to EXISTING query!")

                # print("Existing query : ", existing_query)

                new_response_element = {
                    "response": response,
                    "timestamp": datetime.utcnow(),
                }

                # The new response object should be appended to the responses array,
                # IF: the number of responses is equal to 5 then:
                #   Delete oldest response from array and insert new response
                # ELSE:
                #   Simply append the response object to the responses array

                # Picking out target query from existing queries
                target_query_object = None
                target_query_object = [
                    query_obj
                    for query_obj in existing_query["queries"]
                    if query_obj["query"].lower() == user_query.lower()
                ][0]

                # Filtering out the response object
                responses_object = target_query_object["responses"]
                # Finding out number of responses stored corresponding to current query
                num_responses = len(responses_object)

                # print("Responses object : ", responses_object)
                # print("Number of responses : ", num_responses)

                if num_responses == Config.MAX_DATASOURCE_QUERY_RESPONSES:
                    # Delete the last oldest response
                    responses_object.pop(0)

                # Append new response object to existing responses object
                responses_object.append(new_response_element)

                response_update_response = m_db[self.DATASOURCES_COLLECTION].update_one(
                    query, {"$set": {"queries.$.responses": responses_object}}
                )

                return response_update_response.modified_count

            else:
                print("Saving NEW query!")

                # If it is a new query then insert a new query object
                new_query_element = {
                    "query": user_query,
                    "datasource_name": datasource_name,
                    "datasource_type": datasource_type,
                    "database_executable_query": database_executable_query,
                    "responses": [
                        {"response": response, "timestamp": datetime.utcnow()}
                    ],
                }

                # TO IMPLEMENT :
                # The new query object should be appended to the queries array,
                # IF: the number of queries is equal to 5 then:
                #   Delete oldest query from array and insert new query
                # ELSE:
                #   Simply append the query object to the queries array

                # Picking out all queries
                # Constructing query object to find exisiting query
                datasource_query = {"user._id": ObjectId(user_id)}

                datasource_object = m_db[self.DATASOURCES_COLLECTION].find_one(
                    datasource_query
                )
                # print("Existing_queries : ", datasource_object)
                queries = datasource_object["queries"]

                # Finding out number of queries stored
                num_queries = len(queries)

                # print("queries  : ", queries)
                # print("Number of queries : ", num_queries)

                if num_queries == Config.MAX_DATASOURCE_QUERIES:
                    # Delete the last oldest response
                    queries.pop(0)

                # Append new response object to existing responses object
                queries.append(new_query_element)

                query_update_response = m_db[self.DATASOURCES_COLLECTION].update_one(
                    datasource_query, {"$set": {"queries": queries}}
                )

                return query_update_response.modified_count

        except Exception as e:
            Common.exception_details("myDatasourceService.py : save_query", e)
            return None

    def get_query_history(
        self, user_id, datasource_name=None, limit=10, offset=0, sortorder=-1
    ):
        try:
            pipeline = [
                {"$match": {"user._id": ObjectId(user_id)}},
                {"$unwind": {"path": "$queries", "preserveNullAndEmptyArrays": False}},
            ]

            # If queries from a specific datasource are to be extracted
            if datasource_name:
                pipeline = pipeline + [
                    {"$match": {"queries.datasource_name": datasource_name}}
                ]

            pipeline += [
                {
                    "$unwind": {
                        "path": "$queries.responses",
                        "preserveNullAndEmptyArrays": False,
                    }
                },
                {"$sort": {"queries.responses.timestamp": sortorder}},
                {
                    "$group": {
                        "_id": {
                            "_id": "$_id",
                            "user": "$user",
                            "datasources": "$datasources",
                            "query": "$queries.query",
                            "datasource_name": "$queries.datasource_name",
                        },
                        "responses": {
                            "$push": {
                                "response": "$queries.responses.response",
                                "timestamp": "$queries.responses.timestamp",
                            }
                        },
                        "latestTimestamp": {"$max": "$queries.responses.timestamp"},
                    }
                },
                {"$sort": {"latestTimestamp": sortorder}},
                {
                    "$project": {
                        "_id": "$_id._id",
                        "user": "$_id.user",
                        "datasources": "$_id.datasources",
                        "queries": {
                            "query": "$_id.query",
                            "datasource_name": "$_id.datasource_name",
                            "responses": "$responses",
                        },
                    }
                },
                # {"$skip": offset},
                # {"$limit": limit},
                {
                    "$group": {
                        "_id": {
                            "_id": "$_id",
                            "user": "$user",
                            "datasources": "$datasources",
                        },
                        "queries": {
                            "$push": {
                                "query": "$queries.query",
                                "datasource_name": "$queries.datasource_name",
                                "responses": "$queries.responses",
                            }
                        },
                    }
                },
                {
                    "$project": {
                        "_id": "$_id._id",
                        "user": "$_id.user",
                        "datasources": "$_id.datasources",
                        "queries": "$queries",
                    }
                },
                {
                    "$addFields": {
                        "user._id": {"$toString": "$user._id"},
                        "datasources": {
                            "$map": {
                                "input": "$datasources",
                                "in": {
                                    "createdOn": {
                                        "$dateToString": {"date": "$$this.createdOn"}
                                    },
                                    "database": "$$this.database",
                                    "host": "$$this.host",
                                    "name": "$$this.name",
                                    "port": "$$this.port",
                                    "ssl": "$$this.ssl",
                                    "type": "$$this.type",
                                },
                            }
                        },
                        "queries": {
                            "$map": {
                                "input": "$queries",
                                "in": {
                                    "datasource_name": "$$this.datasource_name",
                                    "query": "$$this.query",
                                    "responses": {
                                        "$map": {
                                            "input": "$$this.responses",
                                            "in": {
                                                "response": "$$this.response",
                                                "timestamp": {
                                                    "$dateToString": {
                                                        "date": "$$this.timestamp"
                                                    }
                                                },
                                            },
                                        }
                                    },
                                },
                            }
                        },
                    },
                },
                {"$unset": "_id"},
            ]

            print("Pipeline : ", pipeline)

            m_db = MongoClient.connect()
            response = m_db[self.DATASOURCES_COLLECTION].aggregate(pipeline)

            if response:
                return Common.cursor_to_dict(response)

            return None

        except Exception as e:
            Common.exception_details("myDatasourceService.py : get_query_history", e)
            return None

    def delete_responses_folder(user_id):
        """
        The function `delete_responses_folder` deletes a folder associated with a user's datasources.

        Args:
          user_id: The user_id parameter is the unique identifier of the user for whom the responses
        folder needs to be deleted.

        Returns:
          a boolean value. If the folder is successfully deleted, it will return True. If there is an
        exception or error, it will return False.
        """
        try:
            _get_datasources_folder = MyDatasourcesService._get_datasources_folder(
                user_id
            )
            shutil.rmtree(_get_datasources_folder)
            return True

        except Exception as e:
            Common.exception_details("myDatasourceService delete_responses_folder", e)
            return False

    def delete_datasource(self, user_id, datasource_name):
        """
        The function `delete_datasource` deletes a specific datasource from a user's list of datasources
        in a MongoDB collection.

        Args:
          user_id: The user_id parameter is the unique identifier of the user whose datasource needs to
        be deleted.
          datasource_name: The `datasource_name` parameter is the name of the datasource that you want
        to delete.

        Returns:
          the number of documents modified in the database.
        """
        try:
            update_query = {"user._id": ObjectId(user_id)}

            update_operation = {"$pull": {"datasources": {"name": datasource_name}}}

            # Perform the update
            m_db = MongoClient.connect()
            response = m_db[self.DATASOURCES_COLLECTION].update_one(
                update_query, update_operation
            )

            return response.modified_count

        except Exception as e:
            Common.exception_details("myDatasourcesService delete_datasource", e)
            return None

    @staticmethod
    def get_datasource_response_file_path(file_name="", user_id=""):
        """
        The function `get_datasource_response_file_path` returns the file path for saving a datasource
        response file based on the provided file name and user ID.

        Args:
          file_name: The name of the file that you want to save or retrieve.
          user_id: The user ID is a unique identifier for each user. It is used to create a folder
        specific to each user where their files can be stored.

        Returns:
          the file save path.
        """
        try:
            mydatasource_folder_path = MyDatasourcesService._get_datasources_folder(
                user_id
            )
            file_save_path = os.path.join(mydatasource_folder_path, file_name)

            return file_save_path

        except Exception as e:
            Common.exception_details(
                "MyDatasourcesService get_datasource_response_file_path", e
            )
            return None

    @staticmethod
    def _get_datasources_folder(user_id):
        """
        The function `_get_datasources_folder` returns the path to the user's folder for storing their
        datasources.

        Args:
          user_id: The user ID is a unique identifier for each user. It is used to create a folder
        specific to that user where their data sources will be stored.

        Returns:
          the path to the "mydatasource" folder for a specific user.
        """
        try:
            user_folder = get_user_folder(user_id)
            mydatasource_folder_path = os.path.join(
                user_folder, Config.USER_MY_DATASOURCES_FOLDER
            )

            # Ensure that the folders exists
            os.makedirs(mydatasource_folder_path, exist_ok=True)

            return mydatasource_folder_path

        except Exception as e:
            Common.exception_details("MyDatasourcesService _get_datasources_folder", e)
            return ""

    @staticmethod
    def _create_response_csv(response=[], user_id=""):
        """
        The function `_create_response_csv` takes a response object, extracts the headers and output
        data, creates an Excel file with the headers as the first row and the data rows following, and
        returns the file name if successful.

        Args:
          response: The `response` parameter is a dictionary that contains the response data. It should
        have the following structure:

        Returns:
          the file name of the created Excel file if the response is not empty and contains both headers
        and output. If any exception occurs during the process, it returns None.
        """
        try:
            if response:
                headers = response["response"]["columns"]
                output = response["response"]["output"]

                if headers and output:
                    timestamp = datetime.utcnow().timestamp()
                    file_name = f"MyDatasourcesResponse_{timestamp}.xlsx"

                    file_path = MyDatasourcesService.get_datasource_response_file_path(
                        file_name, user_id
                    )

                    # Create a new Excel workbook and select the active sheet
                    workbook = Workbook()
                    sheet = workbook.active

                    # Write header names to the first row
                    sheet.append(headers)

                    # Write data rows
                    for data_row in output:
                        sheet.append(data_row)

                    # Save the Excel file
                    workbook.save(file_path)

                    print("Excel file created successfully.")

                    return file_name

            return None

        except Exception as e:
            Common.exception_details("myDatasourcesService _create_response_csv", e)
            return None

    @staticmethod
    def _get_final_query(response):
        """
        The function `_get_final_query` retrieves the final query from a response object, if it exists,
        and returns it.

        Args:
          response: The `response` parameter is a dictionary that contains information about the
        intermediate steps of a process. It is expected to have a key called "intermediate_steps" which
        is a list of steps. Each step is a tuple where the first element is an object with information
        about the tool used and the second

        Returns:
          the final query if the final step in the response is either a SQL database query or a MongoDB
        pipeline. If the final step is not a query, it returns None. If an exception occurs, it also
        returns None.
        """
        try:
            final_step = response["intermediate_steps"][-1][0]
            print("Intermediate steps : ", response["intermediate_steps"][-1])

            if (
                final_step.tool == "sql_db_query"
                or final_step.tool == "mongo_run_pipeline"
            ):
                query = final_step.tool_input
                print("Query : ", query)
                return query
            else:
                return None

        except Exception as e:
            Common.exception_details("MyDatasourcesService._get_final_query", e)
            return None

    @staticmethod
    def _get_final_pipeline_collection(response):
        """
        The function `_get_final_pipeline_collection` returns the pipeline and collection name from a
        response, or None if an exception occurs.

        Args:
          response: The `response` parameter is the response object received from a data source service.

        Returns:
          a list containing the pipeline and collection name. If an exception occurs, it will return a
        list with two None values.
        """
        try:
            query = eval(MyDatasourcesService._get_final_query(response))

            if not query:
                return [None, None]

            pipeline = query["pipeline"]
            collection = query["collection_name"]

            return [pipeline, collection]

        except Exception as e:
            Common.exception_details(
                "MyDatasourcesService._get_final_pipeline_collection", e
            )
            return [None, None]

    @staticmethod
    def _get_existing_query_from_datasources(query, existing_datasource_object):
        """
        The function `_get_existing_query_from_datasources` retrieves an existing query from a
        datasource object based on a given query.

        Args:
          query: The query parameter is the query string that you want to find in the
        existing_datasource_object.
          existing_datasource_object: The `existing_datasource_object` parameter is an object that
        contains information about existing data sources. It is expected to have a property called
        "queries" which is an array of query objects. Each query object should have a property called
        "query" which represents the query string.

        Returns:
          the existing query object if it is found in the list of queries within the
        existing_datasource_object. If the query is not found or an exception occurs, it returns None.
        """
        try:
            existing_query = [
                existing_query
                for existing_query in existing_datasource_object["queries"]
                if query == existing_query["query"]
            ][0]

            return existing_query
        except Exception as e:
            Common.exception_details(
                "MyDatasourcesService._get_existing_query_from_datasources", e
            )
            return None

    @staticmethod
    def _format_db_response(query, response):
        """
        The function `_format_db_response` takes a query and a response as input, formats the response
        based on the query, and returns the formatted response.

        Args:
          query: The `query` parameter represents the query or question that was asked.
          response: The `response` parameter is the original response that needs to be formatted. It is
        a string containing the response data.

        Returns:
          the formatted response.
        """
        try:
            print("Original response : ", response)

            response_schemas = [
                ResponseSchema(name="answer", description="formatted response")
            ]
            output_parser = StructuredOutputParser.from_response_schemas(
                response_schemas
            )
            format_instructions = output_parser.get_format_instructions()
            prompt = PromptTemplate(
                template=""""Reformat the response in context to the query in natural language.
                \nQuery: {query}
                \nResponse: {response}
                \n{format_instructions}
                """,
                input_variables=["query", "response"],
                partial_variables={"format_instructions": format_instructions},
            )

            model = OpenAI(temperature=0)
            _input = prompt.format_prompt(query=query, response=response)
            output = model(_input.to_string())
            formatted_response = output_parser.parse(output)

            print("Formatted response : ", formatted_response["answer"])

            return formatted_response["answer"]

        except Exception as e:
            Common.exception_details("MyDatasourcesService._format_db_response", e)
            return response

    def _format_agent_response(self, response):
        """
        The function `_format_agent_response` returns a proper user response based on the agent's
        response, handling specific failure cases.

        Args:
          response: The `response` parameter is the output generated by the agent. It can be a string
        containing the agent's response to a user query or an error message indicating that the agent
        stopped due to iteration limit or time limit, or that it doesn't know the answer.

        Returns:
          the response. If the response is either "Agent stopped due to iteration limit or time limit."
        or "I don't know", it returns self.ERROR_RESPONSE. Otherwise, it returns the original response.
        """
        try:
            # Returning proper user reponse on agent failure
            if (
                response == "Agent stopped due to iteration limit or time limit."
                or response == "I don't know"
            ):
                return self.ERROR_RESPONSE

            else:
                return response

        except Exception as e:
            Common.exception_details("MyDatasourcesService._format_agent_response", e)
            return response

    def _execute_existing_query(
        self,
        query,
        existing_datasource_object,
        db_connection,
        db_datasource_information,
    ):
        """
        The function `_execute_existing_query` executes an existing query on a database or MongoDB and
        returns the response.

        Args:
          query: The `query` parameter is the query string that you want to execute.
          existing_datasource_object: The `existing_datasource_object` parameter is an object that
        represents an existing datasource. It contains information about the datasource, such as the
        type of datasource (e.g., MongoDB, SQL), the executable query, and other relevant details.
          db_connection: The `db_connection` parameter is the connection object or connection string
        used to connect to the database. It is used to establish a connection to the database before
        executing the query.
          db_datasource_information: The parameter `db_datasource_information` is a dictionary that
        contains information about the database datasource. It likely includes details such as the
        database name, host, port, username, and password. This information is used to establish a
        connection to the database and execute the SQL query.

        Returns:
          a response object. The response object contains information about the execution of the query,
        such as the type of datasource (MongoDB or SQL), the columns returned, and the output of the
        query. If an exception occurs during the execution of the query, the function returns None.
        """
        try:
            existing_query = MyDatasourcesService._get_existing_query_from_datasources(
                query, existing_datasource_object
            )
            executable_query = existing_query["database_executable_query"]
            datasource_type = existing_query["datasource_type"]
            response = None

            if datasource_type == int(Enumerator.DatasourceTypes.MONGODB.value):
                pipeline = executable_query["pipeline"]
                collection = executable_query["collection"]

                # Return None as response if either pipeline or collection is blank
                if (
                    not (pipeline)
                    or not (collection)
                    or len(pipeline) == 0
                    or len(collection) == 0
                ):
                    return None

                response = execute_pipeline(pipeline, collection, db_connection)
            else:
                sql = executable_query["sql"]

                # Return None as response if query is blank
                if not (sql) or len(sql) == 0:
                    return None

                field_names, sql_response = excute_sql_query(
                    sql, db_datasource_information
                )
                response = {
                    "type": "sql",
                    "response": {"columns": field_names, "output": sql_response},
                }

            return response

        except Exception as e:
            Common.exception_details("MyDatasourcesService._execute_existing_query", e)
            return None
