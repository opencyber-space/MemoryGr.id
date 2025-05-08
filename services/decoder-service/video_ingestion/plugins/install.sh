#!/bin/bash

cp timestamper.py /cognit_plugins/python
echo "installed plugin...timestamper"
echo "run 'gst-inspect-1.0 timestamper' to know more about the plugin."

cp video_batcher.py /cognit_plugins/python
echo "installed plugin...video_batcher"
echo "run 'gst-inspect-1.0 video_batcher' to know more about the plugin."

cp video_batcher_sync.py /cognit_plugins/python
echo "installed plugin...video_batcher_sync"
echo "run 'gst-inspect-1.0 test_batcher' to know more about the plugin."

cp test_batcher.py /cognit_plugins/python
echo "installed plugin..test_batcher"
echo "run gst-inspect-1.0 test_batcher to know more about the plugin."

cp video_sink.py /cognit_plugins/python
echo "installed plugin..video_sink"
echo "run gst-inspect-1.0 video_sink to know more about the plugin."

cp fps_checker.py /cognit_plugins/python
echo "installed plguin..fps_checker"
echo "run gst-inspect-1.0 fps_checker to know more about the plugin."