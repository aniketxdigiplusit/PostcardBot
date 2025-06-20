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

qdrant = QdrantClient(host="13.201.222.193", port=6333)

# Load JSON data
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Recreate collection (new method)
if qdrant.collection_exists(COLLECTION_NAME):
    qdrant.delete_collection(collection_name=COLLECTION_NAME)

qdrant.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=models.VectorParams(size=EMBEDDING_DIM, distance=models.Distance.COSINE)
)

# Random fallback data
random_months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
random_prices = [100, 120, 150, 180, 200, 250]

# Transform property for Qdrant
def transform_property_data(raw_property):
    name = (raw_property.get("name") or "").strip()
    intro = (raw_property.get("intro") or "").strip()
    price = (raw_property.get("pricesStartingAt") or "").strip()
    best_time = (raw_property.get("bestTimetoTravel") or "").strip()

    region = raw_property.get("region") or {}
    region_name = (region.get("name") or "").strip()

    country = raw_property.get("country") or {}
    country_name = (country.get("name") or "").strip()

    category = raw_property.get("category") or {}
    category_name = (category.get("name") or "").strip()

    postcards = raw_property.get("postcards", [])
    postcard_objs = []
    postcard_intros = []
    postcard_stories = []

    all_tags = []  # To store activities and tags

    # Extract postcard data (including story tags)
    for pc in postcards:
        pc_name = (pc.get("name") or "").strip()
        pc_intro = (pc.get("intro") or "").strip()
        pc_story = (pc.get("story") or "").strip()  # story added
        postcard_objs.append({"name": pc_name, "intro": pc_intro, "story": pc_story})
        if pc_intro:
            postcard_intros.append(pc_intro)
        if pc_story:
            postcard_stories.append(pc_story)

        # Collect activities from tags
        all_tags.extend([tag.get("name", "") for tag in pc.get("tags", [])])

    # Apply fallback logic for missing data
    if not best_time:
        best_time = random.choice(random_months)

    if not price or not price.replace("$", "").replace(".", "").isdigit():
        price = random.choice(random_prices)
    else:
        price = int(price.replace("$", "").split(".")[0])

    # Embeddings for name, intro, location, category, best_time, activity, postcards, and story
    name_embedding = generate_embedding(name)
    intro_embedding = generate_embedding(intro)
    location_embedding = generate_embedding(f"{country_name} {region_name}".strip())
    category_embedding = generate_embedding(category_name)
    month_embedding = generate_embedding(best_time)
    activity_embedding = generate_embedding(" ".join(all_tags))
    postcard_intro_embedding = generate_embedding(" ".join(postcard_intros))
    postcard_story_embedding = generate_embedding(" ".join(postcard_stories))  # added embedding for stories
    price_embedding = generate_embedding(str(price))  # Embedding for price
    best_time_embedding = generate_embedding(best_time)  # Embedding for bestTimeToTravel

    return {
        "id": str(raw_property.get("id", uuid.uuid4())),
        "payload": {
            "name": name,
            "intro": intro,
            "region": region_name,
            "country": country_name,
            "price": price,
            "category": category_name,
            "bestTimetoTravel": best_time,
            "postcards": postcard_objs,
            "activities": list(set(all_tags)),  # Activities added
            "experiences": postcard_intros,  # Experiences added
            "embedding_name": name_embedding,
            "embedding_intro": intro_embedding,
            "embedding_location": location_embedding,
            "embedding_category": category_embedding,
            "embedding_months": month_embedding,
            "embedding_activities": activity_embedding,
            "embedding_postcards": postcard_intro_embedding,
            "embedding_story": postcard_story_embedding,  # embedding for story
            "embedding_price": price_embedding,  # embedding for price
            "embedding_best_time": best_time_embedding  # embedding for bestTimeToTravel
        },
        "vector": name_embedding  # Primary vector
    }

# Upload to Qdrant
for raw in data:
    try:
        prop = transform_property_data(raw)
        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=[models.PointStruct(
                id=str(uuid.uuid4()),  # Always a new unique UUID
                vector=prop["vector"],
                payload=prop["payload"]
            )]
        )
        logger.info(f"✅ Uploaded: {prop['payload']['name']}")
    except Exception as e:
        logger.warning(f"❌ Failed to upload property {raw.get('name')}: {e}")
