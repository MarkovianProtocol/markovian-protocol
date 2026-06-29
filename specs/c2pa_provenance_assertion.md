# Markovian Provenance Assertion for C2PA

**Assertion label:** `net.markovianprotocol.provenance.v1` *(reverse-domain entity namespace; C2PA third-party convention. Version suffix `.v1` explicit; use double-underscore `__1`/`__2` for multiple instances per C2PA label syntax.)*
**Status:** Draft v0.2, June 28 2026 (harmonized to the live `/stamp` object)
**Type:** C2PA third-party (entity-namespaced) custom assertion within a Content Credential (Manifest).
**Spec pinned:** C2PA Technical Specification **2.3, 2026-01-05** (latest technical spec). 2.2 (2025-05-01) is the last HTML edition.
**Depends on:** the live Markovian public stamp service (`POST /stamp` in `~/sigmasynth/api_server.py`) + verifier (`GET /verify/<merkle_root>`).

> The C2PA third-party-assertion *mechanism* (external entities add entity-namespaced assertions without C2PA approval) is verified from the C2PA spec. The verified slot is the **namespaced third-party assertion** — there is no built-in `c2pa.ai-disclosure` assertion to rely on. Assertions are CBOR-encoded in the assertion store; you author them as JSON `{label, data}` in a c2patool / c2pa-python manifest-definition file and the SDK encodes to CBOR.

---

## 1. Abstract

This defines a C2PA assertion that attaches **verifiable Markovian provenance** to a Content Credential. It suits agent outputs that are content: images, documents, generated media, or data files. The assertion carries the same canonical `markovian-provenance/v1` object used in every other Markovian wrapper (ERC-8004, A2A, VC) — the inner object is byte-identical across doors; only the outer envelope (here, a C2PA CBOR assertion inside a Manifest) differs. It proves **provenance, not truth**: that this exact content was committed to the Markovian chain at a specific time and is independently verifiable, not that the content is accurate.

## 2. Why C2PA

C2PA is the established content-provenance standard, and it explicitly supports third-party extensibility: "future metadata and credential providers are able to add their information without requiring input or approval from the C2PA." External entities add assertions as **entity-namespaced labels** beginning with their internet domain name (e.g. `com.litware`, `net.fineartschool`). Markovian occupies `net.markovianprotocol.*`.

C2PA also natively **separates provenance from veracity**: "C2PA specifications SHOULD NOT provide value judgments about whether a given set of provenance data is 'good' or 'bad,' merely whether the assertions … can be validated as associated with the underlying asset, correctly formed, and free from tampering." Our provenance-not-truth semantics therefore map cleanly onto C2PA.

## 3. Where it lives

A C2PA **Content Credential** (Manifest) attached to an asset contains a Claim, a set of **Assertions**, and a Claim Signature. The Markovian assertion is one assertion in that set (JSON in the manifest-definition file; CBOR in the store):

```json
{
  "label": "net.markovianprotocol.provenance.v1",
  "data": { /* markovian-provenance/v1 object, Section 4 */ }
}
```

Two independent trust layers result: the **C2PA claim signature** (X.509, default `es256`) attests *who built the manifest*; the **Markovian stamp** attests *the underlying commitment and time*, independently re-verifiable with no account.

## 4. The canonical attestation object (`markovian-provenance/v1`)

Byte-identical across all Markovian wrappers. This is exactly what the live `POST /stamp` returns (BN128 **Pedersen commitment only** — no zero-knowledge validity proof for external stamps):

```json
{
  "schema": "markovian-provenance/v1",
  "merkle_root": "<sha256(data_hash:salt:wallet), hex>",
  "data_hash": "<sha256 of the stamped data, hex>",
  "wallet": "<stamper MKV wallet>",
  "zk_commitment": "<BN128 Pedersen commitment point, e.g. [\"x\",\"y\"]>",
  "block_height": 134177,
  "stamped_at": "<timestamp string, e.g. 2026-06-28 20:46:43.286561+00:00>",
  "verify": "https://api.quantsynth.net/verify/<merkle_root>",
  "attestation": "provenance-only; proves data was committed at this time, not that it is correct"
}
```

**Content-binding rule:** POST the **raw content bytes** as the stamp `data` so that the returned `data_hash` equals the asset's own `sha256` — then the Markovian stamp and the C2PA hard binding attest the same bytes. Do NOT pre-hash the content before POSTing (that yields a hash-of-a-hash). `data_hash` SHOULD correspond to the content C2PA hard-binds the manifest to.

## 5. Producing an assertion (flow)

1. Agent generates the content (the asset).
2. Agent POSTs the raw content as `data` to the live stamp service: `POST https://api.quantsynth.net/stamp` (`~/sigmasynth/api_server.py`). Keyless free tier; burns 1 MKV from `wallet`. Returns `{merkle_root, data_hash, wallet, zk_commitment, block_height, stamped_at, verify_url}`.
3. Agent constructs the Section 4 object from that response.
4. Agent builds a C2PA Manifest containing the `net.markovianprotocol.provenance.v1` assertion alongside any standard assertions (the C2PA hard binding to the content remains as normal).
5. Agent signs the Manifest (standard C2PA claim signature) and embeds/attaches the Content Credential to the asset.
6. 1 MKV burned per stamp.

Note: the C2PA claim signature attests the manifest author; the Markovian `zk_commitment` is a BN128 Pedersen commitment to the merkle root. Two independent layers.

## 6. Verifying an assertion (flow)

A C2PA-aware consumer:
1. Reads the Content Credential and validates the C2PA claim signature and hard binding as normal.
2. Locates the `net.markovianprotocol.provenance.v1` assertion.
3. Confirms `data_hash` matches the bound content (`sha256` of the asset bytes).
4. Fetches `verify` (`GET /verify/<merkle_root>`). This is an **existence + commitment lookup**: it returns `{type:"external_stamp", verified:true, merkle_root, data_hash, zk_commitment, block_height, …}`. **`verified:true` means the stamp exists on record with its Pedersen commitment and chain height — it is NOT a validity/correctness proof.**
5. Interprets the result as authenticity-and-time of record, never correctness (Section 7).

A consumer that does not recognize the Markovian label ignores the assertion; the rest of the Content Credential is unaffected.

## 7. Semantics: provenance, not truth

A Markovian assertion asserts only that the content was authentically recorded at `stamped_at`, NOT that the content is accurate, correct, or non-deceptive. Implementations MUST NOT present the assertion as a correctness or authenticity-of-meaning claim. C2PA itself separates provenance from veracity (Section 2); this assertion stays strictly on the provenance side.

## 8. Security considerations

- Trust derives from the independently re-checkable existence + Pedersen commitment at `verify`, not from the assertion's presence in the manifest. A consumer MUST verify.
- Binding `data_hash` to the C2PA hard-bound content prevents lifting the assertion onto different content.
- If the content is later edited, the C2PA hard binding breaks as designed; the Markovian assertion then attests only the original committed bytes.
- External stamps carry a Pedersen commitment only — no zero-knowledge validity proof. Do not represent the commitment as a proof of anything beyond "this root was committed."

## 9. Dependencies and open items

- **Dependency:** the live Markovian stamp service (`POST /stamp` in `~/sigmasynth/api_server.py`, FastAPI on Neo port 8001 behind cloudflared) must be reachable; this wraps it. (The standalone Flask prototype `agent_stamp.py.DEPRECATED` is retired — it used a non-canonical object shape and is not the live service.)
- **Open:** signing certificate / C2PA trust-list strategy (dev self-signed vs trust-anchored CA); first target content type (images vs PDF/documents vs rendered text); whether to additionally use a C2PA `ingredient`/relationship link to a dataset's own Content Credential for chained provenance.

## 10. Reference implementation (planned)

`c2pa_embed.py` + `c2pa_verify.py` on Neo: given content + a Markovian stamp, emit a C2PA Manifest carrying the assertion, and verify a received one. Built on c2pa-python (preferred, installs into `neo_env`) or c2patool / c2pa-rs, not a reimplementation of manifest signing. Wraps the live `POST /stamp`.

## 11. References

- C2PA Technical Specification 2.3 (2026-01-05); 2.2 (2025-05-01, HTML): third-party entity-namespaced assertions; provenance/veracity separation.
- c2patool / c2pa-rs / c2pa-python (contentauth).
- Markovian × ERC-8004 and × A2A specs (same `markovian-provenance/v1` object).
