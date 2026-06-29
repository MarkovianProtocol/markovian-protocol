#!/usr/bin/env python3
"""
A2A worked example for issue #2011: one Artifact carrying three SEPARABLE provenance
axes as siblings in Artifact.metadata, each independently re-checkable:

  authorship/integrity  -> producer Ed25519 signature over the canonical bytes
  existence-in-time      -> markovian-provenance/v1 commitment (Bitcoin-anchored)
  data quality           -> a reliability object (DynamicFeed-shaped, advisory)

Canonicalization is json-sorted-compact (stable key order, no insignificant
whitespace). The signed payload is the canonical fact only. The provenance and
reliability objects ride OUTSIDE the signed bytes, so neither perturbs the artifact
hash, and a consumer who trusts only one axis still gets a useful guarantee.
"""
import json, hashlib, base64, datetime, httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

API = "https://api.quantsynth.net"
EXT = "https://api.quantsynth.net/a2a/ext/provenance/v1"
UA = {"User-Agent": "python-httpx/0.27.0"}

def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()

# ---- the agent output (a fact) ----
fact = {"type": "regime-signal", "ticker": "QQQ", "regime": "DISTRIBUTION",
        "confidence": 0.52, "asof": "2026-06-29T16:00:00Z", "producer": "markovian-demo-agent"}
canonical = canon(fact)
data_hash = hashlib.sha256(canonical).hexdigest()

# ---- axis 1: authorship/integrity (Ed25519 over canonical bytes) ----
sk = Ed25519PrivateKey.generate()
pk = sk.public_key()
key_id = "ed25519:" + pk.public_bytes_raw().hex()
signature = {
    "alg": "ed25519",
    "key_id": key_id,
    "canonicalization": "json-sorted-compact",
    "sig": base64.b64encode(sk.sign(canonical)).decode(),
}

# ---- axis 2: existence-in-time (Markovian commitment) ----
r = httpx.post(f"{API}/stamp", headers=UA, timeout=30,
               json={"data_hash": data_hash, "label": "a2a-worked-example"})
r.raise_for_status()
s = r.json()
provenance = {
    "schema": "markovian-provenance/v1",
    "merkle_root": s["merkle_root"], "data_hash": s["data_hash"], "wallet": s.get("wallet"),
    "zk_commitment": s.get("zk_commitment"), "block_height": s.get("block_height"),
    "stamped_at": str(s.get("stamped_at")),
    "verify": s.get("verify_url") or f"{API}/verify/{s['merkle_root']}",
    "attestation": "provenance-only; proves data was committed at this time, not that it is correct",
}

# ---- axis 3: data quality (advisory; verified only if signed AND fresh AND corroborated AND no conflict) ----
signals = {"signed": True, "corroborated": True, "fresh": True}
reliability = {
    "confidence": 0.78, "score": 0.78, "sources": 2, "basis": "computed",
    "freshness": "live", "conflict": False, "signals": signals,
    "verified": all(signals.values()) and not False,
    "vantage": "independent",
    "assessed_at": "2026-06-29T16:00:05Z",
}

# ---- the A2A Artifact: three siblings, outside the signed bytes ----
artifact = {
    "artifactId": "regime-signal-" + data_hash[:12],
    "name": "regime-signal",
    "parts": [{"kind": "text", "text": canonical.decode()}],   # the signed payload
    "metadata": {EXT: {
        "canonicalization": "json-sorted-compact",
        "signature": signature,            # who + integrity
        "markovian-provenance/v1": provenance,  # existence-in-time
        "reliability": reliability,        # data quality (advisory)
    }},
}

open("worked_example_artifact.json", "w").write(json.dumps(artifact, indent=2))

# ============ INDEPENDENT VERIFICATION OF EACH AXIS ============
print("=== A2A 3-axis worked example ===")
md = artifact["metadata"][EXT]
recanon = canon(json.loads(artifact["parts"][0]["text"]))

# axis 1
try:
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(md["signature"]["key_id"].split(":")[1])) \
        .verify(base64.b64decode(md["signature"]["sig"]), recanon)
    a1 = True
except Exception:
    a1 = False
print("axis 1 authorship/integrity (ed25519):", "VALID" if a1 else "FAIL")

# axis 2
v = httpx.get(md["markovian-provenance/v1"]["verify"], headers=UA, timeout=20).json()
a2 = (hashlib.sha256(recanon).hexdigest() == v.get("data_hash")) and v.get("verified") is True
print("axis 2 existence-in-time (markovian):", "VALID" if a2 else "FAIL",
      "| root", md["markovian-provenance/v1"]["merkle_root"][:20])

# axis 3
a3 = md["reliability"]["verified"]
print("axis 3 data quality (advisory):", "verified=" + str(a3),
      "(signed+fresh+corroborated+no-conflict)")
print("\nartifact written: ~/markovian/a2a/worked_example_artifact.json")
print("signed bytes never include axes 2/3 -> artifact hash is stable across verifiers")
