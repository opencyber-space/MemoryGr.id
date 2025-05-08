from .env import get_env_settings, exit_on_failure, exit_on_success
from .notifier import wrap_notify_failure, wrap_notify_success
from .video_meta import DiscoverVideo
from .pythreads import pythread

import shlex
import time
import requests
import json
import os
import math
import subprocess

TIMEOUT_SIGINT_SUCCESS = 124

env_settings = get_env_settings()

import logging
logging.basicConfig(level = logging.INFO)
logging = logging.getLogger("MainLogger")

validation_keys = [('source_id', str), ('operating_mode', str, ['live', 'batch']), ('url', str), ('fps', str), ('mode', str, ['live', 'video']), ('use_gpu', bool)]
supported_containers = ['mp4', 'mkv', 'flv']

c_map = {
    "mp4" : "qtdemux",
    "mkv" : "matroskademux",
    "flv" : "flvdemux"
}

def wrap_fail(errData):
    wrap_notify_failure(errData)
    exit_on_failure()

def wrap_complete(succData):
    wrap_notify_success(succData)
    exit_on_failure()


def prepare_gpu_decoder_plugin(type="h264"):
    # get the NVIDIA GPU ID, default is 0
    gpu_id = str(os.getenv("NVIDIA_VISIBLE_DEVICES", "0"))
    if type == "h264":
        if gpu_id == "0":
            return "nvh264dec"
        return "nvh264device{}dec".format(gpu_id)
    elif type == "mjpeg":
        if gpu_id == "0":
            return "nvjpegdec"
        return "nvjpegdevice{}dec".format(gpu_id)
    if gpu_id == "0":
        return "nvh265dec"
    return "nvh265device{}dec".format(gpu_id)

def __validate_source_data(data):

    for key in validation_keys:
        key_name, key_type = key[0], key[1]
        if not key_name in data or type(data[key_name]) != key_type: 
            return False, "Key {} missing in source data".format(key_name)
        
        if len(key) > 2:
            #check for category
            val =  data[key_name]
            if val not in key[2]:
                return False, "Key {} has improper value {} supported values are : {}".format(key_name, val, key[2])
    
    if (data['mode'] == 'video') and ((not 'container' in data) or (data['container'] not in supported_containers)):
        return False, "Supported container types not provided container format in supported containers {}".format(supported_containers)
    
    logging.info("Validation passed")

    #check nv-codecs enabled, if not, fallback to CPU mode
    has_env_codecs = os.getenv("NV_CODECS_ENABLED", "No").lower()
    #convert to bool
    has_env_codecs = True if has_env_codecs == "yes" else False
    if (not has_env_codecs) and (data['use_gpu']):
        logging.warning("The worker is not compiled with NVIDIA plugins or not running in a GPU-enabled environment")
        logging.warning("Falling back to CPU mode")

        #disable GPU mode, this will make pipeline to use ffmpeg plugins instead of NV-Codecs
        data['use_gpu'] = False

    return True, "Validation passed"

def run_task():

    try:
        data = env_settings.source_data
        
        source_settings = json.loads(data)

        print(source_settings)
        
        ret, message = __validate_source_data(source_settings)
        if not ret:
            logging.error(message)
            wrap_fail({"errData" : message})
        
        print('Finished validation step')
        #launch source launcher based on source
        if source_settings['mode'] == 'video':
            #TODO: Launch video decoder
            StoredVideoDecoder(source_settings).run_pipeline()
        else:
            LiveDecoder(source_settings).run_pipeline()

    except Exception as e:
        logging.error(e)
        wrap_fail({"errData" : "source data is not json decodable"})


class LiveDecoder:

    def __init__(self, settings):
        
        self.source_id = settings['source_id']
        self.settings = settings
    
    def query_framedb(self, source_settings: dict):

        try:

            framedb_url = source_settings['routing_url']
            get_mapping_api = source_settings['routing_api']

            url = "{}{}".format(framedb_url, get_mapping_api)

            # make the API request to FrameDB:
            payload = {"sourceId": source_settings['source_id']}
            response = requests.post(url, json=payload)
            if response.status_code != 200:
                raise Exception("Server Error = {}".format(response.status_code))
            
            response = response.json()
            if not response['success']:
                raise Exception("Failed to get mapping for {}".format(source_settings['source_id']))
            
            # get the mapping and metadata:
            return True, response['result']['framedbNodes']

        except Exception as e:
            print(e)
            wrap_fail({"errData" : "Failed to communicate with FrameDB", "log" : str(e)})
            return False, str(e)

    
    def get_required_sizes_and_result(self, source_settings: dict):
        
        ret, result = self.query_framedb(source_settings)
        if not ret:
            wrap_fail({"errData": "Failed to query FrameDB", "log": result})
            return False, result
        
        # iterate over nodes and collect width, height data:
        sizes = []
        fps = 8
        act = 8
        ac_data = None
        min_sk = 3

        for node in result:
            metadata = node['metadata']

            if 'sizes' in metadata:
                required_sizes = metadata['sizes']
                for size in required_sizes:
                    if size not in sizes:
                        sizes.append(size)
            
            if 'fps' in metadata:
                fps = metadata['fps']
            if 'act_batch_size' in metadata:
                act = metadata['act_batch_size']
            if 'min_sk' in metadata:
                min_sk = metadata['min_sk']
            if 'ac_data' in metadata and 'head' in metadata['ac_data'] and metadata['ac_data']['head']:
                ac_data = metadata['ac_data']


        return True, {"sizes": sizes, "fps": fps, "act": act, "ac_data": ac_data, "min_sk": min_sk}
    
    def create_decoder(self, source_uri, settings : dict, video_meta: dict, framedb_params: dict):

        units  = []


        if video_meta["codec_name"] == "mjpeg":
            units = [
                "rtspsrc protocol=tcp location=\"{}\" latency=10".format(source_uri),
                "rtpjpegdepay",
            ]

            fps = framedb_params['fps']

            if settings['use_gpu']:

                units.append(" jpegparse ")

                units.extend([prepare_gpu_decoder_plugin("mjpeg")])

                if 'enable_fps_checker' in settings and settings['enable_fps_checker']:
                    units.append(" fps_checker ")
                    
                units.extend([
                    " videorate ",
                    " \"video/x-raw, framerate=(fraction){}\" ".format(fps)
                ])
            else:

                units.append(" jpegparse ")

                units.extend([
                    " jpegdec ",
                    " fps_checker ",
                    " videorate ",
                    " \"video/x-raw, framerate=(fraction){}\" ".format(fps)
                ])

            units.append("tee name=t")

            return True, units
        
        source_unit = "rtspsrc location=\"{}\"".format(source_uri)
        units.append(source_unit)

        depayer = None

        decoder_unit = None

        logging.info("Video metadata {}".format(video_meta))
        
        if video_meta['codec_name'] == 'h264' :

            depayer = "rtph264depay"

            if settings['use_gpu']:
                decoder_unit = "h264parse ! {} ".format(prepare_gpu_decoder_plugin("h264"))
            else:
                decoder_unit = "h264parse ! avdec_h264 "
        
        elif video_meta['codec_name'] == "hevc":

            depayer = "rtph265depay"

            if settings['use_gpu']:
                decoder_unit = "h265parse ! {} ".format(prepare_gpu_decoder_plugin("hevc"))
            else:
                decoder_unit = "h265parse ! avdec_h265 "
        else:
            return False, "Unsupported video format {}".format(video_meta['codec_name'])
        
        units.extend([depayer, decoder_unit])

        if 'enable_fps_checker' in settings and settings['enable_fps_checker']:
            units.append(" fps_checker ")

        fps = framedb_params['fps']

        units.extend([" videorate "])

        # append the caps:
        caps = " \"video/x-raw, framerate=(fraction){}\" ".format(fps)
        units.extend([caps])


        # create a tee after, to spilt pipeline:
        tee = "tee name=t"
        units.extend([tee])
        
        #generated a metadata, check metadata
        return True, units


    def create_encoder(self, settings):
        #sink configuration
        sink = "tidbsink name=mixer"

        if settings['operating_mode'] == 'live':
            sink = "video_batcher name=mixer"

        return  True, [sink]
    

    def create_branches(self, settings: dict, framedb_params: dict, video_meta: dict):
        
        # create a pipeline for each entry of required width and helght:
        sizes = framedb_params['sizes']
        counter = 0

        p_strings = []

        for size in sizes:
            p_string = ""
            if counter == 0:
                p_string = " ! queue ! "
                counter += 1
            else:
                p_string = " t. ! queue ! "
            
            width, height = size.split("x")
            if video_meta['height'] == height and video_meta['width'] == width:
                if settings['use_gpu']:
                    p_string = p_string + "cudaupload ! cudaconvert ! \"video/x-raw(memory:CUDAMemory), format={}\" ! cudadownload ! mixer. ".format(
                        settings['color_format']
                    )
                else:
                    p_string = p_string + "videoconvert ! \"video-x-raw, format={}\" ! mixer.".format(
                        settings['color_format']
                    )
            else:
                if settings['use_gpu']:
                    p_string = p_string + "cudaupload ! cudascale ! cudaconvert ! \"video/x-raw(memory:CUDAMemory), format={}, width={}, height={}\" ! cudadownload ! mixer. ".format(
                        settings['color_format'], width, height
                    )
                else:
                    p_string = p_string + "videoscale ! videoconvert ! \"video/x-raw, format={}, width={}, height={}\" ! mixer. ".format(
                        settings['color_format'], width, height
                    )

            p_strings.append(p_string)
        
        return True, p_strings

    def export_env(self, settings: dict, framedb_meta: dict):
        
        # prepare the env in the format accepted by FrameDB plugin
        w_h_index = {}
        sizes = framedb_meta['sizes']
        for idx, size in enumerate(sizes):
            w_h_index[idx] = {}
            w_h_index[idx]['suffix'] = size
            width, height = size.split("x")
            shape = [int(height), int(width), 3]
            w_h_index[idx]['shape'] = shape
        
        # export update channel data:
        update_channel = {
            "host": settings['updates_url'],
            "port": settings['updates_port'],
            "password": settings['updates_password'],
            "db": 0,
            "isSentinel": settings['is_sentinel'],
        }

        # actuation parameters:
        act_parameters = {}
        if 'ac_data' in framedb_meta and  framedb_meta['ac_data']:
            # actuation controller data found
            act_parameters = {"ac_data": framedb_meta['ac_data']}
        else:
            act_parameters = {
                "host": settings['act_svc'],
                "port": settings['act_port'],
                "password": settings['act_password']
            }

        env = {
            "w_h_index": w_h_index,
            "update_channel": update_channel,
            "act_parameters": act_parameters,
            "routingURL": settings['routing_url'],
            "sourceID": settings['source_id'],
            "skipFrame": int(framedb_meta['min_sk']),
            "update_counter": settings['update_counter'],
            "fQuality": settings['frame_quality'],
            "retry_interval": settings['retry_interval'],
            "cam_url": settings['url'],
            "fps_checker_max_interval": settings.get('fps_checker_max_interval', 30),
            "fps_checker_min_frames": int(settings.get('fps_checker_min_frames', 5))
        }

        return env
    

    def parse_pipeline(self):

        ret, framedb_parameters = self.get_required_sizes_and_result(self.settings)
        if not ret:
            wrap_fail({"errData" : "Failed to get FrameDB metadata", "log" : "None"})
            return False, framedb_parameters

        video_ret, video_meta = DiscoverVideo.GetVideoData(
            self.settings['url'], self.settings.get('retry_interval', 300), self.settings['source_id']
        )

        if not video_ret:
            wrap_fail({"errData": "Failed to get Video parameters", "log": video_meta})
        
        ret_dec, decoder_units = self.create_decoder(
            self.settings['url'],
            self.settings,
            video_meta,
            framedb_parameters
        )
        if not ret_dec:
            return False, decoder_units

        ret_enc, encoder_units = self.create_encoder(self.settings)
        if not ret_enc:
            return False, encoder_units
        
        ret_brances, branch_units = self.create_branches(
            self.settings,
            framedb_parameters,
            video_meta
        )

        print(decoder_units, encoder_units, branch_units)

        # get env 
        env = self.export_env(self.settings, framedb_parameters)

        return True, [decoder_units, encoder_units, branch_units], env

    def __attach_units(self, units):

        # join decoder unit:
        decoder = units[0]
        decoder_string = " ! ".join(decoder)

        # join all branches together:
        branches = units[2]
        branch_string = ""
        for branch in branches:
            branch_string = branch_string + branch + " "
        
        # now plug-in the encoder:
        encoder = units[1]
        encoder_string = "!".join(encoder)
        
        pipeline_string = "{} {} {}".format(encoder_string, decoder_string, branch_string)
        return pipeline_string

    def __live_operator(self, pipeline, env_dict):

        print('Passing env: ', env_dict)

        max_tries = 100
        tries = 0

        buffer_output = {}

        env = json.dumps(env_dict)
        env_system = os.environ.copy()
        env_system['FRAMEDB_C'] = env

        while True:

            proc_parent = open('base_script.sh').read()

            process_string = "gst-launch-1.0 {}".format(pipeline)
            if self.settings['loop_video']:
                """process_string = "idx=0\n while true; do\nexport IDX=$idx\n{}\n\nidx=$(($idx + 1))\nsleep {}\n done;".format(
                    process_string, env_dict.get('retry_interval', '300')
                )"""
                process_string = proc_parent.format(
                    env_dict.get('cam_url', None), process_string, env_dict.get('sourceID', None),
                    env_dict.get('sourceID', None),
                    env_dict.get('retry_interval', 300)
                )

                # print('Running base script: {}', process_string)

            print('Running process = ', process_string)
            child = subprocess.Popen(process_string, shell = True, env = env_system)
            stream_op, stream_error = child.communicate()
            # print(stream_op, stream_error)

            stream_string = "Done"

            ret_code = child.returncode

            if ret_code != 0:
                tries +=1

                buffer_output['try{}'.format(tries)] = stream_string
                if tries > max_tries:
                    print('Process failed for all {} times, exiting'.format(max_tries))
                    logging.error("process failed")
                    wrap_fail({"errData" : "failed to run task", "log" : buffer_output})
            else:
                print('finished successfully')
                logging.info("Decoding finished successfully")
                wrap_complete({"info" : "decoding finished", "log" : buffer_output})


    def run_pipeline(self):

        try:
            ret, pipeline_uints, env = self.parse_pipeline()
            if not ret:
                logging.error(pipeline_uints)
                wrap_fail({"errData" : pipeline_uints})
            
            #generate the shelx command:
            pipeline = self.__attach_units(pipeline_uints)

            print('Running pipeline: ', pipeline)

            if self.settings['operating_mode'] == 'live':
                logging.info("Running live operator")
                self.__live_operator(pipeline, env)

            #run the process:
            process = "gst-launch-1.0 {}".format(pipeline)
            if self.settings['loop_video']:
                process = "idx=0\n while true; do\nexport IDX=$idx\n {}\nidx=$(($idx + 1))\nsleep 2\n done;".format(process)

            logging.info("Running pipeline " + process)

            #launch a subprocess:
            duration = self.settings['duration']
            remaining_duration = duration


            # export the env:
            env = json.dumps(env)

            # copy the system's env and add env to it:
            env_copy = os.environ.copy()
            env_copy['FRAMEDB_C'] = env

            outputs = {}
            tries = 0

            while remaining_duration > 0 :
                remaining_duration = int(remaining_duration)

                #work until there is still time
                process_timeouts = "timeout -s SIGINT {} {}".format(remaining_duration, process)

                st = time.time()
                child_handle = subprocess.Popen(process_timeouts, shell = True, env = env_copy)
                stdout, stderr = child_handle.communicate()
                exitcode = child_handle.returncode
                et = time.time()

                sub_time = et - st

                output_str = "Completed"
                print(output_str, exitcode)

                outputs["try_{}".format(tries + 1)] = output_str

                if exitcode == TIMEOUT_SIGINT_SUCCESS:
                    logging.info("Process completed successfully")
                    wrap_complete({"message" : "Completed execution", "logs" : outputs})
                else:
                    tries = tries + 1

                    #avoid infinite looping core usage
                    time.sleep(2)

                    #get remaining time
                    remaining_duration = remaining_duration - sub_time

                    #add a small offset to compensate startup time-loss
                    logging.info("Process failed, retrying for remaining time {}".format(remaining_duration))

            # job failed throughout the duration
            logging.error("Job failed to run, tried {} times.".format(tries))
            wrap_fail({"errData" : "Failed to decode live stream", "logs" : outputs})

        except Exception as e:
            logging.error(e)
            wrap_fail({"errData" : "Internal error, failed to run pipeline".format(e)})




class StoredVideoDecoder:

    def __init__(self, settings):

        self.source_id = settings['source_id']
        self.settings = settings

    def query_framedb(self, source_settings: dict):

        try:

            framedb_url = source_settings['routing_url']
            get_mapping_api = source_settings['routing_api']

            url = "{}{}".format(framedb_url, get_mapping_api)

            # make the API request to FrameDB:
            payload = {"sourceId": source_settings['source_id']}
            response = requests.post(url, json=payload)
            if response.status_code != 200:
                raise Exception("Server Error = {}".format(response.status_code))
            
            response = response.json()
            if not response['success']:
                raise Exception("Failed to get mapping for {}".format(source_settings['source_id']))
            
            # get the mapping and metadata:
            return True, response['result']['framedbNodes']

        except Exception as e:
            print(e)
            wrap_fail({"errData" : "Failed to communicate with FrameDB", "log" : str(e)})
            return False, str(e)

    
    def get_required_sizes_and_result(self, source_settings: dict):
        
        ret, result = self.query_framedb(source_settings)
        if not ret:
            wrap_fail({"errData": "Failed to query FrameDB", "log": result})
            return False, result
        
        # iterate over nodes and collect width, height data:
        sizes = []
        fps = 8
        act = 8
        ac_data = None
        min_sk = 3

        for node in result:
            metadata = node['metadata']

            if 'sizes' in metadata:
                required_sizes = metadata['sizes']
                for size in required_sizes:
                    if size not in sizes:
                        sizes.append(size)
            
            if 'fps' in metadata:
                fps = metadata['fps']
            if 'min_sk' in metadata:
                min_sk = metadata['min_sk']
            if 'act_batch_size' in metadata:
                act = metadata['act_batch_size']
            if 'ac_data' in metadata and 'head' in metadata['ac_data'] and metadata['ac_data']['head']:
                ac_data = metadata['ac_data']


        return True, {"sizes": sizes, "fps": fps, "act": act, "ac_data": ac_data, "min_sk": min_sk}
    
    def create_decoder(self, source_uri, settings : dict, video_meta: dict, framedb_params: dict):

        units = []


        if video_meta["codec_name"] == "mjpeg":
            units = [
                "filesrc  location=\"{}\"".format(source_uri),
            ]

            demuxer_unit = c_map[ settings['container'] ]
            units.append(demuxer_unit)

            fps = framedb_params['fps']
            if settings['use_gpu']:

                units.append(" jpegparse ")

                units.extend([prepare_gpu_decoder_plugin("mjpeg")])

                if 'enable_fps_checker' in settings and settings['enable_fps_checker']:
                    units.append(" fps_checker ")
                    
                units.extend([
                    " videorate ",
                    " \"video/x-raw, framerate=(fraction){}\" ".format(fps)
                ])
            else:

                units.append(" jpegparse ")

                units.extend([
                    " jpegdec ",
                    " fps_checker ",
                    " videorate ",
                    " \"video/x-raw, framerate=(fraction){}\" ".format(fps)
                ])

            units.append("tee name=t")

            return True, units

        source_unit = "filesrc location=\"{}\"".format(source_uri)

        if settings['loop_video']:
            source_unit = "filesrc location=\"{}\"".format(source_uri)

        units.append(source_unit)

        demuxer_unit = c_map[ settings['container'] ]
        units.append(demuxer_unit)

        decoder_unit = None
        logging.info("Video metadata {}".format(video_meta))

        if video_meta['codec_name'] == 'h264' :
            if settings['use_gpu']:
                decoder_unit = "h264parse ! {} ".format(prepare_gpu_decoder_plugin("h264"))
            else:
                decoder_unit = "h264parse ! avdec_h264 "
        
        elif video_meta['codec_name'] == "hevc":
            if settings['use_gpu']:
                decoder_unit = "h265parse ! {} ".format(prepare_gpu_decoder_plugin("hevc"))
            else:
                decoder_unit = "h265parse ! avdec_h265 "
        else:
            return False, "Unsupported video format {}".format(video_meta['codec_name'])
        
        units.append(decoder_unit)

        if 'enable_fps_checker' in settings and settings['enable_fps_checker']:
            units.append(" fps_checker ")

        if 'use_custom_ts' in settings and settings['use_custom_ts']:
            units.append(" timestamper ")

        fps = framedb_params['fps']

        units.extend([" videorate "])

        # append the caps:
        caps = "\"video/x-raw, framerate=(fraction){}\"".format(fps)
        units.extend([caps])


        # create a tee after, to spilt pipeline:
        # tee = "tee name=t"
        # units.extend([tee])
        
        #generated a metadata, check metadata
        return True, units

    def export_env(self, settings: dict, framedb_meta: dict):
        
        # prepare the env in the format accepted by FrameDB plugin
        w_h_index = {}
        sizes = framedb_meta['sizes']
        for idx, size in enumerate(sizes):
            w_h_index[idx] = {}
            w_h_index[idx]['suffix'] = size
            width, height = size.split("x")
            shape = [int(height), int(width), 3]
            w_h_index[idx]['shape'] = shape
        
        # export update channel data:
        update_channel = {
            "host": settings['updates_url'],
            "port": settings['updates_port'],
            "password": settings['updates_password'],
            "db": 0,
            "isSentinel": settings['is_sentinel'],
        }

        # actuation parameters:
        act_parameters = {}
        if 'ac_data' in framedb_meta and  framedb_meta['ac_data']:
            # actuation controller data found
            act_parameters = {"ac_data": framedb_meta['ac_data']}
        else:
            act_parameters = {
                "host": settings['act_svc'],
                "port": settings['act_port'],
                "password": settings['act_password']
            }

        env = {
            "w_h_index": w_h_index,
            "update_channel": update_channel,
            "act_parameters": act_parameters,
            "routingURL": settings['routing_url'],
            "sourceID": settings['source_id'],
            "skipFrame": int(framedb_meta['min_sk']),
            "update_counter": settings['update_counter'],
            "fQuality": settings['frame_quality'],
            "ohw": [ settings['o_height'], settings['o_width'] ],
            "use_gpu": settings['use_gpu'],
            "retry_interval": settings['retry_interval'],
            "cam_url": settings['url'],
            "fps_checker_max_interval": int(settings.get('fps_checker_max_interval', 30)),
            "fps_checker_min_frames": int(settings.get('fps_checker_min_frames', 5))
        }

        return env

    def create_branches(self, settings: dict, framedb_params: dict, video_meta: dict):
        
        # create a pipeline for each entry of required width and helght:
        p_strings = []

        if settings['use_gpu']:
            p_strings.append(" ! cudaupload ! cudaconvert ! \"video/x-raw(memory:CUDAMemory), format={}\" ! cudadownload ! ".format(
                settings['color_format']
            ))
        else:
            p_strings.append(" ! videoconvert ! \"video-x-raw, format={}\" ! ".format(
                settings['color_format']
            ))
    
        return True, p_strings

    def create_encoder(self, settings):    
        #sink configuration
        sink = ""

        if settings['operating_mode'] == 'live':
            if settings['as_live']:
                sink = " video_writer "
            else:
                sink = " video_batcher name=mixer "

        return  True, [sink]

    def parse_pipeline(self):
        ret, framedb_parameters = self.get_required_sizes_and_result(self.settings)
        if not ret:
            wrap_fail({"errData" : "Failed to get FrameDB metadata", "log" : "None"})
            return False, framedb_parameters

        video_ret, video_meta = DiscoverVideo.GetVideoData(
            self.settings['url'], self.settings.get('retry_interval', 300), self.settings['source_id']
        )

        if not video_ret:
            wrap_fail({"errData": "Failed to get Video parameters", "log": video_meta})

        # set current width and height in pipeline:
        self.settings['o_width'] = video_meta['width']
        self.settings['o_height'] = video_meta['height']
        
        ret_dec, decoder_units = self.create_decoder(
            self.settings['url'],
            self.settings,
            video_meta,
            framedb_parameters
        )
        if not ret_dec:
            return False, decoder_units

        ret_enc, encoder_units = self.create_encoder(self.settings)
        if not ret_enc:
            return False, encoder_units
        
        ret_brances, branch_units = self.create_branches(
            self.settings,
            framedb_parameters,
            video_meta
        )

        env = self.export_env(self.settings, framedb_parameters)

        print(decoder_units, encoder_units, branch_units)

        return True, [decoder_units, encoder_units, branch_units], env
        

    def __attach_units(self, units):

        # join decoder unit:
        decoder = units[0]
        decoder_string = " ! ".join(decoder)

        # join all branches together:
        branches = units[2]
        branch_string = ""
        for branch in branches:
            branch_string = branch_string + branch + " "
        
        # now plug-in the encoder:
        encoder = units[1]
        encoder_string = "!".join(encoder)
        
        pipeline_string = "{} {} {}".format(decoder_string, branch_string, encoder_string)
        return pipeline_string


    def __live_operator(self, pipeline, env_dict):

        print('Passing env: ', env_dict)

        max_tries = 100
        tries = 0

        buffer_output = {}
        env = json.dumps(env_dict)

        env_system = os.environ.copy()
        env_system['FRAMEDB_C'] = env

        #live source never exists, kill the job or push back suspend
        while True:

            proc_parent = open('base_script_recorded.sh').read()

            process_string = "gst-launch-1.0 {}".format(pipeline)
            if self.settings['loop_video']:
                """process_string = "idx=0\n while true; do\nexport IDX=$idx\n{}\n\nidx=$(($idx + 1))\nsleep {}\n done;".format(
                    process_string, env_dict.get('retry_interval', '300')
                )"""
                process_string = proc_parent.format(
                    env_dict.get('cam_url', None), process_string, env_dict.get('sourceID', None),
                    env_dict.get('sourceID', None),
                    env_dict.get('retry_interval', 300)
                )

            print('Running process: {}', process_string)
            child = subprocess.Popen(process_string, shell = True, env = env_system)
            op, error = child.communicate()
            ret_code = child.returncode

            stream_string = "Completed"

            print(stream_string)

            if ret_code != 0:
                tries +=1

                buffer_output['try{}'.format(tries)] = stream_string
            
                if tries > max_tries:
                    print('Process failed for all {} times, exiting'.format(max_tries))
                    logging.error("process failed")
                    wrap_fail({"errData" : "failed to run task", "log" : buffer_output})
            else:
                print('finished successfully')
                logging.info("Decoding finished successfully")
                wrap_complete({"info" : "decoding finished", "log" : buffer_output})


    def run_pipeline(self):

        try:
            ret, pipeline_uints, env = self.parse_pipeline()
            if not ret:
                logging.error(pipeline_uints)
                wrap_fail({"errData" : pipeline_uints})

            # generate the shelx command:
            pipeline = self.__attach_units(pipeline_uints)

            print('Running pipeline: ', pipeline)

            if self.settings['operating_mode'] == "live":
                self.__live_operator(pipeline, env)

            #run the process:
            process = "gst-launch-1.0 {}".format(pipeline)
            if self.settings['loop_video']:
                process = "idx=0\n while true; do\nexport IDX=$idx\n{}\n\nidx=$(($idx + 1))\nsleep 2\n done;".format(process)

            env = json.dumps(env)
            env_system = os.environ.copy()
            env_system['FRAMEDB_C'] = env

            logging.info("Running pipeline " + process)

            #launch a subprocess:
            child_handle = subprocess.Popen(process, shell=True, env = env_system)
            streamdata, error = child_handle.communicate()

            ret_code = child_handle.returncode
            streamdata = "Completed"

            print(streamdata)

            if ret_code == 0 :
                #success:
                logging.info("Execution of pipeline finished successfully")
                wrap_complete({"message" : "completed properly", "logs" : streamdata})

            else:
                logging.info("Execution terminated because of error ")
                wrap_fail({"errData" : "failed execution", "logs" : streamdata})

        except Exception as e:
            logging.error(e)
            wrap_fail({"errData" : "Internal error, failed to run pipeline".format(e)})
