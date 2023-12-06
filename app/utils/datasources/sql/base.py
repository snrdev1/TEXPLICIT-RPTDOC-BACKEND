from langchain.sql_database import SQLDatabase
from langchain.agents import AgentType, initialize_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.llms import OpenAI
from langchain.llms.openai import OpenAI
from sqlalchemy import create_engine

from app.utils.common import Common
from app.utils.datasources.base import get_connection_string, get_limit
from app.utils.datasources.sql.prompt import FORMAT_INSTRUCTIONS, SQL_PREFIX, SQL_SUFFIX


def excute_sql_query(sql, database_connection_info):
    """
    The function `excute_sql_query` executes an SQL query using the provided database connection
    information and returns the field names and response data.

    Args:
      sql: The `sql` parameter is a string that represents the SQL query you want to execute. It should
    be a valid SQL statement that can be executed by the database.
      database_connection_info: The `database_connection_info` parameter is a dictionary that contains
    the information needed to establish a connection to the database. It typically includes details such
    as the host, port, database name, username, and password.

    Returns:
      The function `excute_sql_query` returns a tuple containing two elements: `field_names` and
    `response`. `field_names` is a list of field names retrieved from the cursor description, and
    `response` is a list of rows fetched from the executed SQL query.
    """
    try:
        print("SQL to execute : ", sql)
        connection_string = get_connection_string(database_connection_info)
        engine = create_engine(url=connection_string)
        connection = engine.raw_connection()
        cursor = connection.cursor()
        cursor.execute(sql)

        field_names = [i[0] for i in cursor.description]
        response = list(cursor.fetchall())

        return field_names, response

    except Exception as e:
        Common.exception_details("utils.datasources.sql.base excute_sql_query", e)
        return None


def execute_query(query, datasource_information):
    """
    The `execute_query` function executes a SQL query on a database using the provided datasource
    information and returns the result.

    Args:
      query: The `query` parameter is a string that represents the SQL query that you want to execute on
    the database.
      datasource_information: The `datasource_information` parameter is a dictionary that contains
    information about the database connection. It typically includes details such as the database host,
    port, username, password, and database name. This information is used to establish a connection to
    the database and execute the SQL query.
      all_rows: The `all_rows` parameter is a boolean flag that determines whether to modify the
    captured SQL query to retrieve all rows from the database or not. If `all_rows` is set to `True`,
    the captured SQL query will be modified to retrieve all rows. If `all_rows` is set to. Defaults to
    False

    Returns:
      The function `execute_query` returns two values. The first value is the modified SQL query if it
    was captured, or None if no SQL query was captured. The second value is a dictionary containing the
    type of response (either "sql" or "agent") and the response data. If the response type is "sql", the
    dictionary contains the columns and output of the SQL query. If the response
    """
    try:
        db = get_sql_database_connection(datasource_information)
        agent = _create_sql_agent(db)
        response = agent(query)

        sql_query = None

        final_step = response["intermediate_steps"][-1][0]
        if final_step.tool == "sql_db_query":
            sql_query = final_step.tool_input
            print(f"SQL Captured! : {sql_query}")

        if sql_query:
            # Get limit from query via an LLM
            limit = get_limit(query)

            # If limit is valid and limit is something other than the default limit of langchain LLM
            if limit:
                # Modify the captured sql query
                sql_query = _modify_sql(sql_query, limit)

                print(f"SQL Modified : {sql_query}")

                # Run the modified sql query on the database
                field_names, sql_response = excute_sql_query(
                    sql_query, datasource_information
                )

            else:
                # Run the sql query on the database
                field_names, sql_response = excute_sql_query(
                    sql_query, datasource_information
                )

            return sql_query, {
                "type": "sql",
                "response": {"columns": field_names, "output": sql_response},
            }

        else:
            return None, {
                "type": "agent",
                "response": {"columns": [], "output": response["output"]},
            }

    except Exception as e:
        Common.exception_details("utils.datasources.sql.base execute_query: ", e)
        return None, None


def get_sql_database_connection(database_connection_info):
    """
    The function `get_sql_database_connection` attempts to establish a connection to a SQL database
    using the provided connection information and returns the database object if successful,
    otherwise it returns None.

    Args:
      database_connection_info: The `database_connection_info` parameter is the information required
    to establish a connection to the SQL database. It typically includes details such as the host,
    port, database name, username, and password.

    Returns:
      a SQLDatabase object if the connection is successful, otherwise it returns None.
    """
    try:
        connection_string = get_connection_string(database_connection_info)
        db = SQLDatabase.from_uri(connection_string)
        if db:
            return db
        return None
    except Exception as e:
        Common.exception_details(
            "utils.datasources.sql.base get_sql_database_connection: ", e
        )
        return None


def _create_sql_agent(
    db_connection,
    llm=OpenAI(temperature=0, verbose=True),
    agent_type: AgentType = AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    prefix: str = SQL_PREFIX,
    format_instructions: str = FORMAT_INSTRUCTIONS,
    suffix: str = SQL_SUFFIX,
    top_k: int = 10,
):
    """
    The function `_create_sql_agent` creates a SQL agent using the provided database connection and
    OpenAI language model.

    Args:
      db_connection: The `db_connection` parameter is the connection object or string that is used to
    connect to the database. It can be either a connection object or a string that specifies the
    connection details such as the database name, host, port, username, and password.
      llm: The `llm` parameter is an instance of the OpenAI language model. It is used for generating
    natural language responses based on the given inputs.
      agent_type (AgentType): The `agent_type` parameter specifies the type of SQL agent to be created.
    It is of type `AgentType` which is an enumeration. The possible values for `agent_type` are:
      prefix (str): The `prefix` parameter is a string that is used as the initial input to the language
    model. It typically contains some context or instructions for the model to follow when generating
    SQL queries.
      format_instructions (str): The `format_instructions` parameter is a string that specifies how the
    SQL query should be formatted. It provides instructions to the language model on how to structure
    the query output.
      suffix (str): The `suffix` parameter is a string that is appended to the end of the generated SQL
    query. It can be used to add any additional SQL statements or clauses that are required for the
    specific use case.
      top_k (int): The `top_k` parameter is used to specify the number of completions to return from the
    language model. It determines how many possible SQL queries the agent will generate and rank. The
    higher the value of `top_k`, the more options the agent will consider. Defaults to 10

    Returns:
      The function `_create_sql_agent` returns an instance of `agent_executor` if the execution is
    successful. If there is an exception, it returns `None`.
    """
    try:
        toolkit = SQLDatabaseToolkit(db=db_connection, llm=llm)

        agent_executor = initialize_agent(
            llm=llm,
            tools=toolkit.get_tools(),
            verbose=True,
            agent_type=agent_type,
            handle_parsing_errors=True,
            agent_kwargs={
                "prefix": prefix.format(dialect=toolkit.dialect, top_k=top_k),
                "format_instructions": format_instructions,
                "suffix": suffix,
            },
            return_intermediate_steps=True,
        )

        return agent_executor

    except Exception as e:
        Common.exception_details("utils.datasources.sql.base _create_sql_agent", e)
        return None


def _modify_sql(sql_query, limit):
    """
    The function `_modify_sql` modifies a SQL query by adding or removing a `LIMIT` clause based on the
    provided limit value.

    Args:
      sql_query: The `sql_query` parameter is a string that represents a SQL query. It is the query that
    you want to modify.
      limit: The `limit` parameter is an integer value that specifies the maximum number of rows to be
    returned by the SQL query. If the value of `limit` is -1, it means that there is no limit set and
    all rows should be returned.

    Returns:
      the modified SQL query with the provided limit value or without the existing 'LIMIT' clause. If
    the 'LIMIT' keyword is not found in the SQL query, it returns the original query. If an exception
    occurs during the execution of the function, it returns the original query as well.
    """
    try:
        # Find the last occurrence of 'LIMIT' in the SQL query
        limit_index = sql_query.rfind("LIMIT")

        if limit_index != -1:
            if limit != -1:
                # Replace the existing LIMIT clause with the provided limit value
                sql_with_limit = f"{sql_query[:limit_index]} LIMIT {limit}"
                return sql_with_limit.strip()
            else:
                # Remove the existing 'LIMIT' clause
                sql_without_limit = sql_query[:limit_index].strip()
                return sql_without_limit

        # If 'LIMIT' is not found, return the original query
        return sql_query

    except Exception as e:
        Common.exception_details("utils.datasources.sql.base _modify_sql", e)
        return sql_query
