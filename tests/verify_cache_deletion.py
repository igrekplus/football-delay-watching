import logging
import os
import json
from pathlib import Path
from src.clients.cache_store import create_cache_store
from src.clients.caching_http_client import create_caching_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_cache_delete():
    # 1. CacheStore direct test
    store = create_cache_store(backend="local")
    test_path = "test_delete.json"
    store.write(test_path, {"test": "data"})
    
    assert store.exists(test_path) == True
    logger.info(f"Cache created: {test_path}")
    
    deleted = store.delete(test_path)
    assert deleted == True
    assert store.exists(test_path) == False
    logger.info(f"Cache deleted successfully via CacheStore")

    # 2. CachingHttpClient test
    client = create_caching_client(backend="local")
    url = "https://example.com/api/test"
    params = {"id": "123"}
    
    # Generate path to check later
    _, cache_path = client.get_cache_path(url, params)
    
    # Write some dummy data to the store at that path to simulate cache
    store.write(cache_path, {"_cached_at": "2026-01-01T00:00:00", "data": "dummy"})
    assert store.exists(cache_path) == True
    logger.info(f"Dummy cache created at: {cache_path}")
    
    # Delete via client
    deleted = client.delete_cache(url, params)
    assert deleted == True
    assert store.exists(cache_path) == False
    logger.info(f"Cache deleted successfully via CachingHttpClient")
    
    print("\nSUCCESS: Cache deletion logic verified.")

if __name__ == "__main__":
    test_cache_delete()
