from google.cloud import storage

from app.config import Config
from app.utils.common import Common


class Production:

    @staticmethod
    def get_bucket(bucket_name):
        """
        The function `get_bucket` returns a Google Cloud Storage bucket object based on the provided
        bucket name.

        Args:
          bucket_name: The `bucket_name` parameter is the name of the Google Cloud Storage bucket that
        you want to retrieve.

        Returns:
          The function `get_bucket` returns the bucket object if it is successfully retrieved, or `None`
        if there is an exception or error.
        """
        try:

            if Config.TESTING:
                # Credentials for GCP Connection
                credential_path = Config.GCP_SERVICE_ACCOUNT_FILE

                # Create a client object using the JSON credential file (For local testing purposes)
                client = storage.Client.from_service_account_json(credential_path)

            else:
                # For production environment
                client = storage.Client()

            # Replace 'your-bucket-name' with the actual name of your bucket
            bucket = client.get_bucket(bucket_name)

            return bucket

        except Exception as e:
            Common.exception_details("Production.get_bucket", e)
            return None

    @staticmethod
    def get_users_bucket():
        return Production.get_bucket(Config.GCP_BUCKET_USERS)
