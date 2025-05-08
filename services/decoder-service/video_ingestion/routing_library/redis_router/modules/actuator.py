import json

from redis import connection
from ..pythreads import pythread
from .aios_logger import AIOSLogger
import logging
from queue import Queue
import redis
import time
import copy

logging = logging.getLogger("MainLogger")


class BlockSocket:

    def __init__(self, blockID: str, auth_data: str, mdag_id: str):
        self.block_id = blockID
        self.auth_pwd = auth_data
        self.mdag_id = mdag_id
        self.connection = None
        self.input_queue = "{}__inputs".format(self.block_id)

    def create_connection_or_wait(self):
        # establish the connection and wait if the connection is not established
        while True:
            try:
                host = "{}-svc.dag-space-{}.svc.cluster.local".format(
                            self.block_id, self.mdag_id
                        )
                connection = redis.Redis(
                    host=host,
                    port=6379,
                    password=self.auth_pwd,
                    db=0
                )

                # ping the connection:
                if not connection.ping():
                    raise Exception("Ping failed, reconnecting....")

                # connection is established break from the loop
                self.connection = connection
                return
            except Exception as e:
                logging.error(e)
                logging.error(
                    'Failed to establish redis connection with block {} under mdag {}. Retrying...'.format(
                        self.block_id, self.mdag_id
                    )
                )
                time.sleep(2)
                continue

    def push_data(self, data):
        if not self.connection:
            self.create_connection_or_wait()

        '''
        {'sourceID': 'camera_27_18', 'keys': ['camera_27_18?6?0__0', 'camera_27_18?6?0__5'], 'seqNumbers': [0, 5], 'intSeqNum': 0, 'vdags': ['vdag-e8807', 'vdag-e8807'], 'ts': [1687928012.4921236, 1687928012.5117176], 'nm': {'framedb-5': ['1920x1080', '416x416']}}
        '''
        # push the data:
        try:

            seen_vdags = {}
            job_packets = []

            for idx, vdag in enumerate(data["vdags"]):
                    if vdag not in seen_vdags:
                        seen_vdags[vdag] = 1
                    else:
                        seen_vdags[vdag] +=1

                    if len(job_packets) < seen_vdags[vdag]:
                        job_packets.append({
                            "sourceID": data['sourceID'],
                            "keys": [data['keys'][idx]],
                            "seqNumbers": [data['seqNumbers'][idx]],
                            "intSeqNum": data['intSeqNum'],
                            "vdags": [vdag],
                            "ts": [data['ts'][idx]],
                            "nm": data['nm']
                        })
                    else:
                        job_packets[seen_vdags[vdag] - 1]['vdags'].append(vdag)
                        job_packets[seen_vdags[vdag] - 1]['seqNumbers'].append(data['seqNumbers'][idx])
                        job_packets[seen_vdags[vdag] - 1]['ts'].append(data['ts'][idx])
                        job_packets[seen_vdags[vdag] - 1]['keys'].append(data['keys'][idx])

            for job_packet in job_packets:
                print("pushing final data:",job_packet)
                self.connection.lpush(self.input_queue, json.dumps(job_packet))
    
        except Exception as e:
            logging.error(
                'Error pushing data to block {}, under mdag {}, retrying.'.format(
                    self.block_id, self.mdag_id
                )
            )
            self.create_connection_or_wait()


class BlocksPusher:

    def __init__(self, sourceID, actuation_queue_params):
        self.source_id = sourceID
        self.q_data = actuation_queue_params['ac_data']['head']
        self.mdag_id = actuation_queue_params['ac_data']['mdag_id']

        self.current_seq_number = 0
        self.batch_size = 0
        self.activated = False

        self.current_seqs = []
        self.current_keys = []
        self.ts = []

        self.message_queue = Queue(200)

        self.maps = self.build_maps()
        self.sockets_map = self.create_all_sockets(self.maps['blocks'])
        self.__internal_push_to_queue(self)
    
    def create_all_sockets(self, blocks):

        sockets = {}

        for blockId in blocks:
            socket = BlockSocket(blockId, "Friends123#", self.mdag_id)
            logging.info("Connecting to {}".format(blockId))
            socket.create_connection_or_wait()
            sockets[blockId] = socket
        
        return sockets

    
    def build_maps(self):
        vdag_blocks = {}
        fps_vdags = {}
        blocks = {}

        head = self.q_data['head']
        for entry in head:
            if 'fps' not in entry:
                continue

            if entry['vdagID'] not in vdag_blocks:
                vdag_id = entry['vdagID']
                all_blocks = []
                for block in entry['inputs']:
                    block_id = block['blockID']
                    if block_id not in blocks:
                        blocks[block_id] = block
                    all_blocks.append(block_id)
                vdag_blocks[vdag_id] = all_blocks
            
            # is FPS already present
            fps = entry['fps']
            if fps not in fps_vdags:
                fps_vdags[fps] = [entry['vdagID']]
            else:
                fps_vdags[fps].append(entry['vdagID'])
        
        all_maps = {
            "fps": fps_vdags,
            "vdags": vdag_blocks,
            "blocks": blocks
        }

        print(all_maps)
        return all_maps
    

    @pythread
    def __internal_push_to_queue(self):
        logging.info("Started thread to push events")
        while True:
            try:
                data = self.message_queue.get()
                # process the job packet
                blocks_to_push = {}
                for idx, seqNo in enumerate(data['seq']):
                    for fps in self.maps['fps']:
                        if seqNo % fps == 0:
                            # add this to the push list:
                            vdags = self.maps['fps'][fps]
                            # get the blocks under this vdag
                            for vdag in vdags:
                                blocks = self.maps['vdags'][vdag]
                                for block in blocks:
                                    if block not in blocks_to_push:
                                        blocks_to_push[block] = {
                                            "sourceID": self.source_id,
                                            "keys": [data['keys'][idx]],
                                            "seqNumbers": [seqNo],
                                            "intSeqNum": data['actuationSeq'],
                                            "vdags": [vdag],
                                            "ts": [data['ts'][idx]],
                                            "nm": data['nm']
                                        }
                                    else:
                                        blocks_to_push[block]['keys'].append(data['keys'][idx])
                                        blocks_to_push[block]['seqNumbers'].append(seqNo)
                                        blocks_to_push[block]['vdags'].append(vdag)
                                        blocks_to_push[block]['ts'].append(data['ts'][idx])
                # push to these blocks:
                logging.info(blocks_to_push)
                for block in blocks_to_push:
                    self.sockets_map[block].push_data(blocks_to_push[block])

            except Exception as e:
                logging.error(e)
                continue


    def update(self, seq_number, key_prefix, nm):
        # logging.info("ACtivated? {} {}".format(self.activated, self.batch_size))
        if not self.activated:
            return

        self.current_seqs.append(seq_number)
        self.current_keys.append(key_prefix)
        self.ts.append(time.time())

        if len(self.current_seqs) % self.batch_size == 0:
            # prepare packet:
            # logging.info("Pushing message")
            packet = {
                "sourceID": self.source_id,
                "actuationSeq": self.current_seq_number,
                "keys": copy.copy(self.current_keys),
                "seq": copy.copy(self.current_seqs),
                "ts": copy.copy(self.ts),
                "nm": nm
            }

            self.message_queue.put(copy.copy(packet))
            self.current_seq_number += 1
            self.current_seqs.clear()
            self.current_keys.clear()
            self.ts.clear()

        

    def reset_config(self, config_data):
        self.current_seq_number = 0
        if not config_data:
            self.activated = False
            return
        else:
            self.activated = True
        self.batch_size = config_data['act_batch_size']


class AcPusher:

    def __init__(self, sourceID, actuation_queue_params):
        self.actuation_queue_params = actuation_queue_params
        self.redis_connection = redis.Redis(
            host=actuation_queue_params['host'],
            port=actuation_queue_params['port'],
            db=0,
            password=actuation_queue_params['password']
        )

        self.current_seq_number = 0
        self.batch_size = 0
        self.source_id = sourceID

        self.current_seqs = []
        self.current_keys = []
        self.ts = []

        self.activated = False

        self.message_queue = Queue(100)
        self.queue_name = "{}__act_queue".format(self.source_id)

        # start the actuation queue thread
        self.__internal_push_to_queue(self)
        logging.info("Initialized actuation queue pusher")

    def reset_config(self, config_data):
        self.current_seq_number = 0
        if not config_data:
            self.activated = False
            return
        else:
            self.activated = True
        self.batch_size = config_data['act_batch_size']

    @pythread
    def __internal_push_to_queue(self):

        counter = 0
        logger: AIOSLogger = None

        while True:
            try:
                data = self.message_queue.get()

                if not logger:
                    logger = AIOSLogger({
                        "service_name": "gst-{}".format(data.get("sourceID", "undefined")),
                        "logging_path": "/logs",
                        "serialize": True,
                        "enable_compression": False,
                        "compression_value": None,
                        "enable_log_rotation": False,
                        "enable_error_callbacks": False,
                        "rotation_value": "10MB",
                        "use_verbose_mode": False,
                        "enable_stdout": True
                    })

                # push to the connection:
                data_encoded = json.dumps(data).encode('utf-8')
                if self.redis_connection:
                    self.redis_connection.lpush(
                        self.queue_name,
                        data_encoded
                    )

                    counter +=1

                    if counter == 300:
                        logger.info("FRAMES_PUSHED", "pushed 300 frames", extras={
                            "sourceID": data.get("sourceID", "undefined")
                        })

                        counter = 0

                logging.info("Pushed actuation message {}".format(
                    data['actuationSeq']
                ))
            except Exception as e:
                logging.error("Failed to push actuation message, reconnecting")
                logging.error(e)
                self.redis_connection = redis.Redis(
                    host=self.actuation_queue_params['host'],
                    port=self.actuation_queue_params['port'],
                    password=self.actuation_queue_params['password'],
                    db=0
                )

    def update(self, seq_number, key_prefix, nm):

        if not self.activated:
            return

        self.current_seqs.append(seq_number)
        self.current_keys.append(key_prefix)
        self.ts.append(time.time())

        if len(self.current_seqs) % self.batch_size == 0:
            # prepare packet:
            packet = {
                "sourceID": self.source_id,
                "actuationSeq": self.current_seq_number,
                "keys": copy.copy(self.current_keys),
                "seq": copy.copy(self.current_seqs),
                "ts": copy.copy(self.ts),
                "nm": nm
            }

            self.message_queue.put(packet)
            self.current_seq_number += 1
            self.current_seqs.clear()
            self.current_keys.clear()
            self.ts.clear()

class ActuationController:

    def __init__(self, sourceID, actuation_queue_params):
        logging.info(actuation_queue_params)
        if 'ac_data' in actuation_queue_params and actuation_queue_params['ac_data']:
            print('Block data is provided, pushing events to blocks directly')
            self.__internal = BlocksPusher(sourceID, actuation_queue_params)
        else:
            self.__internal = AcPusher(sourceID, actuation_queue_params)
    
    def update(self, seq_number, key_prefix, nm):
        # print('Block data is not provided, pushing events to actuation controller')
        self.__internal.update(seq_number, key_prefix, nm)
    
    def reset_config(self, config_data):
        self.__internal.reset_config(config_data)


# if __name__ == "__main__":
#    data = json.loads(open('test.json').read())
#    pusher = ActuationController('test-source-123', data)
