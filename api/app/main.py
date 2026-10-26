from fastapi import FastAPI

from app.routers import auth

app = FastAPI(
    title="Clinique Physio Mont-Royal API",
    version="0.1.0",
)

# Versioned API: every business route lives under /api/v1 (spec section 5).
app.include_router(auth.router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    """Used by the host and monitoring to check the API is up."""
    return {"status": "ok"}
