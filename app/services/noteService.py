import datetime
import re

from bson import ObjectId

from app.config import Config
from app.models.mongoClient import MongoClient
from app.utils.common import Common
from app.utils.pipelines import PipelineStages


class NoteService:
    USER_MASTER_COLLECTION = Config.MONGO_USER_MASTER_COLLECTION
    NOTE_MASTER_COLLECTION = Config.MONGO_NOTE_MASTER_COLLECTION

    def create_note(self, user_id, title, content):
        """
        The function creates a note object with a title, content, user ID, and timestamps, checks if a
        note with the same title already exists for the user, inserts the note into the database if it
        doesn't exist, and returns the note object with the inserted ID.
        
        Args:
          user_id: The user_id parameter is the unique identifier of the user who is creating the note.
          title: The title parameter is a string that represents the title of the note.
          content: The "content" parameter is the actual content or body of the note that you want to
        create. It can be any text or information that you want to store in the note.
        
        Returns:
          a tuple with three values. The first value is the processed response of the note object, the
        second value is a boolean indicating whether the note was successfully inserted into the
        database, and the third value is a boolean indicating whether a note with the same title already
        exists for the given user.
        """

        note_obj = {
            "title": title,
            "content": content,
            "createdBy": {
                "_id": ObjectId(user_id),
                "ref": self.USER_MASTER_COLLECTION
            },
            "createdOn": datetime.datetime.now(),
            "updatedOn": None
        }

        m_db = MongoClient.connect()

        note_title_exists = m_db[self.NOTE_MASTER_COLLECTION].find_one({
            "createdBy._id": ObjectId(user_id),
            "title": title
        })

        if note_title_exists:
            return False, True

        insert_resp = m_db[self.NOTE_MASTER_COLLECTION].insert_one(note_obj)

        # note_obj["createdBy"]["_id"] = str(note_obj["createdBy"]["_id"])
        note_obj["createdOn"] = str(note_obj["createdOn"])

        if insert_resp.inserted_id:
            note_obj["_id"] = str(insert_resp.inserted_id)
            return Common.process_response(note_obj), bool(insert_resp.inserted_id), False

    def update_note(self, note_id, title, content):
        """
        The function updates a note's title, content, and updatedOn fields in a MongoDB collection.
        
        Args:
          note_id: The unique identifier of the note that needs to be updated.
          title: The title of the note to be updated.
          content: The `content` parameter is the new content that you want to update for the note.
        
        Returns:
          a boolean value indicating whether the note was successfully updated or not.
        """

        if title == "" and content == "":
            # nothing to update
            return False

        update_obj = {}

        if title:
            update_obj["title"] = title
        if content:
            update_obj["content"] = content

        update_obj["updatedOn"] = datetime.datetime.utcnow()

        m_db = MongoClient.connect()

        update_resp = m_db[self.NOTE_MASTER_COLLECTION].update_one({
            "_id": ObjectId(note_id)
        },
            {"$set": update_obj})

        return bool(update_resp.modified_count)

    def delete_note(self, note_id):
        """
        The function deletes a note from a MongoDB collection based on its ID.
        
        Args:
          note_id: The `note_id` parameter is the unique identifier of the note that you want to delete.
        
        Returns:
          a boolean value indicating whether the note with the given note_id was successfully deleted or
        not.
        """

        m_db = MongoClient.connect()

        delete_resp = m_db[self.NOTE_MASTER_COLLECTION].delete_one({
            "_id": ObjectId(note_id)
        })

        return bool(delete_resp.deleted_count)

    def get_specific_note(self, note_id):
        """
        The function `get_specific_note` retrieves a specific note from a MongoDB collection and
        performs some transformations on the retrieved data.
        
        Args:
          note_id: The note_id parameter is the unique identifier of the note that you want to retrieve.
        It is used to query the database and find the specific note with the matching ID.
        
        Returns:
          the next note object that matches the specified note ID.
        """
        m_db = MongoClient.connect()

        note_obj = m_db[self.NOTE_MASTER_COLLECTION].aggregate([
            PipelineStages.stage_match({"_id": ObjectId(note_id)}),
            PipelineStages.stage_add_fields({
                "_id": {
                    "$toString": "$_id"
                },
                "createdBy._id": {
                    "$toString": "$createdBy._id"
                },
                "createdOn": {
                    "$dateToString": {
                        "date": "$createdOn"
                    }
                },
                "updatedOn": {
                    "$dateToString": {
                        "date": "$updatedOn"
                    }
                }
            })
        ])

        return next(note_obj)

    def get_all_notes_by_user(self, user_id, page_number, num_notes_per_page=5):
        """
        The function `get_all_notes_by_user` retrieves all notes created by a specific user, paginated
        by a specified number of notes per page.
        
        Args:
          user_id: The user_id parameter is the unique identifier of the user for whom you want to
        retrieve the notes.
          page_number: The page number is the number of the page you want to retrieve. It is used for
        pagination, where each page contains a certain number of notes (specified by
        `num_notes_per_page`).
          num_notes_per_page: The `num_notes_per_page` parameter is the number of notes that should be
        displayed on each page of the results. By default, it is set to 5, but you can change it to any
        desired value. Defaults to 5
        
        Returns:
          a list of notes that were created by a specific user, based on the provided user ID. The notes
        are sorted by their creation date in descending order. The function also supports pagination,
        where the page number and the number of notes per page can be specified. The returned notes are
        converted to a dictionary format.
        """
        m_db = MongoClient.connect()

        skips = num_notes_per_page * (page_number - 1)
        limit = num_notes_per_page

        match_query = {"createdBy._id": ObjectId(user_id)}

        # # Check if the requested page exists
        # min_num_notes = skips + 1
        # if m_db[self.NOTE_MASTER_COLLECTION].count_documents({}) < min_num_notes:
        #     # We are requesting a page which is beyond the number of documents
        #     # return an empty array
        #     return []

        pipeline_find = [{"$match": match_query}]
        # Sort and paginate
        pipeline_paginate = [
            {"$sort": {"createdOn": -1}},
            {"$skip": skips},
            {"$limit": limit},
        ]
        # type conversion
        pipeline_type_conversion = [PipelineStages.stage_add_fields({
            "_id": {
                "$toString": "$_id"
            },
            "createdBy._id": {
                "$toString": "$createdBy._id"
            },
            "createdOn": {
                "$dateToString": {
                    "date": "$createdOn"
                }
            },
            "updatedOn": {
                "$dateToString": {
                    "date": "$updatedOn"
                }
            }
        })]
        # Final pipeline
        pipeline = pipeline_find + pipeline_type_conversion + pipeline_paginate
        aggregation = m_db[self.NOTE_MASTER_COLLECTION].aggregate(pipeline)
        all_notes = Common.cursor_to_dict(aggregation)

        return all_notes

    def search_notes(self, user_id, query, page_number, num_notes_per_page=5):
        """
        The `search_notes` function searches for notes in a MongoDB collection based on a user ID and a
        query, and returns paginated results.
        
        Args:
          user_id: The user ID is a unique identifier for a specific user. It is used to filter the
        search results to only include notes created by that user.
          query: The query parameter is the search term that you want to use to search for notes. It can
        be a string that represents the content or title of the notes you are looking for.
          page_number: The page number of the search results you want to retrieve. Each page contains a
        certain number of notes, specified by the `num_notes_per_page` parameter.
          num_notes_per_page: The number of notes to display per page in the search results. By default,
        it is set to 5. Defaults to 5
        
        Returns:
          the search results as a list of dictionaries.
        """
        m_db = MongoClient.connect()

        skips = num_notes_per_page * (page_number - 1)
        limit = num_notes_per_page

        regex = re.compile(query, re.IGNORECASE)
        pipeline_match = [
            {
                "$match": {
                    "$expr": {
                        "$eq": ["$createdBy._id", ObjectId(user_id)],
                    }
                }
            },
            {
                "$match": {
                    "$or": [
                        {"content": {"$regex": regex}},
                        {"title": {"$regex": regex}}
                    ]
                }
            },
            # {"$sort": {"modifiedOn": -1} if sortBy else {"modified": 1}},
        ]

        # # Check if the requested page exists
        # min_num_notes = skips + 1
        # if m_db[self.NOTE_MASTER_COLLECTION].aggregate(pipeline_match).count_documents < min_num_notes:
        #     # We are requesting a page which is beyond the number of documents
        #     # return an empty array
        #     return []

        pipeline_paginate = [
            {"$sort": {"createdOn": -1}},
            {"$skip": skips},
            {"$limit": limit},
        ]

        # type conversion
        pipeline_type_conversion = [PipelineStages.stage_add_fields({
            "_id": {
                "$toString": "$_id"
            },
            "createdBy._id": {
                "$toString": "$createdBy._id"
            },
            "createdOn": {
                "$dateToString": {
                    "date": "$createdOn"
                }
            },
            "updatedOn": {
                "$dateToString": {
                    "date": "$updatedOn"
                }
            }
        })]

        final_pipeline = pipeline_match + pipeline_type_conversion + pipeline_paginate

        search_results = m_db[self.NOTE_MASTER_COLLECTION].aggregate(final_pipeline)
        return Common.cursor_to_dict(search_results)
