import os
import threading
import logging
import time
import gi
import json
import redis

gi.require_version('Gst', '1.0')
gi.require_version('GstBase', '1.0')

from gi.repository import Gst, GObject, GstBase  # noqa: F401, F402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fps_checker")



URL = "decoder-scheduler-svc.framedb-storage.svc.cluster.local"
Q = "stream_alerts"


class FPSChecker(GstBase.BaseTransform):

    GST_PLUGIN_NAME = 'fps_checker'

    __gstmetadata__ = ("fps_checker",
                       "Monitor",
                       "Checks if frame rate drops below a threshold",
                       "prasanna@cognitif.ai")

    __gsttemplates__ = (
        Gst.PadTemplate.new("src",
                            Gst.PadDirection.SRC,
                            Gst.PadPresence.ALWAYS,
                            Gst.Caps.new_any()),
        Gst.PadTemplate.new("sink",
                            Gst.PadDirection.SINK,
                            Gst.PadPresence.ALWAYS,
                            Gst.Caps.new_any())
    )

    def __init__(self):
        super(FPSChecker, self).__init__()

        self.frame_db_config = os.getenv("FRAMEDB_C", None)
        if not self.frame_db_config:
            logger.error("FPSChecker: config settings not provided")
            os._exit(-1)
        self.frame_db_config = json.loads(self.frame_db_config)

        self.min_frames = int(self.frame_db_config.get('fps_checker_min_frames', 5))
        self.max_interval = int(self.frame_db_config.get('fps_checker_max_interval', 30))
        self.source_id = self.frame_db_config['sourceID']

        self.frame_count = 0
        self.stop_thread = False

        self.monitor_thread = threading.Thread(target=self._monitor_fps)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def _push_alert(self, sourceID, data):
        # push an alert:
        try:
            data = json.dumps({"action": "fpsReport", "sourceID": sourceID, "fpsData": data}).encode("utf-8")
            connection = redis.Redis(URL, 6379, db=0)
            connection.lpush(Q, data)
        except Exception as e:
            logger.error("RedisAlertPusherError: {}".format(e))

    def _monitor_fps(self):
        while not self.stop_thread:
            time.sleep(self.max_interval)
            
            current_count = self.frame_count
            self.frame_count = 0

            fps = current_count / self.max_interval
            logger.info(f"FPSChecker: Received {fps:.2f} fps")

            if fps < self.min_frames:
                logger.error("FPSChecker: expected frames not received, sourceID={}".format(self.source_id))

                # push fps report:
                self._push_alert(self.source_id, {
                    "framesReceived": fps,
                    "minFrames": self.min_frames,
                    "intervalSeconds": self.max_interval
                })

                os._exit(1)

    def do_transform_ip(self, buffer: Gst.Buffer) -> Gst.FlowReturn:
        self.frame_count += 1
        return Gst.FlowReturn.OK

    def do_stop(self) -> bool:
        self.stop_thread = True
        return True


# Register plugin
GObject.type_register(FPSChecker)
__gstelementfactory__ = (FPSChecker.GST_PLUGIN_NAME, Gst.Rank.NONE, FPSChecker)
