from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class FrameDBCopy:
    framedb_id: str
    framedb_type: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FrameDBCopy':
        return cls(
            framedb_id=data.get('framedb_id', ''),
            framedb_type=data.get('framedb_type', '')
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'framedb_id': self.framedb_id,
            'framedb_type': self.framedb_type
        }


@dataclass
class FrameDBObject:
    object_id: str  # used as MongoDB _id
    framedb_id: str
    copies: List[FrameDBCopy] = field(default_factory=list)
    framedb_type: str = ''
    size: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FrameDBObject':
        copies_data = data.get('copies', [])
        copies = [FrameDBCopy.from_dict(copy) for copy in copies_data]

        return cls(
            object_id=data.get('_id', ''),  # Note: using _id here
            framedb_id=data.get('framedb_id', ''),
            copies=copies,
            framedb_type=data.get('framedb_type', ''),
            size=data.get('size'),
            metadata=data.get('metadata', {})
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            '_id': self.object_id,
            'framedb_id': self.framedb_id,
            'copies': [copy.to_dict() for copy in self.copies],
            'framedb_type': self.framedb_type,
            'size': self.size,
            'metadata': self.metadata
        }


@dataclass
class StreamsObject:
    queue_name: str  
    framedb_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StreamsObject':
        return cls(
            queue_name=data.get('_id', ''),  
            metadata=data.get('metadata', {})
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            '_id': self.queue_name, 
            'framedb_id': self.framedb_id,
            'metadata': self.metadata
        }

