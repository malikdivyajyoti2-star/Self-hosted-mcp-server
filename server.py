"""Self-hosted MCP server: Streamable HTTP + bearer-token auth."""
import datetime as dt
import hmac
import os
import re
from pathlib import Path

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

API_KEY = os.environ.get("MCP_API_KEY", "")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

mcp = FastMCP("self-hosted-mcp", stateless_http=True)


# ---------- Tools: replace/extend these with your own ----------

@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


@mcp.tool()
def current_time(timezone_offset_hours: float = 0) -> str:
    """Return the current time as ISO-8601, shifted by a UTC offset in hours."""
    tz = dt.timezone(dt.timedelta(hours=timezone_offset_hours))
    return dt.datetime.now(tz).isoformat()


def _note_path(name: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name):
        raise ValueError("Note name must be 1-64 chars: letters, digits, _ or -")
    return DATA_DIR / f"{name}.txt"


@mcp.tool()
def save_note(name: str, content: str) -> str:
    """Save a text note under a name (overwrites if it exists)."""
    _note_path(name).write_text(content, encoding="utf-8")
    return f"Saved note '{name}'."


@mcp.tool()
def read_note(name: str) -> str:
    """Read a previously saved note."""
    p = _note_path(name)
    return p.read_text(encoding="utf-8") if p.exists() else f"No note named '{name}'."


@mcp.tool()
def list_notes() -> list[str]:
    """List all saved note names."""
    return sorted(p.stem for p in DATA_DIR.glob("*.txt"))


# ---------- Resource & prompt examples ----------

@mcp.resource("notes://{name}")
def note_resource(name: str) -> str:
    """Expose a note as an MCP resource."""
    p = _note_path(name)
    return p.read_text(encoding="utf-8") if p.exists() else ""


@mcp.prompt()
def summarize_note(name: str) -> str:
    """Prompt template asking the model to summarize a note."""
    return f"Read the note '{name}' with the read_note tool and summarize it in 3 bullet points."


@mcp.custom_route("/health", methods=["GET"])
async def health(_: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


# ---------- Auth ----------

class BearerAuth:
    """Pure ASGI middleware (safe for streaming responses)."""

    def __init__(self, app):
        self.app = app
        self.expected = f"Bearer {API_KEY}".encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] == "/health":
            return await self.app(scope, receive, send)
        supplied = dict(scope["headers"]).get(b"authorization", b"")
        if not hmac.compare_digest(supplied, self.expected):
            resp = JSONResponse(
                {"error": "unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            return await resp(scope, receive, send)
        await self.app(scope, receive, send)


def main():
    if len(API_KEY) < 16:
        raise SystemExit("Set MCP_API_KEY to a random string of 16+ chars "
                         "(e.g. `openssl rand -hex 32`).")
    app = BearerAuth(mcp.streamable_http_app())  # MCP endpoint served at /mcp
    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
