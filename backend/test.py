from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

qdrant = QdrantClient( url="http://localhost:6333")

# Create collection
if qdrant.collection_exists("test"):
    qdrant.delete_collection("test")

qdrant.create_collection(
    collection_name="test",
    vectors_config={
        "my_vector": VectorParams(size=3, distance=Distance.COSINE),
    }
)

# ✅ Correct format using PointStruct
qdrant.upsert(
    collection_name="test",
    points=[
        PointStruct(
            id=1,
            vector={"my_vector": [0.1, 0.2, 0.3]},
            payload={"name": "sample"}
        )
    ]
)

# ✅ Querying it
results = qdrant.query_points(
    collection_name="test",
    query=[0.1, 0.2, 0.3],
    using="my_vector",
    limit=1,
    with_payload=True
)

print(results)
