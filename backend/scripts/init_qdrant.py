"""Initialize Qdrant collections for the Caregiver Co-Pilot.

Creates three collections with named vectors (dense + sparse) and payload indexes.
Idempotent: skips collections that already exist.

Usage:
    cd backend && python scripts/init_qdrant.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    SparseVectorParams,
    VectorParams,
    PayloadSchemaType,
)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")

DENSE_DIM = 1024

COLLECTIONS = [
    {
        "name": "document_chunks",
        "payload_index": "care_recipient_id",
        "index_type": PayloadSchemaType.KEYWORD,
    },
    {
        "name": "episode_chunks",
        "payload_index": "care_recipient_id",
        "index_type": PayloadSchemaType.KEYWORD,
    },
    {
        "name": "drug_label_chunks",
        "payload_index": "rxnorm_code",
        "index_type": PayloadSchemaType.KEYWORD,
    },
]


def main() -> None:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)

    existing = {c.name for c in client.get_collections().collections}

    for spec in COLLECTIONS:
        name = spec["name"]
        if name in existing:
            print(f"  [skip] {name} already exists")
            continue

        client.create_collection(
            collection_name=name,
            vectors_config={
                "dense": VectorParams(size=DENSE_DIM, distance=Distance.COSINE),
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(),
            },
        )

        client.create_payload_index(
            collection_name=name,
            field_name=spec["payload_index"],
            field_schema=spec["index_type"],
        )

        print(f"  [created] {name}")

    print("Qdrant collections initialized.")


if __name__ == "__main__":
    main()
