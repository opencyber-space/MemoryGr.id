import os
import logging
from pymongo import MongoClient, errors
from typing import Tuple, Dict, Any
from .schema import FrameDBObject, FrameDBCopy, StreamsObject

logger = logging.getLogger(__name__)


class FrameDBObjectDatabase:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["framedb"]
            self.collection = self.db["objects"]
            logger.info("MongoDB connection established for FrameDBObject")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, obj: FrameDBObject) -> Tuple[bool, Any]:
        try:
            document = obj.to_dict()
            result = self.collection.insert_one(document)
            logger.info(f"FrameDBObject inserted with _id: {obj.object_id}")
            return True, result.inserted_id
        except errors.PyMongoError as e:
            logger.error(f"Error inserting FrameDBObject: {e}")
            return False, str(e)

    def update(self, object_id: str, update_fields: Dict[str, Any]) -> Tuple[bool, Any]:
        try:
            result = self.collection.update_one(
                {"_id": object_id},
                {"$set": update_fields},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"FrameDBObject with _id {object_id} updated")
                return True, result.modified_count
            else:
                logger.info(f"No document found with _id {object_id} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating FrameDBObject: {e}")
            return False, str(e)

    def delete(self, object_id: str) -> Tuple[bool, Any]:
        try:
            result = self.collection.delete_one({"_id": object_id})
            if result.deleted_count > 0:
                logger.info(f"FrameDBObject with _id {object_id} deleted")
                return True, result.deleted_count
            else:
                logger.info(f"No document found with _id {object_id} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting FrameDBObject: {e}")
            return False, str(e)

    def query(self, query_filter: Dict[str, Any]) -> Tuple[bool, Any]:
        try:
            result = self.collection.find(query_filter)
            documents = []
            for doc in result:
                doc.pop('_id', None)  # Optional: you can keep _id if desired
                documents.append(doc)
            logger.info(f"Query successful, found {len(documents)} documents")
            return True, documents
        except errors.PyMongoError as e:
            logger.error(f"Error querying FrameDBObjects: {e}")
            return False, str(e)

    def get_by_id(self, object_id: str) -> Tuple[bool, Any]:
        try:
            doc = self.collection.find_one({"_id": object_id})
            if doc:
                instance = FrameDBObject.from_dict(doc)
                logger.info(f"FrameDBObject with _id {object_id} retrieved")
                return True, instance
            else:
                logger.info(f"No FrameDBObject found with _id {object_id}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving FrameDBObject: {e}")
            return False, str(e)
    

    def add_copy(self, object_id: str, copy: FrameDBCopy) -> Tuple[bool, Any]:
        try:
            result = self.collection.update_one(
                {"_id": object_id},
                {"$addToSet": {"copies": copy.to_dict()}}
            )
            if result.modified_count > 0:
                logger.info(f"Copy added to FrameDBObject with _id {object_id}")
                return True, "Copy added"
            else:
                logger.info(f"No change made when adding copy to FrameDBObject with _id {object_id}")
                return False, "Copy already exists or object not found"
        except errors.PyMongoError as e:
            logger.error(f"Error adding copy to FrameDBObject: {e}")
            return False, str(e)


    def remove_copy(self, object_id: str, framedb_id: str) -> Tuple[bool, Any]:
        try:
            result = self.collection.update_one(
                {"_id": object_id},
                {"$pull": {"copies": {"framedb_id": framedb_id}}}
            )
            if result.modified_count > 0:
                logger.info(f"Copy with framedb_id {framedb_id} removed from FrameDBObject {object_id}")
                return True, "Copy removed"
            else:
                logger.info(f"No copy with framedb_id {framedb_id} found in FrameDBObject {object_id}")
                return False, "Copy not found"
        except errors.PyMongoError as e:
            logger.error(f"Error removing copy from FrameDBObject: {e}")
            return False, str(e)


    def copy_exists(self, object_id: str, framedb_id: str) -> Tuple[bool, Any]:
        try:
            result = self.collection.find_one(
                {"_id": object_id, "copies.framedb_id": framedb_id}
            )
            if result:
                logger.info(f"Copy with framedb_id {framedb_id} exists in FrameDBObject {object_id}")
                return True, "Copy exists"
            else:
                logger.info(f"Copy with framedb_id {framedb_id} does not exist in FrameDBObject {object_id}")
                return False, "Copy does not exist"
        except errors.PyMongoError as e:
            logger.error(f"Error checking if copy exists in FrameDBObject: {e}")
            return False, str(e)


class StreamsObjectDatabase:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["framedb"]
            self.collection = self.db["streams"]
            logger.info("MongoDB connection established for StreamsObject")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, obj: StreamsObject) -> Tuple[bool, Any]:
        try:
            document = obj.to_dict()
            result = self.collection.insert_one(document)
            logger.info(f"StreamsObject inserted with _id (queue_name): {obj.queue_name}")
            return True, result.inserted_id
        except errors.PyMongoError as e:
            logger.error(f"Error inserting StreamsObject: {e}")
            return False, str(e)

    def update(self, queue_name: str, update_fields: Dict[str, Any]) -> Tuple[bool, Any]:
        try:
            result = self.collection.update_one(
                {"_id": queue_name},
                {"$set": update_fields},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"StreamsObject with _id (queue_name) {queue_name} updated")
                return True, result.modified_count
            else:
                logger.info(f"No document found with _id {queue_name} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating StreamsObject: {e}")
            return False, str(e)

    def delete(self, queue_name: str) -> Tuple[bool, Any]:
        try:
            result = self.collection.delete_one({"_id": queue_name})
            if result.deleted_count > 0:
                logger.info(f"StreamsObject with _id {queue_name} deleted")
                return True, result.deleted_count
            else:
                logger.info(f"No document found with _id {queue_name} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting StreamsObject: {e}")
            return False, str(e)

    def get_by_id(self, queue_name: str) -> Tuple[bool, Any]:
        try:
            doc = self.collection.find_one({"_id": queue_name})
            if doc:
                instance = StreamsObject.from_dict(doc)
                logger.info(f"StreamsObject with _id {queue_name} retrieved")
                return True, instance
            else:
                logger.info(f"No StreamsObject found with _id {queue_name}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving StreamsObject: {e}")
            return False, str(e)

    def query(self, query_filter: Dict[str, Any]) -> Tuple[bool, Any]:
        try:
            result = self.collection.find(query_filter)
            documents = []
            for doc in result:
                doc.pop('_id', None)
                documents.append(doc)
            logger.info(f"Query successful, found {len(documents)} documents")
            return True, documents
        except errors.PyMongoError as e:
            logger.error(f"Error querying StreamsObjects: {e}")
            return False, str(e)