#!/bin/bash

cp -r /gst-build/pygst_utils /usr/local/lib/python3.8/dist-packages/pygst_utils

mkdir -p /cognit_plugins/python

#install plugins
pushd /gst-build/video_ingestion/plugins
    chmod 777 install.sh
    ./install.sh
popd

gst-inspect-1.0 framedbsink

#run the app
pushd /gst-build/video_ingestion/service
    python3 -u server.py
popd
