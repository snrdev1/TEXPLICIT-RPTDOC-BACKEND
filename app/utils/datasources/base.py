import urllib.parse

from app.utils.common import Common
from app.utils.enumerator import Enumerator

from langchain.output_parsers import GuardrailsOutputParser
from rich import print
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI


def get_connection_string(database_connection_info):
    """
    The function `get_connection_string` takes in a dictionary of database connection information
    and returns the appropriate connection string based on the database type.

    Args:
      database_connection_info: The `database_connection_info` parameter is a dictionary that
    contains the following keys:

    Returns:
      a connection string based on the database type specified in the `database_connection_info`
    parameter. If the database type is MySQL, it returns a MySQL connection string. If the database
    type is SQL Server, it returns a SQL Server connection string. If the database type is MongoDB,
    it returns a MongoDB connection string. If the database type is not recognized, it returns an
    empty string.
    """
    try:
        username = urllib.parse.quote(database_connection_info["username"])
        password = urllib.parse.quote(database_connection_info["password"])
        host = database_connection_info["host"]
        port = database_connection_info["port"]
        database = urllib.parse.quote(database_connection_info["database"])
        datasource_type = database_connection_info["type"]

        # MySQL
        if datasource_type == int(Enumerator.DatasourceTypes.MYSQL.value):
            print("Returning MySQL connection string!")
            if len(username) == 0 and len(password) == 0:
                connection_string = f"mysql+pymysql://{host}:{port}/{database}"
            else:
                connection_string = (
                    f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
                )
            print("Connection String : ", connection_string)
            return connection_string

        # SQL Server
        elif datasource_type == int(Enumerator.DatasourceTypes.MSSQL.value):
            print("Returning SQL Server connection string!")
            if len(username) == 0 and len(password) == 0:
                connection_string = f"mysql+pymssql://{host}/{database}"
            else:
                connection_string = (
                    f"mysql+pymssql://{username}:{password}@{host}/{database}"
                )
            return connection_string

        # PostgreSQL
        elif datasource_type == int(Enumerator.DatasourceTypes.POSTGRESQL.value):
            print("Returning PostgreSQL connection string!")
            if len(username) == 0 and len(password) == 0:
                connection_string = f"postgresql+psycopg2://{host}:{port}/{database}"
            else:
                connection_string = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"
            return connection_string

        # MongoDB
        elif datasource_type == int(Enumerator.DatasourceTypes.MONGODB.value):
            print("Returning MongoDB connection string!")
            if len(username) == 0 and len(password) == 0:
                connection_string = f"mongodb://{host}:{port}/"
            else:
                connection_string = f"mongodb://{username}:{password}@{host}:{port}/"
            return connection_string

        else:
            return ""

    except Exception as e:
        Common.exception_details("utils.datasources.base get_connection_string", e)
        return ""


def get_limit(user_query):
    """
    The function `get_limit` takes a user query as input and uses a rail specification to determine the
    number of results the user wants. If the number is not specified, it returns -1.
    
    Args:
      user_query: The `user_query` parameter is a string that represents the natural language database
    query provided by the user.
    
    Returns:
      the value of the "limit" variable, which is extracted from the output of the model.
    """
    try:
        rail_spec = """
        <rail version="0.1">

        <output>
            <object name="output">
                <integer name="limit" format="valid-range: -1 100" />
            </object>
        </output>

        <prompt>

        Given the natural language database query, find the number of results the user wants.
        If not specified, then output -1.

        Query: {{query}}

        @complete_json_suffix_v2
        </prompt>
        </rail>
        """

        print("user query : ", user_query)
        output_parser = GuardrailsOutputParser.from_rail_string(rail_spec)
        print("Output parser guard base_prompt : ", output_parser.guard.base_prompt)
        prompt = PromptTemplate(
            template=output_parser.guard.base_prompt,
            input_variables=output_parser.guard.prompt.variable_names,
        )
        print("Output parser prompt : ", prompt)
        model = OpenAI(temperature=0)
        print("Model : ", model)
        output = model(prompt.format_prompt(query=user_query).to_string())
        print("Output : ", output)
        print("Output type : ", type(output))
        # limit = output_parser.parse(output)
        limit = eval(output)["limit"]
        print("Limit : ", limit)

        return limit

    except Exception as e:
        Common.exception_details("utils.datasources.base get_limit", e)
        return None
