import json
import hashlib
import pickle
from typing import Any, Optional
from functools import wraps

from app.config import settings


class CacheManager:
    _instance = None
    _redis_client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        if not settings.redis_enabled:
            self._redis_client = None
            return
        
        try:
            import redis
            self._redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=False
            )
            self._redis_client.ping()
        except Exception:
            self._redis_client = None
    
    @property
    def is_available(self) -> bool:
        return self._redis_client is not None
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        raw = f"{prefix}:{args}:{sorted(kwargs.items())}"
        hash_key = hashlib.md5(raw.encode()).hexdigest()
        return f"factor_workbench:{prefix}:{hash_key}"
    
    def get(self, key: str) -> Optional[Any]:
        if not self.is_available:
            return None
        try:
            data = self._redis_client.get(key)
            if data:
                return pickle.loads(data)
        except Exception:
            pass
        return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        if not self.is_available:
            return False
        try:
            if ttl is None:
                ttl = settings.cache_ttl
            self._redis_client.setex(key, ttl, pickle.dumps(value))
            return True
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        if not self.is_available:
            return False
        try:
            self._redis_client.delete(key)
            return True
        except Exception:
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        if not self.is_available:
            return 0
        try:
            keys = self._redis_client.keys(pattern)
            if keys:
                return self._redis_client.delete(*keys)
        except Exception:
            pass
        return 0


cache_manager = CacheManager()


def cached(prefix: str, ttl: int = None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not cache_manager.is_available:
                return func(*args, **kwargs)
            
            cache_key = cache_manager._make_key(prefix, *args, **kwargs)
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator
