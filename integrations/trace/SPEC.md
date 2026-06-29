# TRACE v1 — Cross-Door Provenance Graph (specification)

Status: draft v1. Verb name: TRACE (confirmed; supersedes the working name RESOLVE).
Brand surface migration (resolve.markovianprotocol.com -> trace.*) is a separate follow-up.
Scope: the WALKABLE graph. Zero new cryptography; reuses the existing COMMIT stamp
(Pedersen commitment + Schnorr + Merkle + Bitcoin anchor). Recursive proof folding is a
separate, demand-gated v2 and is out of scope here.

A COMMIT stamp can reference other stamps. The references are bound INSIDE the committed
bytes, so the doors (VC, A2A, MCP, ERC-8004, OTS, EAS, C2PA, CloudEvents) become NODES and
the references become EDGES in one provenance DAG. TRACE is the function that walks a stamp's
references and verifies the lineage. It returns a verified MAP of the graph, never a verdict.

---

## 1. The traceable payload

The bytes a stamp commits to. This is the pre-image of `data_hash`; the parent edges live here,
which is what makes the edges tamper-evident.

```jsonc
{
  "schema": "markovian-provenance/v1",
  "parents": [ <ParentRef>, ... ],   // [] for a leaf node
  "body_hash": "<sha256 hex of the actual content this stamp is about>",
  "produced_by": "<door label, e.g. a2a | cloudevents | c2pa | eas | vc | mcp>"
}
```

`data_hash = SHA256(canonical(payload))`. The COMMIT is created by stamping this `data_hash`
(the /stamp endpoint accepts a pre-computed `data_hash` passthrough). `merkle_root` and
`zk_commitment` are produced by the protocol over the same committed bytes.

Because `parents[]` is inside the pre-image, you cannot re-point or alter a parent without
changing `data_hash`, which changes `merkle_root`, which cascades to every descendant. A parent
reference placed in an outer envelope wrapper (outside the pre-image) is a SOFT POINTER and is
not valid for TRACE.

## 2. ParentRef (the edge)

Reference a parent by FULL identity, not a bare root (prevents cross-format confusion and lets
TRACE validate node and edge in one pass).

```jsonc
{
  "merkle_root": "<parent root, the lookup key>",
  "data_hash":   "<parent data_hash, the content binding>",
  "schema":      "<parent door schema>",
  "relationship": "derivedFrom | parentOf | componentOf | inputTo"
}
```

Relationship enum (reused from C2PA + W3C PROV, do not coin new terms):
- `derivedFrom`  — generic derivation (W3C PROV `wasDerivedFrom`). Default.
- `parentOf`     — this node is an edit/revision of the parent (C2PA).
- `componentOf`  — this node was assembled from the parent among several (C2PA).
- `inputTo`      — the parent was an input to producing this node (C2PA).

v1 ships derivation edges only. Lateral "corroborates / attests-to" edges (a web of trust) are
deliberately excluded; they reintroduce reputation/truth semantics and are deferred.

## 3. Canonical encoding

`canonical()` MUST be deterministic or `data_hash` is not reproducible and independent verifiers
will disagree. v1 PoC uses json-sorted-compact: UTF-8 JSON, `sort_keys=true`, separators `(",",":")`,
no insignificant whitespace. Production SHOULD migrate to DAG-CBOR (sorted keys, shortest ints,
64-bit floats, no indefinite-length items) for cross-language stability.

Multi-parent nodes MUST canonically order `parents` (byte-wise sort by `merkle_root`) BEFORE
hashing, so the child hash is reproducible regardless of producer.

## 4. Carrying a node in a door

The traceable payload travels in the door's native envelope so a consumer can recompute the hash;
the `data_hash`/`merkle_root` are anchored on-chain. Examples:
- A2A: payload in `Artifact.metadata` alongside `provenance_ref`.
- CloudEvents: payload as an extension attribute (e.g. `markoviantrace`) next to `markovianprovenance`.
- C2PA: payload inside the `com.markovianprotocol.provenance.v1` assertion.
The envelope is unmodified otherwise. The same payload format works in every door, which is the
cross-door property.

## 5. The TRACE algorithm

Input: a starting `merkle_root` and access to the envelopes carrying the nodes (an envelope store,
a resolver service, or inline bundle).

```
trace(root, store, seen = {}):
  if root in seen: FAIL "cycle"                      # safety, see section 7
  seen.add(root)
  (door, payload) = store.get(root)                  # payload travels in the door envelope
  onchain = GET /verify/{root}                        # independent, account-free

  node.root         = root
  node.door         = door
  node.hash_binds   = ( SHA256(canonical(payload)) == onchain.data_hash )   # edge is in-band
  node.anchored     = ( onchain.verified == true )                          # Bitcoin anchor
  node.block_height = onchain.block_height
  node.stamped_at   = onchain.stamped_at
  node.parents      = []

  for p in payload.parents:
    pv = GET /verify/{p.merkle_root}
    edge_verified = ( pv.data_hash == p.data_hash )   # claimed parent matches real parent content
    child = trace(p.merkle_root, store, seen)
    node.parents.append({ relationship: p.relationship, edge_verified, node: child })

  return node
```

## 6. Verification rules

A node is VALID iff `hash_binds` AND `anchored`. An edge is VALID iff `edge_verified` (the parent's
real on-chain `data_hash` equals the `data_hash` named in the child's ParentRef) AND the child node
is valid. A lineage is VALID iff every node and every edge in the returned sub-DAG is valid.

TRACE reports WHICH check failed per node/edge (bad node hash vs broken edge vs unconfirmed anchor),
the way OpenTimestamps distinguishes an incomplete from a complete proof. It returns the map and the
per-element verdicts; it does NOT collapse to a single true/false or any claim about correctness of
the content. Provenance, not truth.

## 7. Safety

- Cycle detection: abort if a root reappears on the current path. Content-addressing makes honest
  cycles impossible, but a fabricated `parents[].merkle_root` could collide; treat any cycle as invalid.
- Depth cap: default max walk depth 256; return `truncated: true` + frontier roots beyond it.
- Fan-out cap: bound parents per node. Cost is O(nodes x verify_cost); unbounded walking is a DoS vector.

## 8. Temporal partial order (free property)

If a child anchored at Bitcoin block N commits a parent root in its pre-image, the parent provably
existed before block N. Walking the DAG yields a verifiable temporal partial order over the whole
lineage, anchored to Bitcoin. Adopt OpenTimestamps' incomplete-then-upgrade model so `block_height`
hardens on confirmation.

## 9. Out of scope for v1 (roadmap)

- Recursive proof folding (one O(1) proof for the whole lineage) — v2, demand-gated. Runs on
  Pedersen/BN254 (our curve) via Nova/HyperNova + CycleFold but requires arithmetizing stamp logic
  into R1CS/CCS. Build the DAG, earn the fold.
- Lateral / web-of-trust edges.
- Whole-ancestry zero-knowledge proofs (prove lineage without revealing intermediate stamps).
