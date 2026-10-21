# Self-hosted MCP server

Python + official MCP SDK, Streamable HTTP transport, bearer-token auth.

## Run with Docker
    cp .env.example .env        # then set MCP_API_KEY (openssl rand -hex 32)
    docker compose up -d --build
    curl localhost:8000/health   # -> ok

MCP endpoint: `http://localhost:8000/mcp`

## Run without Docker
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    MCP_API_KEY=$(openssl rand -hex 32) python server.py

## Test with the MCP Inspector
    npx @modelcontextprotocol/inspector
Choose "Streamable HTTP", URL `http://localhost:8000/mcp`, and add the header
`Authorization: Bearer <your key>`.

## Connect a client
Apidog:
    claude mcp add --transport http my-server https://mcp.example.com/mcp \
      --header "Authorization: Bearer <your key>"

## Going public
- Put it behind a reverse proxy with HTTPS (Caddy is easiest:
  `mcp.example.com { reverse_proxy localhost:8000 }`). Never expose the key over plain HTTP.
- If requests are rejected with "Invalid Host header", your SDK version has DNS-rebinding
  protection on; allow your domain via `FastMCP(..., transport_security=TransportSecuritySettings(allowed_hosts=[...]))`.
- Apidog custom connectors expect OAuth rather than a static header; for that, add
  the SDK's auth provider support or front the server with an OAuth-capable gateway.

## Adding tools
Decorate a function with `@mcp.tool()` in `server.py`; type hints become the schema
and the docstring becomes the description.
