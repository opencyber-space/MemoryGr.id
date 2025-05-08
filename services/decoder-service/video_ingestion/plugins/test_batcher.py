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
import gi
import turbojpeg

gi.require_version('Gst', '1.0')
gi.require_version('GstBase', '1.0')
gi.require_version('GObject', '2.0')

from gi.repository import Gst, GObject, GstBase

Gst.init(None)

class TestBatcher(GstBase.Aggregator):
    __gstmetadata__ = ('test_batcher','Video/Mixer', \
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
    def __init__(self):

        try:
            super(TestBatcher, self).__init__()
            self.external_iter = []
            self.turbo_encoder = turbojpeg.TurboJPEG()
            self.pts = None

            self.sk = 0

        except Exception as e:
            raise e
            os._exit(0)

    def mix_buffers(self, agg, pad, bdata):
        try:
            buf = pad.pop_buffer();
            with buf.map(Gst.MapFlags.READ) as info:
                if len(bdata) == 0:
                    bdata.append(np.ndarray(shape = (720, 1280, 3), dtype = np.uint8, buffer = info.data))
                elif len(bdata) == 1:
                    bdata.append(np.ndarray(shape = (416, 416, 3), dtype = np.uint8, buffer = info.data))
                self.pts = buf.pts
            return True
        except Exception as e:
            print(e)
            os._exit(0)

    def do_aggregate(self, timeout):

        try:
            self.foreach_sink_pad(self.mix_buffers, self.external_iter)

            # encode JPEG images:
            print('Enum length: ', len(self.external_iter))
            for idx, data in enumerate(self.external_iter):
                encoded = self.turbo_encoder.encode(data)
                with open('frames/jpeg_{}_{}.jpeg'.format(self.sk ,idx), 'wb') as writer:
                    writer.write(encoded)
            
            for idx in range(10, 10000):
                pass
            
            self.sk += 1
            
            self.external_iter.clear()

            data = b'0x00'

            outbuf = Gst.Buffer.new_allocate(None, 1, None)
            outbuf.fill(0, data)
            outbuf.pts = self.pts
            self.finish_buffer (outbuf)

            return Gst.FlowReturn.OK
        except Exception as e:
            print(e)
            os._exit(0)

GObject.type_register(TestBatcher)
__gstelementfactory__ = ("test_batcher", Gst.Rank.NONE, TestBatcher)
