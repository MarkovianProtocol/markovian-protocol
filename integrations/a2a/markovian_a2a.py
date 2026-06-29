"""
markovian_a2a — reference wrapper for the Markovian × A2A provenance door.

One stamp, N envelopes. This module is the A2A envelope: it takes the live
Markovian STAMP (POST /stamp, burns 1 MKV) and assembles the canonical
markovian-provenance/v1 object, attaches it to an A2A Artifact's metadata
(keyed by the extension URI), and verifies a received attestation end-to-end.

Trust model: A2A carries this in untrusted-by-default metadata. Trust derives
from independently GETting the verify URL (an existence + commitment lookup,
type:external_stamp -> verified:true), NOT from A2A's say-so. Provenance, not truth.
"""

import hashlib
import json

import httpx

API_BASE = "https://api.quantsynth.net"
EXT_URI = "https://api.quantsynth.net/a2a/ext/provenance/v1"
SCHEMA = "markovian-provenance/v1"
ATTESTATION = "provenance-only; proves data was committed at this time, not that it is correct"

_REQUIRED = ("schema", "merkle_root", "data_hash", "wallet",
             "zk_commitment", "block_height", "stamped_at", "verify", "attestation")


def canon(data):
    """Canonicalize exactly as the live /stamp endpoint does before hashing."""
    if isinstance(data, str):
        return data
    return json.dumps(data, sort_keys=True, default=str)


def stamp_output(data, wallet, label=None, timeout=30.0):
    """Call the live STAMP service and assemble the canonical markovian-provenance/v1 object.

    GOTCHA (same as the VC build): the /stamp response omits schema/wallet/attestation.
    We inject schema='markovian-provenance/v1', wallet=the request wallet, and the
    fixed attestation string. Everything else (merkle_root, data_hash, zk_commitment,
    block_height, stamped_at) comes straight from the live response.
    """
    resp = httpx.post(f"{API_BASE}/stamp",
                      json={"wallet": wallet, "data": data, "label": label},
                      timeout=timeout)
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


def attach(metadata, obj):
    """Return an A2A metadata dict carrying the provenance object keyed by the extension URI.

    Pass the result as Artifact.metadata (primary attach point, v1). Works directly with
    a2a-sdk TaskUpdater.add_artifact(metadata=...).
    """
    md = dict(metadata or {})
    md[EXT_URI] = obj
    return md


def verify(obj, data, timeout=30.0):
    """End-to-end verification of a received attestation.

    Returns {transport_ok, stamp_verified, binding_ok, ...}.
      - transport_ok : the provenance object was present and well-formed in A2A metadata.
      - binding_ok   : sha256(canon(data)) == obj.data_hash (attestation bound to these bytes).
      - stamp_verified: independent GET /verify/<root> returns verified:true with matching fields.
    """
    out = {"transport_ok": False, "binding_ok": False, "stamp_verified": False}

    if not (isinstance(obj, dict) and all(k in obj for k in _REQUIRED) and obj.get("schema") == SCHEMA):
        out["error"] = "malformed or missing provenance object"
        return out
    out["transport_ok"] = True

    local_hash = hashlib.sha256(canon(data).encode()).hexdigest()
    out["local_data_hash"] = local_hash
    out["binding_ok"] = (local_hash == obj["data_hash"])

    try:
        vr = httpx.get(obj["verify"], timeout=timeout).json()
    except Exception as e:  # noqa: BLE001
        out["verify_error"] = str(e)
        return out
    out["verify_response"] = vr

    ok = (vr.get("verified") is True
          and vr.get("merkle_root") == obj["merkle_root"]
          and vr.get("data_hash") == obj["data_hash"])
    # block_height may be float-coerced through an A2A protobuf Struct; compare tolerantly.
    try:
        if obj.get("block_height") is not None and vr.get("block_height") is not None:
            ok = ok and int(float(obj["block_height"])) == int(vr["block_height"])
    except (TypeError, ValueError):
        pass
    out["stamp_verified"] = bool(ok)
    return out
