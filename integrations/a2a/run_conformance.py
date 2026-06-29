#!/usr/bin/env python3
"""Markovian as an independent third implementation: run DF's published okf-reliability-v1
conformance vectors through the published JSON Schema. A conformant validator MUST accept
every `valid` vector and reject every `invalid` one."""
import json, httpx
from jsonschema import Draft202012Validator

UA = {"User-Agent": "python-httpx/0.27.0"}
SCHEMA_URL = "https://dynamicfeed.ai/schemas/okf-reliability-v1.json"
VECTORS_URL = "https://raw.githubusercontent.com/dynamicfeed/df-verify/main/reliability/conformance-vectors.json"

schema = httpx.get(SCHEMA_URL, headers=UA, timeout=30).json()
vectors = httpx.get(VECTORS_URL, headers=UA, timeout=30).json()["vectors"]
validator = Draft202012Validator(schema)

passed = 0
fails = []
for v in vectors:
    errs = sorted(validator.iter_errors(v["reliability"]), key=str)
    got = "valid" if not errs else "invalid"
    ok = (got == v["expect"])
    passed += ok
    mark = "OK " if ok else "XX "
    print(f"{mark}[{v['expect']:>7}] {v['label'][:70]}")
    if not ok:
        fails.append((v["label"], v["expect"], got, [e.message for e in errs[:2]]))

print(f"\n=== {passed}/{len(vectors)} vectors agree with expect ===")
for f in fails:
    print("MISMATCH:", f)
