import grpc
import logging
from concurrent import futures
import os
import uuid

import framedb_pb2
import framedb_pb2_grpc

from .process import set_object
from .process import get_object
from .interfaces.memory import RedisInterface
from .interfaces.storage import TiDBInterface
from .routing import ObjectRoutingClient, StreamRoutingClient
from .cluster_info import FrameDBClusterClient

logger = logging.getLogger("ObjectService")



# Load external clients
cluster_client = FrameDBClusterClient(os.getenv("FRAMEDB_CONFIG_SERVICE", "http://framedb-config:5000"))
object_routing_client = ObjectRoutingClient(os.getenv("ROUTING_SERVICE_URL", "http://routing-service:5000"))
stream_routing_client = StreamRoutingClient(os.getenv("ROUTING_SERVICE_URL", "http://routing-service:5000"))

class ObjectServiceImpl(framedb_pb2_grpc.ObjectServiceServicer):
    def SetObject(self, request, context):
        key = request.object.key.strip()
        if not key:
            key = str(uuid.uuid4())
            logger.info(f"Generated new key for object: {key}")

        obj = {
            "key": key,
            "framedb_id": request.object.framedb_id,
            "data": request.object.data,
            "metadata": request.object.metadata,
            "type": request.object.type
        }

        result = set_object(
            obj=obj,
            cluster_client=cluster_client,
            object_routing_client=object_routing_client,
            stream_routing_client=stream_routing_client
        )

        return framedb_pb2.SetObjectResponse(
            success=result["success"],
            message=f"{result['message']} (key={key})",
        )

    def GetObject(self, request, context):
        result = get_object(
            object_id=request.key,
            cluster_client=cluster_client,
            routing_client=object_routing_client,
            stream_routing_client=stream_routing_client
        )

        if not result["found"]:
            return framedb_pb2.GetObjectResponse(
                found=False,
                message=result["message"]
            )

        obj = result["object"]
        return framedb_pb2.GetObjectResponse(
            found=True,
            object=framedb_pb2.Object(
                key=obj["key"],
                framedb_id=obj["framedb_id"],
                data=obj["data"],
                metadata=obj["metadata"],
                type=obj["type"]
            ),
            message=result["message"]
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    framedb_pb2_grpc.add_ObjectServiceServicer_to_server(ObjectServiceImpl(), server)
    server.add_insecure_port('[::]:50051')
    logger.info("gRPC ObjectService running on port 50051")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    serve()
