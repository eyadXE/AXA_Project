# data_extraction_layer/models.py
from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    source: str            # "20_motor.md"
    section_number: str    # "2"
    section_title: str     # "Motor Insurance"
    clause_id: str         # "2.3"
    clause_title: str      # "Wear, tear, and mechanical breakdown"
    line_of_business: str  # "motor"  → lets you filter retrieval by claim type


class Chunk(BaseModel):
    id: str                                   # "clause-2.3"  (deterministic!)
    text: str
    metadata: ChunkMetadata
    vector: list[float] | None = None         # filled later by the embedding step
