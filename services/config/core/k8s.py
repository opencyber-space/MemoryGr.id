from kubernetes import client, config
import logging


class InMemoryDB:
    def __init__(self):
        try:
            config.load_incluster_config()
            logging.info("Using in-cluster Kubernetes configuration.")
        except config.ConfigException:
            config.load_kube_config()
            logging.info("Using local kubeconfig.")

        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.namespace = "framedb"
        self.ensure_namespace()

    def ensure_namespace(self):
        try:
            self.core_v1.read_namespace(self.namespace)
            logging.info(f"Namespace '{self.namespace}' already exists.")
        except Exception as e:
            ns = client.V1Namespace(
                metadata=client.V1ObjectMeta(name=self.namespace))
            self.core_v1.create_namespace(ns)
            logging.info(f"Namespace '{self.namespace}' created.")

    def get_available_node_port(self, start=30700, end=30900) -> int:
        used_ports = set()
        try:
            services = self.core_v1.list_service_for_all_namespaces().items
            for svc in services:
                for port in svc.spec.ports or []:
                    if port.node_port:
                        used_ports.add(port.node_port)
        except Exception as e:
            logging.error(f"Failed to list services: {e}")
            raise

        for port in range(start, end + 1):
            if port not in used_ports:
                logging.info(f"Selected available nodePort: {port}")
                return port

        raise RuntimeError("No available nodePorts in range 30700–30900")

    def create_redis(self, deployment_name: str, redis_config: list, node_selector: dict = None, node_port: int = None):
        if node_port is None:
            node_port = self.get_available_node_port()

        redis_args = []
        for cmd in redis_config:
            redis_args.extend(["--" + cmd.split()[0], *cmd.split()[1:]])

        # Main Redis container
        redis_container = client.V1Container(
            name="redis",
            image="redis:7.2.4",
            args=redis_args,
            ports=[client.V1ContainerPort(container_port=6379)]
        )

        # Redis Exporter sidecar container
        exporter_container = client.V1Container(
            name="redis-exporter",
            image="oliver006/redis_exporter:v1.61.0",
            env=[
                client.V1EnvVar(name="REDIS_ADDR",
                                value="redis://localhost:6379")
            ],
            ports=[client.V1ContainerPort(container_port=9121)]
        )

        pod_spec = client.V1PodSpec(
            containers=[redis_container, exporter_container])
        if node_selector:
            pod_spec.node_selector = node_selector

        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": deployment_name}),
            spec=pod_spec
        )

        spec = client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(
                match_labels={"app": deployment_name}),
            template=template
        )

        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=deployment_name),
            spec=spec
        )

        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=deployment_name),
            spec=client.V1ServiceSpec(
                type="NodePort",
                selector={"app": deployment_name},
                ports=[
                    client.V1ServicePort(
                        name="redis",
                        port=6379,
                        target_port=6379,
                        node_port=node_port
                    ),
                    client.V1ServicePort(
                        name="metrics",
                        port=9121,
                        target_port=9121
                    )
                ]
            )
        )

        try:
            self.apps_v1.create_namespaced_deployment(
                namespace=self.namespace, body=deployment)
            logging.info(f"Deployment '{deployment_name}' created.")
            self.core_v1.create_namespaced_service(
                namespace=self.namespace, body=service)
            logging.info(
                f"Service '{deployment_name}' created with nodePort {node_port}.")
        except Exception as e:
            logging.error(f"Error creating Redis deployment or service: {e}")
            raise

    def remove_deployment(self, deployment_name: str):
        try:
            self.apps_v1.delete_namespaced_deployment(
                name=deployment_name, namespace=self.namespace)
            logging.info(f"Deployment '{deployment_name}' deleted.")
        except Exception as e:
            logging.warning(
                f"Failed to delete deployment '{deployment_name}': {e}")

        try:
            self.core_v1.delete_namespaced_service(
                name=deployment_name, namespace=self.namespace)
            logging.info(f"Service '{deployment_name}' deleted.")
        except Exception as e:
            logging.warning(
                f"Failed to delete service '{deployment_name}': {e}")



class PersistentDB:
    def __init__(self):
        try:
            config.load_incluster_config()
            logging.info("Using in-cluster Kubernetes configuration.")
        except config.ConfigException:
            config.load_kube_config()
            logging.info("Using local kubeconfig.")

        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.namespace = "framedb-storage"
        self.ensure_namespace()

    def ensure_namespace(self):
        try:
            self.core_v1.read_namespace(self.namespace)
            logging.info(f"Namespace '{self.namespace}' already exists.")
        except Exception:
            ns = client.V1Namespace(
                metadata=client.V1ObjectMeta(name=self.namespace))
            self.core_v1.create_namespace(ns)
            logging.info(f"Namespace '{self.namespace}' created.")

    def get_available_node_port(self, start=30900, end=30999) -> int:
        used_ports = set()
        try:
            services = self.core_v1.list_service_for_all_namespaces().items
            for svc in services:
                for port in svc.spec.ports or []:
                    if port.node_port:
                        used_ports.add(port.node_port)
        except Exception as e:
            logging.error(f"Failed to list services: {e}")
            raise

        for port in range(start, end + 1):
            if port not in used_ports:
                logging.info(f"Selected available nodePort: {port}")
                return port

        raise RuntimeError("No available nodePorts in range 30900–30999")

    def create_tidb(self, deployment_name: str, storage_size: str, node_selector: dict = None, node_port: int = None):
        if node_port is None:
            node_port = self.get_available_node_port()

        pvc_name = f"{deployment_name}-pvc"
        volume_name = f"{deployment_name}-storage"

        pvc = client.V1PersistentVolumeClaim(
            metadata=client.V1ObjectMeta(name=pvc_name),
            spec=client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources=client.V1ResourceRequirements(
                    requests={"storage": storage_size}
                )
            )
        )

        container = client.V1Container(
            name="tidb",
            image="pingcap/tidb:v7.1.0",
            ports=[client.V1ContainerPort(container_port=4000)],
            volume_mounts=[client.V1VolumeMount(
                mount_path="/var/lib/tidb", name=volume_name)]
        )

        pod_spec = client.V1PodSpec(containers=[container])
        if node_selector:
            pod_spec.node_selector = node_selector
        pod_spec.volumes = [client.V1Volume(
            name=volume_name,
            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                claim_name=pvc_name
            )
        )]

        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(labels={"app": deployment_name}),
            spec=pod_spec
        )

        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(name=deployment_name),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(
                    match_labels={"app": deployment_name}),
                template=template
            )
        )

        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=deployment_name),
            spec=client.V1ServiceSpec(
                type="NodePort",
                selector={"app": deployment_name},
                ports=[
                    client.V1ServicePort(
                        name="mysql",
                        port=4000,
                        target_port=4000,
                        node_port=node_port
                    )
                ]
            )
        )

        try:
            self.core_v1.create_namespaced_persistent_volume_claim(
                namespace=self.namespace, body=pvc)
            logging.info(f"PVC '{pvc_name}' created with size {storage_size}.")

            self.apps_v1.create_namespaced_deployment(
                namespace=self.namespace, body=deployment)
            logging.info(f"Deployment '{deployment_name}' created.")

            self.core_v1.create_namespaced_service(
                namespace=self.namespace, body=service)
            logging.info(
                f"Service '{deployment_name}' created with nodePort {node_port}.")

        except Exception as e:
            logging.error(f"Error creating TiDB deployment or service: {e}")
            raise

    def remove_deployment(self, deployment_name: str):
        try:
            self.apps_v1.delete_namespaced_deployment(
                name=deployment_name, namespace=self.namespace)
            logging.info(f"Deployment '{deployment_name}' deleted.")
        except Exception as e:
            logging.warning(
                f"Failed to delete deployment '{deployment_name}': {e}")

        try:
            self.core_v1.delete_namespaced_service(
                name=deployment_name, namespace=self.namespace)
            logging.info(f"Service '{deployment_name}' deleted.")
        except Exception as e:
            logging.warning(
                f"Failed to delete service '{deployment_name}': {e}")

        try:
            pvc_name = f"{deployment_name}-pvc"
            self.core_v1.delete_namespaced_persistent_volume_claim(
                name=pvc_name, namespace=self.namespace)
            logging.info(f"PVC '{pvc_name}' deleted.")
        except Exception as e:
            logging.warning(
                f"Failed to delete PVC '{deployment_name}-pvc': {e}")
