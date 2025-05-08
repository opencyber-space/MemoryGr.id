import requests
import time

REQUEST_TIMEOUT = 5


class QueryAPI:

    @staticmethod
    def mk_get_request(url, route):

        URL = "{}{}".format(url, route)

        # make request:
        try:

            response = requests.get(URL, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                raise Exception(
                    "Server Error, Status code {}".format(response.status_code))

            # parse the request as json:
            data = response.json()
            if not data['success']:
                raise Exception(data['payload'])

            return True, data['payload']

        except Exception as e:
            return False, str(e)

    @staticmethod
    def mk_post_request(url, route, data):

        URL = "{}{}".format(url, route)

        # make request:
        try:

            response = requests.post(URL, json=data, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                raise Exception(
                    "Server Error, Status code {}".format(response.status_code))

            # parse the request as json:
            data = response.json()
            if not data['success']:
                raise Exception(data['payload'])

            return True, data['payload']

        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_health(data):

        node = data['node']
        gpu = data['gpuID']

        pod_name = "decoder-{}-gpu-{}".format(
            node, gpu
        )

        # create the service name:
        svc_uri = "http://{}-svc.framedb-storage.svc.cluster.local:5000".format(
            pod_name
        )

        ret, resp = QueryAPI.mk_get_request(svc_uri, "/health")
        return ret, resp

    @staticmethod
    def get_streams(data):

        node = data['node']
        gpu = data['gpuID']

        pod_name = "decoder-{}-gpu-{}".format(
            node, gpu
        )

        # create the service name:
        svc_uri = "http://{}-svc.framedb-storage.svc.cluster.local:5000".format(
            pod_name
        )

        ret, resp = QueryAPI.mk_get_request(svc_uri, "/getStreams")
        if not ret:
            return False, resp

        # return as array:
        result = []
        for job_name in resp:
            res = {
                "jobName": job_name,
                "config": resp[job_name]
            }

            result.append(res)

        return True, result

    @staticmethod
    def restart_stream(data):
        try:

            node = data['node']
            gpu = data['gpuID']

            pod_name = "decoder-{}-gpu-{}".format(
                node, gpu
            )

            # create the service name:
            svc_uri = "http://{}-svc.framedb-storage.svc.cluster.local:5000".format(
                pod_name
            )

            # get all streams
            ret, all_streams = QueryAPI.get_streams(data)
            if not ret:
                raise Exception(all_streams)

            # search for given job
            for job_entry in all_streams:
                if job_entry['jobName'] == (data['sourceId'] + "-decoder"):
                    config = job_entry['config']
                    job_name = job_entry['jobName']

                    # kill the stream:
                    QueryAPI.mk_post_request(svc_uri, "/killStream", {
                        "jobName": job_name
                    })

                    time.sleep(10)

                    # ['jobParameters']['settings']['sourceInfo']

                    # start the stream again
                    start_payload = {
                        "jobName": job_name,
                        "jobParameters": {
                            "settings": {
                                "sourceInfo": config
                            }
                        }
                    }

                    # start the stream
                    return QueryAPI.mk_post_request(
                        svc_uri, "/createStream", start_payload)

        except Exception as e:
            return False, str(e)

    @staticmethod
    def start_with_context(data):
        try:

            node = data['node']
            gpu = data['gpuID']

            pod_name = "decoder-{}-gpu-{}".format(
                node, gpu
            )

            # create the service name:
            svc_uri = "http://{}-svc.framedb-storage.svc.cluster.local:5000".format(
                pod_name
            )

            job_name = data['sourceId'] + "-decoder"
            config = data['config']

            start_payload = {
                "jobName": job_name,
                "jobParameters": {
                    "settings": {
                        "sourceInfo": config
                    }
                }
            }

            return QueryAPI.mk_post_request(
                svc_uri, "/createStream", start_payload)

        except Exception as e:
            return False, str(e)

    @staticmethod
    def restart_with_context(data):
        try:

            job_name = data['sourceId'] + "-decoder"

            node = data['node']
            gpu = data['gpuID']

            pod_name = "decoder-{}-gpu-{}".format(
                node, gpu
            )

            svc_uri = "http://{}-svc.framedb-storage.svc.cluster.local:5000".format(
                pod_name
            )

            # kill stream:
            QueryAPI.mk_post_request(svc_uri, "/killStream", {
                "jobName": job_name
            })

            time.sleep(5)

            # start stream:
            return QueryAPI.start_with_context(data)

        except Exception as e:
            return False, str(e)
