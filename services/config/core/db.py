from dataclasses import dataclass, field
from typing import Dict, Any

import os
import logging
from typing import Tuple, Any, Dict
from pymongo import MongoClient, errors

logger = logging.getLogger(__name__)

@dataclass
class FrameDBMemoryInstance:
    framedb_id: str
    node_id: str
    port: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    public_url: str = ''
    local_url: str = ''
    status: str = ''

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FrameDBMemoryInstance':
        return cls(
            framedb_id=data.get('framedb_id', ''),
            node_id=data.get('node_id', ''),
            port=data.get('port', 0),
            metadata=data.get('metadata', {}),
            public_url=data.get('public_url', ''),
            local_url=data.get('local_url', ''),
            status=data.get('status', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'framedb_id': self.framedb_id,
            'node_id': self.node_id,
            'port': self.port,
            'metadata': self.metadata,
            'public_url': self.public_url,
            'local_url': self.local_url,
            'status': self.status
        }


class FrameDBMemoryDatabase:
    def __init__(self):
        try:
            uri = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            self.client = MongoClient(uri)
            self.db = self.client["framedb"]
            self.collection = self.db["memory_instances"]
            logger.info("MongoDB connection established for FrameDBMemoryInstance")
        except errors.ConnectionFailure as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise

    def insert(self, instance: FrameDBMemoryInstance) -> Tuple[bool, Any]:
        try:
            document = instance.to_dict()
            result = self.collection.insert_one(document)
            logger.info(f"FrameDBMemoryInstance inserted with id: {instance.framedb_id}")
            return True, result.inserted_id
        except errors.PyMongoError as e:
            logger.error(f"Error inserting FrameDBMemoryInstance: {e}")
            return False, str(e)

    def update(self, framedb_id: str, update_fields: Dict[str, Any]) -> Tuple[bool, Any]:
        try:
            result = self.collection.update_one(
                {"framedb_id": framedb_id},
                {"$set": update_fields},
                upsert=True
            )
            if result.modified_count > 0:
                logger.info(f"FrameDBMemoryInstance with id {framedb_id} updated")
                return True, result.modified_count
            else:
                logger.info(f"No document found with framedb_id {framedb_id} to update")
                return False, "No document found to update"
        except errors.PyMongoError as e:
            logger.error(f"Error updating FrameDBMemoryInstance: {e}")
            return False, str(e)

    def delete(self, framedb_id: str) -> Tuple[bool, Any]:
        try:
            result = self.collection.delete_one({"framedb_id": framedb_id})
            if result.deleted_count > 0:
                logger.info(f"FrameDBMemoryInstance with id {framedb_id} deleted")
                return True, result.deleted_count
            else:
                logger.info(f"No document found with framedb_id {framedb_id} to delete")
                return False, "No document found to delete"
        except errors.PyMongoError as e:
            logger.error(f"Error deleting FrameDBMemoryInstance: {e}")
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
            logger.error(f"Error querying FrameDBMemoryInstances: {e}")
            return False, str(e)

    def get_by_id(self, framedb_id: str) -> Tuple[bool, Any]:
        try:
            doc = self.collection.find_one({"framedb_id": framedb_id})
            if doc:
                doc.pop('_id', None)
                instance = FrameDBMemoryInstance.from_dict(doc)
                logger.info(f"FrameDBMemoryInstance with id {framedb_id} retrieved")
                return True, instance
            else:
                logger.info(f"No FrameDBMemoryInstance found with id {framedb_id}")
                return False, "No document found"
        except errors.PyMongoError as e:
            logger.error(f"Error retrieving FrameDBMemoryInstance: {e}")
            return False, str(e)


