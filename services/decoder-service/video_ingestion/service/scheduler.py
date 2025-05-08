import subprocess
import os
import json
from aios_logger import AIOSLogger, ErrorSeverity


class DecoderScheduler:

    def __init__(self, logger: AIOSLogger) -> None:
        self.running_streams = {}
        self.logger = logger

    def prepare_env(self, data: dict) -> dict:
        ingestion_uri = os.getenv("INGESTION_URI", 'http://localhost:8000')
        job_name = data['jobName']
        source_settings = data['jobParameters']['settings']['sourceInfo']

        # check if job exists:
        if job_name in self.running_streams:
            self.logger.error(
                "stream_create", ErrorSeverity.HIGH,
                "Stream {} already exist".format(job_name),
                {"job_name": job_name}, None, None, None
            )
            return {"error": True, "message": "Job already exist and is running."}

        # clone the system environment:
        sys_env = os.environ.copy()

        # set it under running process:
        self.running_streams[job_name] = {
            "config": source_settings,
            "process": None
        }

        # substitute these new variables in this clone:
        sys_env['SOURCE_DATA'] = json.dumps(source_settings)
        sys_env['INGESTION_URI'] = ingestion_uri

        return {"error": False, "env": sys_env}

    def create_stream(self, data: dict) -> dict:

        result = self.prepare_env(data)
        if result['error']:
            return result
        env = result['env']

        # prepare the process:
        job_name = data['jobName']

        # run the process:
        process = subprocess.Popen(
            ["python3", "-u", "main.py"],
            preexec_fn=os.setsid,
            env=env
        )

        # save the sub-process object:
        self.running_streams[job_name]['process'] = process

        self.logger.info(
            "stream_create",
            "Creatrd stream {}".format(job_name),
            extras={
                "pid": process.pid,
                "job_name": job_name
            }
        )

        # return the result:
        return {
            "error": False,
            "message": "Created stream with PID {}".format(process.pid)
        }

    def kill_stream(self, data: dict) -> dict:

        job_name = data['jobName']
        if job_name not in self.running_streams:
            self.logger.error(
                "stream_create", ErrorSeverity.HIGH,
                "Stream {} already exist".format(job_name),
                {"job_name": job_name}, None, None, None
            )
            return {
                "error": True,
                "message": "Job name {} is not running".format(job_name)
            }

        # kill the process:
        process = self.running_streams[job_name]['process']
        pid = process.pid

        group_pid = os.getpgid(pid)
        os.killpg(group_pid, 9)

        self.logger.info(
            "stream_kill",
            "Killed stream {}".format(job_name),
            extras={
                "job_name": job_name,
                "pid": pid
            }
        )

        del self.running_streams[job_name]

        return {"error": False, "message": "Killed stream {}".format(job_name)}

    def get_streams(self) -> dict:
        result_data = {}
        for job in self.running_streams:
            result_data[job] = self.running_streams[job]['config']

        return result_data

    def get_stream(self, job_name) -> dict:
        if job_name not in self.running_streams:
            return {
                "error": True,
                "message": "Job {} does not exist".format(job_name)
            }

        return {
            "error": False,
            "payload": self.running_streams[job_name]['config']
        }
