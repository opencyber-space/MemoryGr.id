from kubernetes import client, config
import yaml
import ast
import os


DEPLOYMENT_FILE_NAME = "yaml/deployment.yaml"
SERVICE_FILE_NAME = "yaml/svc.yaml"
NAMESPACE = "framedb-storage"

PWD_SECRET = os.getenv("REGISTRY_SECRETs")


class K8sAPI:

    @staticmethod
    def create_deployment(data: dict) -> dict:

        try:
            config.load_kube_config()

            enable_frame_write = os.getenv("ENABLE_FRAME_WRITE", "0")
            write_path = os.getenv("FRAMES_WRITE_PATH", "/frames")
            frame_write_interval = int(os.getenv("FRAME_WRITE_INTERVAL", "100"))

            node_name = data['node']
            gpu = str(data['gpuID'])

            pod_templ = open(DEPLOYMENT_FILE_NAME).read()
            svc_templ = open(SERVICE_FILE_NAME).read()

            pod_name = f"decoder-{node_name}-gpu-{gpu}"
            pod_templ = pod_templ.replace("<pod-name>", pod_name)
            pod_templ = pod_templ.replace("<gpu-id>", gpu)
            pod_templ = pod_templ.replace("<machine>", node_name)

            pod_templ = pod_templ.replace("<ENABLE_FRAME_WRITE>", enable_frame_write)
            pod_templ = pod_templ.replace("<FRAME_WRITE_INTERVAL>", frame_write_interval)


            svc_templ = svc_templ.replace("<pod-name>", pod_name)

            pod_spec = yaml.load(pod_templ, Loader=yaml.FullLoader)
            svc_spec = yaml.load(svc_templ, Loader=yaml.FullLoader)

            if PWD_SECRET:
                pod_spec['spec']['template']['spec']['imagePullSecrets'] = [
                    {"name": PWD_SECRET}]

            print(pod_spec)

            cli = client.AppsV1Api()
            cli_svc = client.CoreV1Api()

            pod_response = cli.create_namespaced_deployment(
                namespace=NAMESPACE, body=pod_spec
            )
            svc_response = cli_svc.create_namespaced_service(
                namespace=NAMESPACE, body=svc_spec
            )

            return {
                "payload": {
                    "service_create_result": "Created service successfully",
                    "pod_create_result": "Created pod successfully"
                },
                "error": False
            }

        except Exception as e:
            return {
                "error": True,
                "payload": str(e)
            }

    @staticmethod
    def remove_deployment(data: dict) -> dict:

        try:
            config.load_kube_config()

            gpu = data['gpuID']
            node = data['node']

            pod_name = "decoder-{}-gpu-{}".format(
                node, gpu
            )

            cli = client.AppsV1Api()
            cli_svc = client.CoreV1Api()

            # remove pod:
            pod_remove_res = cli.delete_namespaced_deployment(
                namespace=NAMESPACE,
                name=pod_name,
                body=client.V1DeleteOptions(
                    propagation_policy="Foreground",
                    grace_period_seconds=5
                )
            )

            svc_remove_res = cli_svc.delete_namespaced_service(
                name="{}-svc".format(pod_name),
                namespace=NAMESPACE
            )

            return {
                "error": False,
                "payload": {
                    "service_remove_result": "Removed service successfully",
                    "pod_remove_result": "Remove pod successfully"
                }
            }

        except Exception as e:
            return {
                "error": True,
                "payload": str(e)
            }
