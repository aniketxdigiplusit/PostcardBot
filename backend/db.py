import json
import logging
from qdrant_client import QdrantClient, models
from services.hotel import generate_embedding  # assumes OpenAI embed logic is in this file
import uuid

import random



# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COLLECTION_NAME = "postcard-openai"
EMBEDDING_DIM = 1536

qdrant = QdrantClient(host="localhost", port=6333)

# Load JSON data
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Recreate collection if needed
qdrant.recreate_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=models.VectorParams(size=EMBEDDING_DIM, distance=models.Distance.COSINE)
)

# Transform property for Qdrant
def transform_property_data(raw_property):
    name = raw_property.get("name", "").strip()
    intro = raw_property.get("intro", "").strip()
    price = raw_property.get("pricesStartingAt", "")
    best_time = raw_property.get("bestTimetoTravel", "")

    region = raw_property.get("region") or {}
    region_name = region.get("name", "").strip()

    country = raw_property.get("country") or {}
    country_name = country.get("name", "").strip()

    category = raw_property.get("category") or {}
    category_name = category.get("name", "").strip()

    postcards = raw_property.get("postcards", [])
    postcard_objs = []
    postcard_intros = []

    for pc in postcards:
        pc_name = pc.get("name", "")
        pc_intro = pc.get("intro", "")
        postcard_objs.append({"name": pc_name, "intro": pc_intro})
        if pc_intro:
            postcard_intros.append(pc_intro)

    all_tags = [tag.get("name", "") for pc in postcards for tag in pc.get("tags", [])]
    
    
    # Add this near the top if not already
    random_months = ["January", "February", "March", "April", "May", "June", "July", "August","Sepetmber","October","November","December"]
    random_prices = [100, 120, 150, 180, 200, 250]

    # Inside transform_property_data()
    best_time = raw_property.get("bestTimetoTravel", "").strip()
    if not best_time:
        best_time = random.choice(random_months)

    price = raw_property.get("pricesStartingAt", "").strip()
    if not price or not price.replace("$", "").replace(".", "").isdigit():
        price = random.choice(random_prices)
    else:
        price = int(price.replace("$", "").split(".")[0])

    # Embeddings
    name_embedding = generate_embedding(name)
    intro_embedding = generate_embedding(intro)
    location_embedding = generate_embedding(f"{country_name} {region_name}".strip())
    category_embedding = generate_embedding(category_name)
    month_embedding = generate_embedding(best_time) if best_time else []
    activity_embedding = generate_embedding(" ".join(all_tags))
    postcard_embedding = generate_embedding(" ".join(postcard_intros))

    return {
        "id": str(raw_property["id"]),
        "payload": {
            "name": name,
            "intro": intro,
            "region": region_name,
            "country": country_name,
            "price": price,
            "category": category_name,
            "bestTimetoTravel": best_time,
            "postcards": postcard_objs,
            "embedding_name": name_embedding,
            "embedding_intro": intro_embedding,
            "embedding_location": location_embedding,
            "embedding_category": category_embedding,
            "embedding_months": month_embedding,
            "embedding_activities": activity_embedding,
            "embedding_postcards": postcard_embedding
        },
        "vector": name_embedding  # Primary vector
    }

# Upload to Qdrant
for raw in data:
    try:
        prop = transform_property_data(raw)
        qdrant.upsert(
    collection_name=COLLECTION_NAME,
    points=[
        models.PointStruct(
            id=str(uuid.uuid4()),  # ✅ generate a proper UUID
 # ✅ fix: convert ID to string
            vector=prop["vector"],
            payload=prop["payload"]
        )
    ]
)

        logger.info(f"✅ Uploaded: {prop['payload']['name']}")
    except Exception as e:
        logger.warning(f"❌ Failed to upload property {raw.get('name')}: {e}")
