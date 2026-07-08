import re
import math
import time
from typing import Dict, Any, Tuple, Optional


def tokenize(text: str) -> list[str]:
    """Tokenizes text and returns lowercase alphanumeric tokens."""
    return re.findall(r"\b\w+\b", text.lower())


class SemanticCache:
    """
    A lightweight, pure-Python Semantic Cache using TF-IDF vectorization,
    Cosine Similarity, and TTL-based expiration support.
    """

    def __init__(self):
        # Maps raw query -> {"value": Any, "expires_at": Optional[float]}
        self.cache: Dict[str, Dict[str, Any]] = {}
        # Maps raw query -> list of tokens
        self.tokenized_cache: Dict[str, list[str]] = {}
        # Document frequencies for IDF calculation
        self.df: Dict[str, int] = {}
        # Total number of documents in the cache
        self.num_docs: int = 0

    def _remove(self, query: str):
        """Internal helper to clean up expired/stale keys and decrement TF-IDF indices."""
        if query in self.cache:
            del self.cache[query]
            tokens = self.tokenized_cache.pop(query, [])
            self.num_docs -= 1
            for token in set(tokens):
                if token in self.df:
                    self.df[token] -= 1
                    if self.df[token] <= 0:
                        del self.df[token]

    def add(self, query: str, value: Any, ttl_secs: Optional[int] = None):
        """Adds a query and its response to the cache, updating TF-IDF indices with an optional TTL."""
        if query in self.cache:
            self._remove(query)

        expires_at = time.time() + ttl_secs if ttl_secs is not None else None

        tokens = tokenize(query)
        self.cache[query] = {"value": value, "expires_at": expires_at}
        self.tokenized_cache[query] = tokens
        self.num_docs += 1

        unique_tokens = set(tokens)
        for token in unique_tokens:
            self.df[token] = self.df.get(token, 0) + 1

    def _calculate_tfidf(self, tokens: list[str]) -> Dict[str, float]:
        """Calculates TF-IDF vector for a list of tokens."""
        vector = {}
        if not tokens:
            return vector

        tf = {}
        for token in tokens:
            tf[token] = tf.get(token, 0.0) + 1.0

        total_tokens = len(tokens)
        for token in tf:
            tf[token] = tf[token] / total_tokens

        for token, tf_val in tf.items():
            df_val = self.df.get(token, 0)
            idf = math.log((1.0 + self.num_docs) / (1.0 + df_val)) + 1.0
            vector[token] = tf_val * idf

        return vector

    def _cosine_similarity(
        self, vec1: Dict[str, float], vec2: Dict[str, float]
    ) -> float:
        """Calculates cosine similarity between two sparse vector dictionaries."""
        dot_product = 0.0
        for token in vec1:
            if token in vec2:
                dot_product += vec1[token] * vec2[token]

        mag1 = math.sqrt(sum(val**2 for val in vec1.values()))
        mag2 = math.sqrt(sum(val**2 for val in vec2.values()))

        if mag1 == 0.0 or mag2 == 0.0:
            return 0.0

        return dot_product / (mag1 * mag2)

    def search(
        self, query: str, prefix: str = "", threshold: float = 0.7
    ) -> Tuple[Optional[str], Optional[Any], float]:
        """
        Searches for a semantically similar query in the cache, optionally filtered by metadata prefix.
        Automatically purges expired keys.
        Returns (matched_query, value, similarity_score).
        """
        if not self.cache:
            return None, None, 0.0

        query_tokens = tokenize(query)
        if not query_tokens:
            return None, None, 0.0

        now = time.time()
        expired_keys = []
        filtered_cache = {}

        # Filter and validate TTL
        for q, tokens in self.tokenized_cache.items():
            if prefix and not q.startswith(prefix):
                continue

            expires_at = self.cache[q]["expires_at"]
            if expires_at is not None and now > expires_at:
                expired_keys.append(q)
                continue

            filtered_cache[q] = tokens

        # Clean up expired documents
        for q in expired_keys:
            self._remove(q)

        if not filtered_cache:
            return None, None, 0.0

        # Exact match check first
        full_query = prefix + query
        if full_query in filtered_cache:
            return full_query, self.cache[full_query]["value"], 1.0

        # Compute TF-IDF of current query
        query_vector = self._calculate_tfidf(query_tokens)

        best_match_query = None
        best_similarity = 0.0

        for cached_q, cached_tokens in filtered_cache.items():
            raw_cached_query = cached_q[len(prefix) :] if prefix else cached_q
            cached_query_tokens = tokenize(raw_cached_query)

            cached_vector = self._calculate_tfidf(cached_query_tokens)
            similarity = self._cosine_similarity(query_vector, cached_vector)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match_query = cached_q

        if best_similarity >= threshold and best_match_query:
            return (
                best_match_query,
                self.cache[best_match_query]["value"],
                best_similarity,
            )

        return None, None, best_similarity


class SimulatedRedis:
    """
    Mock Redis client with performance telemetry tracking and simulated latency/TTLs.
    """

    def __init__(self):
        # Maps key -> {"value": Any, "expires_at": Optional[float]}
        self.raw_kv: Dict[str, Dict[str, Any]] = {}
        self.semantic_cache = SemanticCache()
        self.hits = 0
        self.misses = 0
        self.total_queries = 0

    def get(self, key: str) -> Optional[Any]:
        """Simple key-value lookup with TTL evaluation (simulated 1ms latency)."""
        time.sleep(0.001)
        self.total_queries += 1
        entry = self.raw_kv.get(key)

        if entry is None:
            self.misses += 1
            return None

        # Check Expiration
        expires_at = entry.get("expires_at")
        if expires_at is not None and time.time() > expires_at:
            del self.raw_kv[key]
            self.misses += 1
            return None

        self.hits += 1
        return entry["value"]

    def set(self, key: str, value: Any, ttl_secs: Optional[int] = None):
        """Simple key-value set with optional TTL expiration."""
        expires_at = time.time() + ttl_secs if ttl_secs is not None else None
        self.raw_kv[key] = {"value": value, "expires_at": expires_at}

    def get_semantic(
        self, query: str, prefix: str = "", threshold: float = 0.7
    ) -> Tuple[Optional[Any], bool, float, float]:
        """
        Retrieves matching query semantically, with optional metadata prefix filtering.
        Returns (value, is_hit, similarity, latency_ms).
        """
        start_time = time.time()
        self.total_queries += 1

        matched_q, value, similarity = self.semantic_cache.search(
            query, prefix, threshold
        )

        if value is not None:
            self.hits += 1
            time.sleep(0.003)
            is_hit = True
        else:
            self.misses += 1
            time.sleep(0.025)
            is_hit = False

        latency = (time.time() - start_time) * 1000
        return value, is_hit, similarity, latency

    def set_semantic(self, query: str, value: Any, ttl_secs: Optional[int] = None):
        """Stores query and response semantically in the cache with optional TTL."""
        self.semantic_cache.add(query, value, ttl_secs)

    def get_stats(self) -> Dict[str, Any]:
        """Returns cache execution metrics."""
        hit_ratio = (self.hits / self.total_queries) if self.total_queries > 0 else 0.0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_queries": self.total_queries,
            "hit_ratio": round(hit_ratio, 4),
            "cache_size": self.semantic_cache.num_docs,
        }


# Global singleton
redis_client = SimulatedRedis()
