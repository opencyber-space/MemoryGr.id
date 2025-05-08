import os
import logging
import redis
from typing import Dict, Any, List, Tuple
from .k8s import InMemoryDB         # your Kubernetes wrapper
from .db import FrameDBMemoryInstance
from .db import FrameDBMemoryDatabase

from .k8s import PersistentDB
from .db_persistent import FrameDBPersistentDatabase
from .db_persistent import FrameDBPersistentInstance

logger = logging.getLogger(__name__)

public_cluster_ip = os.getenv("CLUSTER_PUBLIC_URL")


def create_framedb_memory_instance(
    db_client: FrameDBMemoryDatabase,
    framedb_id: str,
    node_id: str,
    node_selector: Dict[str, str],
    metadata: Dict[str, Any],
    redis_config: List[str]
) -> Tuple[bool, int, str]:
    try:

        success, result = db_client.get_by_id(framedb_id)
        if success:
            raise Exception(f"framedb with the ID {framedb_id} already exists")

        k8s_client = InMemoryDB()

        # Deploy to Kubernetes
        node_port = k8s_client.get_available_node_port()
        k8s_client.create_redis(framedb_id, redis_config,
                                node_selector=node_selector, node_port=node_port)

        # Compose URLs
        public_url = f"{public_cluster_ip}:{node_port}"
        local_url = f"redis://{framedb_id}.framedb.svc.cluster.local:6379"

        # Create instance record
        instance = FrameDBMemoryInstance(
            framedb_id=framedb_id,
            node_id=node_id,
            port=node_port,
            metadata=metadata,
            public_url=public_url,
            local_url=local_url,
            status="Running"
        )

        success, result = db_client.insert(instance)
        return (success, node_port, "Instance created" if success else f"Insertion failed: {result}")

    except Exception as e:
        logger.error(f"Error creating FrameDBMemoryInstance: {e}")
        return False, -1, str(e)


def remove_framedb_memory_instance(db_client: FrameDBMemoryDatabase, framedb_id: str) -> Tuple[bool, str]:
    try:
        success, result = db_client.get_by_id(framedb_id)
        if not success:
            return False, f"Instance not found: {result}"

        k8s_client = InMemoryDB()

        # Remove from Kubernetes
        k8s_client.remove_deployment(framedb_id)

        # Remove from DB
        deleted, message = db_client.delete(framedb_id)
        return deleted, "Instance removed" if deleted else f"Delete failed: {message}"
    except Exception as e:
        logger.error(f"Error removing FrameDBMemoryInstance: {e}")
        return False, str(e)


def set_config_for_framedb_memory_instance(
    db_client: FrameDBMemoryDatabase,
    framedb_id: str,
    update_fields: Dict[str, Any]
) -> Tuple[bool, str]:
    try:
        success, result = db_client.get_by_id(framedb_id)
        if not success:
            return False, f"Instance not found: {result}"

        instance: FrameDBMemoryInstance = result
        redis_url = instance.local_url

        # Connect to Redis
        r = redis.Redis.from_url(redis_url)

        # Apply CONFIG SET commands
        for key, value in update_fields.items():
            response = r.config_set(key, value)
            logger.info(f"Set config: {key} = {value} => {response}")

        return True, "Configuration updated on Redis"

    except Exception as e:
        logger.error(f"Unhandled error in setting config: {e}")
        return False, str(e)



def create_framedb_persistent_instance(
    db_client: FrameDBPersistentDatabase,
    framedb_id: str,
    node_id: str,
    node_selector: Dict[str, str],
    metadata: Dict[str, Any],
    storage_size: str
) -> Tuple[bool, int, str]:
    try:
        success, result = db_client.get_by_id(framedb_id)
        if success:
            raise Exception(f"framedb with the ID {framedb_id} already exists")

        k8s_client = PersistentDB()

        # Deploy TiDB to Kubernetes
        node_port = k8s_client.get_available_node_port()
        k8s_client.create_tidb(
            deployment_name=framedb_id,
            storage_size=storage_size,
            node_selector=node_selector,
            node_port=node_port
        )

        # Compose URLs
        public_url = f"{public_cluster_ip}:{node_port}"
        local_url = f"mysql://{framedb_id}.framedb-storage.svc.cluster.local:4000"

        # Create instance record
        instance = FrameDBPersistentInstance(
            framedb_id=framedb_id,
            node_id=node_id,
            port=node_port,
            storage_size=storage_size,
            metadata=metadata,
            public_url=public_url,
            local_url=local_url,
            status="Running"
        )

        success, result = db_client.insert(instance)
        return (success, node_port, "Instance created" if success else f"Insertion failed: {result}")

    except Exception as e:
        logger.error(f"Error creating FrameDBPersistentInstance: {e}")
        return False, -1, str(e)


def remove_framedb_persistent_instance(
    db_client: FrameDBPersistentDatabase,
    framedb_id: str
) -> Tuple[bool, str]:
    try:
        success, result = db_client.get_by_id(framedb_id)
        if not success:
            return False, f"Instance not found: {result}"

        k8s_client = PersistentDB()

        # Remove from Kubernetes
        k8s_client.remove_deployment(framedb_id)

        # Remove from DB
        deleted, message = db_client.delete(framedb_id)
        return deleted, "Instance removed" if deleted else f"Delete failed: {message}"
    except Exception as e:
        logger.error(f"Error removing FrameDBPersistentInstance: {e}")
        return False, str(e)
