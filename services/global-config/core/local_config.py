from kubernetes import client, config
from typing import Dict, Any
from kubernetes.client import V1ObjectMeta, V1Namespace
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def setup_framedb_config_service(kube_config_dict: dict, storage_size: str = "1Gi"):
    try:
        # Load kube config
        config.load_kube_config_from_dict(kube_config_dict)

        core_v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()

        namespace = "framedb-config"
        node_port = 32566

        # Create Namespace if not exists
        try:
            core_v1.read_namespace(namespace)
        except client.exceptions.ApiException as e:
            if e.status == 404:
                core_v1.create_namespace(V1Namespace(
                    metadata=V1ObjectMeta(name=namespace)))
                logger.info(f"Namespace '{namespace}' created.")
            else:
                raise

        # Create PersistentVolume
        pv = client.V1PersistentVolume(
            metadata=V1ObjectMeta(name="framedb-mongo-pv"),
            spec=client.V1PersistentVolumeSpec(
                capacity={"storage": storage_size},
                access_modes=["ReadWriteOnce"],
                host_path=client.V1HostPathVolumeSource(
                    path="/mnt/data/framedb-mongo"),
                persistent_volume_reclaim_policy="Retain"
            )
        )

        # Create PersistentVolumeClaim
        pvc = client.V1PersistentVolumeClaim(
            metadata=V1ObjectMeta(name="framedb-mongo-pvc"),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources=client.V1ResourceRequirements(
                    requests={"storage": storage_size})
            )
        )

        # MongoDB Deployment
        mongo_deploy = client.V1Deployment(
            metadata=V1ObjectMeta(name="mongodb"),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector={"matchLabels": {"app": "mongodb"}},
                template=client.V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels={"app": "mongodb"}),
                    spec=client.V1PodSpec(containers=[
                        client.V1Container(
                            name="mongodb",
                            image="mongo:6.0",
                            ports=[client.V1ContainerPort(
                                container_port=27017)],
                            volume_mounts=[client.V1VolumeMount(
                                mount_path="/data/db", name="mongo-storage")]
                        )
                    ],
                        volumes=[client.V1Volume(
                            name="mongo-storage",
                            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                                claim_name="framedb-mongo-pvc")
                        )]
                    )
                )
            )
        )

        # MongoDB Service
        mongo_svc = client.V1Service(
            metadata=V1ObjectMeta(name="framedb-local-config"),
            spec=client.V1ServiceSpec(
                selector={"app": "mongodb"},
                ports=[client.V1ServicePort(port=27017, target_port=27017)]
            )
        )

        # FrameDB Config Service Deployment
        config_deploy = client.V1Deployment(
            metadata=V1ObjectMeta(name="framedb-config"),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector={"matchLabels": {"app": "framedb-config"}},
                template=client.V1PodTemplateSpec(
                    metadata=V1ObjectMeta(labels={"app": "framedb-config"}),
                    spec=client.V1PodSpec(containers=[
                        client.V1Container(
                            name="framedb-config",
                            image="framedb/config-service:latest",  # replace if needed
                            ports=[client.V1ContainerPort(
                                container_port=5000)],
                            env=[client.V1EnvVar(
                                name="MONGO_URL", value="mongodb://framedb-local-config.framedb-config.svc.cluster.local:27017")]
                        )
                    ])
                )
            )
        )

        # Config Service NodePort
        config_svc = client.V1Service(
            metadata=V1ObjectMeta(name="framedb-config-service"),
            spec=client.V1ServiceSpec(
                type="NodePort",
                selector={"app": "framedb-config"},
                ports=[client.V1ServicePort(
                    port=5000, target_port=5000, node_port=node_port)]
            )
        )

        # Create PV, PVC
        core_v1.create_persistent_volume(body=pv)
        core_v1.create_namespaced_persistent_volume_claim(
            namespace=namespace, body=pvc)

        # Create Deployments and Services
        apps_v1.create_namespaced_deployment(
            namespace=namespace, body=mongo_deploy)
        core_v1.create_namespaced_service(namespace=namespace, body=mongo_svc)

        apps_v1.create_namespaced_deployment(
            namespace=namespace, body=config_deploy)
        core_v1.create_namespaced_service(namespace=namespace, body=config_svc)

        logger.info(f"FrameDB config service deployed at nodePort {node_port}")

    except Exception as e:
        logger.error(f"Error setting up FrameDB config service: {e}")
        raise


def remove_framedb_config_service(kube_config_dict: dict):
    try:
        config.load_kube_config_from_dict(kube_config_dict)

        core_v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()

        namespace = "framedb-config"

        # Delete Deployments
        apps_v1.delete_namespaced_deployment(
            name="mongodb", namespace=namespace)
        apps_v1.delete_namespaced_deployment(
            name="framedb-config", namespace=namespace)

        # Delete Services
        core_v1.delete_namespaced_service(
            name="framedb-local-config", namespace=namespace)
        core_v1.delete_namespaced_service(
            name="framedb-config-service", namespace=namespace)

        # Delete PVC
        core_v1.delete_namespaced_persistent_volume_claim(
            name="framedb-mongo-pvc", namespace=namespace)

        # Delete PV
        core_v1.delete_persistent_volume(name="framedb-mongo-pv")

        # Optionally delete namespace
        core_v1.delete_namespace(name=namespace)

        logger.info("FrameDB config service and related resources removed.")
    except Exception as e:
        logger.error(f" Error removing FrameDB config service: {e}")
        raise


def status_framedb_config_service(kube_config_dict: dict) -> Dict[str, Any]:
    try:
        config.load_kube_config_from_dict(kube_config_dict)

        core_v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()

        namespace = "framedb-config"
        result = {"namespace": "missing", "deployments": {}, "pods": [], "services": {}, "pvc": {}}

        # Check namespace
        try:
            core_v1.read_namespace(namespace)
            result["namespace"] = "present"
        except Exception as e:
            return result

        # Check Deployments
        deployments = ["mongodb", "framedb-config"]
        for name in deployments:
            try:
                dep = apps_v1.read_namespaced_deployment(name=name, namespace=namespace)
                available = dep.status.available_replicas or 0
                desired = dep.spec.replicas
                result["deployments"][name] = f"{available}/{desired} available"
            except Exception as e:
                result["deployments"][name] = f"error: {str(e)}"

        # Check Pods
        pods = core_v1.list_namespaced_pod(namespace=namespace).items
        for pod in pods:
            result["pods"].append({
                "name": pod.metadata.name,
                "status": pod.status.phase,
                "ready": all(c.ready for c in pod.status.container_statuses or [])
            })

        # Check Services
        services = ["framedb-local-config", "framedb-config-service"]
        for name in services:
            try:
                svc = core_v1.read_namespaced_service(name=name, namespace=namespace)
                cluster_ip = svc.spec.cluster_ip
                ports = [p.node_port for p in svc.spec.ports if p.node_port]
                result["services"][name] = {"cluster_ip": cluster_ip, "node_ports": ports}
            except Exception as e:
                result["services"][name] = f"error: {str(e)}"

        # Check PVC
        try:
            pvc = core_v1.read_namespaced_persistent_volume_claim(name="framedb-mongo-pvc", namespace=namespace)
            result["pvc"]["status"] = pvc.status.phase
            result["pvc"]["volume_name"] = pvc.spec.volume_name
        except Exception as e:
            result["pvc"]["error"] = str(e)

        return result

    except Exception as e:
        return {"error": str(e)}

