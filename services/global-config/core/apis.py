from flask import Flask, jsonify, request
from .instances import create_framedb_memory_instance_global, remove_framedb_memory_instance_global, set_config
from .instances import create_framedb_persistent_instance_global, remove_framedb_persistent_instance_global
from .db import FrameDBMemoryDatabase, FrameDBPersistentDatabase

from .local_config import (
    setup_framedb_config_service, status_framedb_config_service, remove_framedb_config_service
)
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

db_client = FrameDBMemoryDatabase()
persistent_db_client = FrameDBPersistentDatabase()


@app.route('/global/framedb/instances', methods=['POST'])
def create_global_instance():
    try:
        payload = request.json
        required_fields = ['framedb_id', 'node_id',
                           'metadata', 'redis_config', 'cluster_id']
        for field in required_fields:
            if field not in payload:
                return jsonify({"success": False, "error": f"Missing field: {field}"}), 400

        success, msg = create_framedb_memory_instance_global(
            global_db=db_client,
            framedb_id=payload['framedb_id'],
            node_id=payload['node_id'],
            metadata=payload['metadata'],
            redis_config=payload['redis_config'],
            cluster_id=payload['cluster_id']
        )

        if success:
            return jsonify({"success": True, "message": msg}), 200
        else:
            return jsonify({"success": False, "error": msg}), 400
    except Exception as e:
        logger.error(f"Error in create_global_instance: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/global/framedb/instances/<framedb_id>', methods=['DELETE'])
def delete_global_instance(framedb_id):
    try:
        success, msg = remove_framedb_memory_instance_global(
            db_client, framedb_id)
        if success:
            return jsonify({"success": True, "message": msg}), 200
        else:
            return jsonify({"success": False, "error": msg}), 400
    except Exception as e:
        logger.error(f"Error in delete_global_instance: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/global/framedb/instances/cluster/<cluster_id>', methods=['GET'])
def list_by_cluster(cluster_id):
    try:
        success, results = db_client.list_by_cluster_id(cluster_id)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in list_by_cluster: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/global/framedb/instances/cluster/<cluster_id>/node/<node_id>', methods=['GET'])
def list_by_cluster_and_node(cluster_id, node_id):
    try:
        success, results = db_client.list_by_cluster_and_node(
            cluster_id, node_id)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in list_by_cluster_and_node: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/global/framedb/instances/query', methods=['POST'])
def query_instances():
    try:
        query_filter = request.json or {}
        success, results = db_client.query(query_filter)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in query_instances: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/global/framedb/instances/<framedb_id>', methods=['GET'])
def get_instance_by_id(framedb_id):
    try:
        success, result = db_client.get_by_id(framedb_id)
        if success:
            return jsonify({"success": True, "data": result.to_dict()}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in get_instance_by_id: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/global/framedb/set-config', methods=['POST'])
def status_framedb_config():
    try:
        data = request.json
        
        success, resp = set_config(db_client, framedb_id=data['framedb_id'], data=data.get('config'))

        if success:
            return jsonify({"success": True, "data": resp}), 200
        else:
            return jsonify({"success": False, "error": resp}), 404

    except Exception as e:
        logger.error(f"Error in /framedb-config/status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb-config/setup', methods=['POST'])
def setup_framedb_config():
    try:
        data = request.json
        kube_config = data.get("kube_config")
        storage_size = data.get("storage_size", "1Gi")

        if not kube_config:
            return jsonify({"success": False, "error": "Missing kube_config"}), 400

        setup_framedb_config_service(
            kube_config_dict=kube_config, storage_size=storage_size)
        return jsonify({"success": True, "message": "FrameDB config service setup complete"}), 200

    except Exception as e:
        logger.error(f"Error in /framedb-config/setup: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb-config/remove', methods=['DELETE'])
def remove_framedb_config():
    try:
        data = request.json
        kube_config = data.get("kube_config")

        if not kube_config:
            return jsonify({"success": False, "error": "Missing kube_config"}), 400

        remove_framedb_config_service(kube_config_dict=kube_config)
        return jsonify({"success": True, "message": "FrameDB config service removed"}), 200

    except Exception as e:
        logger.error(f"Error in /framedb-config/remove: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb-config/status', methods=['POST'])
def status_framedb_config():
    try:
        data = request.json
        kube_config = data.get("kube_config")

        if not kube_config:
            return jsonify({"success": False, "error": "Missing kube_config"}), 400

        status = status_framedb_config_service(kube_config_dict=kube_config)
        return jsonify({"success": True, "data": status}), 200

    except Exception as e:
        logger.error(f"Error in /framedb-config/status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



@app.route('/global/framedb/persistent-instances', methods=['POST'])
def create_global_persistent_instance():
    try:
        payload = request.json
        required_fields = ['framedb_id', 'node_id', 'metadata', 'storage_size', 'cluster_id']
        for field in required_fields:
            if field not in payload:
                return jsonify({"success": False, "error": f"Missing field: {field}"}), 400

        success, msg = create_framedb_persistent_instance_global(
            global_db=persistent_db_client,
            framedb_id=payload['framedb_id'],
            node_id=payload['node_id'],
            metadata=payload['metadata'],
            storage_size=payload['storage_size'],
            cluster_id=payload['cluster_id']
        )

        if success:
            return jsonify({"success": True, "message": msg}), 200
        else:
            return jsonify({"success": False, "error": msg}), 400
    except Exception as e:
        logger.error(f"Error in create_global_persistent_instance: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/global/framedb/persistent-instances/<framedb_id>', methods=['DELETE'])
def delete_global_persistent_instance(framedb_id):
    try:
        success, msg = remove_framedb_persistent_instance_global(
            persistent_db_client, framedb_id)
        if success:
            return jsonify({"success": True, "message": msg}), 200
        else:
            return jsonify({"success": False, "error": msg}), 400
    except Exception as e:
        logger.error(f"Error in delete_global_persistent_instance: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/global/framedb/persistent-instances/cluster/<cluster_id>', methods=['GET'])
def list_persistent_by_cluster(cluster_id):
    try:
        success, results = persistent_db_client.list_by_cluster_id(cluster_id)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in list_persistent_by_cluster: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/global/framedb/persistent-instances/cluster/<cluster_id>/node/<node_id>', methods=['GET'])
def list_persistent_by_cluster_and_node(cluster_id, node_id):
    try:
        success, results = persistent_db_client.list_by_cluster_and_node(cluster_id, node_id)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in list_persistent_by_cluster_and_node: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/global/framedb/persistent-instances/query', methods=['POST'])
def query_persistent_instances():
    try:
        query_filter = request.json or {}
        success, results = persistent_db_client.query(query_filter)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in query_persistent_instances: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/global/framedb/persistent-instances/<framedb_id>', methods=['GET'])
def get_persistent_instance_by_id(framedb_id):
    try:
        success, result = persistent_db_client.get_by_id(framedb_id)
        if success:
            return jsonify({"success": True, "data": result.to_dict()}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in get_persistent_instance_by_id: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def run_server():
    try:
        app.run(host='0.0.0.0', port=5000)
    except Exception as e:
        raise e
