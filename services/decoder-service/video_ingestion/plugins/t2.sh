#!/bin/bash


gst-launch-1.0 filesrc location="/frames/video.mp4" \
    ! qtdemux ! h264parse ! nvh264dec ! videorate ! "video/x-raw, framerate=(fraction)1/1" \
    ! cudaupload ! cudaconvert ! "video/x-raw(memory:CUDAMemory), format=BGR" ! cudadownload \
    ! video_writer