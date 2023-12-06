from bson import ObjectId

from app.config import Config
from app.config import Config
from app.models.mongoClient import MongoClient
from app.services.knowledgeItemService import KnowledgeItemService
from app.utils.common import Common
from app.utils.pipelines import PipelineStages


class MyTexplicitService:
    
    def toggle_favourite(self, user_id, ki_id):
        """
            The toggle_favourite function takes in a user_id and ki_id as parameters.
            It then queries the database to find the user with that id, and checks if
            the knowledge item with that ki_id is already present in their favourites array.
            If it is, it removes it from their favourites array; otherwise, adds it to
            their favourites array.

            Args:
                self: Represent the instance of the class
                user_id: Identify the user who is performing the action
                ki_id: Identify the knowledge item that is being favourite

            Returns:
                The modified count and the status
        """

        # Construct favourite data
        favourite_data = {
            "_id": ObjectId(ki_id),
            "ref": "knowledgeItem"
        }

        m_db = MongoClient.connect()

        # Check if the favourite data already exists in the user_data favourties array
        favourite_query = {"_id": ObjectId(user_id), "isActive": True, "favourites": {"$elemMatch": favourite_data}}
        favourite_response = m_db[Config.MONGO_USER_MASTER_COLLECTION].find_one(favourite_query)

        if favourite_response is not None:
            new_values = {"$pull": {"favourites": favourite_data}}
            status = 0
        else:
            new_values = {"$push": {"favourites": favourite_data}}
            status = 1

        user_query = {"_id": ObjectId(user_id), "isActive": True}
        response = m_db[Config.MONGO_USER_MASTER_COLLECTION].update_one(user_query, new_values)

        if response:
            return str(response.modified_count), status

        return None, None

    def get_all(self, user_id, query="", media_tags=None, domains=None, offset=0, limit=10):
        """
        The function `get_all` retrieves knowledge items based on various filters and returns the
        results as a dictionary.
        
        Args:
          user_id: The user_id parameter is the unique identifier of the user for whom you want to
        retrieve the knowledge items.
          query: The `query` parameter is used to filter the knowledge items based on a search query. It
        performs a text search on the knowledge items and returns the ones that match the query.
          media_tags: The `media_tags` parameter is used to filter the knowledge items based on their
        tags. It accepts a list of tags as input. Only the knowledge items that have at least one of the
        specified tags will be returned in the results.
          domains: The "domains" parameter is a list of domain IDs. It is used to filter the knowledge
        items by their domain. Only knowledge items that belong to the specified domains will be
        returned.
          offset: The offset parameter is used to specify the starting point of the results. It
        determines how many items to skip before returning the results. For example, if offset is set to
        10, the first 10 items will be skipped and the results will start from the 11th item. Defaults
        to 0
          limit: The `limit` parameter specifies the maximum number of results to be returned in a
        single query. In this case, it is set to 10, meaning that the function will return at most 10
        results. Defaults to 10
        
        Returns:
          the results of a MongoDB aggregation query. The results are converted into a dictionary format
        and returned.
        """

        m_db = MongoClient.connect()

        ki_pipeline = KnowledgeItemService.get_general_ki_pipeline()
        
        filter = {}
        if query and query != "":
            print("Filter by query!")
            filter["$text"] = {"$search": query}

        if domains:
            print("Filter by domains!")
            domains = [ObjectId(domain_id) for domain_id in domains]
            filter["domainId"] = {"$in": domains}

        if media_tags:
            print("Filter by media_tags!")
            filter["tags"] = {"$in": media_tags}
            
        filter['likes'] = {
          '$in': [ObjectId(user_id)]
        }
        
        pipeline =  [
            {
                '$match': filter
            },
            PipelineStages.stage_add_fields({
                "bookmarked" : str(user_id),
            }),
            PipelineStages.stage_skip(offset),
            PipelineStages.stage_limit(limit)
        ] + ki_pipeline

        results = m_db[Config.MONGO_KI_COLLECTION].aggregate(pipeline)

        return Common.cursor_to_dict(results)
