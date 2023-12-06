import datetime

from bson import ObjectId
from flask import request

from app.config import Config
from app.models.mongoClient import MongoClient
from app.utils.common import Common
from app.utils.enumerator import Enumerator
from app.utils.parser import Parser
from app.utils.pipelines import PipelineStages


class PostService:
    
    POST_COLLECTION = Config.MONGO_POST_COLLECTION
    POST_COMMENT_COLLECTION = Config.MONGO_POST_COMMENT_COLLECTION
    GROUP_COLLECTION = Config.MONGO_GROUP_COLLECTION
    USER_COLLECTION = Config.MONGO_USER_MASTER_COLLECTION
    KI_COLLECTION = Config.MONGO_KI_COLLECTION
    POST_COMMENT_LIKE_COLLECTION = Config.MONGO_POST_COMMENT_LIKE_COLLECTION
    DOMAIN_COLLECTION = Config.MONGO_DOMAIN_MASTER_COLLECTION

    def get_specific_post(self, postId, userId):
        """
        The function `get_specific_post` retrieves a specific post from a MongoDB collection and
        performs various lookup operations to fetch related data.
        
        Args:
          postId: The `postId` parameter is the ID of the specific post that you want to retrieve. It is
        used to match the post in the database and retrieve its details.
          userId: The `userId` parameter is the ID of the user for whom you want to get the specific
        post.
        
        Returns:
          the response_data, which is a dictionary containing the data of the specific post.
        """
        group_logo_route = request.host_url + "groups/media/logo/"
        m_db = MongoClient.connect()
        projection_keys = [
            "postId"
            "likes",
            "ownLike"
        ]

        post_pipeline = [
            PipelineStages.stage_match({'_id' : ObjectId(postId)}),
            # {
            #     # '$project' : {
            #     #     "postId" : "$_id",
            #     #     "ownLike" : { "$eq": [ "$user.type", ObjectId(userId) ] }
            #     # }
            #     "$addFields" : {
            #         "ownLike" : {
            #             '$cond' : {
            #                 "if" : { "$in" : ["$likes", [ObjectId(userId)]] }, 
            #                 # "if" : { "likes" : { "$in" : [ObjectId(userId) ] } },
            #                 "then" : {"$toBool" : "true"}, 
            #                 "else" : {"$toBool" : "false"}
            #             }
            #         }
            #     }
            # }
        ]

        post_pipeline += [
            # Look up for KI Data from KI Collection
            PipelineStages.stage_lookup(self.KI_COLLECTION, "itemId", "_id", "ki"),

            PipelineStages.stage_unwind("ki"),

            PipelineStages.stage_lookup(self.DOMAIN_COLLECTION, "ki.domainId", "_id", "domainData"),

            # Lookup Group Data from Group Collection
            PipelineStages.stage_lookup(self.GROUP_COLLECTION, "groupId", "_id", "groupData"),

            # Lookup User Data from User Collection
            PipelineStages.stage_lookup(self.USER_COLLECTION, "postedBy.id", "_id", "userData"),

            PipelineStages.stage_unwind("groupData"),

            PipelineStages.stage_add_fields({'likes': {
                    '$map': {
                        'input': '$likes',
                        'as': 'like',
                        'in': {'$toString': '$$like'}
                    }
                },
                'groupData.media.logo' : {
                    "$cond": {
                        "if": {"$ne": ["$groupData.media.logo", ""]},
                        "then": {"$concat": [group_logo_route, "$groupData.media.logo"]},
                        "else": "$groupData.media.logo",
                    }
                }
            }),

            PipelineStages.stage_unset(['ki.embeddings', 'ki.highlightsSummary'])
        ]

        # print(post_pipeline)

        response = m_db[self.POST_COLLECTION].aggregate(post_pipeline)
        response_data = Common.cursor_to_dict(response)
        print("RESPONSE :", response_data)
        return response_data
    
    def get_comments_by_post(self, post_id: str, sort_by: int = int(Enumerator.CommentSortBy.TOP_COMMENTS.value), user_obj: dict = None) -> dict:
        """
        The function `get_comments_by_post` retrieves comments for a specific post, sorted by a
        specified criteria, and includes additional information such as likes and child comments.
        
        Args:
          post_id (str): The post_id parameter is a string that represents the ID of the post for which
        you want to retrieve the comments.
          sort_by (int): The `sort_by` parameter is an optional integer parameter that determines the
        sorting order of the comments. It accepts the following values:
          user_obj (dict): The `user_obj` parameter is a dictionary that represents the user object. It
        contains information about the user, such as their ID, name, and other relevant details. This
        parameter is optional and can be set to `None` if not needed.
        
        Returns:
          a dictionary containing the comments and the total count of comments for a given post.
        """

        m_db = MongoClient.connect()

        comment_type_array = Enumerator.convert_to_list(Enumerator.CommentType)
        pipeline_comments_all = [
            {"$match": {
                "ki.type": ObjectId(post_id),
                # "$expr": {"$cond": {
                #     "if": {"$ne": [filter_by, 0]},
                #     "then": {"$eq": ["$type", filter_by]},
                #     "else": True
                # }},
                "comment": {"$not": {"$regex": "^\s+$"}}
            }
            },
            {"$sort": {"created": -1}},
        ]
        print(user_obj)
        pipeline_comments_root = [
            {"$match": {"mainParent": None}}
        ]
        pipeline_additional_info = [
            {"$addFields": {
                "commentType": {
                    "$reduce": {
                        "input": comment_type_array,
                        "initialValue": "",
                        "in": {
                            "$cond": [
                                {"$eq": ["$$this.id", "$type"]},
                                "$$this.value",
                                "$$value"
                            ]
                        }
                    }
                }
            }},
            {"$lookup": {
                "from": self.POST_COMMENT_LIKE_COLLECTION,
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
                            "ownLike": {"$eq": ["$user.type", ObjectId(user_obj["_id"])]},
                            "_id": 0
                        }
                    }
                ], "as": "likes",
            }
            },
            {"$addFields": {
                "likesCount": {"$size": "$likes"},
                "ownLike":
                    {"$ifNull": [
                        # {"$first":
                            {"$filter": {
                                "input": "$likes.ownLike",
                                "cond": {"$eq": ["$$this", True]}
                            }},
                        # },
                        False]
                    },
            }
            },
            {"$unset": ["likes"]},
        ]
        pipeline_children = [
            {"$lookup": {
                "from": self.POST_COMMENT_COLLECTION,
                "let": {"kiType": "$ki.type", "mainParentType": "$_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$ki.type", "$$kiType"]},
                                    {"$eq": ["$mainParent.type",
                                             "$$mainParentType"]}
                                ]
                            }
                        }
                    },
                    {"$sort": {"created": 1}},
                ],
                "as": "children"
            }}
        ]
        pipeline_children[0]['$lookup']['pipeline'].extend(
            pipeline_additional_info)

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

        pipeline_sort_by = [{
            "$sort": sort_by_condition
        }]

        collection = m_db[self.POST_COMMENT_COLLECTION]
        pipeline = pipeline_comments_all + [{
            "$facet": {
                # + pipeline_rating,
                "comments": pipeline_comments_root + pipeline_additional_info + pipeline_children + pipeline_sort_by,
                "totalCount": pipeline_count
            }
        }]
        aggregation = collection.aggregate(pipeline)
        result = next(aggregation)
        if not result:
            result = {"comments": [], "totalCount": 0}
        else:
            result['totalCount'] = result['totalCount'][0]['totalCount'] if len(
                result['totalCount']) > 0 else 0

        return result
    
    def save_comment_on_post(
            self,
            user_obj: dict,
            ki_id: str,
            comment: str,
            comment_type: int,
            parent=None,
            main_parent=None,
            reply_to=None
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

        parent_obj = {
            "type": ObjectId(parent),
            "ref": Config.MONGO_POST_COMMENT_COLLECTION
        } if parent else None

        main_parent_obj = {
            "type": ObjectId(main_parent),
            "ref": Config.MONGO_POST_COMMENT_COLLECTION
        } if main_parent else None

        # future_fix - "authorImg" is set to a default user icon for now
        print(user_obj)

        comment_obj = {
            "ki": {
                "type": ObjectId(ki_id),
                "ref": Config.MONGO_POST_COMMENT_COLLECTION
            },
            "user": {
                "type": ObjectId(user_obj["_id"]),
                "ref": "txp_user_master"
            },
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

        result = m_db[self.POST_COMMENT_COLLECTION].insert_one(comment_obj)

        return bool(result.inserted_id)
    
    def edit_comment_on_post(self, user_obj: dict, comment_id: str, new_comment: str) -> bool:
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

        result = m_db[self.POST_COMMENT_COLLECTION].update_one(
            filter={"_id": ObjectId(comment_id)},
            update={"$set": {
                "comment": new_comment,
                "updated": datetime.datetime.utcnow(),
                "updatedBy": {"type": ObjectId(user_obj["_id"]), "ref": "txp_user_master"}
            }}
        )

        return bool(result.modified_count)

    def toggle_like_on_comment(self, user_obj: dict, comment_id: str) -> bool:
        """
        The function `toggle_like_on_comment` toggles the like status on a comment by either adding or
        removing a like object in the database.
        
        Args:
          user_obj (dict): The `user_obj` parameter is a dictionary that represents the user object. It
        contains information about the user, such as their ID, name, email, etc.
          comment_id (str): The comment_id parameter is a string that represents the unique identifier
        of the comment.
        
        Returns:
          a boolean value indicating whether the like on the comment was successfully toggled.
        """

        m_db = MongoClient.connect()

        existing_object = m_db[self.POST_COMMENT_LIKE_COLLECTION].find_one({
            "comment.type": ObjectId(comment_id),
            "user.type": ObjectId(user_obj["_id"])
        })

        if existing_object:
            deleted_result = m_db[self.POST_COMMENT_LIKE_COLLECTION].delete_one({
                "comment.type": ObjectId(comment_id),
                "user.type": ObjectId(user_obj["_id"])
            })

            return bool(deleted_result.deleted_count)

        else:
            new_object = {
                "comment": {"type": ObjectId(comment_id), "ref": self.POST_COMMENT_LIKE_COLLECTION},
                "user": {"type": ObjectId(user_obj["_id"]), "ref": 'txp_user_master'},
                "created": datetime.datetime.utcnow(),
                "updated": None
            }

            inserted_result = m_db[self.POST_COMMENT_LIKE_COLLECTION].insert_one(
                new_object)

            return bool(inserted_result.inserted_id)

    def delete_comment_on_post(self, user_obj: dict, comment_id,delete_child_comments: bool = True) -> bool:
        """
        The function `delete_comment_on_post` deletes a comment on a post, along with its child comments
        if specified, and returns a boolean indicating whether the deletion was successful.
        
        Args:
          user_obj (dict): The `user_obj` parameter is a dictionary that represents the user who is
        trying to delete the comment. It likely contains information such as the user's ID, username,
        and other relevant details.
          comment_id: The comment_id parameter is the unique identifier of the comment that you want to
        delete.
          delete_child_comments (bool): A boolean parameter that determines whether to delete child
        comments of the specified comment or not. If set to True, it will delete all child comments of
        the specified comment. If set to False, it will only delete the specified comment. Defaults to
        True
        
        Returns:
          a boolean value indicating whether the deletion of the comment(s) was successful or not.
        """

        m_db = MongoClient.connect()
        
        delete_filter = [{"_id": ObjectId(comment_id)}]

        if delete_child_comments:
            delete_filter.extend([{"parent.type": ObjectId(comment_id)}, {
                "mainParent.type": ObjectId(comment_id)}])

        result = m_db[self.POST_COMMENT_COLLECTION].delete_many(
            filter={
                "$or": delete_filter
            })

        return bool(result.deleted_count)

