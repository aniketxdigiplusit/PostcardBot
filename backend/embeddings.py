import json
import torch
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("all-MiniLM-L6-v2")

def load_encoded_vectors(path):
    with open(path, "r") as f:
        data = json.load(f)

    labels = [item["label"] for item in data]
    vectors = [item["vector"] for item in data]

    return labels, torch.tensor(vectors)

def semantic_match(query: str, labels, vectors, top_k=3, threshold=0.5):
    query_vector = model.encode(query, convert_to_tensor=True)
    cosine_scores = util.pytorch_cos_sim(query_vector, vectors)[0]

    top_results = torch.topk(cosine_scores, k=top_k)
    
    matches = []
    for score, idx in zip(top_results.values, top_results.indices):
        if score >= threshold:
            matches.append((labels[idx], float(score)))
    
    return matches

location_labels, location_vectors = load_encoded_vectors("encoded_locations.json")
activity_labels, activity_vectors = load_encoded_vectors("encoded_activities.json")
property_labels, property_vectors = load_encoded_vectors("encoded_properties.json")
