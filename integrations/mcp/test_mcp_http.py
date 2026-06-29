#!/usr/bin/env python3
"""Public end-to-end proof for the Markovian MCP door over Streamable HTTP.

Connects a real MCP Streamable-HTTP client to the PUBLIC url
https://api.quantsynth.net/mcp (through Cloudflare, not localhost), runs the
handshake, lists tools, calls markovian_stamp for a REAL chain stamp, and
independently cross-checks /verify.
"""
import json

import anyio
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = "https://api.quantsynth.net/mcp"
WALLET = "135nd7CXWJ8QRjuCDkXoM5oxx9MKc7YNjN"


def line(t):
    print("\n" + "=" * 70 + f"\n{t}\n" + "=" * 70)


async def main():
    async with streamablehttp_client(URL) as (read, write, _get_sid):
        async with ClientSession(read, write) as session:
            line("1. INITIALIZE (public, via Cloudflare)")
            init = await session.initialize()
            print("negotiated protocolVersion:", init.protocolVersion)
            print("serverInfo:", init.serverInfo.model_dump())

            line("2. tools/list")
            tools = await session.list_tools()
            for t in tools.tools:
                print(f"  - {t.name}: {t.title}")

            line("3. tools/call markovian_stamp {data:'mcp-http-proof', wallet:135nd7...}")
            res = await session.call_tool(
                "markovian_stamp", {"data": "mcp-http-proof", "wallet": WALLET}
            )
            print("isError:", res.isError)
            print("\n-- structuredContent --")
            print(json.dumps(res.structuredContent, indent=2))
            print("\n-- result _meta --")
            print(json.dumps(res.meta, indent=2))
            root = res.structuredContent["merkle_root"]
            meta_root = res.meta["com.markovianprotocol/provenance"]["merkle_root"]
            print("\nstructuredContent.merkle_root == _meta.merkle_root :", root == meta_root)
            print("block_height:", res.structuredContent["block_height"])

            line("4. INDEPENDENT cross-check: GET /verify/<merkle_root>")
            vr = httpx.get(f"https://api.quantsynth.net/verify/{root}", timeout=30).json()
            print(json.dumps(vr, indent=2))
            print("\nPASS:", vr.get("type") == "external_stamp" and vr.get("verified") is True)


if __name__ == "__main__":
    anyio.run(main)
