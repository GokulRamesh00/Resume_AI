from sentence_transformers import SentenceTransformer
from scipy.spatial.distance import cosine
from typing import List, Tuple
import numpy as np
import pickle
import faiss
import redis
import logging

# Initialize Redis client with error handling
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    # Test the connection
    redis_client.ping()
    redis_connected = True
except redis.exceptions.ConnectionError:
    logging.warning("Redis connection failed. Using fallback in-memory cache.")
    redis_client = None
    redis_connected = False

model = SentenceTransformer('all-MiniLM-L6-v2')

# Fallback in-memory cache
in_memory_cache = {}

class VectorQueryCache:
    def __init__(self, dimension: int, redis_client, model):
        self.redis_client = redis_client
        self.model = model
        self.index = faiss.IndexFlatL2(dimension)
        self.query_keys = []  # To maintain the order of queries
        self.fallback_cache = {}  # Fallback in-memory cache


    def add_to_cache(self, query: str, result: str):
        query_embedding = self.model.encode(query)
        self.index.add(np.array([query_embedding]))
        
        # Generate a unique key for the query
        key = f"query:{len(self.query_keys)}"
        self.query_keys.append(key)
        
        # Store the result in Redis or fallback
        if self.redis_client:
            try:
                self.redis_client.set(key, pickle.dumps(result))
            except:
                # Fallback to in-memory cache if Redis fails
                self.fallback_cache[key] = result
        else:
            # Use in-memory cache
            self.fallback_cache[key] = result


    def get_cached_query_result(self, query: str, k: int = 2, threshold: float = 0.8) -> List[Tuple[str, float]]:
        query_embedding = self.model.encode(query)
        
        # Search the index
        D, I = self.index.search(np.array([query_embedding]), k)
        
        results = []
        for i, (distance, idx) in enumerate(zip(D[0], I[0])):
            if idx != -1:  # Valid index
                similar_query_key = self.query_keys[idx]
                similarity = 1 - (distance / 2)  # Convert L2 distance to similarity
                
                if similarity >= threshold:
                    cached_result = self.get_from_cache(similar_query_key)
                    if cached_result:
                        results.append((cached_result, similarity))
        
        return results

    def get_from_cache(self, key):
        """Retrieve and unpickle a value from Redis or fallback."""
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    return pickle.loads(value)
            except:
                # Fallback to in-memory cache if Redis fails
                if key in self.fallback_cache:
                    return self.fallback_cache[key]
        else:
            # Use in-memory cache
            if key in self.fallback_cache:
                return self.fallback_cache[key]
        return None

def initialize_cache(dimension: int, redis_client, model) -> VectorQueryCache:
    return VectorQueryCache(dimension, redis_client, model)


def store_in_cache(cache: VectorQueryCache, query: str, result: str):
    """Store a value in the Vector Query Cache."""
    try:
        cache.add_to_cache(query, result)
    except Exception as e:
        logging.warning(f"Failed to store in cache: {str(e)}")


def get_cached_query_result(cache: VectorQueryCache, query: str) -> str:
    """Get a cached query result using vector similarity search."""
    try:
        results = cache.get_cached_query_result(query)
        if results:
            best_result, similarity = results[0]  # Get the most similar result
            print(f"Found cached result with similarity: {similarity:.2f}")
            return best_result
    except Exception as e:
        logging.warning(f"Error accessing cache: {str(e)}")
    return None


# Helper function to retrieve or initialize the cache
def retrieve_or_initialize_cache():
    # You might want to store the cache object in a global variable or in Redis itself
    global vector_cache
    if 'vector_cache' not in globals():
        vector_cache = initialize_cache(384, redis_client, model)  # Adjust dimension as needed
    return vector_cache