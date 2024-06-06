import os
import sys

import certifi
import pymongo

from app.config import Config


class MongoClient:
    __MongoDB = None

    def __init__(self):
        """
        The __init__ function is called when the class is instantiated.
        It sets up the connection to MongoDB and creates a database object that can be used by other functions in this class.

        Args:
            self: Represent the instance of the class

        Returns:
            The mongoclient object
        """
        if MongoClient.__MongoDB is None:
            connection_string = Config.MONGO_CONNECTION_STRING
            sys.stdout.flush()

            try:
                print(f"\n🔌 Mongo connection string : {connection_string}\n")
                print("🗳️ Connecting to database...")

                # Configuration settings for the MongoDB client
                client_settings = {
                    'maxPoolSize': 100,  # Maximum number of connections in the pool
                    'retryWrites': True,  # Automatically retry certain write operations if they fail
                    'heartbeatFrequencyMS': 10000,  # Send heartbeat messages every 10 seconds
                    'socketTimeoutMS': None,  # No timeout on socket operations (wait indefinitely)
                }

                if Config.GCP_PROD_ENV and not Config.TESTING:
                    # Include TLS CA file for secure connections in production
                    client_settings['tlsCAFile'] = certifi.where()

                # Create a MongoDB client with the specified settings
                client = pymongo.MongoClient(connection_string, **client_settings)

                database = client[Config.MONGO_DATABASE]

                MongoClient.__MongoDB = database
                print("☑️ Successfully connected to database!")

                # Flush the standard output buffer
                sys.stdout.flush()

            except Exception as e:
                print("error in connecting to db", e, file=sys.stderr)
                print(e, file=sys.stderr)
                sys.stderr.flush()
                raise Exception(e)

    @staticmethod
    def connect():
        """
        The connect function is a static method that returns the MongoDB instance.
        If it does not exist, it creates one and then returns it.

        Args:

        Returns:
            A mongodb instance
        """
        if MongoClient.__MongoDB is None:
            MongoClient()

        return MongoClient.__MongoDB
