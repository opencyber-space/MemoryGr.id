"""
Shared fixtures that mock all three backends so no live DB is required.
Each memory store receives: mock_weaviate, mock_arango, mock_postgres, mock_embedder.
"""
import pytest
from unittest.mock import MagicMock

from agentic_memory.config import MemoryConfig
from agentic_memory.embeddings import EmbeddingProvider

DIM = 1536
FAKE_EMBEDDING = [0.1] * DIM


@pytest.fixture
def mock_weaviate():
    m = MagicMock()
    m.search.return_value = []
    return m


@pytest.fixture
def mock_arango():
    m = MagicMock()
    m.get_node.return_value = None
    m.get_related.return_value = []
    m.find_entity_path.return_value = []
    m.search_nodes.return_value = []
    return m


@pytest.fixture
def mock_postgres():
    m = MagicMock()
    m.execute.return_value = []
    m.execute_one.return_value = None
    return m


@pytest.fixture
def mock_embedder():
    e = MagicMock(spec=EmbeddingProvider)
    e.embed.return_value = FAKE_EMBEDDING
    e.embed_batch.return_value = [FAKE_EMBEDDING]
    return e


@pytest.fixture
def config():
    return MemoryConfig()


@pytest.fixture
def store_kwargs(mock_weaviate, mock_arango, mock_postgres, mock_embedder, config):
    return dict(
        weaviate=mock_weaviate,
        arango=mock_arango,
        postgres=mock_postgres,
        embedder=mock_embedder,
        config=config,
    )
