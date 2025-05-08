from flask import Flask, jsonify, request
from flask_cors import CORS
from aios_logger import AIOSLogger
from scheduler import DecoderScheduler

import json

app = Flask("__main__")
CORS(app)

logger = AIOSLogger()
ds = DecoderScheduler(logger)

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

# health endpoint:
@app.route("/health", methods = ["GET"])
def health():

    log_request(request, None, "/health")
    
    return jsonify({
        "success": True, "payload": "pong"
    })

@app.route("/getStreams", methods = ["GET"])
def getStreams():

    log_request(request, None, "/getStreams")

    streams = ds.get_streams()

    return jsonify({
        "success": True, "payload": streams
    })

@app.route("/getStream", methods = ["POST"])
def getStreamByID():
    data = request.get_json()

    log_request(request, data, "/getStream")

    if not 'jobName' in data:
        return jsonify({
            "success": False, "payload": "sourceID not found"
        })
    
    result = ds.get_stream(data['jobName'])
    if result['error']:
        return jsonify({
            "success": False,
            "payload": result["message"] 
        })
    
    return jsonify({
        "success": True,
        "payload": result["payloa"]
    })

@app.route("/createStream", methods = ["POST"])
def createStream():

    data = request.get_json()
    log_request(request, data, "/createStream")

    result = ds.create_stream(data)
    
    return jsonify({
        "success": not result["error"],
        "payload": result["message"]
    })

@app.route("/killStream", methods = ["POST"])
def killStream():

    data = request.get_json()
    log_request(request, data, "/killStream")

    if not 'jobName' in data:
        return jsonify({
            "success": False,
            "payload": "jobName not found in payload"
        })
    
    result = ds.kill_stream(data)
    return jsonify({
        "success": not result["error"],
        "payload": result["message"]
    })


app.run(host="0.0.0.0", port=5000)
