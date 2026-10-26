from fastapi import FastAPI

app = FastAPI(
    title="Clinique Physio Mont-Royal API",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Used by the host and monitoring to check the API is up."""
    return {"status": "ok"}
