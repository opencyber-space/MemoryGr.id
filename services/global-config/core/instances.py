from typing import Dict, Any, List, Tuple
from .proxy_in_memory import InMemoryAPIClient
from .proxy_persistent import PersistentAPIClient
from .db import FrameDBMemoryInstance, FrameDBMemoryDatabase, FrameDBPersistentDatabase, FrameDBPersistentInstance
from .cluster_db import get_cluster_public_url

import logging

logger = logging.getLogger(__name__)


def create_framedb_memory_instance_global(
    global_db: FrameDBMemoryDatabase,
    framedb_id: str,
    node_id: str,
    metadata: Dict[str, Any],
    redis_config: List[str],
    cluster_id: str
) -> Tuple[bool, str]:
    try:
        cluster_url = get_cluster_public_url(cluster_id)
        api_client = InMemoryAPIClient(cluster_url)

        node_selector = {"nodeID": node_id}

        # Call remote cluster to create framedb instance
        success, result = api_client.create_instance(
            framedb_id=framedb_id,
            node_id=node_id,
            node_selector=node_selector,
            metadata=metadata,
            redis_config=redis_config
        )

        if not success:
            return False, f"Cluster call failed: {result}"

        # Compose URLs
        public_url = f"{cluster_url}:{result}"
        local_url = f"redis://{framedb_id}.framedb.svc.cluster.local:6379"

        instance = FrameDBMemoryInstance(
            framedb_id=framedb_id,
            node_id=node_id,
            port=result,
            metadata=metadata,
            public_url=public_url,
            local_url=local_url,
            status="Running",
            cluster_id=cluster_id
        )

        inserted, response = global_db.insert(instance)
        if inserted:
            return True, "Instance created in global registry"
        else:
            return False, f"DB insert failed: {response}"

    except Exception as e:
        logger.error(f"Global create failed: {e}")
        return False, str(e)


def remove_framedb_memory_instance_global(global_db: FrameDBMemoryDatabase, framedb_id: str) -> Tuple[bool, str]:
    try:
        found, instance = global_db.get_by_id(framedb_id)
        if not found:
            return False, "Instance not found in global registry"

        cluster_url = get_cluster_public_url(instance.cluster_id)
        api_client = InMemoryAPIClient(cluster_url)

        # Call remote cluster to remove deployment
        deleted, msg = api_client.delete_instance(framedb_id)
        if not deleted:
            return False, f"Cluster removal failed: {msg}"

        # Remove from global DB
        removed, db_msg = global_db.delete(framedb_id)
        return removed, "Removed from global registry" if removed else f"DB deletion failed: {db_msg}"

    except Exception as e:
        logger.error(f"Global delete failed: {e}")
        return False, str(e)

def set_config(global_db: FrameDBMemoryDatabase, framedb_id: str, data: dict):
    try:

        found, instance = global_db.get_by_id(framedb_id)
        if not found:
            return False, "Instance not found in global registry"
        
        cluster_url = get_cluster_public_url(instance.cluster_id)
        api_client = InMemoryAPIClient(cluster_url)

        return api_client.set_redis_config(framedb_id, data)

    except Exception as e:
        logger.error(f"Config set error: {e}")
        return False, str(e)


def create_framedb_persistent_instance_global(
    global_db: FrameDBPersistentDatabase,
    framedb_id: str,
    node_id: str,
    metadata: Dict[str, Any],
    storage_size: str,
    cluster_id: str
) -> Tuple[bool, str]:
    try:
        cluster_url = get_cluster_public_url(cluster_id)
        api_client = PersistentAPIClient(cluster_url)

        node_selector = {"nodeID": node_id}

        # Call remote cluster to create persistent instance
        success, result = api_client.create_instance(
            framedb_id=framedb_id,
            node_id=node_id,
            node_selector=node_selector,
            metadata=metadata,
            storage_size=storage_size
        )

        if not success:
            return False, f"Cluster call failed: {result}"

        # Compose URLs
        public_url = f"{cluster_url}:{result}"
        local_url = f"mysql://{framedb_id}.framedb-storage.svc.cluster.local:4000"

        instance = FrameDBPersistentInstance(
            framedb_id=framedb_id,
            node_id=node_id,
            port=result,
            storage_size=storage_size,
            metadata=metadata,
            public_url=public_url,
            local_url=local_url,
            status="Running",
            cluster_id=cluster_id
        )

        inserted, response = global_db.insert(instance)
        if inserted:
            return True, "Instance created in global registry"
        else:
            return False, f"DB insert failed: {response}"

    except Exception as e:
        logger.error(f"Global create failed (persistent): {e}")
        return False, str(e)


def remove_framedb_persistent_instance_global(
    global_db: FrameDBPersistentDatabase,
    framedb_id: str
) -> Tuple[bool, str]:
    try:
        found, instance = global_db.get_by_id(framedb_id)
        if not found:
            return False, "Instance not found in global registry"

        cluster_url = get_cluster_public_url(instance.cluster_id)
        api_client = PersistentAPIClient(cluster_url)

        # Call remote cluster to remove persistent deployment
        deleted, msg = api_client.delete_instance(framedb_id)
        if not deleted:
            return False, f"Cluster removal failed: {msg}"

        # Remove from global DB
        removed, db_msg = global_db.delete(framedb_id)
        return removed, "Removed from global registry" if removed else f"DB deletion failed: {db_msg}"

    except Exception as e:
        logger.error(f"Global delete failed (persistent): {e}")
        return False, str(e)
