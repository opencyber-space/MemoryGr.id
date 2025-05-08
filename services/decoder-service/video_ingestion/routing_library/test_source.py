import os 
from redis_router import RedisRouter, FrameValidator
import time
import signal
import math
import sys


sv = str(sys.argv[1])

updateChannelData = {
        "host" : "10.101.228.116",
        "port" : 26379,
        "password" : "Friends123#",
        "db" : 0,
        "isSentinel" : True
}

routingService = {
        "uri" : "http://10.96.94.43:8000",
        "api" : "/routing/getMapping",
        "update_api" : "/routing/updateMapping",
        "act_params": {
                "host": sv,
                "port": 6379,
                "password": "Friends123#"
        }
}

router = RedisRouter(
    sourceId = 'chennai-source-123',
    routingService = routingService,
    enableUpdates = True,
    updateChannelData = updateChannelData,
    asynchronous = True
)


# validator = FrameValidator('test-local-3', validator_rule_fn = None, use_own_keys = False)


index = 0

data_map = {
        "1920x1080": os.urandom(300 * 1024),
        "416x416": os.urandom(150*1024),
        "608x608": os.urandom(200*200)
}


def get_key_map(sizes, seq):

    data = [data_map[k] for k in sizes]
    return {
            "{}__{}__{}".format(key_prefix, seq, k): v
            for k, v in zip(sizes, data)
    }


FPS = 25
sk = 0
key_prefix = "chennai-source-123"
ref_key_prefix = "ref__chennai-source-123"
#n_f = 0

for j in range(0, 1000):

    # get metadata:

    table = router.get_routing_table()
    m = router.get_metadata()
    if not m:
       print('exiting! no sources to serve')
       os._exit(0)
    fps = m['fps']
    # print('Current FPS', fps)
    # for each nodeTag in metadata, identify width height:
    write_map = {}
    sk_offset = math.floor(FPS / fps)
    for entry in table:
        required_sizes = table[entry]['metadata']['sizes']
        ref_count = table[entry]['metadata']['ref_count']
        k_m = get_key_map(required_sizes, sk)
        ref_key = "{}__{}".format(ref_key_prefix, sk)
        k_m[ref_key] = ref_count
        write_map[entry] = {"data": k_m}

    # write to framedb:
    router.mapped_put(key_prefix, write_map)

    time.sleep(1/fps)

    # update the actuation controller
    router.act_controller.update(sk, "{}__{}".format(key_prefix, sk))
    index += 1
    sk = index * sk_offset
