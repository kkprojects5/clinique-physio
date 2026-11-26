"""Settings and HTTP protections needed in production (NFR-03)."""

from app.core.config import Settings


def make_settings(**values):
    base = {"database_url": "postgresql://u:p@h/db", "jwt_secret": "x", "field_encryption_key": "k"}
    return Settings(_env_file=None, **{**base, **values})


def test_host_database_urls_get_the_psycopg_driver():
    neon = make_settings(database_url="postgresql://u:p@ep-x.neon.tech/db?sslmode=require")
    heroku_style = make_settings(database_url="postgres://u:p@h/db")
    already = make_settings(database_url="postgresql+psycopg://u:p@h/db")

    assert neon.database_url == "postgresql+psycopg://u:p@ep-x.neon.tech/db?sslmode=require"
    assert heroku_style.database_url.startswith("postgresql+psycopg://")
    assert already.database_url == "postgresql+psycopg://u:p@h/db"


def test_allowed_origins_are_a_comma_separated_list():
    s = make_settings(allowed_origins="https://a.vercel.app, http://localhost:5173")

    assert s.allowed_origin_list == ["https://a.vercel.app", "http://localhost:5173"]


def test_security_headers_on_every_response(client):
    response = client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"


def test_cors_allows_the_web_app_and_refuses_other_sites(client):
    allowed = client.options(
        "/api/v1/services",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    other = client.options(
        "/api/v1/services",
        headers={"Origin": "https://evil.example.com", "Access-Control-Request-Method": "GET"},
    )

    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert allowed.headers.get("access-control-allow-credentials") == "true"
    assert "access-control-allow-origin" not in other.headers


def test_website_csp_only_runs_scripts_from_known_places():
    """Challenge B-C4: even if a script got into the page, the browser refuses to run it.

    No inline script, no eval, no plugins, no framing; scripts only from the site and Stripe.
    """
    import json
    from pathlib import Path

    config = json.loads((Path(__file__).parents[2] / "web" / "vercel.json").read_text("utf-8"))
    headers = {h["key"]: h["value"] for rule in config["headers"] for h in rule["headers"]}
    policy = dict(
        (part.split()[0], part.split()[1:])
        for part in headers["Content-Security-Policy"].split(";")
        if part.strip()
    )

    assert policy["script-src"][0] == "'self'"
    assert all(source.startswith("https://") for source in policy["script-src"][1:])
    assert "'unsafe-inline'" not in policy["script-src"]
    assert "'unsafe-eval'" not in policy["script-src"]
    assert policy["object-src"] == ["'none'"]
    assert policy["frame-ancestors"] == ["'none'"]
    assert policy["base-uri"] == ["'self'"]
