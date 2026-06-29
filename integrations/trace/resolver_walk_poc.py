#!/usr/bin/env python3
"""
TRACE resolver PoC (data availability).

Same two-door lineage as cross_door_poc, but instead of handing TRACE the payloads in a
local bundle, each stamp's traceable payload is PUBLISHED to the resolver, and the walk
fetches every node ONLY from GET /trace/resolve/{root}. This proves a lineage can be walked
over the network when the verifier was not handed the envelopes. Also proves the resolver
rejects a payload whose hash does not match the committed stamp.
"""
import json, hashlib, httpx

API = "https://api.quantsynth.net"
UA = {"User-Agent": "python-httpx/0.27.0"}

def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()

def stamp(payload, label):
    dh = hashlib.sha256(canon(payload)).hexdigest()
    r = httpx.post(f"{API}/stamp", headers=UA, timeout=30,
                   json={"data_hash": dh, "label": label})
    r.raise_for_status()
    return r.json()

def publish(root, payload):
    return httpx.post(f"{API}/trace/publish", headers=UA, timeout=30,
                      json={"root": root, "payload": payload})

# ---- node A (leaf), node B (derived from A) ----
content_A = {"type": "regime-signal", "ticker": "QQQ", "regime": "DISTRIBUTION", "producer": "agent-alpha"}
payload_A = {"schema": "markovian-provenance/v1", "derived_from": [],
             "body_hash": hashlib.sha256(canon(content_A)).hexdigest(), "produced_by": "a2a"}
sA = stamp(payload_A, "trace-resolver-A")

content_B = {"type": "trade-decision", "ticker": "QQQ", "action": "REDUCE", "producer": "agent-beta"}
payload_B = {"schema": "markovian-provenance/v1",
             "derived_from": [{"merkle_root": sA["merkle_root"], "data_hash": sA["data_hash"],
                               "schema": "markovian-provenance/v1", "relationship": "derivedFrom"}],
             "body_hash": hashlib.sha256(canon(content_B)).hexdigest(), "produced_by": "cloudevents"}
sB = stamp(payload_B, "trace-resolver-B")

# ---- publish both payloads to the resolver ----
pa = publish(sA["merkle_root"], payload_A)
pb = publish(sB["merkle_root"], payload_B)
print("=== TRACE resolver PoC ===")
print("publish A:", pa.status_code, "| publish B:", pb.status_code)

# ---- forged-payload rejection ----
forged = dict(payload_A); forged["body_hash"] = "deadbeef" * 8
fr = publish(sA["merkle_root"], forged)
print("publish forged payload for A:", fr.status_code, "(expected 409)")

# ---- TRACE walk: fetch every node ONLY from the resolver ----
def trace_via_resolver(root, seen=None):
    seen = seen or set()
    if root in seen:
        raise RuntimeError("cycle at " + root)
    seen.add(root)
    rr = httpx.get(f"{API}/trace/resolve/{root}", headers=UA, timeout=20)
    if rr.status_code == 404:
        return {"root": root, "resolved": False, "note": "unresolved frontier"}
    payload = rr.json()["payload"]
    v = httpx.get(f"{API}/verify/{root}", headers=UA, timeout=20).json()
    node = {"root": root, "resolved": True, "door": payload.get("produced_by"),
            "hash_binds": hashlib.sha256(canon(payload)).hexdigest() == v.get("data_hash"),
            "anchored": v.get("verified") is True, "block_height": v.get("block_height"),
            "derived_from": []}
    for ref in payload["derived_from"]:
        pv = httpx.get(f"{API}/verify/{ref['merkle_root']}", headers=UA, timeout=20).json()
        edge_ok = pv.get("data_hash") == ref["data_hash"]
        child = trace_via_resolver(ref["merkle_root"], seen)
        node["derived_from"].append({"relationship": ref["relationship"], "edge_verified": edge_ok, "node": child})
    return node

resolved = trace_via_resolver(sB["merkle_root"])

def ok(n):
    good = n.get("resolved") and n.get("hash_binds") and n.get("anchored")
    for e in n.get("derived_from", []):
        good = good and e["edge_verified"] and ok(e["node"])
    return good

def show(n, i=0):
    pad = "  " * i
    print(f"{pad}- {n.get('door') or '?':<11} {n['root'][:22]}...  resolved={n.get('resolved')} hash_binds={n.get('hash_binds')} anchored={n.get('anchored')}")
    for e in n.get("derived_from", []):
        print(f"{pad}    edge[{e['relationship']}] verified={e['edge_verified']}")
        show(e["node"], i + 2)

print("\nlineage walked entirely from the network resolver:")
show(resolved)
print("\nLINEAGE VALID (resolver-only):", ok(resolved))
assert pa.status_code == 200 and pb.status_code == 200
assert fr.status_code == 409
assert ok(resolved)
print("ALL INVARIANTS HOLD: published lineage resolves + verifies over the network; forged payload rejected (409).")
