#!/bin/bash

gst-launch-1.0 -m test_batcher name=mixer ! fakesink sync=true \
    filesrc location="/frames/video.mp4" ! qtdemux ! h264parse ! nvh264dec ! videorate  ! "video/x-raw, framerate=(fraction)1/1" ! tee name=t \
        ! queue ! cudaupload ! cudaconvert ! cudascale ! "video/x-raw(memory:CUDAMemory), format=BGR, width=1280, height=720" ! cudadownload ! mixer. \
        t. ! queue  !  cudaupload ! cudaconvert ! cudascale ! "video/x-raw(memory:CUDAMemory), format=BGR, width=416, height=416" ! cudadownload ! mixer. 
    
