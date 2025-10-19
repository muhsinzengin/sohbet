import time
import threading
from functools import wraps
from typing import Any, Dict, Optional

class MessageCache:
    """Thread-safe message caching system"""

    def __init__(self, max_size: int = 1000, ttl: int = 300):  # 5 dakika TTL
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired"""
        return time.time() - entry['timestamp'] > self.ttl

    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time - entry['timestamp'] > self.ttl
        ]
        for key in expired_keys:
            del self._cache[key]

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if not self._is_expired(entry):
                    return entry['value']
                else:
                    del self._cache[key]
            return None

    def set(self, key: str, value: Any):
        """Set value in cache"""
        with self._lock:
            # Cleanup expired entries if cache is getting full
            if len(self._cache) >= self.max_size:
                self._cleanup_expired()

            # If still full, remove oldest entries
            if len(self._cache) >= self.max_size:
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k]['timestamp']
                )
                del self._cache[oldest_key]

            self._cache[key] = {
                'value': value,
                'timestamp': time.time()
            }

    def delete(self, key: str):
        """Delete entry from cache"""
        with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()

    def get_thread_messages(self, thread_id: str, limit: int = 50) -> Optional[list]:
        """Get cached messages for a thread"""
        return self.get(f"thread_messages:{thread_id}:{limit}")

    def set_thread_messages(self, thread_id: str, messages: list, limit: int = 50):
        """Cache messages for a thread"""
        self.set(f"thread_messages:{thread_id}:{limit}", messages)

    def invalidate_thread(self, thread_id: str):
        """Invalidate all cache entries for a thread"""
        with self._lock:
            keys_to_delete = [
                key for key in self._cache.keys()
                if f"thread_messages:{thread_id}:" in key
            ]
            for key in keys_to_delete:
                del self._cache[key]

# Global cache instance
message_cache = MessageCache()

def cached_thread_messages(limit: int = 50):
    """Decorator for caching thread messages"""
    def decorator(func):
        @wraps(func)
        def wrapper(thread_id, *args, **kwargs):
            cache_key = f"thread_messages:{thread_id}:{limit}"
            cached_result = message_cache.get(cache_key)

            if cached_result is not None:
                return cached_result

            result = func(thread_id, *args, **kwargs)
            if result:
                message_cache.set(cache_key, result)
            return result
        return wrapper
    return decorator
