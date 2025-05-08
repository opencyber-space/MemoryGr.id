import requests
from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class PersistentAPIClient:
    def __init__(self, cluster_url: str):
        self.cluster_url = cluster_url.rstrip('/')

    def create_instance(
        self,
        framedb_id: str,
        node_id: str,
        node_selector: Dict[str, str],
        metadata: Dict[str, Any],
        storage_size: str
    ) -> Tuple[bool, Any]:
        try:
            url = f"{self.cluster_url}/framedb/persistent-instances"
            payload = {
                "framedb_id": framedb_id,
                "node_id": node_id,
                "node_selector": node_selector,
                "metadata": metadata,
                "storage_size": storage_size
            }

            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                port = response.json().get("port", 0)
                logger.info(f"Remote persistent instance created on port {port}")
                return True, port
            else:
                logger.warning(f"Failed to create persistent instance: {response.text}")
                return False, response.text
        except Exception as e:
            logger.error(f"Exception during create_instance: {e}")
            return False, str(e)

    def delete_instance(self, framedb_id: str) -> Tuple[bool, str]:
        try:
            url = f"{self.cluster_url}/framedb/persistent-instances/{framedb_id}"
            response = requests.delete(url, timeout=10)
            if response.status_code == 200:
                logger.info(f"Remote persistent instance '{framedb_id}' deleted")
                return True, "Deleted"
            else:
                logger.warning(f"Failed to delete persistent instance: {response.text}")
                return False, response.text
        except Exception as e:
            logger.error(f"Exception during delete_instance: {e}")
            return False, str(e)
