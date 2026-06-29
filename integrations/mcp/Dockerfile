# Markovian Provenance MCP server (stdio). Builds a container Glama (and any MCP
# host) can run + introspect: tools markovian_stamp and markovian_verify.
FROM python:3.11-slim
WORKDIR /app
COPY markovian_mcp.py .
RUN pip install --no-cache-dir mcp httpx
CMD ["python", "markovian_mcp.py"]
