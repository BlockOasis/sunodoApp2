from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from enum import Enum

class Status(str, Enum):
    UNDEFINED = "undefined"
    OPEN = "open"
    DISPUTING = "disputing"
    FINALIZED = "finalized"
    DISPUTED = "disputed"
    VALIDATED = "validated"
    CONTRADICTED = "contradicted"

class User(BaseModel):
    open_claims: Dict[str, None] = Field(default_factory=dict)
    open_disputes: Dict[str, None] = Field(default_factory=dict)
    total_disputes: int
    won_disputes: int
    total_claims: int
    correct_claims: int

class Chunk(BaseModel):
    data: bytes

    def __str__(self):
        return f"{len(self.data)}b"

class DataChunks(BaseModel):
    chunks_data: Dict[int, Chunk]
    total_chunks: int

    def __str__(self):
        size = sum(len(chunk.data) for chunk in self.chunks_data.values())
        chunk_indexes = list(self.chunks_data.keys())
        return f"TotalChunks: {self.total_chunks}, CurrentSize: {size}, Chunks: {chunk_indexes}"

class Claim(BaseModel):
    user_address: str
    disputing_user_address: Optional[str]
    timestamp_of_claim: str
    status: Status
    collateral: int
    compProof: str
    compCID: str
    prepCID: str
    lastUpdated: int

class SimplifiedClaim(BaseModel):
    id: str
    status: Status
    value: int

# New Models
class IoTDevice(BaseModel):
    device_id: str
    location: str
    device_type: str
    owner_wallet: str

class WaterUsageRecord(BaseModel):
    record_id: int
    device_id: str
    timestamp: int
    water_usage: float

class Dispute(BaseModel):
    dispute_id: int
    claim_id: int
    challenger_wallet: str
    reason: str
    status: Status

class ValidatorNode(BaseModel):
    node_id: int
    wallet: str
    reputation: int

class AggregatorNode(BaseModel):
    node_id: int
    wallet: str
    aggregated_records: List[WaterUsageRecord] = []

# Additional classes and functions can be implemented as needed to support operations like CRUD operations, data validation, etc.
