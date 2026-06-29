#!/usr/bin/env python3
"""
CloudEvents door PoC: a markovian-provenance/v1 record rides on a CloudEvent as
custom extension attributes (lowercase-alphanumeric names, string values, per the
CloudEvents type system). The same event data is hash-committed to the Bitcoin-
anchored chain, so any consumer of the event can verify provenance with no account.
"""
import json, hashlib, uuid, datetime, httpx
from cloudevents.core.v1.event import CloudEvent
from cloudevents.core.formats.json import JSONFormat

API = "https://api.quantsynth.net"
UA = {"User-Agent": "python-httpx/0.27.0"}

def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()

# 1. the event payload (an agent output)
data = {"agent": "markovian-demo-agent", "output": "BULLISH",
        "confidence": 0.83, "asof": "2026-06-29T16:00:00Z"}
canonical = canon(data)
data_hash = hashlib.sha256(canonical).hexdigest()

# 2. commit the data hash (label has 'poc' -> excluded from adoption signal)
s = httpx.post(f"{API}/stamp", headers=UA, timeout=30,
               json={"data_hash": data_hash, "label": "cloudevents-poc"}).json()
record = {
    "schema": "markovian-provenance/v1",
    "merkle_root": s["merkle_root"], "data_hash": s["data_hash"], "wallet": s.get("wallet"),
    "zk_commitment": s.get("zk_commitment"), "block_height": s.get("block_height"),
    "stamped_at": str(s.get("stamped_at")),
    "verify": s.get("verify_url") or f"{API}/verify/{s['merkle_root']}",
    "attestation": "provenance-only; proves data was committed at this time, not that it is correct",
}

# 3. CloudEvent with Markovian provenance as extension attributes
attrs = {
    "id": str(uuid.uuid4()),
    "source": "https://markovianprotocol.com/demo-agent",
    "type": "com.markovianprotocol.agent.output",
    "specversion": "1.0",
    "time": datetime.datetime(2026, 6, 29, 16, 0, 0, tzinfo=datetime.timezone.utc),
    "datacontenttype": "application/json",
    # extension attributes (names lowercase alnum; values are strings, CloudEvents type system)
    "markovianroot": record["merkle_root"],
    "markovianverify": record["verify"],
    "markovianprovenance": json.dumps(record, separators=(",", ":")),
}
ce = CloudEvent(attrs, data)

# 4. serialize (structured JSON) + round-trip through the SDK
fmt = JSONFormat()
wire = fmt.write(ce)
ce2 = fmt.read(CloudEvent, wire)

print("=== CloudEvents door PoC ===")
print("event type:", ce2.get_type(), "| id:", ce2.get_id())
root_rt = ce2.get_extension("markovianroot")
rec_rt = json.loads(ce2.get_extension("markovianprovenance"))
print("markovianroot extension round-trips:", root_rt == record["merkle_root"])
print("full record round-trips:", rec_rt.get("schema") == "markovian-provenance/v1")

# 5. independent verification
v = httpx.get(record["verify"], headers=UA, timeout=20).json()
print("data_hash == on-chain:", hashlib.sha256(canon(ce2.get_data())).hexdigest() == v.get("data_hash"))
print("public verifier verified:", v.get("verified"))
print("verify URL:", record["verify"])

open("cloudevents_poc_event.json", "wb").write(wire)
print("\nartifact written: cloudevents_poc_event.json")
