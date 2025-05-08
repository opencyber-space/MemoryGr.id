import requests
from typing import Dict, Any, List, Optional, Tuple


class InMemoryAPIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def create_instance(
        self,
        framedb_id: str,
        node_id: str,
        node_selector: Dict[str, str],
        metadata: Dict[str, Any],
        redis_config: List[str]
    ) -> Tuple[bool, Any]:
        url = f"{self.base_url}/framedb/instances"
        payload = {
            "framedb_id": framedb_id,
            "node_id": node_id,
            "node_selector": node_selector,
            "metadata": metadata,
            "redis_config": redis_config
        }
        response = requests.post(url, json=payload)
        response = response.json()

        is_success = response.get("success", False)
        if not is_success:
            return False, response['error']

        return True, response['port']

    def delete_instance(self, framedb_id: str) -> Tuple[bool, Any]:
        url = f"{self.base_url}/framedb/instances/{framedb_id}"
        response = requests.delete(url)
        return self._handle_response(response)

    def set_redis_config(self, framedb_id: str, config: Dict[str, str]) -> Tuple[bool, Any]:
        url = f"{self.base_url}/framedb/instances/{framedb_id}/config"
        response = requests.post(url, json=config)
        return self._handle_response(response)

    def update_instance_fields(self, framedb_id: str, fields: Dict[str, Any]) -> Tuple[bool, Any]:
        url = f"{self.base_url}/framedb/instances/{framedb_id}/update"
        response = requests.post(url, json=fields)
        return self._handle_response(response)

    def list_instances(self, filters: Optional[Dict[str, Any]] = None) -> Tuple[bool, Any]:
        url = f"{self.base_url}/framedb/instances"
        response = requests.get(url, json=filters or {})
        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> Tuple[bool, Any]:
        try:
            data = response.json()
            return data.get("success", False), data.get("data") or data.get("message") or data.get("error")
        except Exception as e:
            return False, f"Failed to parse response: {e}"

