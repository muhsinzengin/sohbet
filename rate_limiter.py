from flask import request, jsonify
from functools import wraps
import time
from collections import defaultdict

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        # Rate limits: (max_requests, window_seconds)
        self.limits = {
            'message': (10, 60),  # 10 messages per minute
            'upload': (5, 300),   # 5 uploads per 5 minutes
            'api': (100, 3600),   # 100 API calls per hour
        }

    def is_allowed(self, key, limit_type='api'):
        now = time.time()
        max_requests, window = self.limits.get(limit_type, (100, 3600))

        # Clean old requests
        self.requests[key] = [req_time for req_time in self.requests[key]
                             if now - req_time < window]

        # Check if under limit
        if len(self.requests[key]) >= max_requests:
            return False

        # Add current request
        self.requests[key].append(now)
        return True

    def get_remaining_time(self, key, limit_type='api'):
        now = time.time()
        _, window = self.limits.get(limit_type, (100, 3600))

        if not self.requests[key]:
            return 0

        oldest_request = min(self.requests[key])
        return max(0, window - (now - oldest_request))

def rate_limit(limit_type='api'):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Get client identifier (IP + user agent for better uniqueness)
            client_key = f"{request.remote_addr}_{request.headers.get('User-Agent', '')}"

            limiter = getattr(wrapper, '_limiter', None)
            if limiter is None:
                limiter = RateLimiter()
                setattr(wrapper, '_limiter', limiter)

            if not limiter.is_allowed(client_key, limit_type):
                remaining_time = limiter.get_remaining_time(client_key, limit_type)
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'retry_after': int(remaining_time),
                    'message': f'Too many requests. Try again in {int(remaining_time)} seconds.'
                }), 429

            return f(*args, **kwargs)
        return wrapper
    return decorator

# Global rate limiter instance
rate_limiter = RateLimiter()
