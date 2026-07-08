import sys
import os
import time

# Ensure backend folder is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.cache import redis_client, SemanticCache


def test_raw_cache_ttl():
    # Set key with 1 second TTL
    redis_client.set("ttl_key", "temporary_val", ttl_secs=1)
    assert redis_client.get("ttl_key") == "temporary_val"

    # Wait for expiry
    time.sleep(1.1)
    assert redis_client.get("ttl_key") is None


def test_semantic_cache_matching():
    cache = SemanticCache()
    # Seed multiple queries to establish document frequency (raising similarity score)
    cache.add("Where is the nearest exit for Section 101?", "Route to Gate A")
    cache.add("How do I find a hot dog stand?", "Route to Food Court")
    cache.add("Is there an accessible toilet near Section 104?", "Route to Restrooms")

    # Exact check
    matched_q, val, similarity = cache.search(
        "Where is the nearest exit for Section 101?"
    )
    assert val == "Route to Gate A"
    assert similarity == 1.0

    # Semantic match
    matched_q, val, similarity = cache.search("Where is nearest exit Section 101?")
    assert val == "Route to Gate A"
    assert similarity >= 0.8


def test_semantic_cache_prefix_isolation():
    cache = SemanticCache()

    # Add identical queries under different prefixes (standard vs. mobility_impaired)
    cache.add("Section_101_Section_201_standard_en_how to go?", "Route Standard Stairs")
    cache.add(
        "Section_101_Section_201_mobility_impaired_en_how to go?",
        "Route Stairs Free Elevator",
    )

    # Query under standard prefix
    matched_q, val, similarity = cache.search(
        query="how to go?", prefix="Section_101_Section_201_standard_en_", threshold=0.8
    )
    assert val == "Route Standard Stairs"

    # Query under mobility_impaired prefix
    matched_q, val, similarity = cache.search(
        query="how to go?",
        prefix="Section_101_Section_201_mobility_impaired_en_",
        threshold=0.8,
    )
    assert val == "Route Stairs Free Elevator"
