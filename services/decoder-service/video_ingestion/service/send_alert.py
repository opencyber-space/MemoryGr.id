import redis
import sys
import json

URL = "decoder-scheduler-svc.framedb-storage.svc.cluster.local"
Q = "stream_alerts"

def push_alert():

    if len(sys.argv) < 2:
        print('failed to send alert, sourceID not supplied')
        return
    
    sourceID = str(sys.argv[1])
    # push an alert:
    try:
        data = json.dumps({"action": "sendAlert", "sourceID": sourceID}).encode("utf-8")
        connection = redis.Redis(URL, 6379, db=0)
        connection.lpush(Q, data)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    push_alert()
