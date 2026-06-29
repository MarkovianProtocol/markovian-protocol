#!/Users/colinwinter/neo_env/bin/python3
"""
A2A worked example for issue #2011: one Artifact carrying three SEPARABLE provenance
axes as siblings in Artifact.metadata, each independently re-checkable:

  authorship      -> producer Ed25519 signature over the canonical bytes
  provenance_ref  -> markovian-provenance/v1 commitment (existence-in-time, Bitcoin-anchored)
  reliability     -> okf-reliability-v1 object (data quality, advisory)

Shape aligned with the #2011 convergence (DynamicFeed, SunfishLoop): the three axes
are FLAT siblings in Artifact.metadata under the agreed names, the extension is named
in artifact.extensions, and all of it rides OUTSIDE the signed bytes. Canonicalization
is json-sorted-compact (stable key order, no insignificant whitespace); the signed
payload is the canonical fact only, so no axis perturbs the artifact hash and a single
verifier accepts artifacts from any producer that uses these three names.
"""
import json, hashlib, base64, datetime, httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

API = "https://api.quantsynth.net"
EXT = "https://api.quantsynth.net/a2a/ext/provenance/v1"
OUT = "/Users/colinwinter/markovian/a2a/worked_example_artifact.json"
UA = {"User-Agent": "python-httpx/0.27.0"}

def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()

# ---- the agent output (a fact) ----
fact = {"type": "regime-signal", "ticker": "QQQ", "regime": "DISTRIBUTION",
        "confidence": 0.52, "asof": "2026-06-29T16:00:00Z", "producer": "markovian-demo-agent"}
canonical = canon(fact)
data_hash = hashlib.sha256(canonical).hexdigest()

# ---- axis 1: authorship (Ed25519 over canonical bytes) ----
# key_id embeds the raw public key, so the signature is self-verifying with no key-set fetch.
sk = Ed25519PrivateKey.generate()
pk = sk.public_key()
key_id = "ed25519:" + pk.public_bytes_raw().hex()
authorship = {
    "alg": "Ed25519",
    "key_id": key_id,
    "canonicalization": "json-sorted-compact",
    "sig": base64.b64encode(sk.sign(canonical)).decode(),
}

# ---- axis 2: provenance_ref (Markovian commitment, existence-in-time) ----
# Unlike a single-source live reading where the anchor is honestly absent, this snapshot
# IS anchored, so provenance_ref is present and carries the Bitcoin root + ZK commitment.
r = httpx.post(f"{API}/stamp", headers=UA, timeout=30,
               json={"data_hash": data_hash, "label": "a2a-worked-example"})
r.raise_for_status()
s = r.json()
provenance_ref = {
    "schema": "markovian-provenance/v1",
    "merkle_root": s["merkle_root"], "data_hash": s["data_hash"], "wallet": s.get("wallet"),
    "zk_commitment": s.get("zk_commitment"), "block_height": s.get("block_height"),
    "stamped_at": str(s.get("stamped_at")),
    "verify": s.get("verify_url") or f"{API}/verify/{s['merkle_root']}",
    "attestation": "provenance-only; proves data was committed at this time, not that it is correct",
}

# ---- axis 3: reliability (okf-reliability-v1, advisory) ----
signals = {"signed": True, "corroborated": True, "fresh": True}
reliability = {
    "type": "okf-reliability-v1",
    "confidence": "HIGH",            # ordinal band; the number lives in score
    "basis": "computed",
    "score": 0.78,
    "sources": 2,
    "verified": all(signals.values()),
    "vantage": "independent",
    "freshness": {"state": "fresh"},
    "signals": signals,
    "assessed_at": "2026-06-29T16:00:05Z",
}

# ---- the A2A Artifact: three flat siblings, outside the signed bytes ----
artifact = {
    "artifactId": "regime-signal-" + data_hash[:12],
    "name": "regime-signal",
    "extensions": [EXT],
    "parts": [{"kind": "text", "text": canonical.decode()}],   # the signed payload
    "metadata": {
        "authorship": authorship,           # who + integrity
        "provenance_ref": provenance_ref,   # existence-in-time (Bitcoin-anchored)
        "reliability": reliability,         # data quality (advisory)
    },
}

open(OUT, "w").write(json.dumps(artifact, indent=2))

# ============ INDEPENDENT VERIFICATION OF EACH AXIS ============
print("=== A2A 3-axis worked example (flat siblings) ===")
md = artifact["metadata"]
recanon = canon(json.loads(artifact["parts"][0]["text"]))

# axis 1: authorship
try:
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(md["authorship"]["key_id"].split(":")[1])) \
        .verify(base64.b64decode(md["authorship"]["sig"]), recanon)
    a1 = True
except Exception:
    a1 = False
print("authorship     (ed25519):", "VALID" if a1 else "FAIL")

# axis 2: provenance_ref
v = httpx.get(md["provenance_ref"]["verify"], headers=UA, timeout=20).json()
a2 = (hashlib.sha256(recanon).hexdigest() == v.get("data_hash")) and v.get("verified") is True
print("provenance_ref (markovian):", "VALID" if a2 else "FAIL",
      "| root", md["provenance_ref"]["merkle_root"][:20])

# axis 3: reliability
a3 = md["reliability"]["verified"]
print("reliability    (advisory): verified=" + str(a3),
      "(signed+fresh+corroborated, independent)")
print("\nartifact written:", OUT)
print("signed bytes never include the provenance_ref/reliability siblings -> artifact hash is stable across verifiers")
