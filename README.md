# Markovian Protocol

A provenance and trust layer for autonomous agents. The Markovian Protocol turns any
agent output into a timestamped, chain-recorded, independently verifiable record. It
proves that data was committed at a point in time. It does not claim the data is correct.
Provenance, not truth.

## COMMIT

COMMIT is the entrance. It is a content-agnostic stamp: an agent sends a hash, the
protocol writes a Merkle root plus a BN128 Pedersen commitment to the chain, and returns
a receipt that anyone can verify with no account and without trusting the issuer.

The canonical record is the same object everywhere, `markovian-provenance/v1`:

```json
{
  "schema": "markovian-provenance/v1",
  "merkle_root": "<sha256(data_hash:salt:wallet)>",
  "data_hash": "<sha256 of the committed data>",
  "wallet": "<stamper wallet>",
  "zk_commitment": "<BN128 Pedersen point>",
  "block_height": 0,
  "stamped_at": "<timestamp>",
  "verify": "https://api.quantsynth.net/verify/<merkle_root>",
  "attestation": "provenance-only; proves data was committed at this time, not that it is correct"
}
```

## Doors

One commit, many envelopes. The same record plugs into the standards agents already use.

| Standard | Status | How it plugs in |
|---|---|---|
| W3C Verifiable Credentials | Live | The record becomes the credentialSubject of a signed VC |
| A2A, Agent2Agent | Live | A data-only extension attaches the record to Artifact.metadata |
| Model Context Protocol | Live | An MCP server exposes a stamp tool and a verify tool |
| ERC-8004, Trustless Agents | Testnet | A validation provider answers on the Validation Registry |
| C2PA | Planned | A namespaced assertion inside a content manifest |

Reference pages for each door, with live examples:

- W3C VC: https://markovianprotocol.com/vc.html
- A2A: https://markovianprotocol.com/a2a.html
- MCP: https://markovianprotocol.com/mcp.html
- ERC-8004: https://markovianprotocol.com/erc8004.html

## Try it

The doors are live. These calls run against the public endpoint, no account required.

```bash
# Verify any record (browser or API)
curl https://api.quantsynth.net/verify/<merkle_root>

# The MCP server (Streamable HTTP, trailing slash required)
# https://api.quantsynth.net/mcp/   tools: markovian_stamp, markovian_verify

# The A2A extension definition
curl https://api.quantsynth.net/a2a/ext/provenance/v1
```

A real record, verifiable in the browser: https://demo.markovianprotocol.com

The MCP server is listed in the official MCP registry as `io.github.MarkovianProtocol/provenance`.

## This repository

- `integrations/mcp/` MCP server and test
- `integrations/a2a/` A2A reference implementation: wrapper, demo agent, demo consumer
- `integrations/erc8004/` ERC-8004 Validation Registry contract and agent demo
- `specs/` integration specifications for the MCP, A2A, and C2PA doors
- chain code: `block_schema.py`, `miner.py`, `zk_markov.py`, `market_settler.py`, `reader_settler.py`
- `whitepaper.md`

The live signal pipeline and the production API are operated privately. This repository
holds the protocol primitive, the door integrations, and the specifications.

## License

Apache-2.0. See LICENSE and NOTICE.
