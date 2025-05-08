import os
import logging
from typing import Dict, Any
from cachetools import LFUCache


from .interfaces.memory import RedisInterface
from .interfaces.storage import TiDBInterface
from .cluster_info import FrameDBClusterClient
from .routing import ObjectRoutingClient
from .routing import StreamRoutingClient

logger = logging.getLogger(__name__)


# Default cache size fallback
cache_size = int(os.getenv("CONNECTIONS_CACHE_ENV_SIZE", 100))

# Global connection cache: framedb_id -> RedisInterface or TiDBInterface
CONNECTION_CACHE = LFUCache(maxsize=cache_size)

def get_cached_connection(framedb_id: str, url: str, kind: str):
    if framedb_id in CONNECTION_CACHE:
        return CONNECTION_CACHE[framedb_id]

    if kind == "in-memory" or kind == "stream":
        conn = RedisInterface(url)
    elif kind == "storage":
        conn = TiDBInterface(url)
    else:
        raise ValueError(f"Unsupported connection type: {kind}")

    conn.connect()
    CONNECTION_CACHE[framedb_id] = conn
    return conn


def set_object(
    obj: Dict[str, Any],
    cluster_client: FrameDBClusterClient,
    object_routing_client: ObjectRoutingClient,
    stream_routing_client: StreamRoutingClient
) -> Dict[str, Any]:
    framedb_id = obj["framedb_id"]
    storage_type = obj["type"]
    cluster_id = os.getenv("CLUSTER_ID")

    # Step 1: Get instance info
    if storage_type == "in-memory":
        response = cluster_client.get_instance_by_id(framedb_id)
    elif storage_type == "storage":
        response = cluster_client.get_persistent_instance_by_id(framedb_id)
    elif storage_type == "stream":
        response = cluster_client.get_instance_by_id(
            framedb_id)  # stream queues use Redis
    else:
        return {"success": False, "message": f"Unsupported type: {storage_type}"}

    if not response["success"]:
        return {"success": False, "message": f"FrameDB instance not found: {response['error']}"}

    instance = response["data"]
    instance_cluster_id = instance.get("cluster_id", "")
    url = instance["local_url"] if instance_cluster_id == cluster_id else instance["public_url"]

    # Step 2: Write data
    try:
        if storage_type == "in-memory":
            redis = get_cached_connection(framedb_id, url, "in-memory")
            redis.connect()
            redis.set(obj["key"], obj["data"])

        elif storage_type == "storage":
            tidb = get_cached_connection(framedb_id, url, "storage")
            tidb.connect()
            tidb.set(obj["key"], obj["data"])

        elif storage_type == "stream":
            redis = get_cached_connection(framedb_id, url, "stream")
            redis.connect()
            redis.lpush(obj["key"], obj["data"])

    except Exception as e:
        logger.error(f"Write failed for key {obj['key']}: {e}")
        return {"success": False, "message": f"Write failed: {e}"}

    # Step 3: Register in routing
    try:
        if storage_type == "stream":
            status, result = stream_routing_client.register_stream(
                queue_name=obj["key"],
                framedb_id=framedb_id,
                metadata=obj.get("metadata", {})
            )
        else:
            status, result = object_routing_client.create_object(
                object_id=obj["key"],
                framedb_id=framedb_id,
                framedb_type=storage_type,
                size=len(obj["data"]),
                metadata=obj.get("metadata", {})
            )

        if status == 200 and result.get("success"):
            return {"success": True, "message": "Object stored and routed successfully"}
        else:
            return {"success": False, "message": f"Routing failed: {result}"}

    except Exception as e:
        logger.error(f"Routing registration failed: {e}")
        return {"success": False, "message": f"Routing registration failed: {e}"}


def get_object(
    object_id: str,
    cluster_client: FrameDBClusterClient,
    routing_client: ObjectRoutingClient,
    stream_routing_client: StreamRoutingClient
) -> Dict[str, Any]:
    current_cluster = os.getenv("CLUSTER_ID")

    # Step 1: Routing lookup
    try:
        status, route_info = routing_client.get_object(object_id)
        if status != 200 or not route_info.get("success"):
            # fallback to stream lookup
            status, route_info = stream_routing_client.get_stream(object_id)
            if status != 200 or not route_info.get("success"):
                return {"found": False, "message": f"Object/stream '{object_id}' not found in routing service"}
            metadata = route_info["data"]
            framedb_type = "stream"
        else:
            metadata = route_info["data"]
            framedb_type = metadata.get("framedb_type")
    except Exception as e:
        logger.error(f"Routing lookup failed: {e}")
        return {"found": False, "message": f"Routing lookup failed: {e}"}

    framedb_id = metadata.get("framedb_id")
    copies = metadata.get("copies", [])

    # Step 2: Choose best copy
    selected_framedb_id = framedb_id
    for copy in copies:
        if copy.get("cluster_id") == current_cluster:
            selected_framedb_id = copy.get("framedb_id")
            break

    # Step 3: Resolve instance
    try:
        response = cluster_client.get_instance_by_id(selected_framedb_id) \
            if framedb_type in ("in-memory", "stream") \
            else cluster_client.get_persistent_instance_by_id(selected_framedb_id)

        if not response["success"]:
            return {"found": False, "message": f"FrameDB instance not found: {response['error']}"}
    except Exception as e:
        logger.error(f"Error fetching instance info: {e}")
        return {"found": False, "message": f"Failed to fetch instance info: {e}"}

    instance = response["data"]
    url = instance["local_url"] if instance.get(
        "cluster_id") == current_cluster else instance["public_url"]

    # Step 4: Read data
    try:
        if framedb_type == "in-memory":
            redis = get_cached_connection(framedb_id, url, "in-memory")
            redis.connect()
            data = redis.get(object_id)
        elif framedb_type == "storage":
            tidb = get_cached_connection(framedb_id, url, "storage")
            tidb.connect()
            data = tidb.get(object_id)
        elif framedb_type == "stream":
            redis = get_cached_connection(framedb_id, url, "stream")
            redis.connect()
            data = redis.rpop(object_id)
    except Exception as e:
        logger.error(f"Data read failed: {e}")
        return {"found": False, "message": f"Data read failed: {e}"}

    if data is None:
        return {"found": False, "message": f"No data found for key '{object_id}'"}

    return {
        "found": True,
        "object": {
            "key": object_id,
            "data": data,
            "metadata": metadata.get("metadata", {}),
            "framedb_id": selected_framedb_id,
            "type": framedb_type
        },
        "message": "Object retrieved successfully"
    }
