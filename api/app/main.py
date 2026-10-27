from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.rate_limit import limiter
from app.routers import auth, me, staff

app = FastAPI(
    title="Clinique Physio Mont-Royal API",
    version="0.1.0",
)

# Rate limiting: too many requests from one IP address get 429 (NFR-05).
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Versioned API: every business route lives under /api/v1 (spec section 5).
app.include_router(auth.router, prefix="/api/v1")
app.include_router(me.router, prefix="/api/v1")
app.include_router(staff.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    """Used by the host and monitoring to check the API is up."""
    return {"status": "ok"}
