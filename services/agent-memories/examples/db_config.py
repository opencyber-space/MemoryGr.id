"""
Shared DB configuration for all examples.

Defaults point to the NodePort addresses defined in k8s/:
  Postgres  34.93.251.223:30432
  ArangoDB  34.93.251.223:30529
  Weaviate  34.93.251.223:30880

Override any value with environment variables.
"""
import os

from agentic_memory.config import ArangoConfig, MemoryConfig, WeaviateConfig, PostgresConfig, RedisConfig


def make_config(embedding_dim: int = 1536) -> MemoryConfig:
    return MemoryConfig(
        postgres=PostgresConfig(
            host=os.environ.get("POSTGRES_HOST", "34.93.251.223"),
            port=int(os.environ.get("POSTGRES_PORT", "30432")),
            database=os.environ.get("POSTGRES_DB", "agent_memory"),
            username=os.environ.get("POSTGRES_USER", "postgres"),
            password=os.environ.get("POSTGRES_PASSWORD", "postgres"),
        ),
        arango=ArangoConfig(
            url=os.environ.get("ARANGO_URL", "http://34.93.251.223:30529"),
            username=os.environ.get("ARANGO_USER", "root"),
            password=os.environ.get("ARANGO_PASSWORD", "password"),
            database=os.environ.get("ARANGO_DB", "agent_memory"),
        ),
        weaviate=WeaviateConfig(
            host=os.environ.get("WEAVIATE_HOST", "34.93.251.223"),
            port=int(os.environ.get("WEAVIATE_PORT", "30880")),
            grpc_port=int(os.environ.get("WEAVIATE_GRPC_PORT", "30851")),
            embedding_dim=embedding_dim,
        ),
        redis=RedisConfig(
            host=os.environ.get("REDIS_HOST", "34.93.251.223"),
            port=int(os.environ.get("REDIS_PORT", "30637")),
            password=os.environ.get("REDIS_PASSWORD", "r-32344"),
        ),
        embedding_model="text-embedding-3-small",
    )


def make_openai_config() -> MemoryConfig:
    """Alias kept for backward compatibility."""
    return make_config()
