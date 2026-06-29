# Markovian Provenance over MCP

Draft spec v0.1 (2026-06-28). Status: LIVE. stdio + public Streamable HTTP both proven.
  stdio : ~/markovian/mcp/markovian_mcp.py (proof: test_mcp_stamp.py)
  HTTP  : https://api.quantsynth.net/mcp (proof: test_mcp_http.py) - mounted into
          ~/sigmasynth/api_server.py at /mcp, json_response=True (no SSE, Cloudflare-clean),
          stateless=True, DNS-rebind protection off (intentionally public). Same Server
          instance reused from markovian_mcp.py (no logic duplication).
Built on official MCP Python SDK `mcp` 1.26.0 (neo_env), negotiates protocolVersion 2025-11-25.
Door: MCP (Model Context Protocol, the open standard from Anthropic).
Primitive: one stamp, N envelopes. This is the MCP envelope for `markovian-provenance/v1`.

Semantic invariant (non-negotiable): PROVENANCE, NOT TRUTH. A stamp proves data
was committed at a time on the Markovian chain. It does not assert the data is
correct. Every surface below preserves that line.

---

## 0. Pinned protocol facts

- Current STABLE MCP revision: **2025-11-25**. Source of truth is the TypeScript
  schema at `schema/2025-11-25/schema.ts`. [CONFIRM]
  https://modelcontextprotocol.io/specification/2025-11-25/
  https://github.com/modelcontextprotocol/specification/blob/main/schema/2025-11-25/schema.ts
- Lineage: 2024-11-05 (initial) -> 2025-03-26 -> 2025-06-18 -> 2025-11-25 (current).
  A release candidate 2026-07-28 exists (RC locked 2026-05-21, final publish
  2026-07-28). We pin to 2025-11-25 because it is the shipped stable as of this draft. [CONFIRM]
  https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/
- Transport: JSON-RPC 2.0 over either stdio or Streamable HTTP. Stateful, with
  capability negotiation in `initialize`. [CONFIRM]
  https://modelcontextprotocol.io/specification/2025-11-25/basic
- Roles: Host (LLM app) -> Client (connector) -> Server (capability provider).
  Markovian ships a Server.

---

## 1. Where provenance attaches (candidate surfaces, ranked)

MCP gives a Server three feature classes: **Tools** (model-invocable functions),
**Resources** (addressable data/context), **Prompts** (templated workflows). A
tool result (`CallToolResult`) carries `content[]`, optional `structuredContent`,
optional `isError`, and a reserved `_meta` object. [CONFIRM]
https://modelcontextprotocol.io/specification/2025-11-25/server/tools

Four candidate homes for `markovian-provenance/v1`:

1. **A `markovian_stamp` tool**, agent calls it, gets a stamp back. The stamp IS
   the output, so it belongs in `structuredContent` (+ mirrored TextContent for
   back-compat). USE THIS as the active door.
2. **`_meta` on any tool result**, provenance rides alongside another tool's
   real output without polluting model-facing `content`. This is the convention
   that makes the OTHER N tools carry provenance. USE THIS as the standard.
3. **A provenance resource** (`markovian://verify/{merkle_root}`), addressable,
   re-fetchable proof object. Secondary, nice-to-have.
4. `content[]` text/embedded-resource block, REJECTED as primary. Putting a hash
   blob in `content` dumps it into the LLM context where the model would try to
   reason over a cryptographic commitment. Provenance is machine metadata, not
   model fuel. `_meta` is the semantically correct home.

---

## 2. Recommended integration shape

**Ship BOTH, sequenced. (a) is the vehicle that proves (b).**

- **(a) Markovian MCP Server** exposing a `markovian_stamp` tool (and a
  `markovian_verify` tool + provenance resources). This is concrete, deployable
  now, and mirrors the existing `signal_db_mcp.py` stdio pattern already running
  in the stack. Any MCP client (Claude Desktop, Claude Code, any agent) gains a
  stamp capability with zero bespoke integration.

- **(b) Provenance-on-tool-results convention**, a published rule that ANY MCP
  server MAY attach the `markovian-provenance/v1` object to its tool results under
  a reverse-DNS `_meta` key. This is the actual standards contribution and the
  "N envelopes" move: it lets every tool result in the ecosystem carry verifiable
  provenance, not just Markovian's own.

Why this split, justified against the real schema:

- The stamp tool's output is structured data, so `structuredContent` is its
  correct field; the spec says structured tools SHOULD also serialize JSON into a
  TextContent block for back-compat, which we do. [CONFIRM] /server/tools
- For the convention on OTHER tools, provenance is orthogonal to that tool's
  output, so `_meta` is correct: the spec explicitly defines `_meta` as the
  reserved channel for "additional metadata" that implementations "MUST NOT make
  assumptions about." That is provenance-not-truth encoded at the protocol level.
  [CONFIRM] /basic#_meta
- `_meta` key naming: any prefix whose second label is `modelcontextprotocol` or
  `mcp` is RESERVED. Reverse-DNS is recommended. We own markovianprotocol.com, so
  we use prefix **`com.markovianprotocol/`** with name `provenance` =>
  `com.markovianprotocol/provenance`. This is NOT reserved (second label is
  `markovianprotocol`, not mcp). [CONFIRM] /basic#_meta

---

## 3. The envelope

### 3.1 Canonical inner object (unchanged across all doors)

```json
{
  "schema": "markovian-provenance/v1",
  "merkle_root": "...",
  "data_hash": "...",
  "wallet": "...",
  "zk_commitment": "<BN128 Pedersen point>",
  "block_height": 0,
  "stamped_at": "<ts>",
  "verify": "https://api.quantsynth.net/verify/<merkle_root>",
  "attestation": "provenance-only; proves data was committed at this time, not that it is correct"
}
```

Note: external stamps carry a BN128 Pedersen `zk_commitment` only. There is NO
Schnorr proof and NO `zk_valid` field for external stamps. Do not add either.

### 3.2 `markovian_stamp` tool, definition

```json
{
  "name": "markovian_stamp",
  "title": "Markovian Provenance Stamp",
  "description": "Commit a piece of data to the Markovian chain and return a verifiable provenance stamp. Proves the data existed and was committed at this time. Does NOT assert the data is correct. Burns 1 MKV per call.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "data": {
        "type": "string",
        "description": "The exact bytes/string to stamp. Hashed server-side; the raw data is not stored."
      }
    },
    "required": ["data"],
    "additionalProperties": false
  },
  "outputSchema": {
    "type": "object",
    "properties": {
      "schema":        { "type": "string" },
      "merkle_root":   { "type": "string" },
      "data_hash":     { "type": "string" },
      "wallet":        { "type": "string" },
      "zk_commitment": { "type": "string" },
      "block_height":  { "type": "integer" },
      "stamped_at":    { "type": "string" },
      "verify":        { "type": "string" },
      "attestation":   { "type": "string" }
    },
    "required": ["schema","merkle_root","data_hash","zk_commitment","block_height","stamped_at","verify","attestation"]
  },
  "annotations": {
    "title": "Markovian Provenance Stamp",
    "readOnlyHint": false,
    "destructiveHint": false,
    "idempotentHint": false,
    "openWorldHint": true
  }
}
```

`readOnlyHint:false` and `idempotentHint:false` because a stamp mutates chain
state and burns 1 MKV; each call is a distinct on-chain event. `openWorldHint:true`
because it reaches an external service. [CONFIRM ToolAnnotations fields against
schema.ts] /server/tools

### 3.3 `markovian_stamp` tool, result

The stamp is the output, so it goes in `structuredContent`, is mirrored as a
JSON TextContent block (back-compat per spec), and is ALSO placed in `_meta`
under our reverse-DNS key so a downstream relay can lift it verbatim into the
convention of section 3.4.

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"schema\":\"markovian-provenance/v1\",\"merkle_root\":\"a1b2...\",\"data_hash\":\"9f3c...\",\"wallet\":\"1NeoMKV8...\",\"zk_commitment\":\"(0x12..,0x34..)\",\"block_height\":77810,\"stamped_at\":\"2026-06-28T19:04:11Z\",\"verify\":\"https://api.quantsynth.net/verify/a1b2...\",\"attestation\":\"provenance-only; proves data was committed at this time, not that it is correct\"}"
      }
    ],
    "structuredContent": {
      "schema": "markovian-provenance/v1",
      "merkle_root": "a1b2...",
      "data_hash": "9f3c...",
      "wallet": "1NeoMKV8...",
      "zk_commitment": "(0x12..,0x34..)",
      "block_height": 77810,
      "stamped_at": "2026-06-28T19:04:11Z",
      "verify": "https://api.quantsynth.net/verify/a1b2...",
      "attestation": "provenance-only; proves data was committed at this time, not that it is correct"
    },
    "isError": false,
    "_meta": {
      "com.markovianprotocol/provenance": {
        "schema": "markovian-provenance/v1",
        "merkle_root": "a1b2...",
        "data_hash": "9f3c...",
        "wallet": "1NeoMKV8...",
        "zk_commitment": "(0x12..,0x34..)",
        "block_height": 77810,
        "stamped_at": "2026-06-28T19:04:11Z",
        "verify": "https://api.quantsynth.net/verify/a1b2...",
        "attestation": "provenance-only; proves data was committed at this time, not that it is correct"
      }
    }
  }
}
```

### 3.4 Provenance-on-tool-results convention (the standard)

Any MCP server MAY make its tool outputs verifiable by stamping the serialized
output and attaching the returned envelope to `_meta` under
`com.markovianprotocol/provenance`. The tool's real `content` / `structuredContent`
are untouched. Example: a weather tool that also proves what it returned and when.

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "result": {
    "content": [
      { "type": "text", "text": "{\"temperature\": 22.5, \"conditions\": \"Partly cloudy\"}" }
    ],
    "structuredContent": { "temperature": 22.5, "conditions": "Partly cloudy" },
    "_meta": {
      "com.markovianprotocol/provenance": {
        "schema": "markovian-provenance/v1",
        "merkle_root": "c4d5...",
        "data_hash": "<sha of the serialized output>",
        "wallet": "1NeoMKV8...",
        "zk_commitment": "(0x..,0x..)",
        "block_height": 77811,
        "stamped_at": "2026-06-28T19:06:02Z",
        "verify": "https://api.quantsynth.net/verify/c4d5...",
        "attestation": "provenance-only; proves data was committed at this time, not that it is correct"
      }
    }
  }
}
```

Rule for the convention: `data_hash` MUST be the hash of the EXACT serialized
output bytes the server returned, so a verifier can re-hash `content`/`structuredContent`
and match. The stamp proves "this server emitted these bytes at this time," nothing more.

### 3.5 Provenance resource (secondary)

A Markovian server MAY expose the proof as an addressable resource so clients can
re-fetch it later:

```json
{
  "uri": "markovian://verify/a1b2...",
  "name": "Provenance for a1b2...",
  "title": "Markovian stamp a1b2...",
  "description": "External-stamp provenance record. Provenance, not truth.",
  "mimeType": "application/json"
}
```

`resources/read` returns the `markovian-provenance/v1` object as a
TextResourceContents body (`{uri, mimeType, text}`). [CONFIRM ReadResourceResult
contents shape against schema.ts] /server/resources

### 3.6 `markovian_verify` tool (optional convenience)

Wraps `GET /verify/{merkle_root}`. Input `{ "merkle_root": "..." }`. Returns the
verifier payload `{type:"external_stamp", verified:true, ...}` in `structuredContent`.
Lets an agent confirm a stamp without leaving the MCP session.

### 3.7 How provenance-not-truth is preserved here

- The `attestation` string is carried verbatim in every surface.
- `markovian_stamp` description and the resource description both say "does NOT
  assert the data is correct."
- Placement in `_meta` is itself the message: the spec defines `_meta` as metadata
  clients "MUST NOT make assumptions about." A stamp is metadata about commitment
  time, never a truth claim about the payload.
- No `zk_valid` / no Schnorr proof on external stamps. A verifier confirms the
  commitment exists, not that the committed content is true.

---

## 4. Open schema questions

RESOLVED against the live SDK (mcp 1.26.0, schema 2025-11-25) during the v1 build:

1. RESOLVED. `CallToolResult` fields = `meta` (alias `_meta`), `content`,
   `structuredContent`, `isError`. `_meta` carried end-to-end to an MCP client.
   GOTCHA: the SDK silently drops a `meta=` constructor kwarg (no populate_by_name);
   set `.meta` by attribute so it serializes as `_meta`.
2. RESOLVED. `ToolAnnotations` accepts title, readOnlyHint, destructiveHint,
   idempotentHint, openWorldHint (all used in markovian_stamp).
3. RESOLVED. `structuredContent` present and round-trips in 2025-11-25.

Still open:
4. [CONFIRM] `ReadResourceResult.contents[]` shape (TextResourceContents vs
   BlobResourceContents) and whether resources accept a custom URI scheme
   (`markovian://`) without registration.
5. [CONFIRM] Whether `_meta` is permitted on the `structuredContent` sub-object or
   only on the top-level result (we only use top-level result `_meta`, which is safe).
6. [CONFIRM] `execution.taskSupport` semantics if we later make stamping a Task
   (async call-now/fetch-later) primitive added in 2025-11-25.
7. Decide whether to ALSO target the 2026-07-28 RC once final (it carries `_meta`
   on `tools/call` params + richer CallToolResult `_meta` control). Re-pin after publish.

---

## 5. Build / deploy on Neo

The stamp already exists: `POST https://api.quantsynth.net/stamp` (FastAPI
`api_server.py` on Neo, port 8001, behind cloudflared, keyless free tier, burns
1 MKV). The MCP server is a thin wrapper over it. Two transports:

- **stdio (ship first):** `~/markovian/mcp/markovian_mcp.py`. Single-file
  JSON-RPC-over-stdin loop, exact pattern of `~/.claude/signal_db_mcp.py`. Calls
  `POST /stamp` with httpx, reshapes the response into the section 3.3 result.
  Drop-in for Claude Desktop / Claude Code via `~/.claude.json` mcpServers.
- **Streamable HTTP (ship second, for remote agents):** mount an MCP ASGI app
  into the existing `api_server.py` at `https://api.quantsynth.net/mcp`, reusing
  the live cloudflared tunnel. This is the agent-economy reach play. Note:
  Streamable HTTP is the current HTTP transport; the old HTTP+SSE (2024-11-05) is
  deprecated, do not build on SSE-only. [CONFIRM transport status] /basic

Files to create:
- `~/markovian/mcp/markovian_mcp.py` (stdio reference server)
- `~/markovian/mcp/http_app.py` OR a `/mcp` mount added to `api_server.py`
- `~/markovian/mcp/test_mcp_stamp.py` (end-to-end proof, section 6)

SDK: use the official MCP Python SDK (`mcp`, FastMCP high-level API) for the HTTP
server so transport/lifecycle is handled. The stdio reference can stay
dependency-light (raw JSON-RPC loop) to match the existing house pattern, or use
FastMCP for less code. Pin protocolVersion `2025-11-25` in `initialize` (the
existing signal-db server still reports `2024-11-05`; the new server should
advertise current). [CONFIRM SDK supports 2025-11-25]

Pattern reference already in stack: `~/.claude/signal_db_mcp.py` (stdio),
plus market_data/tastytrade/ntfy/neo/google MCP servers in `~/.claude/`.

---

## 6. Launch checklist + proof test

1. Confirm `POST /stamp` live: `curl -s -X POST https://api.quantsynth.net/stamp
   -H 'content-type: application/json' -d '{"data":"mcp-smoke-test"}'` returns
   merkle_root + block_height.
2. Write `markovian_mcp.py` (stdio), reshape `/stamp` -> section 3.3 result.
3. Register in `~/.claude.json` under mcpServers as `markovian` ->
   `python3 ~/markovian/mcp/markovian_mcp.py`.
4. Restart MCP host; confirm `tools/list` shows `markovian_stamp` (+ verify).
5. PROOF TEST (`test_mcp_stamp.py`): spawn the server, send `initialize`, then
   `tools/call markovian_stamp {"data":"hello provenance"}`. Assert the result has
   `structuredContent.merkle_root` and `_meta["com.markovianprotocol/provenance"]`.
6. END-TO-END VERIFY: take the returned `merkle_root`, `GET
   https://api.quantsynth.net/verify/{merkle_root}`, assert
   `{type:"external_stamp", verified:true}`. Stamp -> tool -> verify, closed loop.
7. (Phase 2) Mount `/mcp` Streamable HTTP on api_server.py; repeat proof test
   against the remote URL with an MCP HTTP client.

One-line success criterion: an MCP client calls `markovian_stamp`, gets a real
chain stamp, and the `merkle_root` verifies true at `/verify` without any other tooling.

---

## 7. External dependencies / blockers

- Official MCP Python SDK version that supports 2025-11-25 (for the HTTP server).
  stdio reference has no hard dep beyond httpx.
- Transport choice: stdio reaches local hosts (Claude Desktop/Code) immediately;
  remote agents need the Streamable HTTP mount + tunnel (already exists).
- Client adoption of the `_meta` convention (section 3.4) is out of our control;
  the stamp tool (3.2) works regardless and seeds the pattern.
- `com.markovianprotocol/` prefix depends on us keeping markovianprotocol.com (we
  do, registered Cloudflare Jun 18 2026).
- No registry listing yet (e.g. the public MCP server directory); discovery is a
  later growth lever, not a launch blocker.

---

## 8. Source list

- https://modelcontextprotocol.io/specification/2025-11-25/
- https://modelcontextprotocol.io/specification/2025-11-25/basic
- https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- https://github.com/modelcontextprotocol/specification/blob/main/schema/2025-11-25/schema.ts
- https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/
- https://github.com/modelcontextprotocol/python-sdk
