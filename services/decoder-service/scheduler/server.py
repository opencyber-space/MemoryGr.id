from flask import Flask, jsonify, request
from flask_cors import CORS
from modules.aios_logger import AIOSLogger
import json

from modules.query import QueryAPI
from modules.k8s import K8sAPI

app = Flask("__main__")
CORS(app)

logger = AIOSLogger()

logger.info("server_init", "Initialized Server to start decode requests", extras={})

def log_request(req: request, payload: dict, api_name: str):
    logger.info(
        "api_request",
        "{} got request".format(api_name),
        {
            "headers": json.dumps(dict(req.headers)),
            "payload": json.dumps(payload) if payload else None,
            "api_name": api_name
        }
    )



@app.route("/createInstance", methods=["POST"])
def create_instance():
    data = request.get_json()
    log_request(request, data, "/createInstance")

    if 'node' not in data or 'gpuID' not in data:
        return jsonify({"success": False, "payload": "either node or gpuID is not provided"})
    
    # call k8s api:
    resp = K8sAPI.create_deployment(data)
    
    return jsonify({
        "success": not resp['error'],
        "payload": resp['payload']
    })

@app.route("/removeInstance", methods=["POST"])
def remove_instance():
    data = request.get_json()
    log_request(request, data, "/removeInstance")

    if 'node' not in data or 'gpuID' not in data:
        return jsonify({"success": False, "payload": "either node or gpuID is not provided"})
    
    # call k8s api:
    resp = K8sAPI.remove_deployment(data)
    
    return jsonify({
        "success": not resp['error'],
        "payload": resp['payload']
    })

@app.route("/queryHealth", methods=["POST"])
def queryHealth():

    data = request.get_json()
    log_request(request, data, "/queryHealth")

    if 'node' not in data or 'gpuID' not in data:
        return jsonify({"success": False, "payload": "either node or gpuID is not provided"})
    
    ret, res = QueryAPI.get_health(data)
    return jsonify({
        "success": ret,
        "payload": res
    })

@app.route("/querySources", methods=["POST"])
def querySources():
    
    data = request.get_json()
    log_request(request, data, "/querySources")

    if 'node' not in data or 'gpuID' not in data:
        return jsonify({"success": False, "payload": "either node or gpuID is not provided"})
    
    ret, res = QueryAPI.get_streams(data)
    return jsonify({
        "success": ret,
        "payload": res
    })


@app.route("/restartSource", methods=["POST"])
def restartSource():
    
    data = request.get_json()
    log_request(request, data, "/restartSource")

    if 'node' not in data or 'gpuID' not in data:
        return jsonify({"success": False, "payload": "either node or gpuID is not provided"})
    
    ret, res = QueryAPI.restart_stream(data)
    return jsonify({
        "success": ret,
        "payload": res
    })


@app.route("/startWithContext", methods=["POST"])
def startWithContext():
    
    data = request.get_json()
    log_request(request, data, "/startWithContext")

    if 'node' not in data or 'gpuID' not in data:
        return jsonify({"success": False, "payload": "either node or gpuID is not provided"})
    
    ret, res = QueryAPI.start_with_context(data)
    return jsonify({
        "success": ret,
        "payload": res
    })

@app.route("/restartWithContext", methods=["POST"])
def restartWithContext():
    
    data = request.get_json()
    log_request(request, data, "/startWithContext")

    if 'node' not in data or 'gpuID' not in data:
        return jsonify({"success": False, "payload": "either node or gpuID is not provided"})
    
    ret, res = QueryAPI.restart_with_context(data)
    return jsonify({
        "success": ret,
        "payload": res
    })


app.run('0.0.0.0', port=5000)