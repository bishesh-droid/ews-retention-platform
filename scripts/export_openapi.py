"""Run after server starts to export the auto-generated OpenAPI schema."""
import httpx
import json
import pathlib


def export_openapi():
    """Export OpenAPI schema from running server."""
    resp = httpx.get("http://localhost:8000/openapi.json", timeout=30)
    resp.raise_for_status()
    schema = resp.json()
    out = pathlib.Path("docs/openapi.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(schema, indent=2))
    print(f"OpenAPI schema exported to {out} ({len(schema['paths'])} paths)")


if __name__ == "__main__":
    export_openapi()
