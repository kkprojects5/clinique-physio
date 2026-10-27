from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.rate_limit import limiter
from app.routers import auth, catalog, me, staff, therapist

app = FastAPI(
    title="Clinique Physio Mont-Royal API",
    version="0.1.0",
)

# Only our own web apps may call the API from a browser, with cookies (NFR-03).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Security headers on every response (NFR-03)."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = response.headers.get("Cache-Control", "no-store")
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Rate limiting: too many requests from one IP address get 429 (NFR-05).
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Versioned API: every business route lives under /api/v1 (spec section 5).
app.include_router(auth.router, prefix="/api/v1")
app.include_router(me.router, prefix="/api/v1")
app.include_router(staff.router, prefix="/api/v1")
app.include_router(catalog.router, prefix="/api/v1")
app.include_router(therapist.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    """Used by the host and monitoring to check the API is up."""
    return {"status": "ok"}
