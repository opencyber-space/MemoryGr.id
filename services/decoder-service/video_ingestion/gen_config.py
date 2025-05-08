import json

config = {
    "w_h_index": {
        0: {
            "shape": [416, 416, 3],
            "suffix": "416x416"
        }
    },
    "update_channel": {
        "host" : "10.101.228.116",
        "port" : 26379,
        "password" : "Friends123#",
        "db" : 0,
        "isSentinel" : True
    },
    "act_parameters": {
        "host": "sv",
        "port": 6379,
        "password": "Friends123#"
    },
    "routingURL": "http://10.96.94.43:8000",
    "sourceID": "chennai-source-123",
    "skipFrame": 8,
    "refCount": 1
}

print(str(json.dumps(config)))