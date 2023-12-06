import os
import shutil

from bson import ObjectId
from google.cloud import storage

from app.config import Config
from app.config import Config
from app.models.mongoClient import MongoClient
from app.utils.common import Common
from app.utils.enumerator import Enumerator
from app.utils.pipelines import PipelineStages
from app.utils.production import Production


class UserManagementService:
    PRODUCTION_CHECK = Config.GCP_PROD_ENV

    def create_user(self, user_data):
        """
        The create_user function creates a new user in the database.

        Args:
            self: Represent the instance of the class
            user_data (dict): A dictionary containing all the information for a single user.

        Returns:
            The id of the user created
        """
        user_data["isActive"] = True

        m_db = MongoClient.connect()

        response = m_db[Config.MONGO_USER_MASTER_COLLECTION].insert_one(user_data)
        print(f"Record {response} inserted successfully!")

        if response:
            id = str(response.inserted_id)
            if self.PRODUCTION_CHECK:
                # Name of the folder you want to create
                folder_name = id + "/"

                bucket = Production.get_users_bucket()

                # Create an empty blob to represent the folder (blobs are like objects in GCS)
                folder_blob = bucket.blob(folder_name)
                # Upload an empty string to create an empty folder
                folder_blob.upload_from_string("")

                print(f"Created folder {folder_name} in bucket {bucket}!")
            else:
                folder_path = os.path.join(Config.USER_FOLDER, id)
                os.makedirs(folder_path, exist_ok=True)
                print("Folder created for user : ", id)

            return id

        return None

    def get_child_users(self, parent_user, user_id="", pageIndex=0, pageSize=0):
        """
        The function `get_child_users` retrieves child users based on the parent user and user ID, and
        returns the result as a dictionary.

        Args:
            parent_user: The `parent_user` parameter is the ID of the parent user for whom you want to
        retrieve the child users.
            user_id: The `user_id` parameter is an optional parameter that specifies the ID of a specific
        child user. If provided, the function will return information about that specific child user. If
        not provided, the function will return information about all child users under the specified
        `parent_user`.
            pageIndex: The current page index
            pageSize: The number of records in the page

        Returns:
            the result of the aggregation pipeline as a dictionary.
        """
        # print("Page index :", pageIndex)
        # print("Page size :" , pageSize)
        total_recs = 0
        m_db = MongoClient.connect()
        unset_fields = [
            "passwordHash",
            "subscription",
            "role",
            "image",
            "favourites",
            "recommends",
            "invoices"
        ]
        if user_id == "":
            skip = (pageIndex - 1) * pageSize
            total_recs = m_db[Config.MONGO_USER_MASTER_COLLECTION].count_documents(
                {
                    "parentUserId": ObjectId(parent_user),
                    "role": int(Enumerator.Role.Child.value),
                    "isActive": True,
                }
            )
            # print("Total records :", total_recs)
            # print("Limit :", pageSize)
            # print("Skip :", skip)
            pipeline = [
                PipelineStages.stage_match(
                    {
                        "parentUserId": ObjectId(parent_user),
                        "role": int(Enumerator.Role.Child.value),
                        "isActive": True,
                    }
                ),
                PipelineStages.stage_unset(unset_fields),
                {
                    "$group": {
                        "_id": "$_id",
                        "name": {"$first": "$name"},
                        "email": {"$first": "$email"},
                    }
                },
                # PipelineStages.stage_group({"_id": "$_id"})
                PipelineStages.stage_sort({"_id": 1}),
                PipelineStages.stage_skip(skip),
                PipelineStages.stage_limit(pageSize),
            ]
        else:
            print("Inside else statement")
            pipeline = [
                PipelineStages.stage_match(
                    {
                        "_id": ObjectId(user_id),
                        "parentUserId": ObjectId(parent_user),
                        "role": int(Enumerator.Role.Child.value),
                        "role": int(Enumerator.Role.Child.value),
                        "isActive": True,
                    }
                ),
                PipelineStages.stage_unset(unset_fields),
            ]
            # print("\nPipeline : ", pipeline)
        response = m_db[Config.MONGO_USER_MASTER_COLLECTION].aggregate(pipeline)

        return Common.cursor_to_dict(response), total_recs

    def get_user_menus(self, menu_ids):
        """
        The function `get_user_menus` retrieves menu information from a MongoDB database based on a list
        of menu IDs.
        
        :param menu_ids: A list of menu IDs that we want to retrieve from the database
        :return: If the length of `menu_ids` is greater than 0, a list of dictionaries containing the
        `id` and `name` of each menu is returned. If `menu_ids` is empty, `None` is returned.
        """
        m_db = MongoClient.connect()
        results = []
        if len(menu_ids) > 0:
            # Converting menus ids to object ids
            menu_ids = [ObjectId(id) for id in menu_ids]
            query = {"_id": {"$in": menu_ids}}
            menus = m_db[Config.MONGO_MENU_MASTER_COLLECTION].find(query)

            for menu in menus:
                results.append({"id": str(menu["_id"]), "name": str(menu["name"])})
            return results
        else:
            return None

    def edit_user(self, user_id, data, parent_user_id):
        """
        The function `edit_user` updates the data of a user in a MongoDB collection based on the
        provided user ID and parent user ID.

        Args:
          user_id: The user_id parameter is the unique identifier of the user that needs to be edited.
          data: The `data` parameter is a dictionary that contains the updated information for the user.
        It includes the following keys:
          parent_user_id: The `parent_user_id` parameter is the ID of the parent user. It is used to
        ensure that the user being edited belongs to the specified parent user.

        Returns:
          the number of documents modified in the database.
        """
        m_db = MongoClient.connect()
        print(f"Edit user {user_id} with data : ", data)
        # print(type(parent_user_id))
        try:
            response = m_db[Config.MONGO_USER_MASTER_COLLECTION].update_one(
                {"_id": ObjectId(user_id), "parentUserId": ObjectId(parent_user_id)},
                {
                    "$set": {
                        "name": data["name"],
                        "email": data["email"],
                        "permissions": {"menu": data["menus"]},
                    }
                },
            )
            return response.modified_count
        except Exception as e:
            Common.exception_details("usermanagementservice.py : edit_user", e)
            return None

    def delete_user(self, user_id, parent_user_id):
        """
        The `delete_user` function deletes a user from a database, removes their folder from Google
        Cloud Platform (GCP) or the local file system, and returns the number of deleted users.

        Args:
          user_id: The user_id parameter is the unique identifier of the user that needs to be deleted.
          parent_user_id: The `parent_user_id` parameter is the ID of the parent user. It is used to
        verify that the user being deleted belongs to the specified parent user.

        Returns:
          the number of documents deleted from the database if the user is successfully deleted from GCP
        or the file system. If the user is not deleted, it returns None.
        """
        m_db = MongoClient.connect()
        user_del_flag = False

        # 1. Delete folder from GCP and system
        # 2. Remove user from DB

        # Check if GCP
        if self.PRODUCTION_CHECK:
            bucket = Production.get_users_bucket()

            # Find folder whose name matches with user id
            blob = bucket.blob(user_id + "/")
            print("BLOB to delete : ", blob)
            blob.delete()
            user_del_flag = True
        else:
            folder_path = os.path.join(Config.USER_FOLDER, user_id)
            print("ROOT :", folder_path)
            if os.path.isdir(folder_path):
                # Iterate over all the files and subdirectories in the folder
                for filename in os.listdir(folder_path):
                    file_path = os.path.join(folder_path, filename)
                    # Check if it's a file or a directory
                    if os.path.isfile(file_path):
                        # Delete the file
                        os.remove(file_path)
                    else:
                        # Recursively delete the subdirectory
                        shutil.rmtree(file_path)

                # Delete empty folder
                os.rmdir(folder_path)
                user_del_flag = True
                print(f"Deleted folder: {folder_path}")
            else:
                print(f"Not a valid folder: {folder_path}")
                user_del_flag = False

        # If user is deleted from GCP / file system then delete it from database
        if user_del_flag == True:
            response = m_db[Config.MONGO_USER_MASTER_COLLECTION].delete_one(
                {"_id": ObjectId(user_id), "parentUserId": ObjectId(parent_user_id)}
            )
            print("User removed from database!")
            print(response)
            return response.deleted_count

        else:
            return None
