#!/usr/bin/env python3
"""
TRACE cross-door PoC.

Node A (a leaf) rides inside an A2A artifact. Node B (derived from A) rides inside a CloudEvent.
B references A IN-BAND: A's full ParentRef is inside the bytes B commits to, so the edge is
tamper-evident. TRACE then walks B -> A ACROSS the two different doors and verifies, for each
node, that (1) the payload carried in the envelope hashes to the on-chain data_hash (edge is in
the pre-image) and (2) the stamp is Bitcoin-anchored; and for each edge, that the claimed parent
matches the real parent's on-chain content.

This is the defensible novelty claim made runnable: one provenance graph spanning unmodified
protocol envelopes, edges bound in-band, every node independently Bitcoin-anchored.
"""
import json, hashlib, uuid, datetime, httpx
from cloudevents.core.v1.event import CloudEvent
from cloudevents.core.formats.json import JSONFormat

API = "https://api.quantsynth.net"
UA = {"User-Agent": "python-httpx/0.27.0"}

def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()

def stamp(payload, label):
    """Commit the canonical payload by passing its sha256 as data_hash (passthrough)."""
    dh = hashlib.sha256(canon(payload)).hexdigest()
    r = httpx.post(f"{API}/stamp", headers=UA, timeout=30,
                   json={"data_hash": dh, "label": label})
    r.raise_for_status()
    return r.json()

def record(s):
    return {
        "schema": "markovian-provenance/v1",
        "merkle_root": s["merkle_root"], "data_hash": s["data_hash"],
        "wallet": s.get("wallet"), "zk_commitment": s.get("zk_commitment"),
        "block_height": s.get("block_height"), "stamped_at": str(s.get("stamped_at")),
        "verify": s.get("verify_url") or f"{API}/verify/{s['merkle_root']}",
    }

# ============ NODE A: leaf, carried in an A2A artifact ============
content_A = {"type": "regime-signal", "ticker": "QQQ", "regime": "DISTRIBUTION",
             "asof": "2026-06-29T16:00:00Z", "producer": "agent-alpha"}
payload_A = {
    "schema": "markovian-provenance/v1",
    "parents": [],
    "body_hash": hashlib.sha256(canon(content_A)).hexdigest(),
    "produced_by": "a2a",
}
recA = record(stamp(payload_A, "trace-poc-A-a2a"))

a2a_artifact = {
    "artifactId": "regime-signal-" + recA["data_hash"][:12],
    "name": "regime-signal",
    "extensions": ["https://api.quantsynth.net/a2a/ext/provenance/v1"],
    "parts": [{"kind": "text", "text": canon(content_A).decode()}],
    "metadata": {
        "provenance_ref": recA,
        "trace_payload": payload_A,   # the pre-image, so a consumer can recompute the hash
    },
}

# ============ NODE B: derives from A, carried in a CloudEvent ============
content_B = {"type": "trade-decision", "ticker": "QQQ", "action": "REDUCE",
             "rationale": "distribution regime observed by agent-alpha",
             "asof": "2026-06-29T16:05:00Z", "producer": "agent-beta"}
payload_B = {
    "schema": "markovian-provenance/v1",
    "parents": [
        {"merkle_root": recA["merkle_root"], "data_hash": recA["data_hash"],
         "schema": "markovian-provenance/v1", "relationship": "derivedFrom"}
    ],
    "body_hash": hashlib.sha256(canon(content_B)).hexdigest(),
    "produced_by": "cloudevents",
}
recB = record(stamp(payload_B, "trace-poc-B-cloudevents"))

ce = CloudEvent({
    "id": str(uuid.uuid4()),
    "source": "https://markovianprotocol.com/agent-beta",
    "type": "com.markovianprotocol.agent.output",
    "specversion": "1.0",
    "time": datetime.datetime(2026, 6, 29, 16, 5, 0, tzinfo=datetime.timezone.utc),
    "datacontenttype": "application/json",
    "markovianroot": recB["merkle_root"],
    "markovianverify": recB["verify"],
    "markovianprovenance": json.dumps(recB, separators=(",", ":")),
    "markoviantrace": json.dumps(payload_B, separators=(",", ":")),   # the pre-image
}, content_B)
wire = JSONFormat().write(ce)

# ============ Build the consumer's envelope store FROM the two real envelopes ============
store = {}
# from the A2A artifact:
store[a2a_artifact["metadata"]["provenance_ref"]["merkle_root"]] = ("a2a", a2a_artifact["metadata"]["trace_payload"])
# from the parsed CloudEvent (round-tripped through the real SDK):
ce2 = JSONFormat().read(CloudEvent, wire)
recB_rt = json.loads(ce2.get_extension("markovianprovenance"))
payloadB_rt = json.loads(ce2.get_extension("markoviantrace"))
store[recB_rt["merkle_root"]] = ("cloudevents", payloadB_rt)

# ============ TRACE: walk B -> A across the two doors ============
def trace(root, store, seen=None):
    seen = seen or set()
    if root in seen:
        raise RuntimeError("cycle detected at " + root)
    seen.add(root)
    door, payload = store[root]
    v = httpx.get(f"{API}/verify/{root}", headers=UA, timeout=20).json()
    node = {
        "root": root,
        "door": door,
        "hash_binds": hashlib.sha256(canon(payload)).hexdigest() == v.get("data_hash"),
        "anchored": v.get("verified") is True,
        "block_height": v.get("block_height"),
        "parents": [],
    }
    for p in payload["parents"]:
        pv = httpx.get(f"{API}/verify/{p['merkle_root']}", headers=UA, timeout=20).json()
        edge_verified = pv.get("data_hash") == p["data_hash"]
        child = trace(p["merkle_root"], store, seen)
        node["parents"].append({"relationship": p["relationship"], "edge_verified": edge_verified, "node": child})
    return node

resolved = trace(recB_rt["merkle_root"], store)

# ============ Report ============
def collect(n, nodes, edges, doors):
    nodes.append(n["root"]); doors.add(n["door"])
    ok = n["hash_binds"] and n["anchored"]
    for e in n["parents"]:
        edges.append(e["edge_verified"])
        ok = ok and e["edge_verified"] and collect(e["node"], nodes, edges, doors)
    return ok

nodes, edges, doors = [], [], set()
lineage_valid = collect(resolved, nodes, edges, doors)

print("=== TRACE cross-door PoC ===")
print("Node B (trade-decision) root:", recB["merkle_root"])
print("Node A (regime-signal) root :", recA["merkle_root"])
print("B carried in              : CloudEvent")
print("A carried in              : A2A artifact")
print()
def show(n, indent=0):
    pad = "  " * indent
    print(f"{pad}- {n['door']:<11} {n['root'][:24]}...  hash_binds={n['hash_binds']} anchored={n['anchored']} block={n['block_height']}")
    for e in n["parents"]:
        print(f"{pad}    edge[{e['relationship']}] verified={e['edge_verified']}")
        show(e["node"], indent + 2)
show(resolved)
print()
print("nodes walked        :", len(nodes))
print("doors spanned       :", sorted(doors))
print("all nodes anchored  :", all(httpx.get(f'{API}/verify/{r}', headers=UA, timeout=20).json().get('verified') for r in nodes))
print("all edges in-band   :", all(edges))
print("LINEAGE VALID       :", lineage_valid)

# ============ Tamper test: the edge is in the pre-image, so re-pointing it must break the hash ============
import copy
print()
print("=== tamper test (re-point B's parent in the carried payload only) ===")
forged = copy.deepcopy(payloadB_rt)
forged["parents"][0]["merkle_root"] = "deadbeef" * 8     # forge the parent reference
onchain_B = httpx.get(f"{API}/verify/{recB_rt['merkle_root']}", headers=UA, timeout=20).json()
binds_after_tamper = hashlib.sha256(canon(forged)).hexdigest() == onchain_B.get("data_hash")
print("forged parent ref -> hash_binds:", binds_after_tamper, "(expected False)")
print("=> a soft pointer cannot be forged undetected: the parent is inside the committed bytes.")
assert lineage_valid and not binds_after_tamper, "PoC invariants failed"
print("\nALL INVARIANTS HOLD: honest lineage verifies, forged edge is rejected.")
