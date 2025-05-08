import os
import logging
from flask import Flask, request, jsonify
from typing import Dict, Any

from .db import FrameDBMemoryDatabase, FrameDBMemoryInstance
from .db_persistent import FrameDBPersistentDatabase

from .instance import (
    create_framedb_memory_instance,
    remove_framedb_memory_instance,
    set_config_for_framedb_memory_instance,
    create_framedb_persistent_instance,
    remove_framedb_persistent_instance
)

app = Flask(__name__)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

db_client = FrameDBMemoryDatabase()
persistent_db_client = FrameDBPersistentDatabase()

public_cluster_ip = os.getenv("CLUSTER_PUBLIC_URL")


@app.route('/framedb/instances', methods=['POST'])
def create_instance():
    try:
        payload = request.json
        framedb_id = payload["framedb_id"]
        node_id = payload["node_id"]
        node_selector = payload.get("node_selector", {})
        metadata = payload.get("metadata", {})
        redis_config = payload.get("redis_config", [])

        success, port, msg = create_framedb_memory_instance(
            db_client=db_client,
            framedb_id=framedb_id,
            node_id=node_id,
            node_selector=node_selector,
            metadata=metadata,
            redis_config=redis_config
        )

        if success:
            return jsonify({"success": True, "message": msg, "port": port}), 200
        else:
            return jsonify({"success": False, "error": msg}), 400
    except Exception as e:
        logger.error(f"Error in create_instance: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/instances/<framedb_id>', methods=['DELETE'])
def delete_instance(framedb_id):
    try:
        success, msg = remove_framedb_memory_instance(db_client, framedb_id)

        if success:
            return jsonify({"success": True, "message": msg}), 200
        else:
            return jsonify({"success": False, "error": msg}), 400
    except Exception as e:
        logger.error(f"Error in delete_instance: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/instances/<framedb_id>/config', methods=['POST'])
def set_config(framedb_id):
    try:
        config_updates: Dict[str, Any] = request.json
        success, msg = set_config_for_framedb_memory_instance(
            db_client=db_client,
            framedb_id=framedb_id,
            update_fields=config_updates
        )

        if success:
            return jsonify({"success": True, "message": msg}), 200
        else:
            return jsonify({"success": False, "error": msg}), 400
    except Exception as e:
        logger.error(f"Error in set_config: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/instances/<framedb_id>/update', methods=['POST'])
def update_instance_fields(framedb_id):
    try:
        update_fields: Dict[str, Any] = request.json
        success, msg = db_client.update(framedb_id, update_fields)

        if success:
            return jsonify({"success": True, "message": "Fields updated"}), 200
        else:
            return jsonify({"success": False, "error": msg}), 400
    except Exception as e:
        logger.error(f"Error in update_instance_fields: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/instances', methods=['GET'])
def list_instances():
    try:
        query_filter = request.json if request.is_json else {}
        success, results = db_client.query(query_filter)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in list_instances: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



@app.route('/framedb/persistent-instances', methods=['POST'])
def create_persistent_instance():
    try:
        payload = request.json
        framedb_id = payload["framedb_id"]
        node_id = payload["node_id"]
        node_selector = payload.get("node_selector", {})
        metadata = payload.get("metadata", {})
        storage_size = payload.get("storage_size", "1Gi")

        success, port, msg = create_framedb_persistent_instance(
            db_client=persistent_db_client,
            framedb_id=framedb_id,
            node_id=node_id,
            node_selector=node_selector,
            metadata=metadata,
            storage_size=storage_size
        )

        if success:
            return jsonify({"success": True, "message": msg, "port": port}), 200
        else:
            return jsonify({"success": False, "error": msg}), 400
    except Exception as e:
        logger.error(f"Error in create_persistent_instance: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/persistent-instances/<framedb_id>', methods=['DELETE'])
def delete_persistent_instance(framedb_id):
    try:
        success, msg = remove_framedb_persistent_instance(persistent_db_client, framedb_id)

        if success:
            return jsonify({"success": True, "message": msg}), 200
        else:
            return jsonify({"success": False, "error": msg}), 400
    except Exception as e:
        logger.error(f"Error in delete_persistent_instance: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/persistent-instances/<framedb_id>/update', methods=['POST'])
def update_persistent_instance(framedb_id):
    try:
        update_fields: Dict[str, Any] = request.json
        success, msg = persistent_db_client.update(framedb_id, update_fields)

        if success:
            return jsonify({"success": True, "message": "Fields updated"}), 200
        else:
            return jsonify({"success": False, "error": msg}), 400
    except Exception as e:
        logger.error(f"Error in update_persistent_instance: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/persistent-instances', methods=['GET'])
def list_persistent_instances():
    try:
        query_filter = request.json if request.is_json else {}
        success, results = persistent_db_client.query(query_filter)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in list_persistent_instances: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/persistent-instances/<framedb_id>', methods=['GET'])
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