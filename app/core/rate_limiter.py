import os
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

# Use Redis in production, fallback to memory in local dev
redis_url = os.getenv("REDIS_URL")

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=redis_url if redis_url else "memory://",
)

async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom JSON response when someone hits the rate limit."""
    return JSONResponse(
        status_code=429,
        content={"detail": f"Too many login attempts. Please try again later."},
    )