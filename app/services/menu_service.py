from bson import ObjectId

from app.config import Config
from app.models.mongoClient import MongoClient
from app.utils.common import Common
from app.utils.pipelines import PipelineStages
from app.utils.enumerator import Enumerator
from app.utils.formatter import cursor_to_dict

class MenuService:
    def get_menu_items(self, menu_ids=[]):
        try:
            if len(menu_ids) > 0:
                menu_ids = [ObjectId(id) for id in menu_ids]
                pipeline = [PipelineStages.stage_match({"_id": {"$in": menu_ids}})]
            else:
                pipeline = [
                    PipelineStages.stage_match(
                        {
                            "index": {
                                "$nin": [
                                    int(Enumerator.MenuItems.Admin.value)
                                ]
                            }
                        }
                    )
                ]

            pipeline += MenuService.get_general_menu_pipeline()
            m_db = MongoClient.connect()
            menu = m_db[Config.MONGO_MENU_MASTER_COLLECTION].aggregate(pipeline)

            return cursor_to_dict(menu)

        except Exception as e:
            Common.exception_details("MenuService.get_all_menu_items : ", e)
            return None

    @staticmethod
    def get_general_menu_pipeline():
        menu_pipeline = [
            PipelineStages.stage_add_fields(
                {
                    "_id": {"$toString": "$_id"},
                }
            ),
        ]

        return menu_pipeline
