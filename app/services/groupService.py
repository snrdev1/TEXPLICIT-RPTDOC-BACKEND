import os
import time
from datetime import datetime, timezone

from bson import ObjectId
from flask import request

from app.config import Config
from app.models.mongoClient import MongoClient
from app.services.userService import UserService
from app.utils.common import Common
from app.utils.pipelines import PipelineStages


class GroupService:
    GROUP_COLLECTION = Config.MONGO_GROUP_COLLECTION
    POST_COLLECTION = Config.MONGO_POST_COLLECTION
    POST_COMMENT_COLLECTION = Config.MONGO_POST_COMMENT_COLLECTION
    KI_COLLECTION = Config.MONGO_KI_COLLECTION
    USER_COLLECTION = Config.MONGO_USER_MASTER_COLLECTION

    def create_group(self, user_id, domain_id, name, description=""):
        """
        The create_group function creates a new group in the database.
            Args:
                user_id (str): The id of the user creating the group.
                domain_id (str): The id of the domain to which this group belongs.
                name (str): The name of this new group.

        Args:
            self: Represent the instance of the class
            user_id: Identify the user that is creating the group
            domain_id: Identify the domain that the group belongs to
            name: Create a name for the group
            description: Give a description of the group

        Returns:
            The Objectid of the newly created group

        """
        m_db = MongoClient.connect()

        group_info = {
            "name": name,
            "domainId": ObjectId(domain_id),
            "description": description,
            "createdBy": {"_id": ObjectId(user_id), "ref": "user"},
            "createdOn": datetime.utcnow(),
            "media": {"logo": ""},
            "members": [ObjectId(user_id)],
            "isActive": True,
        }

        response = m_db[self.GROUP_COLLECTION].insert_one(group_info)

        if response:
            return str(response.inserted_id)

        return None

    def get_by_name(self, name):
        """
        The function `get_by_name` retrieves a group from a MongoDB collection based on the provided
        name.

        Args:
          name: The `name` parameter is the name of the group that you want to retrieve from the
        database.

        Returns:
          either a dictionary representing the group that matches the given name, or None if no matching
        group is found.
        """
        m_db = MongoClient.connect()

        pipeline = [
            PipelineStages.stage_match({"name": name})
        ] + self._get_common_group_pipeline()

        group = m_db[self.GROUP_COLLECTION].aggregate(pipeline)

        if group:
            return Common.cursor_to_dict(group)
        else:
            return None

    def get_by_domain_and_user(self, domain_id, user_id):
        """
        The get_by_domain_and_user function is used to retrieve a group's ID by the domain and user IDs.

        Args:
            self: Represent the instance of the class
            domain_id: Find the domain that is associated with a group
            user_id: Find the group created by a specific user

        Returns:
            The id of the group
        """
        m_db = MongoClient.connect()

        response = m_db[self.GROUP_COLLECTION].find_one(
            {"domainId": ObjectId(domain_id), "createdBy._id": ObjectId(user_id)}
        )

        if response:
            return str(response["_id"])

        return None

    def get_by_id(self, group_id):
        """
        The get_by_id function is used to retrieve a group by its id.


        Args:
            self: Refer to the current instance of a class
            group_id: Find the group with that id

        Returns:
            A dictionary of the group with the specified id


        """
        m_db = MongoClient.connect()

        pipeline = [
            PipelineStages.stage_match({"_id": ObjectId(group_id)})
        ] + self._get_common_group_pipeline()

        group = m_db[self.GROUP_COLLECTION].aggregate(pipeline)

        return Common.cursor_to_dict(group)[0]

    def delete_group(self, group_id):
        """
        The delete_group function deletes a group from the database.

        Args:
            self: Reference the class itself
            group_id: Identify the group to be deleted

        Returns:
            A boolean

        """
        m_db = MongoClient.connect()

        delete_response = m_db[self.GROUP_COLLECTION].delete_one(
            {"_id": ObjectId(group_id)}
        )

        if delete_response.deleted_count > 0:
            return True
        else:
            return False

    def get_all_user_related_groups(self, user_id):
        """
        The get_all_user_related_groups function returns all groups that a user is related to.
            This includes groups that the user has created, and groups that the user is a member of.

        Args:
            self: Represent the instance of the class
            user_id: Find the user in the database

        Returns:
            A list of groups that the user is a member of

        """
        m_db = MongoClient.connect()

        pipeline = [
            PipelineStages.stage_match({"members": {"$in": [ObjectId(user_id)]}}),
        ] + self._get_common_group_pipeline()

        response = m_db[self.GROUP_COLLECTION].aggregate(pipeline)

        return Common.cursor_to_dict(response)

    def get_user_related_groups_by_domain_id(self, user_id, domain_id):
        """
        The get_user_related_groups_by_domain_id function returns a list of groups that the user is a member of.
            The function takes in two parameters:
                1) user_id - the id of the user whose related groups are being retrieved.
                2) domain_id - the id of the domain to which all returned groups belong.

        Args:
            self: Represent the instance of the class
            user_id: Find the groups that a user is in
            domain_id: Find the groups that are related to a specific domain

        Returns:
            A list of groups that the user is a member of
        """
        m_db = MongoClient.connect()

        pipeline = [
            PipelineStages.stage_match(
                {
                    "members": {"$in": [ObjectId(user_id)]},
                    "domainId": ObjectId(domain_id),
                }
            ),
        ] + self._get_common_group_pipeline()

        response = m_db[self.GROUP_COLLECTION].aggregate(pipeline)

        return Common.cursor_to_dict(response)

    def add_member(self, user_id, group_id):
        """
        The add_member function adds a user to the group.
            Args:
                user_id (str): The id of the user being added to the group.
                group_id (str): The id of the group that is adding a member.

        Args:
            self: Represent the instance of the class
            user_id: Add a user to the group
            group_id: Identify the group that we want to add a member to

        Returns:
            An update result object
        """
        m_db = MongoClient.connect()

        response = m_db[self.GROUP_COLLECTION].update_one(
            {"_id": ObjectId(group_id)}, {"$push": {"members": ObjectId(user_id)}}
        )

        return response

    def delete_member(self, user_id, group_id):
        """
        The delete_member function takes in a user_id and group_id, then deletes the member from the group.
            Args:
                user_id (str): The id of the user to be deleted from a group.
                group_id (str): The id of the group that will have its member deleted.

        Args:
            self: Represent the instance of the class
            user_id: Identify the user to be removed from the group
            group_id: Identify the group that the user is in

        Returns:
            The response from the mongodb update_one function

        """
        m_db = MongoClient.connect()

        response = m_db[self.GROUP_COLLECTION].update_one(
            {"_id": ObjectId(group_id)}, {"$pull": {"members": ObjectId(user_id)}}
        )

        return response

    def get_members_ids(self, group_id):
        """
        The get_members_ids function takes in a group_id and returns the members of that group.


        Args:
            self: Represent the instance of the class
            group_id: Find the group in the database

        Returns:
            A list of ids

        """
        m_db = MongoClient.connect()

        response = m_db[self.GROUP_COLLECTION].find_one({"_id": ObjectId(group_id)})

        return response["members"]

    def get_members(self, group_id):
        """
        The get_members function takes in a group_id and returns the members of that group.
            It does this by first connecting to the MongoDB database, then finding the document with
            an _id equal to ObjectId(group_id). Then it uses UserService() to get all users with ids in response['members'].

        Args:
            self: Represent the instance of the class
            group_id: Find the group in the database

        Returns:
            A list of users in a group

        """
        m_db = MongoClient.connect()

        response = m_db[self.GROUP_COLLECTION].find_one({"_id": ObjectId(group_id)})

        users = UserService().get_user_by_ids(response["members"])

        return users

    def get_group_creator(self, group_id):
        """
        The function `get_group_creator` retrieves the creator of a group based on the group ID.

        Args:
          group_id: The group_id parameter is the unique identifier of the group for which you want to
        retrieve the creator.

        Returns:
          the string representation of the "_id" field of the "createdBy" object in the response.
        """
        m_db = MongoClient.connect()

        response = m_db[self.GROUP_COLLECTION].find_one({"_id": ObjectId(group_id)})

        return str(response["createdBy"]["_id"])

    def get_post_creator(self, post_id):
        """
        The function `get_post_creator` retrieves the ID of the user who created a post with the given
        post ID.

        Args:
          post_id: The post_id parameter is the unique identifier of the post for which you want to
        retrieve the creator.

        Returns:
          the ID of the user who created the post.
        """
        m_db = MongoClient.connect()

        response = m_db[self.POST_COLLECTION].find_one({"_id": ObjectId(post_id)})

        return str(response["postedBy"]["id"])

    def get_posted_knowledge_item(self, ki_id, group_id):
        """
        The function `get_posted_knowledge_item` retrieves a knowledge item from a MongoDB collection
        based on its ID and group ID.

        Args:
          ki_id: The `ki_id` parameter is the ID of the knowledge item that you want to retrieve. It is
        expected to be a string representing the Object ID of the knowledge item.
          group_id: The `group_id` parameter is the unique identifier of the group to which the
        knowledge item belongs.

        Returns:
          the knowledge item that matches the given ki_id and group_id.
        """
        m_db = MongoClient.connect()

        response = m_db[self.POST_COLLECTION].find_one(
            {"itemId": ObjectId(ki_id), "groupId": ObjectId(group_id)}
        )

        return response

    def post_knowledge_item(self, user_id, ki_id, group_id, caption=""):
        """
        The function `post_knowledge_item` posts a knowledge item with the given user ID, knowledge item
        ID, group ID, and optional caption.

        Args:
          user_id: The user ID of the user who is posting the knowledge item.
          ki_id: The `ki_id` parameter is the ID of the knowledge item that you want to post. This ID is
        used to identify the specific knowledge item in the database.
          group_id: The `group_id` parameter is the unique identifier of the group where the knowledge
        item will be posted.
          caption: The "caption" parameter is an optional parameter that allows you to provide a caption
        for the knowledge item being posted. It is a string that can be used to provide additional
        information or context about the knowledge item. If no caption is provided, it will default to
        an empty string.

        Returns:
          the ID of the inserted document as a string if the insertion is successful. If the insertion
        fails, it returns None.
        """
        m_db = MongoClient.connect()

        data = {
            "itemId": ObjectId(ki_id),
            "groupId": ObjectId(group_id),
            "caption": caption,
            "postedBy": {"id": ObjectId(user_id), "ref": "user"},
            "postDate": datetime.utcnow(),
            "likes": [],
        }

        response = m_db[self.POST_COLLECTION].insert_one(data)

        if response:
            return str(response.inserted_id)

        return None

    def delete_post(self, post_id):
        """Delete a knowledge item from a group

        Args:
            self.DB (str): The mongo database to work on
            ki_id (str): The Id of knowledge item to delete
            group_id (str): The Id of group from which knowledge item is to be deleted

        Returns:
            boolean: Status, whether the KI was deleted or not
        """
        m_db = MongoClient.connect()
        print("Post id : ", post_id)
        print("Post id type :", type(post_id))
        delete_response = m_db[self.POST_COLLECTION].delete_one(
            {"_id": ObjectId(post_id)}
        )

        if delete_response.deleted_count > 0:
            return True
        else:
            return False

    def get_all_knowledge_items(
        self,
        groups,
        query="",
        media_tags=[],
        domains=None,
        start_date=None,
        end_date=None,
        offset=0,
        limit=10,
        sort_order=-1,
    ):
        """
        The function `get_all_knowledge_items` retrieves knowledge items based on various filters such
        as groups, query, media tags, domains, start and end dates, offset, limit, and sort order.

        Args:
          groups: A list of group IDs to filter the knowledge items by.
          query: The search query to filter knowledge items based on text search.
          media_tags: The `media_tags` parameter is used to filter knowledge items based on specific
        tags. It accepts a list of tags as input.
          domains: The "domains" parameter is used to filter knowledge items by their domain. It accepts
        a list of domain IDs.
          start_date: The `start_date` parameter is used to specify the start date for filtering
        knowledge items. It is a string representing a date in ISO format (e.g.,
        "2022-01-01T00:00:00Z").
          end_date: The `end_date` parameter is used to specify the end date of the date range for
        filtering the knowledge items. It is a string representing a date in ISO format (e.g.,
        "2022-12-31T23:59:59Z").
          offset: The offset parameter is used to specify the starting point of the results. It
        determines how many items to skip before returning the results. For example, if offset is set to
        10, the first 10 items will be skipped and the results will start from the 11th item. Defaults
        to 0
          limit: The "limit" parameter specifies the maximum number of knowledge items to retrieve in a
        single query. Defaults to 10
          sort_order: The `sort_order` parameter determines the order in which the knowledge items are
        sorted. A value of `-1` indicates descending order (from newest to oldest), and a value of `1`
        indicates ascending order (from oldest to newest).

        Returns:
          a cursor to a MongoDB collection.
        """

        m_db = MongoClient.connect()

        print("Domanins :  ", domains)
        print("Groups : ", groups)

        pipeline_group_details = [
            {
                "$lookup": {
                    "from": "GROUP_MASTER",
                    "let": {"gid": "$groupId"},
                    "pipeline": [{"$match": {"$expr": {"$eq": ["$_id", "$$gid"]}}}],
                    "as": "group",
                }
            }
        ]

        pipeline_user_details = [
            {
                "$lookup": {
                    "from": "USER_MASTER",
                    "let": {"uid": "$postedBy.id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$_id", "$$uid"]}}},
                        {"$project": {"name": 1, "image": 1}},
                    ],
                    "as": "postedBy",
                }
            }
        ]

        pipeline_ki_details = [
            {
                "$lookup": {
                    "from": "KNOWLEDGE_ITEM_MASTER",
                    "let": {"kid": "$postdata.itemId"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$eq": ["$_id", "$$kid"]
                                },  # Check if _id equals $$kid
                            },
                        },
                        {"$addFields": {"url": "$metadata.url"}},
                        {"$unset": ["embeddings", "original", "metadata", "summary"]},
                    ],
                    "as": "ki",
                }
            }
        ]

        pipeline_ki_details += [
            {"$unwind": "$ki"},
            {
                "$project": {
                    "_id": "$ki._id",
                    "title": "$ki.title",
                    "description": "$ki.description",
                    "domainId": "$ki.domainId",
                    "tags": "$ki.tags",
                    "thumbnail": "$ki.thumbnail",
                    "postdata": 1,
                }
            },
        ]
        pipeline_domain_details = [
            {
                "$lookup": {
                    "from": "DOMAIN_MASTER",
                    "let": {"did": "$domainId"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$_id", "$$did"]}}},
                        {"$project": {"_id": 0, "topic": 1}},
                    ],
                    "as": "domainName",
                }
            }
        ]
        if media_tags != []:
            pipeline_ki_details[0]["$lookup"]["pipeline"][0]["$match"]["tags"] = {
                "$in": media_tags
            }
        if query != "":
            pipeline_ki_details[0]["$lookup"]["pipeline"][0]["$match"]["$text"] = {
                "$search": query
            }
        if domains is not None:
            pipeline_ki_details[0]["$lookup"]["pipeline"][0]["$match"]["domainId"] = {
                "$in": domains
            }

        pipeline_comment_details = [
            {
                "$lookup": {
                    "from": "POST_COMMENT",
                    "let": {"pid": "$postdata._id"},
                    "pipeline": [
                        {"$match": {"$expr": {"$eq": ["$ki.type", "$$pid"]}}},
                        {
                            "$project": {
                                "comment": 1,
                            }
                        },
                    ],
                    "as": "commentData",
                }
            }
        ]
        print("Start date : ", start_date)
        print("End date : ", end_date)
        if start_date != None and end_date != None:
            start_date = datetime.fromisoformat(start_date[:-1]).astimezone(
                timezone.utc
            )
            end_date = datetime.fromisoformat(end_date[:-1]).astimezone(timezone.utc)
            pipeline = [
                {
                    "$match": {
                        "$and": [
                            {"groupId": {"$in": groups}},
                            {"postDate": {"$gte": start_date, "$lte": end_date}},
                        ]
                    }
                }
            ]
        else:
            pipeline = [{"$match": {"groupId": {"$in": groups}}}]
        group_logo_route = request.host_url + "groups/media/logo/"
        pipeline += [
            {
                "$addFields": {
                    "likes": {
                        "$map": {
                            "input": "$likes",
                            "as": "like",
                            "in": {"$toString": "$$like"},
                        }
                    }
                }
            },
            *pipeline_user_details,
            *pipeline_group_details,
            {"$addFields": {"postdata": "$$ROOT"}},
            {"$project": {"_id": 0, "postdata": 1}},
            {"$unwind": "$postdata.group"},
            {
                "$addFields": {
                    "postdata.group.media.logo": {
                        "$cond": {
                            "if": {"$ne": ["$postdata.group.media.logo", ""]},
                            "then": {
                                "$concat": [
                                    group_logo_route,
                                    "$postdata.group.media.logo",
                                ]
                            },
                            "else": "$group.media.logo",
                        }
                    }
                }
            },
            *pipeline_ki_details,
            *pipeline_domain_details,
            *pipeline_comment_details,
            PipelineStages.stage_skip(offset),
            PipelineStages.stage_limit(limit),
        ]
        # query = "automotive "
        # if query and query != "":
        #     print("Filter by query!")
        #     pipeline += [{"$match":{"$text": {"$search": query}}}]

        # if domains:
        #     print("Filter by domains!")
        #     domains = [ObjectId(domain_id) for domain_id in domains]
        #     pipeline += [PipelineStages.stage_match({"domainId": {"$in": domains}})]

        # if media_tags:
        #     print("Filter by media_tags!")
        #     pipeline += [PipelineStages.stage_match({"tags": {"$in": media_tags}})]
        # print("\n\nPipeline : ", pipeline)
        st = time.time()
        response = m_db[self.POST_COLLECTION].aggregate(pipeline)
        et = time.time()
        # print("total time", et - st)

        return Common.cursor_to_dict(response)

    def save_or_update_logo(self, group_id, image=None):
        """
        The function `save_or_update_logo` saves or updates a group logo image file in a specified
        folder and updates the corresponding database record.

        Args:
          group_id: The group_id parameter is the unique identifier of the group for which the logo is
        being saved or updated.
          image: The `image` parameter is an optional parameter that represents the logo image file to
        be saved or updated. It is expected to be a file object.

        Returns:
          the number of modified documents in the database if the update operation is successful. If the
        update operation fails or there is no response, it returns None.
        """
        # Ensure that the group image upload folder exists
        os.makedirs(Config.GROUP_IMAGE_UPLOAD_FOLDER, exist_ok=True)

        if image and Common.allowed_file(image.filename):
            file_extension = Common.get_file_extension(image.filename)
            filename = str(group_id) + "__group_logo__" + "." + file_extension
            print("filename : ", filename)
            print(
                "Config.GROUP_IMAGE_UPLOAD_FOLDER : ",
                Config.GROUP_IMAGE_UPLOAD_FOLDER,
            )
            image_path = os.path.join(Config.GROUP_IMAGE_UPLOAD_FOLDER, filename)
            print("Image path: " + image_path)
            image.save(image_path)

            # path_to_private_key = Environment().GCP_PRIVATE_KEY_PATH
            # client = storage.Client()

            # bucket = client.bucket(Environment().BUCKET_NAME)
            # blob = bucket.blob(filename)
            # blob.upload_from_string(image.read())

            m_db = MongoClient.connect()

            query = {"_id": ObjectId(group_id), "isActive": True}
            value = {"$set": {"media.logo": str(filename)}}
            # value = {"$set": {"groupImg": "https://storage.cloud.google.com/" \
            # + str(Environment().BUCKET_NAME)+"/" + str(filename)}}
            response = m_db[self.GROUP_COLLECTION].update_one(query, value)

            if response:
                return str(response.modified_count)

            return None

    def save_or_update_group_data(self, group_id, name=None, description=None):
        """
        The function saves or updates group data in a MongoDB collection based on the provided group ID,
        name, and description.

        Args:
          group_id: The group_id parameter is the unique identifier of the group whose data needs to be
        saved or updated.
          name: The name parameter is a string that represents the new name for the group. It is
        optional and can be None if no name update is required.
          description: The "description" parameter is an optional parameter that represents the new
        description value for the group. If provided, it will update the description of the group with
        the new value.

        Returns:
          the number of documents modified in the database if the update operation is successful. If the
        update operation fails or no documents are modified, it returns None.
        """
        m_db = MongoClient.connect()

        query = {"_id": ObjectId(group_id), "isActive": True}
        new_values = {}
        if name:
            new_values["name"] = name.strip()
        if description:
            new_values["description"] = description.strip()

        value = {"$set": new_values}

        response = m_db[self.GROUP_COLLECTION].update_one(query, value)

        if response:
            return str(response.modified_count)

        return None

    def get_post_by_id(self, post_id):
        """
        The function `get_post_by_id` retrieves a post from a MongoDB collection based on its ID and
        performs some data transformations before returning the result.

        Args:
          post_id: The `post_id` parameter is the unique identifier of the post you want to retrieve
        from the database.

        Returns:
          the first document that matches the given post_id after performing some transformations on the
        fields.
        """
        m_db = MongoClient.connect()

        pipeline = [
            PipelineStages.stage_match({"_id": ObjectId(post_id)}),
            PipelineStages.stage_add_fields(
                {
                    "_id": {"$toString": "$_id"},
                    "groupId": {"$toString": "$groupId"},
                    "itemId": {"$toString": "$itemId"},
                    "postDate": {"$dateToString": {"date": "$postDate"}},
                    "postedBy.id": {"$toString": "$postedBy.id"},
                    "ref": "ref",
                    "likes": {
                        "$map": {
                            "input": "$likes",
                            "as": "like",
                            "in": {"$toString": "$$like"},
                        }
                    },
                }
            ),
        ]

        response = m_db[self.POST_COLLECTION].aggregate(pipeline)

        return Common.cursor_to_dict(response)[0]

    def update_post_likes(self, post_id, likes):
        """
        The function updates the likes of a post in a MongoDB collection.

        Args:
          post_id: The post_id parameter is the unique identifier of the post that needs to be updated.
          likes: A list of user IDs who have liked the post.

        Returns:
          the number of documents that were modified in the database.
        """
        m_db = MongoClient.connect()

        # Convert all user_id to ObjectId
        likes = [ObjectId(user_id) for user_id in likes]

        response = m_db[self.POST_COLLECTION].update_one(
            {"_id": ObjectId(post_id)}, {"$set": {"likes": likes}}
        )

        return response.modified_count

    @staticmethod
    def get_image_path(image_name):
        """
        The function `get_image_path` takes an image name as input and returns the full path of the
        image file.

        Args:
          image_name: The name of the image file.

        Returns:
          the image path, which is the result of joining the "GROUP_IMAGE_UPLOAD_FOLDER" directory path
        with the provided image name.
        """
        image_path = os.path.join(Config.GROUP_IMAGE_UPLOAD_FOLDER, image_name)
        return image_path

    @staticmethod
    def _get_common_group_pipeline():
        """
        The _get_common_group_pipeline function is used to create a common pipeline for all group queries.
        It adds the following fields:
            - _id (string)
            - createdOn (string)
            - createdBy._id (string) and ref
            - domainId (string)
            - member_count (# of members in the group, integer value), and members array with each member's id as string values.

        Args:

        Returns:
            A list of stages

        """
        group_logo_route = request.host_url + "groups/media/logo/"

        common_group_pipeline = [
            PipelineStages.stage_add_fields(
                {
                    "_id": {"$toString": "$_id"},
                    "createdOn": {"$toString": "$createdOn"},
                    "createdBy": {
                        "_id": {"$toString": "$createdBy._id"},
                        "ref": "$createdBy.ref",
                    },
                    "domainId": {"$toString": "$domainId"},
                    "member_count": {"$size": "$members"},
                    "members": {
                        "$map": {
                            "input": "$members",
                            "as": "member",
                            "in": {"$toString": "$$member"},
                        }
                    },
                    "media.logo": {
                        "$cond": {
                            "if": {"$ne": ["$media.logo", ""]},
                            "then": {"$concat": [group_logo_route, "$media.logo"]},
                            "else": "$media.logo",
                        }
                    },
                }
            )
        ]

        return common_group_pipeline
