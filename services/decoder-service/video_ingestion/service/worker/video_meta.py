import json,copy
import subprocess
import time

import logging
logging = logging.getLogger("MainLogger")

import shlex
import time
import os

class DiscoverVideo:

    @staticmethod
    def GetVideoData(url, retry_interval, source_id):
        ffmpeg_command = ""
        if not url.startswith("rtsp://") and not url.startswith("rtsps://"):
            if not os.path.exists(url) :
                return False, "stored video does not exist"
            ffmpeg_command = "ffprobe -show_entries stream=codec_type,codec_name,width,height -v quiet -of json"
        else:
          ffmpeg_command = "/usr/bin/ffprobe -show_entries stream=codec_type,codec_name,width,height -of json -stimeout 10000000"
        args = shlex.split(ffmpeg_command)
        args.append(url)
        print(os.environ)
        print(os.getuid())
        print('LD_LIBRARY_PATH:', os.environ.get('LD_LIBRARY_PATH'))
        result = subprocess.run(
           ['ffprobe', '-protocols'],
           stdout=subprocess.PIPE,
           stderr=subprocess.PIPE
        )
        result = subprocess.run(
          ['ldd', '/usr/bin/ffprobe'],
           stdout=subprocess.PIPE,
           stderr=subprocess.PIPE
        )
        print(result.stdout.decode())
        result = subprocess.run(
          ['ffprobe'],
          stdout=subprocess.PIPE,
          stderr=subprocess.PIPE,
          env=dict(os.environ, LD_DEBUG='libs')
        )
        ssl_lines = [line for line in result.stderr.decode().split('\n') if 'libssl' in line]
        print('OpenSSL libraries loaded:', ssl_lines)
        print('Supported protocols:', result.stdout.decode())
        ffprobe_output = subprocess.run(['which','ffprobe'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        print('stdout:', ffprobe_output.stdout.decode())
        print('stderr:', ffprobe_output.stderr.decode())
        print('returncode:', ffprobe_output.returncode)
        ffprobe_output = subprocess.run(['/usr/bin/ffprobe','--version'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        print('stdout:', ffprobe_output.stdout.decode())
        print('stderr:', ffprobe_output.stderr.decode())
        print('returncode:', ffprobe_output.returncode)
        while True:
            try:
                #ffprobe_output = subprocess.check_output(args)
                args1 = copy.copy(args)
                ffprobe_output = subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                print('stdout:', ffprobe_output.stdout.decode())
                print('stderr:', ffprobe_output.stderr.decode())
                print('returncode:', ffprobe_output.returncode)
                # check stream :
                #result = json.loads(ffprobe_output.decode('utf-8'))
                result = json.loads(ffprobe_output.stdout.decode())
                print("stdout:",result)
                #check if video element is present :
                streams = result['streams']
                for stream in streams :
                    if stream['codec_type'] == "video" :
                        logging.info("Identified metadata: {}".format(stream))
                        return True, stream
    
                raise Exception("no video source detected")
	
            except Exception as e :
                logging.error("failed to query video info: {}, retrying in {}seconds..".format(e, retry_interval))
                # raise an alert:
                os.system("python3 send_alert.py {}".format(source_id))
                time.sleep(int(retry_interval))
                continue

