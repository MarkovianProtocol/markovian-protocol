# Markovian Provenance Extension for A2A

**Extension URI:** `https://api.quantsynth.net/a2a/ext/provenance/v1`
**Status:** Draft v0.2, June 28 2026 (harmonized to the live `/stamp` service)
**v1 URI policy:** Self-contained, served from our stack at `GET https://api.quantsynth.net/a2a/ext/provenance/v1` (mirrors the VC door serving its @context at /vc/provenance/v1). Brand migration to markovianprotocol.com is a deferred v2 (same posture as the VC issuer-DID decision); the URI is an opaque identifier, so the rename is a non-breaking re-publish.
**Type:** A2A **Data-only Extension** (exposes structured data in the Agent Card / message metadata; adds no RPC method, no new task state, no state-machine change)
**Depends on:** A2A extension mechanism (`AgentExtension` in `AgentCapabilities`); the live Markovian public stamp service (`POST https://api.quantsynth.net/stamp`) + verifier (`GET https://api.quantsynth.net/verify/<merkle_root>`).

> NOTE: The A2A extension *mechanism* (declaration via `AgentExtension`, permissionless publication by URI, per-request activation via the `A2A-Extensions` header) is verified against the A2A v1.0.0 specification. The Markovian object below is harmonized BYTE-IDENTICAL to the canonical `markovian-provenance/v1` carried across every other Markovian door (ERC-8004, C2PA, VC). Only the OUTER envelope differs per door: here, the `AgentExtension` declaration plus the `metadata[<URI>]` attachment on an Artifact.

---

## 1. Abstract

This extension lets an A2A agent attach **verifiable provenance** to the outputs it produces. Each attestation is a Markovian **STAMP**: a timestamped, chain-recorded commitment to a dataset or output, independently verifiable by any party. The extension proves **provenance, not truth**: it attests that specific data was committed at a specific time and is bound to a specific record, NOT that the output is correct.

It is the A2A envelope for the same `markovian-provenance/v1` object used in every other Markovian integration. One provenance object, multiple ecosystem wrappers.

## 2. Terminology

- **Stamp** — a public Markovian commit produced by `POST /stamp`: a Merkle root (`sha256(data_hash:salt:wallet)`), a BN128 **Pedersen** commitment, a chain `block_height`, and a timestamp. External stamps carry a Pedersen commitment ONLY — no validity proof is generated or required.
- **Attestation** — the `markovian-provenance/v1` provenance object (Section 4) carried over A2A.
- **Verifier** — the public Markovian endpoint (`https://api.quantsynth.net/verify/<merkle_root>`). It is an **existence + commitment lookup** (returns `type:external_stamp, verified:true`), NOT a validity proof.
- **Subject** — the dataset or output the attestation is about; bound by `data_hash`.

## 3. Declaring support (Agent Card)

An agent declares this extension in its Agent Card via an `AgentExtension` object inside `AgentCapabilities.extensions` (verified A2A mechanism):

```json
{
  "capabilities": {
    "extensions": [
      {
        "uri": "https://api.quantsynth.net/a2a/ext/provenance/v1",
        "description": "Outputs carry a Markovian STAMP: a timestamped, chain-recorded, independently verifiable provenance commitment. Proves the data was committed at this time, not that it is correct.",
        "required": false,
        "params": {
          "verifier": "https://api.quantsynth.net/verify/",
          "commitment": "bn128-pedersen"
        }
      }
    ]
  }
}
```

`required: false` means counterpart agents that do not understand the extension can still interact; provenance is additive. An agent MAY set `required: true` only if it will refuse interaction with peers that cannot process provenance.

**Per-request activation:** a client that wants provenance includes the `A2A-Extensions` HTTP header listing the extension URI; the server SHOULD echo the `A2A-Extensions` header listing the extensions it activated.

## 4. The attestation object (`markovian-provenance/v1`)

BYTE-IDENTICAL to the object used across all Markovian doors:

```json
{
  "schema": "markovian-provenance/v1",
  "merkle_root": "<sha256(data_hash:salt:wallet), hex>",
  "data_hash": "<sha256 of the stamped data, hex>",
  "wallet": "<stamper MKV wallet>",
  "zk_commitment": "<BN128 Pedersen commitment point, e.g. [\"x\",\"y\"]>",
  "block_height": <int>,
  "stamped_at": "<timestamp string, e.g. 2026-06-28 20:46:43.286561+00:00>",
  "verify": "https://api.quantsynth.net/verify/<merkle_root>",
  "attestation": "provenance-only; proves data was committed at this time, not that it is correct"
}
```

- `merkle_root` is the canonical identifier of the stamp; it is `sha256(data_hash:salt:wallet)`.
- `data_hash` binds the attestation to the exact bytes being attested. The underlying data itself is NOT carried (privacy-preserving notary: agents stamp a hash, keep the data).
- `zk_commitment` is a BN128 Pedersen commitment point. External stamps carry the commitment only; no validity proof is attached.
- `block_height` is the live Markovian chain height at stamp time.
- `stamped_at` is a timestamp string.
- `verify` resolves to the public existence + commitment lookup (Section 7).

## 5. Carrying an attestation

A2A `metadata` is a `map[string, Any]` available on the **Message**, **Task**, **Artifact**, and **Part** objects.

1. **Per-output (primary).** The attestation is placed in the producing **Artifact**'s `metadata`, keyed by the extension URI:
   ```json
   "metadata": {
     "https://api.quantsynth.net/a2a/ext/provenance/v1": { /* attestation object, Section 4 */ }
   }
   ```
   It MAY additionally be mirrored onto the enclosing `Task.metadata` or `Message.metadata` for task-level provenance, using the same URI key.

2. **Agent-Card level (supply-chain, optional).** Following the `sigstore/sigstore-a2a` pattern, a provenance bundle MAY be attached to the signed Agent Card as verification material, attesting the provenance of the agent build/config itself. This is complementary to, and out of scope of, the data-only per-output attestation.

The Section 4 object is identical regardless of attachment point.

## 6. Producing an attestation (flow)

1. Agent produces an output (or selects a dataset to attest).
2. Agent computes `sha256(subject)` (this becomes `data_hash`).
3. Agent calls the live Markovian stamp service: `POST https://api.quantsynth.net/stamp` with `{ "wallet": "<MKV wallet>", "data": <subject or its hash>, "label": "<optional>" }`. This burns 1 MKV. The service computes `data_hash`, derives `merkle_root = sha256(data_hash:salt:wallet)`, produces the BN128 Pedersen `zk_commitment`, records the current `block_height`, persists the row, and returns `{ merkle_root, data_hash, zk_commitment, block_height, stamped_at, verify_url, wallet, mkv_burned }`.
4. Agent builds the Section 4 object from that response and attaches it (Section 5).

## 7. Verifying an attestation (flow)

A receiving agent that supports the extension:
1. Reads the attestation object from the Artifact `metadata` (Section 5).
2. Recomputes `sha256` of the received subject and checks it equals `data_hash` (binding).
3. Fetches `verify` and confirms the lookup returns `type:external_stamp, verified:true` with a matching `merkle_root`. This is an **existence + commitment lookup, NOT a validity proof**.
4. Treats a `verified:true` result as **"this data was committed at `stamped_at` and is bound to this record,"** NOT as a correctness judgment (Section 8).

A receiving agent that does NOT support the extension ignores the metadata and interacts normally.

## 8. Semantics: provenance, not truth

This is the load-bearing rule. A `verified:true` attestation asserts **time of record and binding to a record**, never correctness of content. Implementations MUST NOT present a verified Markovian attestation as a claim that the attested output is true, accurate, or correct. This matches the W3C Verifiable Credentials principle that verifying a credential does not evaluate the truth of its claims.

## 9. Security considerations

- A2A treats extension-carried metadata as **untrusted by default**. This extension addresses that directly: trust derives from **independently GETting `verify`** at the public Markovian endpoint, NOT from A2A's say-so or the producing agent's assertion. A consumer MUST verify rather than trust the attached object.
- `data_hash` binding prevents an attestation from being lifted onto different data.
- The verifier endpoint MUST be reachable for independent verification; a cached/mirrored verifier is RECOMMENDED to avoid a single point of dependency.

## 10. Dependencies and open items

- **Dependency:** the live Markovian public stamp service (`POST /stamp`) and verifier (`GET /verify/<merkle_root>`); this extension wraps them. The spec is publishable now.
- **Confirmed (v0.2):** `AgentExtension` schema = `{ uri (required), description, required, params }`; metadata is `map[string,Any]` on Message/Task/Artifact/Part; primary attach = `Artifact.metadata` keyed by URI; per-request activation = `A2A-Extensions` header; extension type = Data-only.
- **Open:** A2A has no central extension registry; discovery is per-agent (Agent Card + `A2A-Extensions` negotiation). Optional `sigstore-a2a` Agent-Card bundle shape is out of scope for v1.

## 11. Reference implementation (planned)

`markovian-a2a` (Python library + CLI), the `sigstore/sigstore-a2a` analog: stamp an output, build the attestation, attach it to an Artifact's `metadata`, and verify a received attestation. It wraps the **live FastAPI `POST /stamp` endpoint** in `~/sigmasynth/api_server.py` (NOT the deprecated `~/markovian/agent_stamp.py.DEPRECATED`, which used a divergent Postgres `agent_provenance` table and a proof scheme that does not match the live external-stamp path). Builds on the official `a2a-sdk` (Python) for Agent Card / Artifact types.

## 12. References

- A2A v1.0.0 specification — extensions (`AgentExtension` in `AgentCapabilities`, `A2A-Extensions` activation header), https://a2a-protocol.org/latest/specification/ and https://a2a-protocol.org/latest/topics/extensions/
- `sigstore/sigstore-a2a` (precedent: keyless signing + provenance bundles on Agent Cards), https://github.com/sigstore/sigstore-a2a
- Markovian × ERC-8004 integration spec (same `markovian-provenance/v1` object).
- W3C Verifiable Credentials Data Model 2.0 (provenance-not-truth principle).
