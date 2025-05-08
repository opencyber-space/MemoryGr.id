from flask import Flask, request, jsonify
from .db import FrameDBObjectDatabase, StreamsObject, StreamsObjectDatabase
from .schema import FrameDBCopy, FrameDBObject, StreamsObject
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)

db_client = FrameDBObjectDatabase()
streams_db = StreamsObjectDatabase()


@app.route('/framedb/objects', methods=['POST'])
def create_framedb_object():
    try:
        data = request.json
        obj = FrameDBObject.from_dict(data)
        success, msg = db_client.insert(obj)
        if success:
            return jsonify({"success": True, "message": "Object inserted", "id": str(msg)}), 201
        else:
            return jsonify({"success": False, "error": msg}), 400
    except Exception as e:
        logger.error(f"Error in create_framedb_object: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/objects/<object_id>/update', methods=['POST'])
def update_framedb_object(object_id):
    try:
        update_fields = request.json
        success, msg = db_client.update(object_id, update_fields)
        if success:
            return jsonify({"success": True, "message": "Fields updated"}), 200
        else:
            return jsonify({"success": False, "error": msg}), 400
    except Exception as e:
        logger.error(f"Error in update_framedb_object: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/objects/<object_id>', methods=['DELETE'])
def delete_framedb_object(object_id):
    try:
        success, msg = db_client.delete(object_id)
        if success:
            return jsonify({"success": True, "message": "Object deleted"}), 200
        else:
            return jsonify({"success": False, "error": msg}), 404
    except Exception as e:
        logger.error(f"Error in delete_framedb_object: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/objects/<object_id>', methods=['GET'])
def get_framedb_object(object_id):
    try:
        success, obj = db_client.get_by_id(object_id)
        if success:
            return jsonify({"success": True, "data": obj.to_dict()}), 200
        else:
            return jsonify({"success": False, "error": obj}), 404
    except Exception as e:
        logger.error(f"Error in get_framedb_object: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/objects', methods=['GET'])
def list_framedb_objects():
    try:
        query_filter = request.json if request.is_json else {}
        success, results = db_client.query(query_filter)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in list_framedb_objects: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/objects/<object_id>/add-copy', methods=['POST'])
def add_copy_to_object(object_id):
    try:
        data = request.json
        copy = FrameDBCopy.from_dict(data)
        success, msg = db_client.add_copy(object_id, copy)
        if success:
            return jsonify({"success": True, "message": msg}), 200
        else:
            return jsonify({"success": False, "error": msg}), 400
    except Exception as e:
        logger.error(f"Error in add_copy_to_object: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/objects/<object_id>/remove-copy', methods=['POST'])
def remove_copy_from_object(object_id):
    try:
        data = request.json
        framedb_id = data.get('framedb_id')
        if not framedb_id:
            return jsonify({"success": False, "error": "framedb_id is required"}), 400
        success, msg = db_client.remove_copy(object_id, framedb_id)
        if success:
            return jsonify({"success": True, "message": msg}), 200
        else:
            return jsonify({"success": False, "error": msg}), 404
    except Exception as e:
        logger.error(f"Error in remove_copy_from_object: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/objects/<object_id>/copy-exists/<framedb_id>', methods=['GET'])
def check_copy_exists(object_id, framedb_id):
    try:
        success, msg = db_client.copy_exists(object_id, framedb_id)
        return jsonify({"success": success, "message": msg}), 200 if success else 404
    except Exception as e:
        logger.error(f"Error in check_copy_exists: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/streams', methods=['POST'])
def create_stream():
    try:
        data = request.json
        obj = StreamsObject.from_dict(data)
        success, msg = streams_db.insert(obj)
        if success:
            return jsonify({"success": True, "message": "Stream inserted", "id": str(msg)}), 201
        else:
            return jsonify({"success": False, "error": msg}), 400
    except Exception as e:
        logger.error(f"Error in create_stream: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/streams/<queue_name>/update', methods=['POST'])
def update_stream(queue_name):
    try:
        update_fields = request.json
        success, msg = streams_db.update(queue_name, update_fields)
        if success:
            return jsonify({"success": True, "message": "Fields updated"}), 200
        else:
            return jsonify({"success": False, "error": msg}), 400
    except Exception as e:
        logger.error(f"Error in update_stream: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/streams/<queue_name>', methods=['DELETE'])
def delete_stream(queue_name):
    try:
        success, msg = streams_db.delete(queue_name)
        if success:
            return jsonify({"success": True, "message": "Stream deleted"}), 200
        else:
            return jsonify({"success": False, "error": msg}), 404
    except Exception as e:
        logger.error(f"Error in delete_stream: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/streams/<queue_name>', methods=['GET'])
def get_stream(queue_name):
    try:
        success, obj = streams_db.get_by_id(queue_name)
        if success:
            return jsonify({"success": True, "data": obj.to_dict()}), 200
        else:
            return jsonify({"success": False, "error": obj}), 404
    except Exception as e:
        logger.error(f"Error in get_stream: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/framedb/streams', methods=['GET'])
def list_streams():
    try:
        query_filter = request.json if request.is_json else {}
        success, results = streams_db.query(query_filter)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in list_streams: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def run_server():
    app.run(host='0.0.0.0', port=5000)