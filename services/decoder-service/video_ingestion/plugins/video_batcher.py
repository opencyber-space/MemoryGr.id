'''
Simple mixer element, accepts 320 x 240 RGBA at 30 fps
on any number of sinkpads.

Requires PIL (Python Imaging Library)

Example pipeline:

gst-launch-1.0 py_videomixer name=mixer ! videoconvert ! autovideosink \
        videotestsrc ! mixer. \
        videotestsrc pattern=ball ! mixer. \
        videotestsrc pattern=snow ! mixer.
'''

import numpy as np
import time
import os
import logging

import copy
import turbojpeg
import json
from redis_router import RedisRouter

from PIL import Image
import gi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fps_checker")

gi.require_version('Gst', '1.0')
gi.require_version('GstBase', '1.0')
gi.require_version('GObject', '2.0')

from gi.repository import Gst, GObject, GstBase

Gst.init(None)

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
        "host": "10.104.63.239",
        "port": 6379,
        "password": "Friends123#"
    },
    "routingURL": "http://10.96.94.43:8000",
    "sourceID": "chennai-source-123",
    "skipFrame": 8
}


# Completely fixed input / output
ICAPS = Gst.Caps(Gst.Structure('video/x-raw',
                               format='RGBA',
                               width=1920,
                               height=1080,
                               framerate=Gst.Fraction(5, 1)))

OCAPS = Gst.Caps(Gst.Structure('video/x-raw',
                               format='RGBA',
                               width=1920,
                               height=1080,
                               framerate=Gst.Fraction(5, 1)))



N_BATCHES = int(os.getenv("DALI_BATCH_SIZE", 8))
N_THREADS = int(os.getenv("DALI_THREADS", 1))
DEVICE_ID = int(os.getenv("DALI_DEVICE_ID", 0))

# Gst.Caps.new_any()

class VideoBatcher(GstBase.Aggregator):
    __gstmetadata__ = ('video_batcher','Video/Mixer', \
                      'Batches multiple videos streams raw frames', 'prasanna@cognitif.ai')

    __gsttemplates__ = (
            Gst.PadTemplate.new_with_gtype("sink_%u",
                                Gst.PadDirection.SINK,
                                Gst.PadPresence.REQUEST,
                                Gst.Caps.new_any(),
                                GstBase.AggregatorPad.__gtype__),
            Gst.PadTemplate.new_with_gtype("src",
                                Gst.PadDirection.SRC,
                                Gst.PadPresence.ALWAYS,
                                Gst.Caps.new_any(),
                                GstBase.AggregatorPad.__gtype__)
    )

# required fields:
    # 1. w_h_index = {0: {"shape": [416,416,3], "suffix": "416x416"}...}
    # 2. update_channel = {host:, port:, password:, db:, isSentinel: }
    # 3. act_parameters = {host: , port: port, password: },
    # 4. routingURL = ,
    # 5. sourceID = ,
    # 6. skipFrame = ,
    # 7. refCount = ,
    # 8. fQuality=

    def __init__(self):

        try:
            super(VideoBatcher, self).__init__()
            self.external_iter = []
            self.turbo_encoder = turbojpeg.TurboJPEG()

            self.enable_frame_write = os.getenv("ENABLE_FRAME_WRITE", "0")
            if self.enable_frame_write != "0":
                self.enable_frame_write = True
            else:
                self.enable_frame_write = False

            logger.info("Frames writer enabled = {}".format(self.enable_frame_write))
            
            self.frame_write_interval = int(os.getenv("FRAME_WRITE_INTERVAL", "100"))

            self.write_path = os.getenv("FRAMES_WRITE_PATH", "/frame-dumps")


            self.frame_db_config = os.getenv("FRAMEDB_C")
            self.frame_db_config = json.loads(self.frame_db_config)
            self.frame_write_counter = 0

            print('config', self.frame_db_config)

            w_h_index = self.frame_db_config['w_h_index']

            # process w_h keys and add them to mapping array:
            w_h_keys = sorted(list(w_h_index.keys()))
            
            self.w_h_map = []
            for wh_key in w_h_keys:
                wh_key = int(wh_key)
                self.w_h_map.append(
                    (w_h_index[str(wh_key)]['shape'], w_h_index[str(wh_key)]['suffix'])
                )
            print(self.w_h_map)

            self.wh_index_map = {}
            for wh_key in w_h_keys:
                suffix = w_h_index[wh_key]['suffix']
                if suffix not in self.wh_index_map:
                    self.wh_index_map[suffix] = int(wh_key)

            # key prefix:
            self.source_id = self.frame_db_config['sourceID']
            self.current_restart_counter = int(os.getenv("IDX", "0"))
            self.key_prefix = "{}?{}?{}".format(
                self.source_id, self.frame_db_config['update_counter'],
                self.current_restart_counter 
            )
            self.ref_key_prefix = "ref__{}".format(self.key_prefix)

            print('Init done!')

            self.routingService = {
                "uri" : self.frame_db_config['routingURL'],
                "api" : "/routing/getMapping",
                "update_api" : "/routing/updateMapping",
                "act_params": self.frame_db_config['act_parameters']
            }

            self.update_channel_data = self.frame_db_config['update_channel']
            
            self.router = RedisRouter(
                sourceId=self.source_id,
                routingService=self.routingService,
                enableUpdates=True,
                updateChannelData=self.update_channel_data,
                asynchronous=False
            )

            self.quality = self.frame_db_config['fQuality']
            self.sk = self.frame_db_config['skipFrame']
            self.table = self.router.get_routing_table()
            self.counter = 0
            print('Updated new configuration')


            self.node_map = {}

            for entry in self.table:
                m = self.table[entry]['metadata']
                sizes = m['sizes'] if 'sizes' in m else []
                self.node_map[entry] = sizes
            
            print('Node Map: ', self.node_map)

        except Exception as e:
            raise e

    def mix_buffers(self, agg, pad, bdata):
        try:
            buf = pad.pop_buffer()
            with buf.map(Gst.MapFlags.READ) as info:
                bdata.append(
                    np.ndarray(shape = self.w_h_map[len(bdata)][0], dtype = np.uint8, buffer = info.data)
                )

            return True
        except Exception as e:
            print(e)
            os._exit(0)

    def do_aggregate(self, timeout):

        try:
            self.foreach_sink_pad(self.mix_buffers, self.external_iter)

            if self.router.is_updated_once:
                print('Routing table update was detected, stopping frame-flow')
                self.external_iter.clear()
                return Gst.FlowReturn.OK
            
            if self.enable_frame_write:
                self.frame_write_counter = self.frame_write_counter + 1

            encoded_data = []
            for idx in range(len(self.external_iter)):
                encoded = self.turbo_encoder.encode(self.external_iter[idx], quality=self.quality)
                encoded_data.append(encoded)
            
            # iterate over w_h index and push each frame to routing library:
            key_map = {}
            prefix = "{}__{}".format(self.key_prefix, self.counter)

            ref_key = "{}__{}".format(self.ref_key_prefix, self.counter)

            for entry in self.table:
                m = self.table[entry]['metadata']
                sizes = m['sizes']
                key_map[entry] = {}
                size_map = {}
                for size in sizes:
                    frame_idx = self.wh_index_map[size]
                    key = "{}__{}".format(prefix, size)
                    size_map[key] = encoded_data[frame_idx]

                    if self.enable_frame_write:
                        if size == "1920x1080":
                            if self.frame_write_counter % self.frame_write_interval == 0:
                                ts = time.time()
                                w_p = os.path.join(self.write_path, self.source_id)
                                if not os.path.exists(w_p):
                                    os.mkdir(w_p)
                                    
                                write_path = os.path.join(w_p, str(ts) + ".jpg")
                                logger.info("Writing frame at path = {}".format(write_path))
                                open(write_path, 'wb').write(encoded_data[frame_idx])


                size_map[ref_key] = m['ref_count']
                key_map[entry] = size_map
                
            self.router.batch_put(key_map)

            # update the actuation controller:
            self.router.act_controller.update(self.counter, prefix, self.node_map)
            self.counter = self.counter + self.sk

            # allocate and create buffers
            self.external_iter.clear()
            return Gst.FlowReturn.OK
        except Exception as e:
            print(e)
            os._exit(0)

GObject.type_register(VideoBatcher)
__gstelementfactory__ = ("video_batcher", Gst.Rank.NONE, VideoBatcher)
