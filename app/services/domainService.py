from datetime import datetime

from bson import ObjectId

from app.config import Config
from app.models.mongoClient import MongoClient
from app.utils.common import Common
from app.utils.pipelines import PipelineStages


class DomainService:

    DOMAIN_PENDING_COLLECTION = Config.MONGO_DOMAIN_PENDING_COLLECTION
    DOMAIN_MASTER_COLLECTION = Config.MONGO_DOMAIN_MASTER_COLLECTION
    KI_COLLECTION = Config.MONGO_KI_COLLECTION

    def request_new_domain(self, user_id, domain_data):
        """
        The function `request_new_domain` inserts a new domain request into a MongoDB collection and
        returns the response.
        
        Args:
          user_id: The user_id parameter is the unique identifier of the user who is requesting the new
        domain.
          domain_data: The `domain_data` parameter is a dictionary that contains the information about
        the new domain being requested. It should include the following key-value pairs:
        
        Returns:
          the result of the insert operation. If the insert operation is acknowledged, it will return
        the response of the insert operation with the inserted ID. If the insert operation is not
        acknowledged, it will return None.
        """
        m_db = MongoClient.connect()

        domain_data["requestedBy"] = {
            "_id": ObjectId(user_id),
            "ref": "user"
        }
        domain_data["requestDate"] = datetime.utcnow()

        insert_response = m_db[self.DOMAIN_PENDING_COLLECTION].insert_one(
            domain_data)

        if insert_response.acknowledged:
            return Common.process_response(insert_response.inserted_id)
        else:
            return None

    def get_domain_by_topic(self, topic):
        """
        The function checks if a domain with a given topic exists in a MongoDB database.
        
        Args:
          topic: The "topic" parameter is the topic for which we want to find an existing domain.
        
        Returns:
          a boolean value. If an existing domain is found with the given topic, it returns True.
        Otherwise, it returns False.
        """
        m_db = MongoClient.connect()

        # Perform a search for an existing domain by the topic
        existing_domain = m_db[self.DOMAIN_MASTER_COLLECTION].find_one({"topic": topic}) \
            or \
            m_db[self.DOMAIN_PENDING_COLLECTION].find_one({"topic": topic})

        if existing_domain:
            return True
        else:
            return False

    def get_all_domains(self):
        """
        The function `get_all_domains` retrieves all domains from a MongoDB collection, along with the
        count of documents for each domain.
        
        Returns:
          the result of the aggregation pipeline as a dictionary.
        """
        m_db = MongoClient.connect()

        pipeline = [
            {
                "$group": {
                    "_id": "$domainId",
                    "count": {"$sum": 1},
                },
            },
            {
                "$lookup": {
                    "from": self.DOMAIN_MASTER_COLLECTION,
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "domain",
                },
            },
            {
                "$unwind": "$domain",
            },
            {
                "$project": {
                    "domain": {
                        "$mergeObjects": [
                            "$domain",
                              {"ki_count": "$count"},
                        ],
                    },
                    "_id": 0
                },
            },
            PipelineStages.stage_change_root("domain"),
            PipelineStages.stage_sort({
                "topic" : 1
            }),
            PipelineStages.stage_add_fields({
                "_id": {"$toString": "$_id"}
            })
        ]

        response = m_db[self.KI_COLLECTION].aggregate(pipeline)

        return Common.cursor_to_dict(response)

    def get_domain_by_id(self, domain_id):
        """
        The function `get_domain_by_id` retrieves a domain from a MongoDB collection based on its ID.
        
        Args:
          domain_id: The `domain_id` parameter is the unique identifier of the domain that you want to
        retrieve from the database.
        
        Returns:
          the result of the aggregation pipeline as a dictionary.
        """
        m_db = MongoClient.connect()

        pipeline = [
            PipelineStages.stage_match({"_id": ObjectId(domain_id)}),
            PipelineStages.stage_add_fields({
                "_id": {
                    "$toString": "$_id"
                }
            })
        ]

        response = m_db[self.DOMAIN_MASTER_COLLECTION].aggregate(pipeline)

        return Common.cursor_to_dict(response)

    def get_domains_by_ids(self, domains=[], include_kis = True):
        """
        The function `get_domains_by_ids` retrieves domain information from a MongoDB database based on
        a list of domain IDs, and includes additional information about associated KIs (Knowledge Items)
        if specified.
        
        Args:
          domains: The `domains` parameter is a list of domain IDs. These IDs are used to filter the
        domains that will be retrieved from the database.
          include_kis: The parameter `include_kis` is a boolean flag that determines whether to include
        the KIs (Knowledge Items) in the response or not. If `include_kis` is set to `True`, the
        pipeline will perform a lookup on the `ki_collection` and add the count of matching documents.
        Defaults to True
        
        Returns:
          the result of the aggregation pipeline as a dictionary.
        """
        m_db = MongoClient.connect()

        ki_collection = self.KI_COLLECTION

        # Convert all string domain _id  to ObjectId
        domains = [ObjectId(domain) for domain in domains]

        pipeline = [
            PipelineStages.stage_match({"_id": {"$in": domains}}),
        ]

        if(include_kis):
            ki_pipeline = [
                {
                    "$lookup": {
                        "from": ki_collection,
                        "let": {"domainId": "$_id"},
                        "pipeline": [
                            {
                                "$match":
                                    {
                                        "$expr": {"$eq": ["$domainId", "$$domainId"]}
                                    }
                            },
                            {"$count": "matching_document_count"}
                        ],
                        "as": "matching_documents"
                    }
                },
                PipelineStages.stage_add_fields(
                    {
                        "_id": {"$toString": "$_id"},
                        "ki_count": {
                            "$ifNull": [{"$arrayElemAt": ["$matching_documents.matching_document_count", 0]}, 0]
                        }
                    }
                ),
                PipelineStages.stage_unset(["matching_documents"])
            ]
            pipeline += ki_pipeline
        else:
            pipeline += [
                PipelineStages.stage_add_fields(
                    {
                        "_id": {"$toString": "$_id"},
                    }
                ),
                PipelineStages.stage_unset(["keywords", "subtopics", "processed"])
            ]
        
        response = m_db[self.DOMAIN_MASTER_COLLECTION].aggregate(pipeline)

        return Common.cursor_to_dict(response)
