import requests
import os


class ClusterClient:
    def __init__(self):
        self.base_url = os.getenv("CLUSTER_SERVICE_URL", "http://localhost:3000")

    def read_cluster(self, cluster_id):
        try:
            response = requests.get(f"{self.base_url}/clusters/{cluster_id}")
            response.raise_for_status()
            return True, response.json()
        except Exception as err:
            return False, f"Error occurred: {err}"

def get_cluster_public_url(cluster_id):
    try:

        cluster_data = ClusterClient().read_cluster(cluster_id)
        framedb_config_url = cluster_data['config']['urlMap'].get('framedb_config_url')

        if framedb_config_url == "":
            raise  Exception("cluster does not provide framedb config service")
        
        return framedb_config_url


    except Exception as e:
        raise e
