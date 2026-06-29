#!/usr/bin/env python3
"""markovian_mcp - MCP door (v1, stdio) for the Markovian provenance stamp.

One stamp, N envelopes. This is the MCP envelope: a stdio Model Context Protocol
server (official SDK) that exposes the live Markovian STAMP to any MCP client/agent.

Tools:
  markovian_stamp(data, wallet, label?) -> commit `data` to the Markovian chain
      (POST /stamp, burns 1 MKV) and return the canonical markovian-provenance/v1
      object in structuredContent, mirrored as a JSON TextContent block, AND under
      result _meta key "com.markovianprotocol/provenance".
  markovian_verify(merkle_root)          -> independent GET /verify/{root} lookup.

Trust model: a stamp proves data was COMMITTED at a time, NOT that it is correct.
PROVENANCE, NOT TRUTH. External stamps carry a BN128 Pedersen commitment only -
there is no Schnorr proof and no zk_valid field. Verifiers derive trust from the
public /verify endpoint, never from this server's say-so.

Pattern reference: ~/markovian/a2a/markovian_a2a.py (stamp assembly) and the
house stdio MCP servers in ~/.claude/.
"""
import json

import anyio
import httpx
from mcp.server.lowlevel import Server
import mcp.types as types

API_BASE = "https://api.quantsynth.net"
SCHEMA = "markovian-provenance/v1"
ATTESTATION = "provenance-only; proves data was committed at this time, not that it is correct"
PROV_KEY = "com.markovianprotocol/provenance"  # reserved-safe _meta key (reverse-DNS)
TIMEOUT = 30.0

server = Server("markovian", version="0.1.0")


# ── core: live stamp + canonical assembly (mirrors the A2A door) ──────────────
def stamp_output(data: str, wallet: str, label=None) -> dict:
    """POST /stamp and assemble the canonical markovian-provenance/v1 object.

    GOTCHA: the /stamp response omits schema/wallet/attestation - inject them.
    httpx default User-Agent avoids the Cloudflare 403 on api.quantsynth.net.
    """
    resp = httpx.post(
        f"{API_BASE}/stamp",
        json={"wallet": wallet, "data": data, "label": label},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    s = resp.json()
    merkle_root = s["merkle_root"]
    return {
        "schema": SCHEMA,                                   # injected
        "merkle_root": merkle_root,
        "data_hash": s["data_hash"],
        "wallet": wallet,                                   # injected
        "zk_commitment": s.get("zk_commitment"),
        "block_height": s.get("block_height"),
        "stamped_at": str(s.get("stamped_at")),
        "verify": s.get("verify_url") or f"{API_BASE}/verify/{merkle_root}",
        "attestation": ATTESTATION,                         # injected
    }


def verify_root(merkle_root: str) -> dict:
    """Independent existence + commitment lookup against the public verifier."""
    try:
        r = httpx.get(f"{API_BASE}/verify/{merkle_root}", timeout=TIMEOUT)
    except Exception as e:  # noqa: BLE001
        return {"verified": False, "error": str(e), "merkle_root": merkle_root}
    if r.status_code != 200:
        return {"verified": False, "status": r.status_code, "merkle_root": merkle_root}
    try:
        return r.json()
    except Exception as e:  # noqa: BLE001
        return {"verified": False, "error": f"non-json verifier response: {e}",
                "merkle_root": merkle_root}


# ── tool definitions ──────────────────────────────────────────────────────────
_STAMP_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "schema": {"type": "string"},
        "merkle_root": {"type": "string"},
        "data_hash": {"type": "string"},
        "wallet": {"type": "string"},
        "zk_commitment": {"type": ["string", "null"]},
        "block_height": {"type": ["integer", "null"]},
        "stamped_at": {"type": "string"},
        "verify": {"type": "string"},
        "attestation": {"type": "string"},
    },
    "required": ["schema", "merkle_root", "data_hash", "wallet",
                 "stamped_at", "verify", "attestation"],
}

TOOLS = [
    types.Tool(
        name="markovian_stamp",
        title="Markovian Provenance Stamp",
        description=(
            "Commit a piece of data to the Markovian chain and return a verifiable "
            "provenance stamp (canonical markovian-provenance/v1). Proves the data "
            "existed and was committed at this time. Does NOT assert the data is "
            "correct. Burns 1 MKV per call."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "data": {"type": "string",
                         "description": "Exact bytes/string to stamp. Hashed server-side; raw data is not stored."},
                "wallet": {"type": "string",
                           "description": "MKV wallet that pays the 1 MKV burn and is recorded as committer."},
                "label": {"type": "string",
                          "description": "Optional human label for the stamp."},
            },
            "required": ["data", "wallet"],
            "additionalProperties": False,
        },
        outputSchema=_STAMP_OUTPUT_SCHEMA,
        annotations=types.ToolAnnotations(
            title="Markovian Provenance Stamp",
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    ),
    types.Tool(
        name="markovian_verify",
        title="Markovian Verify",
        description=(
            "Independently verify a Markovian stamp by merkle_root via the public "
            "verifier. Returns the verifier payload (type:external_stamp, verified:bool). "
            "An unknown/edited root returns verified:false."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "merkle_root": {"type": "string", "description": "merkle_root to verify."},
            },
            "required": ["merkle_root"],
            "additionalProperties": False,
        },
        annotations=types.ToolAnnotations(
            title="Markovian Verify",
            readOnlyHint=True,
            openWorldHint=True,
        ),
    ),
]


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> types.CallToolResult:
    try:
        if name == "markovian_stamp":
            obj = await anyio.to_thread.run_sync(
                lambda: stamp_output(arguments["data"], arguments["wallet"],
                                     arguments.get("label"))
            )
            result = types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(obj))],
                structuredContent=obj,
                isError=False,
            )
            # NOTE: the SDK silently drops a `meta=` constructor kwarg (no
            # populate_by_name); set the field by attribute so it serializes as _meta.
            result.meta = {PROV_KEY: obj}
            return result

        if name == "markovian_verify":
            vr = await anyio.to_thread.run_sync(
                lambda: verify_root(arguments["merkle_root"])
            )
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=json.dumps(vr))],
                structuredContent=vr,
                isError=False,
            )

        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Unknown tool: {name}")],
            isError=True,
        )
    except Exception as e:  # noqa: BLE001
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Error: {e}")],
            isError=True,
        )


async def main():
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    anyio.run(main)
