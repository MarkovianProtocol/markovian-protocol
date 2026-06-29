"""
demo_consumer, REAL A2A client that drives the Markovian provenance door end-to-end.

Single command:  /Users/colinwinter/neo_env/bin/python3 demo_consumer.py
It starts demo_agent.py (127.0.0.1:8090), sends an A2A task with the A2A-Extensions
request header set to the extension URI, receives the artifact, extracts
metadata[URI], verifies it end-to-end (binding + independent /verify), and runs a
tamper check. Prints a clear PASS/FAIL block. Tears the agent down on exit.
"""

import asyncio
import os
import subprocess
import sys
import time
import uuid

sys.path.insert(0, "/Users/colinwinter/markovian/a2a")

import httpx
from google.protobuf.json_format import MessageToDict

import a2a.types as T
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory, ClientCallContext

import markovian_a2a as mp

PY = "/Users/colinwinter/neo_env/bin/python3"
AGENT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_agent.py")
BASE = "http://127.0.0.1:8090"
CARD_PATH = "/.well-known/agent-card.json"


def _start_agent():
    proc = subprocess.Popen([PY, AGENT], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    # Poll the AgentCard endpoint until the server is up.
    for _ in range(40):
        try:
            r = httpx.get(BASE + CARD_PATH, timeout=2.0)
            if r.status_code == 200:
                return proc
        except Exception:
            pass
        if proc.poll() is not None:
            out = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(f"agent exited early:\n{out}")
        time.sleep(0.5)
    raise RuntimeError("agent did not become ready on 127.0.0.1:8090")


def _extract_artifact(responses):
    """Pull the first Artifact (with metadata) out of the A2A stream responses."""
    for resp in responses:
        if resp.HasField("artifact_update") and resp.artifact_update.HasField("artifact"):
            return resp.artifact_update.artifact
        if resp.HasField("task"):
            if resp.task.artifacts:
                return resp.task.artifacts[0]
    return None


async def run():
    async with httpx.AsyncClient(timeout=60.0) as hx:
        # Wire the A2A-Extensions activation header onto every outbound request.
        hx.headers["A2A-Extensions"] = mp.EXT_URI

        card = await A2ACardResolver(hx, BASE).get_agent_card()
        declared = [e.uri for e in card.capabilities.extensions]
        print(f"[consumer] agent card extensions declared: {declared}")

        client = ClientFactory(ClientConfig(httpx_client=hx, streaming=False)).create(card)

        msg = T.Message(
            message_id=str(uuid.uuid4()),
            role=T.Role.ROLE_USER,
            parts=[T.Part(text="What is the current QQQ regime?")],
            extensions=[mp.EXT_URI],
        )
        req = T.SendMessageRequest(message=msg)
        ctx = ClientCallContext(service_parameters={"A2A-Extensions": mp.EXT_URI})

        responses = [r async for r in client.send_message(req, context=ctx)]
        await client.close()

        artifact = _extract_artifact(responses)
        if artifact is None:
            print("FAIL: no artifact returned")
            return False

        # Recover the stamped bytes (the Part text) and the provenance metadata.
        raw = artifact.parts[0].text if artifact.parts else ""
        md = MessageToDict(artifact.metadata) if artifact.metadata else {}
        obj = md.get(mp.EXT_URI)
        if obj is None:
            print(f"FAIL: artifact carried no provenance under {mp.EXT_URI}; metadata={md}")
            return False
        # block_height comes back float-coerced through the Struct; tidy for display.
        if isinstance(obj.get("block_height"), float) and obj["block_height"].is_integer():
            obj["block_height"] = int(obj["block_height"])

        print("\n=== Artifact.metadata[\"" + mp.EXT_URI + "\"] ===")
        import json as _j
        print(_j.dumps(obj, indent=2))

        # End-to-end verify (binding + independent /verify).
        result = mp.verify(obj, raw)
        print("\n=== verify() result ===")
        print(_j.dumps({k: v for k, v in result.items() if k != "verify_response"}, indent=2))
        print("independent /verify response:", _j.dumps(result.get("verify_response", {})))

        ok = result["transport_ok"] and result["stamp_verified"] and result["binding_ok"]

        # Tamper check: mutate the artifact bytes -> binding must fail.
        print("\n=== TAMPER CHECK (mutate artifact bytes) ===")
        tampered = mp.verify(obj, raw + "X")
        print(_j.dumps({k: tampered[k] for k in ("transport_ok", "stamp_verified", "binding_ok")}, indent=2))
        tamper_caught = (tampered["binding_ok"] is False)

        # Second tamper: mutate data_hash -> stamp_verified must fail.
        print("=== TAMPER CHECK (mutate data_hash) ===")
        bad = dict(obj); bad["data_hash"] = "0" * 64
        bad["verify"] = f"{mp.API_BASE}/verify/{bad['merkle_root']}"
        tampered2 = mp.verify(bad, raw)
        print(_j.dumps({k: tampered2[k] for k in ("transport_ok", "stamp_verified", "binding_ok")}, indent=2))
        tamper2_caught = (tampered2["stamp_verified"] is False)

        print("\n" + "=" * 60)
        if ok and tamper_caught and tamper2_caught:
            print("RESULT: PASS , A2A artifact carried a real Markovian stamp,")
            print(f"        merkle_root={obj['merkle_root']}")
            print(f"        block_height={obj['block_height']}  stamp_verified=True  binding_ok=True")
            print("        tamper rejected on both bytes and data_hash.")
            print("=" * 60)
            return True
        print("RESULT: FAIL")
        print(f"  happy_path_ok={ok} tamper_bytes_caught={tamper_caught} tamper_hash_caught={tamper2_caught}")
        print("=" * 60)
        return False


def main():
    proc = _start_agent()
    try:
        ok = asyncio.run(run())
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
