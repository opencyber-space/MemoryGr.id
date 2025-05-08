import numpy as np
import time
import os
import copy
import time
import turbojpeg
import json
import logging
from redis_router import RedisRouter

from PIL import Image
import gi

gi.require_version('Gst', '1.0')
gi.require_version('GstBase', '1.0')
gi.require_version('GObject', '2.0')

from gi.repository import Gst, GObject, GstBase

Gst.init(None)


from nvidia.dali.pipeline import Pipeline
from nvidia.dali import ops
from nvidia.dali import types
from nvidia.dali import fn


class FrameHolder:
    def __init__(self):
        self.frame = None
    
    def __iter__(self):
        self.i = 0
        self.n = 100000000000000000000
        return self
    
    def __next__(self):
        return [self.frame]


class DALIPipeline(Pipeline):
    
    def __init__(
        self, batch_size=1, n_threads=1, device_id=0,
        external_iter=None, w_h_map=None, use_gpu=True,
        current_h_w=[1080, 1920]
    ):
        super(DALIPipeline, self).__init__(
            batch_size, n_threads, device_id
        )

        self.device_string = "gpu" if use_gpu else "cpu"
        self.input_source = ops.ExternalSource(source=external_iter, device=self.device_string)

        # create operators based on width, height required:
        # contains DALI operations that were formed dynamically given the width, height from config
        self.resizer_ops = []
        self.has_native_size = False
        self.native_size_idx = -1

        for idx, w_h in enumerate(w_h_map):
            height, width, channels = w_h[0]
            if height == current_h_w[0] and width == current_h_w[1]:
                self.has_native_size = True
                self.native_size_idx = idx
            else:
                op = ops.Resize(device=self.device_string, resize_x=width, resize_y=height)
                self.resizer_ops.append(op)
        
    
    def define_graph(self):

        frame = self.input_source()
        # apply for all the ops:
        outputs = []
        for op in self.resizer_ops:
            outputs.append(op(frame))
        
        if self.has_native_size:
            outputs.insert(self.native_size_idx, frame)

        return outputs


class VideoWriterSink(GstBase.BaseSink):

    __gstmetadata__ = ('video_writer','Sink', \
                      'Plugin written using TiDBWriter, a library used to write frames to TiDB', 'prasanna@cognitif.ai')


    __gsttemplates__ = Gst.PadTemplate.new("sink",
                                           Gst.PadDirection.SINK,
                                           Gst.PadPresence.ALWAYS,
                                           Gst.Caps.new_any())

    sync = True

    def __init__(self):
        try:
            super(VideoWriterSink, self).__init__()
            self.turbo_encoder = turbojpeg.TurboJPEG()
            self.frame_db_config = os.getenv("FRAMEDB_C")
            self.frame_db_config = json.loads(self.frame_db_config)
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
            self.sk = self.frame_db_config['skipFrame']
            self.counter = 0
            self.quality = self.frame_db_config['fQuality']
            print('Updated new configuration')
            self.current_pts = None
            self.table = self.router.get_routing_table()
            self.d_to_send = b'0x00'
            # create DALI pipeline:
            self.original_hw = self.frame_db_config['ohw']
            # create the iterator:
            self.frame_holder = FrameHolder()
            self.use_gpu = self.frame_db_config['use_gpu']

            self.node_map = {}

            for entry in self.table:
                m = self.table[entry]['metadata']
                sizes = m['sizes'] if 'sizes' in m else []
                self.node_map[entry] = sizes
            
            print('Node Map: ', self.node_map)

            self.resizer_pipeline = DALIPipeline(
                w_h_map=self.w_h_map,
                current_h_w=self.original_hw,
                use_gpu=self.use_gpu,
                external_iter=self.frame_holder
            )

            self.resizer_pipeline.build()
            print('Created DALI pipeline')

        except Exception as e:
            logging.error(e)
            os._exit(0)
  
    def do_render(self, buffer):
        
        #map_gst_buffer is a generator that yields buffer data
        try:
            with buffer.map(Gst.MapFlags.READ) as frame:

                if self.router.is_updated_once:
                    print('Routing table update was detected, stopping frame-flow')
                    return Gst.FlowReturn.OK

                self.frame_holder.frame = np.ndarray(
                    shape = (self.original_hw[0], self.original_hw[1], 3), dtype = np.uint8, buffer=frame.data
                )

                resized_frames = self.resizer_pipeline.run()
                
                # push frame to decoder:
                resized_frames_cpu = None
                if self.use_gpu:
                    resized_frames_cpu = [
                        gpu_tensor.as_cpu().as_array().squeeze() for gpu_tensor in resized_frames
                    ]

                else:
                    resized_frames_cpu = [
                        cpu_tensor.as_array().squeeze() for cpu_tensor in resized_frames
                    ]
                
                encoded_data = []
                for idx, cpu_array in enumerate(resized_frames_cpu):
                    encoded_jpeg = self.turbo_encoder.encode(cpu_array, quality=self.quality)
                    encoded_data.append(encoded_jpeg)
                
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
                    size_map[ref_key] = m['ref_count']
                    key_map[entry] = size_map
                    
                self.router.batch_put(key_map)
                # logging.info("Pushing to act controller")
                # update the actuation controller:
                self.router.act_controller.update(self.counter, prefix, self.node_map)
                self.counter = self.counter + self.sk

            return Gst.FlowReturn.OK

        except Exception as e:
            logging.error(e)
            os._exit(0)



GObject.type_register(VideoWriterSink)
__gstelementfactory__ = ("video_writer", Gst.Rank.NONE, VideoWriterSink)
