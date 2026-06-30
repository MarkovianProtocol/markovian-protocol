# Root Dockerfile for the Markovian Provenance MCP server, buildable from repo
# root so Glama and other MCP hosts find it with no path config. Mirrors
# integrations/mcp/Dockerfile; builds the stdio server exposing markovian_stamp
# and markovian_verify.
FROM python:3.11-slim
WORKDIR /app
COPY integrations/mcp/markovian_mcp.py .
RUN pip install --no-cache-dir mcp httpx
CMD ["python", "markovian_mcp.py"]
