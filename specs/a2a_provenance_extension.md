# Markovian Provenance Extension for A2A

**Extension URI:** `https://api.quantsynth.net/a2a/ext/provenance/v1`
**Status:** Draft v0.3, June 29 2026 (converged with the field-table design forming in [a2aproject/A2A#2011](https://github.com/a2aproject/A2A/issues/2011))
**v1 URI policy:** Self-contained, served from our stack at `GET https://api.quantsynth.net/a2a/ext/provenance/v1`. The URI is an opaque identifier; brand migration to markovianprotocol.com is a non-breaking re-publish (deferred v2).
**Type:** A2A **Data-only Extension** (exposes structured data in message/artifact metadata; adds no RPC method, no new task state, no state-machine change)
**Depends on:** A2A extension mechanism (`AgentExtension` in `AgentCapabilities`); the live Markovian public stamp service (`POST https://api.quantsynth.net/stamp`) + verifier (`GET https://api.quantsynth.net/verify/<merkle_root>`).

> **v0.3 note.** v0.2 carried a single `markovian-provenance/v1` object keyed by the extension URI. The #2011 thread converged on a better shape: three **separable, flat siblings** in `Artifact.metadata`, each about a different claim, each independently re-checkable, none inside the signed fact bytes. This extension owns one of the three siblings, `provenance_ref` (existence-in-time), and composes with the other two rather than absorbing them. The Markovian object itself is unchanged and stays byte-identical to every other Markovian door (ERC-8004, C2PA, VC).

---

## 1. Abstract

This extension lets an A2A agent attach **verifiable existence-in-time** to the outputs it produces, as one axis of a separable provenance envelope. The axis is a Markovian **STAMP**: a timestamped, chain-recorded commitment, independently verifiable by any party with no account. It proves **provenance, not truth**: that specific data was committed at a specific time and bound to a specific record, NOT that the output is correct.

It does not try to be the whole trust story. An output's envelope has at least three independent claims, and conflating them is the failure mode this design avoids.

## 2. The three separable axes (field table)

An agent's output carries up to three **flat siblings** in `Artifact.metadata`. Each references the artifact/fact hash, each is checked independently, and **none appears inside the signed fact bytes**, so no sibling can perturb the artifact hash another verifier computes.

| Sibling | Claim it makes | Primitive | Verify against |
|---|---|---|---|
| `authorship` | who produced it + integrity | Ed25519 signature over the canonical fact (`json-sorted-compact`) | the producer key set at `metadata.verify` |
| `provenance_ref` | existence-in-time (this extension) | `markovian-provenance/v1` commitment (Merkle root + BN128 Pedersen, Bitcoin-anchored) | the public Markovian verifier (Section 6) |
| `reliability` | is the reading any good | `okf-reliability-v1` object (signed AND fresh AND corroborated AND no conflict) | `https://dynamicfeed.ai/schemas/okf-reliability-v1.json` |

`provenance_ref` is **OPTIONAL** and has two honest states: **ABSENT** when nothing was anchored, **PRESENT** when a snapshot is. Its presence proves the bytes existed at a time, never that they are correct.

## 3. Non-promotion semantics (load-bearing)

This is the rule the whole design exists to enforce. Each axis is a different non-promotion:

- **`signed != verified`.** A valid `authorship` signature proves who and integrity, never that the content is true. (W3C VC principle: verifying a credential does not evaluate its claims.)
- **`existence-in-time != correct`.** A valid `provenance_ref` proves when, never that the reading is right. The same key can sign the same payload at any moment; the anchor fixes the time, nothing more.
- **reliability is advisory, not a verdict.** A `reliability` object is `verified: true` only when signed AND fresh AND corroborated (sources >= 2, independent vantage) AND no conflict; even then it is a graded judgment, not proof of correctness.

Implementations MUST keep the three axes separable (no single `trusted` flag) and MUST NOT let any one axis alone promote a reading to trusted.

## 3a. The anchor attaches without perturbation

Because `provenance_ref` lives in metadata and not in the signed fact bytes, attaching it does not touch `authorship`: the Ed25519 signature stays valid over the unchanged canonical fact, and the artifact hash any other verifier computes is unchanged. The PRESENT and ABSENT states differ only in metadata. (Worked pair: `integrations/a2a/worked_example_artifact.json` and `integrations/a2a/a2a_artifact_present_anchor.json`.)

## 4. The `provenance_ref` object (`markovian-provenance/v1`)

BYTE-IDENTICAL to the object used across all Markovian doors:

```json
{
  "schema": "markovian-provenance/v1",
  "merkle_root": "<sha256(data_hash:salt:wallet), hex>",
  "data_hash": "<sha256 of the stamped data, hex>",
  "wallet": "<stamper MKV wallet>",
  "zk_commitment": "<BN128 Pedersen commitment point, [\"x\",\"y\"]>",
  "block_height": <int>,
  "stamped_at": "<timestamp string>",
  "verify": "https://api.quantsynth.net/verify/<merkle_root>",
  "attestation": "provenance-only; proves data was committed at this time, not that it is correct"
}
```

- `merkle_root` is the canonical stamp identifier, `sha256(data_hash:salt:wallet)`.
- `data_hash` binds the attestation to the exact bytes; the data itself is NOT carried (privacy-preserving notary).
- `zk_commitment` is a BN128 Pedersen commitment point. External stamps carry the commitment only; no validity proof is attached.
- `verify` resolves to the public existence + commitment lookup (Section 6).

## 5. Declaring support and carrying

**Declare** in the Agent Card via `AgentExtension` inside `AgentCapabilities.extensions`:

```json
{ "capabilities": { "extensions": [
  { "uri": "https://api.quantsynth.net/a2a/ext/provenance/v1",
    "description": "Outputs may carry a Markovian provenance_ref: a timestamped, chain-recorded, independently verifiable existence-in-time commitment. Proves the data was committed at this time, not that it is correct.",
    "required": false,
    "params": { "verifier": "https://api.quantsynth.net/verify/", "commitment": "bn128-pedersen" } }
] } }
```

**Activate per request** with the `A2A-Extensions` header; the server SHOULD echo the header listing what it activated.

**Carry** the axes as flat siblings in the producing `Artifact.metadata`:

```json
"metadata": {
  "authorship":     { "alg": "Ed25519", "key_id": "...", "canonicalization": "json-sorted-compact", "sig": "..." },
  "verify":         "<producer key set URL>",
  "provenance_ref": { "schema": "markovian-provenance/v1", "merkle_root": "...", "...": "..." },
  "reliability":    { "type": "okf-reliability-v1", "...": "..." }
}
```

`provenance_ref` is omitted entirely in the ABSENT state. A consumer that does not understand a sibling ignores it and interacts normally; provenance is additive.

## 6. Producing and verifying

**Produce:** compute `sha256(subject)`, call `POST /stamp` (`{wallet, data, label}`), build the Section 4 object from the response, attach it as the `provenance_ref` sibling. (The reference SDK exposes this as one call: `markovian.MarkovianClient().stamp(...)`.)

**Verify `provenance_ref`:** recompute `sha256` of the received subject and check it equals `data_hash` (binding); GET `verify` and confirm `type:external_stamp, verified:true` with a matching `merkle_root`. This is an **existence + commitment lookup, NOT a validity proof**. Treat `verified:true` as "committed at `stamped_at`, bound to this record," never as a correctness judgment.

A consumer checks each axis with its own verifier and never lets one promote a reading (Section 3).

## 7. Conformance

The design is exercised by a re-runnable suite, not asserted:

- **Reliability object:** 12 vectors (6 valid accepted, 6 invalid rejected) against `okf-reliability-v1`, including the corroboration-lie (`verified:true` with `sources<2`), the `UNVERIFIED`-but-`verified:true` case, and the disputed-reading-graded-HIGH ceiling.
- **Artifact level:** full A2A Artifacts carrying the three flat siblings; per-axis checks (reliability against schema, authorship as an Ed25519 block, `provenance_ref` against its own verifier), both anchor states.
- **Status:** three independent implementations agree on the reliability suite (Markovian, dynamicfeed.ai, and SunfishLoop), each with a runnable runner rather than an assertion.

Reference files: `integrations/a2a/run_conformance.py`, `integrations/a2a/worked_example_artifact.json`, `integrations/a2a/a2a_artifact_present_anchor.json`.

## 8. Security considerations

- A2A treats extension-carried metadata as **untrusted by default**. Trust here derives from **independently GETting `verify`**, NOT from A2A's say-so or the producing agent's assertion. A consumer MUST verify, not trust.
- `data_hash` binding prevents an attestation from being lifted onto different data.
- Keeping the axes separable prevents a valid signature or a valid anchor from being misread as a correctness claim.
- A cached/mirrored verifier is RECOMMENDED to avoid a single point of dependency.

## 9. Open items and credits

- A2A has no central extension registry; discovery is per-agent (Agent Card + `A2A-Extensions` negotiation).
- The `authorship` and `reliability` sibling shapes are co-developed; `reliability` (`okf-reliability-v1`) is dynamicfeed.ai's schema. This extension specifies only `provenance_ref` normatively and references the other two by their own definitions.
- Field-table convergence and the separability principle come out of #2011, with @Dynamicfeedai, @0xbrainkid, and SunfishLoop. The next step is a single shared artifact-vector file the implementations point at.

## 10. References

- A2A v1.0.0 specification (extensions: `AgentExtension`, `A2A-Extensions` header), https://a2a-protocol.org/latest/specification/
- a2aproject/A2A#2011 (field-table convergence), https://github.com/a2aproject/A2A/issues/2011
- `okf-reliability-v1` schema, https://dynamicfeed.ai/schemas/okf-reliability-v1.json
- `sigstore/sigstore-a2a` (Agent-Card provenance bundles precedent), https://github.com/sigstore/sigstore-a2a
- W3C Verifiable Credentials Data Model 2.0 (provenance-not-truth principle).
