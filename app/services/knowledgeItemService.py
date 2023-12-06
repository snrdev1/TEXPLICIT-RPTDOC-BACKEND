import datetime
from urllib.parse import parse_qs, urlparse

from bson import ObjectId

from app.config import Config
from app.models.mongoClient import MongoClient
from app.services.userService import UserService
from app.utils import constants as Constants
from app.utils.common import Common
from app.utils.email_helper import EmailHelper
from app.utils.enumerator import Enumerator
from app.utils.parser import Parser
from app.utils.pipelines import PipelineStages


class KnowledgeItemService:

    # ADMIN

    def get_pending_kis(
        self, query=None, tags=[], sortby="score", sortorder=-1, offset=0, limit=10
    ):
        """
        The function `get_pending_kis` retrieves pending knowledge items (KIs) based on specified
        filters and sorting criteria.

        Args:
          query: The `query` parameter is used to specify a search query to filter the results. It is an
        optional parameter and can be set to `None` if no search query is needed.
          tags: The `tags` parameter is a list of tags that can be used to filter the results. Only
        knowledge items that have at least one of the specified tags will be returned.
          sortby: The "sortby" parameter determines the field by which the results should be sorted. It
        can have two possible values: "score" or "created". If "score" is chosen, the results will be
        sorted by the score of the documents. If "created" is chosen, the results will. Defaults to
        score
          sortorder: The `sortorder` parameter determines the order in which the results are sorted.
          offset: The offset parameter is used to specify the number of documents to skip before
        returning the results. It is used for pagination purposes. For example, if offset is set to 10,
        the first 10 documents will be skipped and the results will start from the 11th document.
        Defaults to 0
          limit: The `limit` parameter determines the maximum number of results to be returned by the
        function. In this case, it is set to 10, which means that the function will return a maximum of
        10 pending KIs. Defaults to 10

        Returns:
          a list of dictionaries representing the pending KIs (Knowledge Items) that match the given
        query and filters.
        """
        if sortby not in ["score", "created"]:
            sortby = "score"

        search_pipeline = []
        if query:
            search_pipeline = [
                PipelineStages.stage_match({"$text": {"$search": query}})
            ]

        # If tags have been passed in as filter
        if tags:
            search_pipeline += [PipelineStages.stage_match({"tags": {"$in": tags}})]

        ki_pipeline = self.get_general_ki_pipeline()
        common_pipeline = [
            PipelineStages.stage_sort({sortby: sortorder, "_id": sortorder}),
            PipelineStages.stage_skip(offset),
            PipelineStages.stage_limit(limit),
        ]

        pipeline = search_pipeline + ki_pipeline + common_pipeline

        m_db = MongoClient.connect()
        kis = m_db[Config.MONGO_KI_PENDING_COLLECTION].aggregate(pipeline)

        return Common.cursor_to_dict(kis)

    def get_pending_knowledge_item_by_id(self, ki_id):
        """
        The function `get_pending_knowledge_item_by_id` retrieves a pending knowledge item from a
        MongoDB collection based on its ID.

        Args:
          ki_id: The `ki_id` parameter is the ID of the knowledge item that you want to retrieve.

        Returns:
          the knowledge item with the specified ID from the pending knowledge item collection. If an
        error occurs, it returns None.
        """
        try:
            pipeline = [PipelineStages.stage_match({"_id": ObjectId(ki_id)})]
            m_db = MongoClient.connect()
            ki = m_db[Config.MONGO_KI_PENDING_COLLECTION].aggregate(pipeline)

            return Common.cursor_to_dict(ki)

        except Exception as e:
            Common.exception_details(
                "knowlegdeItemService.get_pending_knowledge_item_by_id", e
            )
            return None

    def approve_knowledge_item(self, ki_id):
        """
        The `approve_knowledge_item` function updates the status of a knowledge item from pending to
        approved, transfers it from the pending collection to the master collection, sends an email
        notification to the creator, and returns the updated knowledge item.
        
        Args:
          ki_id: The `ki_id` parameter is the unique identifier of the knowledge item that needs to be
        approved.
        
        Returns:
          The function `approve_knowledge_item` returns a tuple containing three values: a boolean value
        indicating the success of the operation, the knowledge item that was approved, and the ID of the
        inserted knowledge item in the master collection.
        """
        try:
            # Update status of the knowledge item in the knowledgeitem pending collection
            m_db = MongoClient.connect()

            # query to retrieve pending query
            query = {"_id": ObjectId(ki_id)}
            
            # Transfer ki from pending to master collection
            ki = m_db[Config.MONGO_KI_PENDING_COLLECTION].find_one(query)
            
            # Insert into master collection
            # Changing the ki status
            ki["status"] = int(Enumerator.KnowledgeItemStatus.Approved.value)
            # Adding a likes array
            ki["likes"] = []
            ki_master_insert_response = m_db[Config.MONGO_KI_COLLECTION].insert_one(ki)
                
            # Delete the KI from pending collection
            m_db[Config.MONGO_KI_PENDING_COLLECTION].delete_one(query)

            # Send a mail to the user
            creator = UserService().get_user_by_id(ki["createdBy"]["user_id"])

            mailBody = Constants.KI_APPROVED_MAILBODY.format(
                receiver=creator["name"],
                ki_title=ki["title"],
                sender=Config.MAIL_SENDER_NAME
            )

            receivers = []
            receivers.append({"name": creator["name"], "email": creator["email"]})

            success = EmailHelper.send_mail(
                Constants.KI_APPROVED_MAILSUBJECT, mailBody, receivers, None
            )

            return (
                True,
                ki,
                str(ki_master_insert_response.inserted_id),
            )

        except Exception as e:
            Common.exception_details("knowlegdeItemService.approve_knowledge_item", e)
            return None, None, None

    def reject_knowledge_item(self, ki_id, reasons=[], reason_comment=""):
        """
        The `reject_knowledge_item` function rejects a knowledge item by updating its status, adding
        rejection reasons, transferring it to the rejected collection, deleting it from the pending
        collection, and sending a rejection email to the creator.

        Args:
          ki_id: The `ki_id` parameter is the unique identifier of the knowledge item that needs to be
        rejected.
          reasons: A list of reasons for rejecting the knowledge item. Each reason is a string.
          reason_comment: The `reason_comment` parameter is an optional comment that can be provided to
        further explain the reason for rejecting the knowledge item. It is a string that can be used to
        provide additional context or details about the rejection.

        Returns:
          the number of modified documents in the knowledge item pending collection if the rejection
        process is successful. If there is an error or an exception occurs, it returns None.
        """
        try:
            # Construct reason text
            reason_text = ""
            if len(reasons) > 0:
                formatted_reasons = "<br/>".join(
                    [f"{index + 1}: {item}" for index, item in enumerate(reasons)]
                )
                reason_text = (
                    "<br/><br/>"
                    + Enumerator.KiRejectionReason.preface.value
                    + "<br/>"
                    + formatted_reasons
                )

            # If a reason comment exists
            if reason_comment and reason_comment != "":
                reason_text += (
                    "<br/><br/>"
                    + Enumerator.KiRejectionReason.suffix.value
                    + reason_comment
                    + "."
                )

            # Update status of the knowledge item in the knowledgeitem pending collection
            m_db = MongoClient.connect()

            query = {"_id": ObjectId(ki_id)}
            new_values = {
                "$set": {
                    "status": int(Enumerator.KnowledgeItemStatus.Rejected.value),
                    "rejectionReason": reason_text,
                }
            }
            response = m_db[Config.MONGO_KI_PENDING_COLLECTION].update_one(query, new_values)

            if response:
                # Transfer ki from pending to master collection
                ki = m_db[Config.MONGO_KI_PENDING_COLLECTION].find_one({"_id": ObjectId(ki_id)})

                # Insert into rejected collection
                m_db[Config.MONGO_KI_REJECTED_COLLECTION].insert_one(ki)

                # Delete from pending collection
                m_db[Config.MONGO_KI_PENDING_COLLECTION].delete_one(ki)

                # Send a mail to the user
                creator = UserService().get_user_by_id(ki["createdBy"]["user_id"])

                mailBody = Constants.KI_REJECTED_MAILBODY.format(
                    receiver=creator["name"],
                    ki_title=ki["title"],
                    reason=reason_text,
                    sender=Config.MAIL_SENDER_NAME
                )

                receivers = []
                receivers.append({"name": creator["name"], "email": creator["email"]})

                success = EmailHelper.send_mail(
                    Constants.KI_REJECTED_MAILSUBJECT, mailBody, receivers, None
                )

                return str(response.modified_count)

            return None

        except Exception as e:
            Common.exception_details("knowlegdeItemService.approve_knowledge_item", e)
            return None

    # USER

    def get_kis_by_domain_id(
        self,
        domain_id,
        query=None,
        tags=[],
        sortby="score",
        sortorder=-1,
        offset=0,
        limit=10,
    ):
        """
        The function `get_kis_by_domain_id` retrieves Knowledge Items (KIs) based on a domain ID, with
        optional filtering by query, tags, sorting, offset, and limit.

        Args:
          domain_id: The `domain_id` parameter is the ID of the domain for which you want to retrieve
        the Knowledge Items (KIs).
          query: The `query` parameter is used to specify a search query to filter the knowledge items.
        It is a string that represents the search query.
          tags: The "tags" parameter is a list of tags that can be used to filter the Knowledge Items.
        Only the Knowledge Items that have at least one of the specified tags will be returned.
          sortby: The "sortby" parameter determines the field by which the Knowledge Items (KIs) should
        be sorted. It can have two possible values: "score" or "created". If "score" is chosen, the KIs
        will be sorted by their score in descending order. If "created". Defaults to score
          sortorder: The parameter "sortorder" determines the order in which the results are sorted. It
        accepts two values: 1 for ascending order and -1 for descending order. In the given code, the
        default value for "sortorder" is -1, which means the results will be sorted in descending order
          offset: The offset parameter is used to specify the number of documents to skip before
        starting to return the documents. It is used for pagination purposes. Defaults to 0
          limit: The "limit" parameter determines the maximum number of Knowledge Items (KIs) to be
        returned in the result. It specifies the number of KIs that should be included in the response.
        Defaults to 10

        Returns:
          a list of Knowledge Items (KIs) that match the specified criteria. The KIs are retrieved from
        a MongoDB collection and are filtered by the domain ID, query, tags, and sorted based on the
        specified sortby and sortorder parameters. The function returns a limited number of KIs based on
        the offset and limit parameters.
        """
        if sortby not in ["score", "created"]:
            sortby = "score"

        m_db = MongoClient.connect()

        search_pipeline = []
        if query:
            search_pipeline = [
                PipelineStages.stage_match({"$text": {"$search": query}})
            ]

        # If tags have been passed in as filter
        if tags:
            search_pipeline += [PipelineStages.stage_match({"tags": {"$in": tags}})]

        # Filter the Knowledge Items by the domain
        search_pipeline += [
            PipelineStages.stage_match({"domainId": ObjectId(domain_id)})
        ]

        ki_pipeline = self.get_general_ki_pipeline()
        common_pipeline = [
            PipelineStages.stage_sort({sortby: sortorder, "_id": sortorder}),
            PipelineStages.stage_skip(offset),
            PipelineStages.stage_limit(limit),
        ]

        unset_fields = ['embeddings', 'highlightsSummary', 'domain.keywords']

        pipeline = search_pipeline + ki_pipeline + common_pipeline + [PipelineStages.stage_unset(unset_fields)]
        kis = m_db[Config.MONGO_KI_COLLECTION].aggregate(pipeline)

        return Common.cursor_to_dict(kis)

    def get_domain_id(self, ki_id):
        """
        The function `get_domain_id` retrieves the domain ID associated with a given KI ID from a
        MongoDB collection.

        Args:
          ki_id: The `ki_id` parameter is the identifier of a document in the Config.MONGO_KI_COLLECTION collection.

        Returns:
          the value of the "domainId" field from the document in the Config.MONGO_KI_COLLECTION collection that
        matches the given ki_id.
        """
        m_db = MongoClient.connect()

        response = m_db[Config.MONGO_KI_COLLECTION].find_one({"_id": ObjectId(ki_id)})

        return response["domainId"]

    def get_ki_by_id(self, ki_id):
        """Retrieve a specific Knowledge items for a user

        Args:
            ki_id (str): KI ID

        Returns:
            A specific Knowledge Item corresponding to a particular KI ID
        """

        m_db = MongoClient.connect()

        ki_pipeline = self.get_general_ki_pipeline()

        pipeline = [PipelineStages.stage_match({"_id": ObjectId(ki_id)})] + ki_pipeline

        ki = m_db[Config.MONGO_KI_COLLECTION].aggregate(pipeline)

        return Common.cursor_to_dict(ki)[0]

    def get_by_url(self, user_id, url):
        """
        The `get_by_url` function takes a user ID and a URL as input and retrieves a knowledge item from
        a MongoDB database based on the URL.

        Args:
          user_id: The `user_id` parameter is used to identify the user for whom the knowledge item is
        being retrieved. It is not directly used in the `get_by_url` method, but it is likely used
        elsewhere in the code to determine the context or permissions of the user.
          url: The `url` parameter is a string that represents the URL of a podcast episode, YouTube
        video, book, PubMed article, ScienceDirect article, or TED talk.

        Returns:
          the `knowledge_item` and `pending` variables.
        """
        try:
            # Get ID if any from URL
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            paths = parsed_url.path.rstrip("/").split("/")
            meta_id = ""
            query = None
            id_type = ""

            if domain == "podcasts.apple.com":
                queries = parse_qs(parsed_url.query)
                ids = queries.get("i")
                if not ids:
                    raise Exception("No iTunes ID for podcast episode found in URL")
                meta_id = int(ids[0])
                id_type = ".itunes_id"

            elif domain == "open.spotify.com":
                if paths[-2] != "episode":
                    raise Exception("Spotify URL not for podcast episode")
                meta_id = paths[-1]
                id_type = ".spotify_id"

            elif "podcasts.google.com/feed/" in url:
                if paths[-2] != "episode":
                    raise Exception("Google URL not for podcast episode")
                meta_id = paths[-1]
                id_type = ".google_id"

            elif "youtube.com" in domain:
                queries = parse_qs(parsed_url.query)
                ids = queries.get("v")
                if not ids:
                    raise Exception(f"YouTube ID not found in url", url)
                meta_id = ids[0]
                youtube_url = "https://www.youtube.com/watch?v=" + meta_id
                query = {
                    "$or": [
                        {"metadata.id": meta_id},
                        {"metadata.additional_links.youtube_url": youtube_url},
                    ]
                }

            elif "books.google" in domain or (
                ".google." in domain and (len(paths) > 1 and paths[1] == "books")
            ):
                queries = parse_qs(parsed_url.query)
                ids = queries.get("id")
                if ids:
                    meta_id = ids[0]
                else:
                    meta_id = paths[-1]

            elif domain == "pubmed.ncbi.nlm.nih.gov":
                meta_id = paths[-1]

            elif "sciencedirect" in domain and "pii" in paths:
                meta_id = paths[-1]

            elif ".ted." in domain:
                slug = paths[-1]
                url = "https://www.ted.com/talks/" + slug
                query = {"metadata.url": url}

            # Construct query
            if not query:
                query = {f"metadata.id{id_type}": meta_id}

            print("query : ", query)

            # Find knowledge_item in MongoDB
            m_db = MongoClient.connect()

            knowledge_item = m_db[Config.MONGO_KI_COLLECTION].find_one(query)
            pending = False

            if knowledge_item:
                return knowledge_item, pending

            # If knowledge_item is not found in master collection then try in pending collection
            if not knowledge_item:
                knowledge_item = m_db[Config.MONGO_KI_PENDING_COLLECTION].find_one(query)

            # If all else fails try once to search the exact url in the pending collection to avoid duplicate inserts
            if not knowledge_item:
                knowledge_item = m_db[Config.MONGO_KI_PENDING_COLLECTION].find_one(
                    {"metadata.url": url}
                )

            if knowledge_item:
                pending = True

            return knowledge_item, pending

        except Exception as e:
            Common.exception_details("knowledge_itemService.py : get_by_url", e)
            raise Exception(e)

    def ki_save(self, user_id, url, domain_id, comment=""):
        """
        The `ki_save` function saves a knowledge item (KI) to a database, including information such as
        the user ID, URL, domain ID, and optional comment.

        Args:
          user_id: The user ID is the unique identifier of the user who is saving the knowledge item. It
        is used to associate the knowledge item with the user who created it.
          url: The URL of the domain for which the knowledge item is being saved.
          domain_id: The `domain_id` parameter is the unique identifier for the domain to which the
        knowledge item belongs.
          comment: The "comment" parameter is an optional parameter that represents a comment made by
        the user during the creation of a Knowledge Item (KI). This comment will be stored as the first
        comment on the KI when it is approved.

        Returns:
          a dictionary with the key "ki_id" and the value being the string representation of the
        inserted ID if the insertion is successful. If the insertion is not successful or if the
        "new_object" is empty, it returns None.
        """
        try:
            domain_details = self.get_domain_details(url, True)
            new_object = domain_details["domainDetails"]

            print("new_object : ", new_object)

            if new_object:
                new_object["createdBy"] = None
                new_object["domainId"] = ObjectId(domain_id)

                new_object["status"] = int(Enumerator.KnowledgeItemStatus.Open.value)

                if user_id:
                    # Insert the id of user along with new KI info
                    new_object["createdBy"] = {
                        "user_id": ObjectId(user_id),
                        "ref": "users",
                    }

                    # If user has made a comment during KI creation insert it
                    # This comment is to become the first comment on the KI when it is approved
                    if comment and comment != "":
                        new_object["createdBy"]["comment"] = comment

                m_db = MongoClient.connect()

                inserted_result = m_db[Config.MONGO_KI_PENDING_COLLECTION].insert_one(
                    new_object
                )

                result = None
                if inserted_result.inserted_id:
                    result = {"ki_id": str(inserted_result.inserted_id)}

                return result
            else:
                return None

        except Exception as e:
            Common.exception_details("knowledge_itemService.py : ki_save", e)
            raise Exception(e)

    def update_ki_likes(self, ki_id, likes):
        """
        The function updates the "likes" field of a document in a MongoDB collection with the given
        ki_id.

        Args:
          ki_id: The `ki_id` parameter is the ID of the ki (knowledge item) that you want to update the
        likes for.
          likes: The `likes` parameter is a list of user IDs.

        Returns:
          the number of documents that were modified in the database.
        """
        m_db = MongoClient.connect()

        # convert all _ids inside likes to ObjectId
        likes = [ObjectId(user_id) for user_id in likes]

        response = m_db[Config.MONGO_KI_COLLECTION].update_one(
            {"_id": ObjectId(ki_id)}, {"$set": {"likes": likes}}
        )

        return response.modified_count

    # KI Comments Start

    def get_comments_by_ki(
        self,
        ki_id: str,
        sort_by: int = int(Enumerator.CommentSortBy.TOP_COMMENTS.value),
        user_obj: dict = None,
    ) -> dict:
        """
        The function `get_comments_by_ki` retrieves comments related to a specific knowledge item,
        sorted by different criteria, and includes additional information such as likes and child
        comments.

        Args:
          ki_id (str): The `ki_id` parameter is a string that represents the ID of a knowledge item. It
        is used to filter the comments based on the knowledge item ID.
          sort_by (int): The `sort_by` parameter is an optional parameter that determines the sorting
        order of the comments. It accepts an integer value that corresponds to different sorting
        options. The available sorting options are:
          user_obj (dict): The `user_obj` parameter is a dictionary that represents the user object. It
        contains information about the user, such as their ID, name, and other relevant details. This
        parameter is optional and can be set to `None` if not needed.

        Returns:
          a dictionary containing the comments and the total count of comments.
        """
        m_db = MongoClient.connect()

        comment_type_array = Enumerator.convert_to_list(Enumerator.CommentType)
        pipeline_comments_all = [
            {
                "$match": {
                    "ki.type": ObjectId(ki_id),
                    # "$expr": {"$cond": {
                    #     "if": {"$ne": [filter_by, 0]},
                    #     "then": {"$eq": ["$type", filter_by]},
                    #     "else": True
                    # }},
                    "comment": {"$not": {"$regex": "^\s+$"}},
                }
            },
            {"$sort": {"created": -1}},
        ]
        print(user_obj)
        pipeline_comments_root = [{"$match": {"mainParent": None}}]
        pipeline_additional_info = [
            {
                "$addFields": {
                    "commentType": {
                        "$reduce": {
                            "input": comment_type_array,
                            "initialValue": "",
                            "in": {
                                "$cond": [
                                    {"$eq": ["$$this.id", "$type"]},
                                    "$$this.value",
                                    "$$value",
                                ]
                            },
                        }
                    }
                }
            },
            {
                "$lookup": {
                    "from": Config.MONGO_KI_LIKE_COLLECTION,
                    "let": {"comment": "$_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$comment.type", "$$comment"]},
                                    ]
                                }
                            }
                        },
                        {
                            "$project": {
                                "commentid": "$_id",
                                "ownLike": {
                                    "$eq": ["$user.type", ObjectId(user_obj["_id"])]
                                },
                                "_id": 0,
                            }
                        },
                    ],
                    "as": "likes",
                }
            },
            {
                "$addFields": {
                    "likesCount": {"$size": "$likes"},
                    "ownLike": {
                        "$ifNull": [
                            # {"$first":
                            {
                                "$filter": {
                                    "input": "$likes.ownLike",
                                    "cond": {"$eq": ["$$this", True]},
                                }
                            },
                            # },
                            False,
                        ]
                    },
                }
            },
            {"$unset": ["likes"]},
        ]
        pipeline_children = [
            {
                "$lookup": {
                    "from": Config.MONGO_KI_COMMENTS_COLLECTION,
                    "let": {"kiType": "$ki.type", "mainParentType": "$_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$ki.type", "$$kiType"]},
                                        {
                                            "$eq": [
                                                "$mainParent.type",
                                                "$$mainParentType",
                                            ]
                                        },
                                    ]
                                }
                            }
                        },
                        {"$sort": {"created": 1}},
                    ],
                    "as": "children",
                }
            }
        ]
        pipeline_children[0]["$lookup"]["pipeline"].extend(pipeline_additional_info)

        # pipeline_rating = [
        #     {
        #         "$lookup": {
        #             "from": Environment().MONGO_knowledge_item_RATING_COLLECTION,
        #             "let": {"kiType": "$ki.type", "userId": "$user.type", "type": "$type"},
        #              "pipeline": [
        #                  {
        #                         "$match": {
        #                             "$expr": {
        #                                 "$and": [
        #                                     {"$eq": ["$ki.type", "$$kiType"]},
        #                                     {"$eq": ["$user.type", "$$userId"]},
        #                                     {"$eq": [1, "$$type"]}
        #                                 ]
        #                             }
        #                         }
        #                     },
        #                  {"$project": {
        #                         "rating": 1
        #                     }
        #                     }
        #               ],
        #              "as": "ratings",
        #             }
        #     },
        #     {
        #         "$addFields": {
        #              "rating": {
        #                  "$ifNull": [{"$arrayElemAt": ["$ratings.rating", 0]}, 0]
        #                  }
        #          }
        #         },
        #     {"$unset": ["ratings"]},
        # ]

        pipeline_count = [{"$count": "totalCount"}]

        sort_by_condition = {}

        if sort_by == int(Enumerator.CommentSortBy.TOP_COMMENTS.value):
            sort_by_condition = {"likesCount": -1}
        elif sort_by == int(Enumerator.CommentSortBy.LATEST_COMMENTS.value):
            sort_by_condition = {"created": -1}
        elif sort_by == int(Enumerator.CommentSortBy.OLDEST_COMMENTS.value):
            sort_by_condition = {"created": 1}

        pipeline_sort_by = [{"$sort": sort_by_condition}]

        collection = m_db[Config.MONGO_KI_COMMENTS_COLLECTION]
        pipeline = pipeline_comments_all + [
            {
                "$facet": {
                    # + pipeline_rating,
                    "comments": pipeline_comments_root
                    + pipeline_additional_info
                    + pipeline_children
                    + pipeline_sort_by,
                    "totalCount": pipeline_count,
                }
            }
        ]
        aggregation = collection.aggregate(pipeline)
        result = next(aggregation)
        if not result:
            result = {"comments": [], "totalCount": 0}
        else:
            result["totalCount"] = (
                result["totalCount"][0]["totalCount"]
                if len(result["totalCount"]) > 0
                else 0
            )

        return result

    def save_comment_on_ki(
        self,
        user_obj: dict,
        ki_id: str,
        comment: str,
        comment_type: int,
        parent=None,
        main_parent=None,
        reply_to=None,
    ) -> bool:
        """
        The save_comment_on_ki function saves a comment on a KI.
            Args:
                user_obj (dict): The user object of the person who is commenting.
                ki_id (str): The ID of the KI that is being commented on.
                comment (str): The text content of the comment itself.  This can be an empty string, but not None or Falsey values like 0 or &quot;&quot;.  If you want to delete a comment, use delete_comment instead! :)
                parent(optional) (str): If this is a reply to another comment, then this should be set to that

        Args:
            self: Represent the instance of the class
            user_obj: dict: Pass in the user object
            ki_id: str: Identify the ki that is being commented on
            comment: str: Pass the comment text
            comment_type: int: Determine the type of comment
            parent: Identify the parent comment of a reply
            main_parent: Identify the main parent of a comment
            reply_to: Specify the user who is being replied to

        Returns:
            A boolean value
        """

        parent_obj = (
            {
                "type": ObjectId(parent),
                "ref": Config.MONGO_KI_COMMENTS_COLLECTION,
            }
            if parent
            else None
        )

        main_parent_obj = (
            {
                "type": ObjectId(main_parent),
                "ref": Config.MONGO_KI_COMMENTS_COLLECTION,
            }
            if main_parent
            else None
        )

        # future_fix - "authorImg" is set to a default user icon for now
        print(user_obj)

        comment_obj = {
            "ki": {
                "type": ObjectId(ki_id),
                "ref": Config.MONGO_KI_COMMENTS_COLLECTION,
            },
            "user": {"type": ObjectId(user_obj["_id"]), "ref": "txp_user_master"},
            "comment": comment,
            "created": datetime.datetime.utcnow(),
            "authorName": user_obj["name"],
            "authorImg": "/assets/images/user-icon.png",
            "deleted": False,
            "parent": parent_obj,
            "mainParent": main_parent_obj,
            "replyTo": reply_to,
            "type": comment_type,
            "updated": None,
            "updatedBy": None,
        }

        m_db = MongoClient.connect()

        result = m_db[Config.MONGO_KI_COMMENTS_COLLECTION].insert_one(comment_obj)

        return bool(result.inserted_id)

    def edit_comment_on_ki(
        self, user_obj: dict, comment_id: str, new_comment: str
    ) -> bool:
        """Edit comment on a KI for a user

        Args:
            user_obj (dict): User object
            comment_id (str): Comment ID
            new_comment (str): The edited version of the comment

        Returns:
            True -> if the comment was successfully edited
            False -> otherwise
        """
        m_db = MongoClient.connect()

        result = m_db[Config.MONGO_KI_COMMENTS_COLLECTION].update_one(
            filter={"_id": ObjectId(comment_id)},
            update={
                "$set": {
                    "comment": new_comment,
                    "updated": datetime.datetime.utcnow(),
                    "updatedBy": {
                        "type": ObjectId(user_obj["_id"]),
                        "ref": "txp_user_master",
                    },
                }
            },
        )

        return bool(result.modified_count)

    def toggle_like_on_comment(self, user_obj: dict, comment_id: str) -> bool:
        """
        The function toggles the like status on a comment for a given user.

        Args:
          user_obj (dict): The `user_obj` parameter is a dictionary that represents a user object. It
        contains information about the user, such as their ID, name, email, etc.
          comment_id (str): The comment_id parameter is the unique identifier of the comment that the
        user wants to toggle the like on.

        Returns:
          a boolean value indicating whether the like on the comment was successfully toggled.
        """
        m_db = MongoClient.connect()

        existing_object = m_db[Config.MONGO_KI_LIKE_COLLECTION].find_one(
            {
                "comment.type": ObjectId(comment_id),
                "user.type": ObjectId(user_obj["_id"]),
            }
        )

        if existing_object:
            deleted_result = m_db[Config.MONGO_KI_LIKE_COLLECTION].delete_one(
                {
                    "comment.type": ObjectId(comment_id),
                    "user.type": ObjectId(user_obj["_id"]),
                }
            )

            return bool(deleted_result.deleted_count)

        else:
            new_object = {
                "comment": {
                    "type": ObjectId(comment_id),
                    "ref": Config.MONGO_KI_LIKE_COLLECTION,
                },
                "user": {"type": ObjectId(user_obj["_id"]), "ref": "txp_user_master"},
                "created": datetime.datetime.utcnow(),
                "updated": None,
            }

            inserted_result = m_db[Config.MONGO_KI_LIKE_COLLECTION].insert_one(
                new_object
            )

            return bool(inserted_result.inserted_id)

    def delete_comment_on_ki(
        self, user_obj: dict, comment_id: str, delete_child_comments: bool = True
    ) -> bool:
        """
        The function `delete_comment_on_ki` deletes a comment and its child comments from a MongoDB
        collection based on the provided comment ID and user object.

        Args:
          user_obj (dict): A dictionary containing information about the user who is deleting the
        comment.
          comment_id (str): The comment_id parameter is a string that represents the unique identifier
        of the comment that needs to be deleted.
          delete_child_comments (bool): The `delete_child_comments` parameter is a boolean flag that
        determines whether or not to delete child comments along with the specified comment. If set to
        `True`, it will delete all child comments of the specified comment. If set to `False`, it will
        only delete the specified comment and not its child. Defaults to True

        Returns:
          a boolean value indicating whether the deletion of the comment(s) was successful or not.
        """
        m_db = MongoClient.connect()

        delete_filter = [{"_id": ObjectId(comment_id)}]

        if delete_child_comments:
            delete_filter.extend(
                [
                    {"parent.type": ObjectId(comment_id)},
                    {"mainParent.type": ObjectId(comment_id)},
                ]
            )

        result = m_db[Config.MONGO_KI_COMMENTS_COLLECTION].delete_many(
            filter={"$or": delete_filter}
        )

        return bool(result.deleted_count)

    # KI Comments End

    def search_ki_using_params(
        self,
        query,
        domains=[],
        mediatags="",
        sortby="score",
        sortorder=-1,
        offset=0,
        limit=10,
    ):
        """Return all KIs corresponding to a search query

        Args:
            query (str): The search query.
            domains (list, optional): The domains to filter the Knowledge Items by.
            mediatags (str, optional): Media tags to filter the KIs. Defaults to "".
            sortby (str, optional): Parameter to sort the KIs. Defaults to "score".
            sortorder (int, optional): Parameter that determines the sort order of the KIs. Defaults to -1.
            offset (int, optional): Number of KIs to skip before returning. Defaults to 0.
            limit (int, optional): Max number of KIs to return. Defaults to 10.

        Returns:
            dict: A dictionary of all searched KIs
        """

        if sortby not in ["score", "created"]:
            sortby = "score"

        m_db = MongoClient.connect()

        # If mediatags are passed in then filter the KIs by tags otherwise get all KIs
        if mediatags:
            # If mediatags are not in the known tags list return empty list
            if mediatags not in ["podcast", "tedtalks", "youtube", "books", "research"]:
                return []

            search_pipeline = [
                PipelineStages.stage_match(
                    {"tags": mediatags, "$text": {"$search": query}}
                )
            ]
        else:
            search_pipeline = [
                PipelineStages.stage_match({"$text": {"$search": query}})
            ]

        # Filter the Knowledge Items by the domains
        domains = [ObjectId(domain_id) for domain_id in domains]
        search_pipeline += [PipelineStages.stage_match({"domainId": {"$in": domains}})]

        ki_pipeline = self.get_general_ki_pipeline()
        score_pipeline = [
            PipelineStages.stage_add_fields({"score": {"$meta": "textScore"}})
        ]
        common_pipeline = [
            PipelineStages.stage_sort({sortby: sortorder}),
            PipelineStages.stage_skip(offset),
            PipelineStages.stage_limit(limit),
        ]

        # elastic_data, elastic_counts = ElasticService.GetBysemantic(
        #     query=query, from_index=skips, size=limit, tag=mediatags)
        elastic_data = None
        elastic_counts = 0
        if elastic_data:
            ki_list = [ObjectId(item["_id"]) for item in elastic_data]
            ki_array = [
                {"k": ObjectId(item["_id"]), "v": round(item["_score"])}
                for item in elastic_data
            ]

            # Match KIs already found by ElasticSearch
            search_pipeline = [
                PipelineStages.stage_match(
                    {
                        "_id": {"$in": ki_list},
                        "tags": mediatags,
                        "$text": {"$search": query},
                    }
                )
            ]
            # Replace score field with ElasticSearch score
            score_pipeline = [
                PipelineStages.stage_add_fields(
                    {
                        "score": {
                            "$reduce": {
                                "input": ki_array,
                                "initialValue": 0,
                                "in": {
                                    "$cond": [
                                        {"$eq": ["$$this.k", "$_id"]},
                                        "$$this.v",
                                        "$$value",
                                    ]
                                },
                            }
                        }
                    }
                )
            ]

        pipeline = search_pipeline + ki_pipeline + score_pipeline + common_pipeline
        kis = m_db[Config.MONGO_KI_COLLECTION].aggregate(pipeline)

        return Common.cursor_to_dict(kis)

    @staticmethod
    def get_general_ki_pipeline():
        """Common Knowledge Item pipeline

        Returns:
            list: Common knowledge Item pipeline
        """

        ki_pipeline = [
            PipelineStages.stage_lookup("DOMAIN_MASTER", "domainId", "_id", "domain"),
            PipelineStages.stage_unwind("domain"),
            PipelineStages.stage_add_fields(
                {
                    "created": {"$dateToString": {"date": "$created"}},
                    "domainId": {"$toString": "$domainId"},
                    "_id": {"$toString": "$_id"},
                    "likes": {
                        "$map": {
                            "input": "$likes",
                            "as": "like",
                            "in": {"$toString": "$$like"},
                        }
                    },
                    "domain._id": {"$toString": "$domain._id"},
                    "url": "$metadata.url",
                }
            ),
            PipelineStages.stage_unset(
                ["metadata", "original", "permission", "updated", "embeddings"]
            ),
        ]

        return ki_pipeline

    @staticmethod
    def get_domain_details(url, get_data=False):
        """
        The function `get_domain_details` takes a URL as input and returns the domain details and the
        type of URL.

        Args:
          url: The `url` parameter is a string that represents the URL of a website or webpage. It is
        used to identify the domain and path of the URL.
          get_data: The `get_data` parameter is a boolean flag that determines whether or not to
        retrieve additional data from the given URL. If `get_data` is set to `True`, the function will
        call different methods from the `Parser` class to extract specific information based on the
        domain of the URL. If. Defaults to False

        Returns:
          The function `get_domain_details` returns a dictionary with two keys: "domainDetails" and
        "url_type". The value of "domainDetails" is the object obtained by parsing the URL, and the
        value of "url_type" is a string indicating the type of URL (e.g., "ApplePodcast",
        "SpotifyPodcast", "GooglePodcast", "GoogleBooks", "
        """
        try:
            # Storing the domain name
            domain = urlparse(url).netloc

            # Storing the path
            path = urlparse(url).path[1:6]
            url_type = None
            new_object = None
            dic = domain.split(".")

            # if domain == 'podcasts.apple.com':
            if dic[0] == "podcasts" and dic[1] == "apple":
                # podcast
                if get_data:
                    new_object = Parser().get_podcast_info(url)
                url_type = "ApplePodcast"
            # elif domain == 'open.spotify.com':
            elif dic[0] == "open" and dic[1] == "spotify":
                # podcast
                if get_data:
                    new_object = Parser().get_podcast_info(url)
                url_type = "SpotifyPodcast"
            # elif domain == 'podcasts.google.com':
            elif dic[0] == "podcasts" and dic[1] == "google":
                # podcast
                if get_data:
                    new_object = Parser().get_podcast_info(url)
                url_type = "GooglePodcast"
            # elif (domain == 'www.google.co.in' and path == 'books') or (domain == 'books.google.co.in'):
            elif (dic[1] == "google" and path == "books") or (
                dic[0] == "books" and dic[1] == "google"
            ):
                # book
                if get_data:
                    new_object = Parser().get_book_info(url)
                url_type = "GoogleBooks"
            # elif domain == 'www.youtube.com':
            elif dic[1] == "youtube":
                # youtube
                if get_data:
                    new_object = Parser().get_youtube_info(url)
                url_type = "Youtube"
            elif domain == "pubmed.ncbi.nlm.nih.gov":
                # research
                if get_data:
                    new_object = Parser().get_research_info(url)
                url_type = "Pubmed"
            # elif domain == 'www.sciencedirect.com':
            elif dic[1] == "sciencedirect":
                # research
                if get_data:
                    new_object = Parser().get_research_info(url)
                url_type = "ScienceDirect"
            # elif domain == 'www.ted.com':
            elif dic[1] == "ted":
                # tedtalks
                if get_data:
                    new_object = Parser().get_tedtalks_info(url)
                url_type = "TedTalks"
            else:
                if get_data:
                    new_object = Parser().not_supported_ki(url)
                url_type = None

            return {"domainDetails": new_object, "url_type": url_type}
        except Exception as e:
            Common.exception_details("knowledge_itemService.py : get_domain_details", e)
            raise Exception(e)
