from CacheDB import CacheDB
from mongoengine import connect
import os
from dotenv import load_dotenv
from util import cosine_similarity
import numpy as np

def cache_hit(query_embedding, similarity_threshold: float = 0.85):
    load_dotenv()
    connect(host=os.getenv("MONGO_URI"))

    cached_entries = CacheDB.objects(evaluation__in=["good", "neutral"])
    
    if not cached_entries:
        return None, None, 0
    
    best_match = None
    best_similarity = 0.0
    for entry in cached_entries:
        cached_embedding = np.array(entry.embedding, dtype=np.float32)
        similarity = 1-cosine_similarity(query_embedding, cached_embedding)
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = entry
    
    if best_similarity >= similarity_threshold:
        return best_match.answer, best_match.query, best_similarity
    
    return None, None, 0