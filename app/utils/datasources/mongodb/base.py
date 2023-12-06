from ast import literal_eval

import pymongo
from langchain.agents import AgentType, initialize_agent
from langchain.chains.llm import LLMChain
from langchain.llms import OpenAI
from langchain.llms.openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain.tools import Tool

from app.utils.common import Common
from app.utils.datasources.base import get_connection_string
from app.utils.datasources.mongodb.prompt import (
    FORMAT_INSTRUCTIONS,
    MONGODB_PREFIX,
    MONGODB_SUFFIX,
)

llm = OpenAI(temperature=0, verbose=True)
db = None


def mongo_get_collection_names(_) -> str:
    """
    Searches the database and returns all the collection names.

    Returns an error response if it encounters an error.
    """
    try:
        collection_names = db.list_collection_names()

        # Joining the elements as strings with comma separation
        result_string = ",".join(collection_names)

        return result_string
    except Exception as e:
        return "Error : " + str(e)


def get_document_schema(obj, indent=""):
    """
    The function `get_document_schema` recursively generates a schema for a given object, including the
    data types of its properties and whether they are lists or dictionaries.

    Args:
      obj: The `obj` parameter is the object for which you want to generate the document schema. It
    should be a dictionary-like object that contains the properties and values you want to include in
    the schema.
      indent: The `indent` parameter is used to specify the indentation level for each nested property
    in the schema. It is a string that represents the number of tabs to be added before each property.

    Returns:
      a string representation of the document schema.
    """
    schema = ""
    for key, value in obj.items():
        if not callable(value):  # we don't want to print functions
            # specify the specific data types you want to check
            specific_data_types = [list, dict]
            data_type = ""
            for data_type_class in specific_data_types:
                # if the current property is an instance of the data type
                if isinstance(value, data_type_class):
                    # get its name
                    data_type = f"==is_{data_type_class.__name__}=="
                    break
            # print to console (e.g., roles object is_list)
            schema = schema + f"{indent} {key} : {type(value).__name__} {data_type}"
            # if the current property is of dict type, print its sub-properties too
            if isinstance(value, dict):
                schema = schema + get_document_schema(value, indent + "\t")

    return schema


def mongo_get_collection_schema(collection_name: str) -> str:
    """
    Searches the collection and returns all the fields, field data types and indexes.

    Returns an error response if it encounters an error.
    """
    try:
        collection = db[collection_name]
        sample_document_collection = collection.find_one({})
        schema = f"{collection_name} SCHEMA : {get_document_schema(sample_document_collection)} INDEX INFO :\n{str(collection.index_information())}"
        return schema

    except Exception as e:
        return "Error : " + str(e)


def mongo_run_pipeline(pipeline_collection_object: str):
    """
    Extracts the pipeline and the collection name from the input object.
    Then, runs the pipeline on the collection and returns the result.

    Returns an error response if it encounters an error.
    """
    try:
        # Converting the string input from the llm to a dictionary
        pipeline_collection_object = eval(pipeline_collection_object)
        pipeline: list = pipeline_collection_object["pipeline"]
        collection_name = pipeline_collection_object["collection_name"]
        output = db[collection_name].aggregate(pipeline)
        return Common.cursor_to_dict(output)

    except Exception as e:
        return "Error : " + str(e)


def mongo_pipeline_checker(pipeline: str):
    """
    Runs the pipeline and uses an LLM to check that it will not cause any DML changes.
    Rewrites the pipeline if mistakes are detected.

    Returns an error response if it encounters an error.
    """
    try:
        pipeline_checker_prompt = """              
                {pipeline}

                Double check the pymongo pipeline above for common mistakes, including:
                - Syntactic errors 
                - Making DML actions (INSERT, UPDATE, DELETE, DROP etc.) on the database

                If there are any of the above mistakes, rewrite the pipeline. If there are no mistakes, just reproduce the original pipeline.
            """

        llm_chain = LLMChain(
            llm=llm,
            prompt=PromptTemplate(
                template=pipeline_checker_prompt, input_variables=["pipeline"]
            ),
        )
        response = llm_chain.predict(pipeline=pipeline)
        return response

    except Exception as e:
        return "Error : " + str(e)


def get_tools(db_connection):
    """
    The function `get_tools` returns a list of tools for interacting with a MongoDB database.

    Args:
      db_connection: The `db_connection` parameter is the connection object to the MongoDB database. It
    is used to establish a connection to the database and perform operations on it.

    Returns:
      a list of Tool objects.
    """
    global db
    db = db_connection
    mongo_get_collection_names_description = (
        "The tool searches the database and returns all the collection names as a list."
        "If an error response is returned then recheck your input and try again."
    )

    mongo_get_collection_schema_description = (
        "Input to this tool is a collection name."
        "The tool searches the collection and returns all the fields, field data types and indexes in the collection."
        "If an error response is returned then recheck your input and try again."
    )

    mongo_run_pipeline_description = (
        "Input to this tool is a python dictionary."
        "The dictionary should contain two fields :"
        "pipeline: The pymongo pipeline, collection_name: The collection name on which pipeline is to be run."
        "The tool runs the pipeline on the given collection and returns the response."
        "If an error response is returned then rewrite your pipeline or collection name and try again."
    )

    mongo_pipeline_checker_description = (
        "Use this tool to double check if your pipeline is correct before executing it."
        "ALWAYS use this tool before executing a pipeline with mongo_run_pipeline!"
    )

    tools = [
        Tool(
            func=mongo_get_collection_names,
            name="mongo_get_collection_names",
            description=mongo_get_collection_names_description,
        ),
        Tool(
            func=mongo_get_collection_schema,
            name="mongo_get_collection_schema",
            description=mongo_get_collection_schema_description,
        ),
        Tool(
            func=mongo_run_pipeline,
            name="mongo_run_pipeline",
            description=mongo_run_pipeline_description,
            return_direct=True,
        ),
        Tool(
            func=mongo_pipeline_checker,
            name="mongo_pipeline_checker",
            description=mongo_pipeline_checker_description,
        ),
    ]

    return tools


def create_mongodb_agent(db_connection):
    """
    The function `create_mongodb_agent` creates and returns an agent executor for MongoDB with specified
    parameters.

    Args:
      db_connection: The `db_connection` parameter is the connection object or string that is used to
    connect to the MongoDB database. It is used to establish a connection to the database and retrieve
    the necessary tools for the agent.

    Returns:
      the agent_executor object.
    """
    tools = get_tools(db_connection)
    agent_executor = initialize_agent(
        tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
        agent_kwargs={
            "prefix": MONGODB_PREFIX,
            "format_instructions": FORMAT_INSTRUCTIONS,
            "suffix": MONGODB_SUFFIX,
        },
        return_intermediate_steps=True,
    )

    return agent_executor


def execute_pipeline(pipeline, collection, database):
    """
    The function `execute_pipeline` takes a pipeline, collection, and database as input, executes
    the pipeline on the specified collection in the database, and returns the result as a string.

    Args:
      pipeline: The pipeline parameter is a string representation of a MongoDB aggregation pipeline.
    It is a sequence of stages that define the operations to be performed on the data in the
    collection. Each stage in the pipeline performs a specific operation, such as filtering,
    sorting, grouping, or transforming the data.
      collection: The "collection" parameter refers to the name of the collection in the database
    where the pipeline will be executed. In MongoDB, a collection is a group of MongoDB documents,
    similar to a table in a relational database.
      database: The `database` parameter refers to the database object or connection that you are
    using to interact with the database. It is typically an instance of a database driver or client
    library that provides methods for executing queries and interacting with the database.

    Returns:
      a string representation of the output of the pipeline aggregation operation performed on the
    specified collection in the database. If an exception occurs during the execution of the
    pipeline, the function will return None.
    """
    try:
        pipeline = literal_eval(pipeline)
        output = database[collection].aggregate(pipeline)
        return Common.cursor_to_dict(output)

    except Exception as e:
        Common.exception_details("execute_pipeline", e)
        return None


def check_mongo_connection(client, database):
    """
    The function `check_mongo_connection` checks if a connection to a MongoDB database can be
    established by accessing the collection names.

    Args:
      client: The `client` parameter is an instance of the MongoDB client. It is used to connect to
    the MongoDB server and perform database operations.
      database: The `database` parameter is the name of the MongoDB database that you want to check
    the connection for.

    Returns:
      a boolean value. It returns True if the connection to the MongoDB database is successful and
    False if there is an exception or error.
    """
    try:
        # Just check if collection names can be accessed
        db = client[database]
        db.list_collection_names()
        return True
    except Exception as e:
        return False


def get_mongodb_database_connection(database_connection_info):
    """
    The function `get_mongodb_database_connection` establishes a connection to a MongoDB database
    using the provided connection information.

    Args:
      database_connection_info: The parameter `database_connection_info` is a dictionary that
    contains information about the MongoDB database connection. It typically includes the following
    keys:

    Returns:
      a MongoDB database connection object (db) if the connection is successful. If there is an
    error in establishing the connection, it returns None.
    """
    try:
        connection_string = get_connection_string(database_connection_info)
        client = pymongo.MongoClient(connection_string)
        db = client[database_connection_info["database"]]
        if db is not None:
            return db
        return None
    except Exception as e:
        print("Connection error: ", e)
        return None
