# Markovian Protocol

Proof-of-Intelligence blockchain. Miners compute verified Markov state transitions instead of arbitrary hashes. The work is the product.

## What it is

Bitcoin SHA-256 secures the chain. The work function replaces brute-force hashing with Markov matrix multiplication — each valid block contains a BN128 ZK proof attesting that the miner computed `s_N = M^N × s`, where:

- `M` is the protocol-published transition matrix (current market regime model)
- `s` derives deterministically from the previous block hash
- The ZK proof (Pedersen commitment + Schnorr sigma) is verified on-chain

Block output = verified market regime classification: ACCUMULATION / MARKUP / DISTRIBUTION.

## Live network

- Chain height: 114,000+ blocks
- Block time: ~60 seconds
- 3 active miners (genesis)
- Explorer: [chain.quantsynth.net](https://chain.quantsynth.net)
- API: [api.quantsynth.net/tip](https://api.quantsynth.net/tip)

## Mine

```bash
git clone https://github.com/MarkovianProtocol/markovian-protocol.git
cd markovian-protocol
pip install requests numpy py_ecc
python3 miner.py --address YOUR_MKV_ADDRESS
```

No GPU required. Runs on any hardware. CPU-bound on the ZK proof generation.

## Files

| File | Purpose |
|---|---|
| `miner.py` | Miner loop — polls /tip, computes work, submits blocks |
| `block_schema.py` | Block structure, genesis M, extraction function φ |
| `zk_markov.py` | BN128 Pedersen commitment + Schnorr sigma proof |

## Protocol

- Coin: MKV (unit: Kov, 1 MKV = 100,000,000 Kov)
- Reward: 50,000,000 Kov per block
- Difficulty: adjusted via transition depth N
- Supply: dynamic, tied to verified network output
- Settlement: BTC (transparent) + XMR (private)

## Whitepaper

[whitepaper.md](whitepaper.md) — full protocol specification including ZK security proof, emission model, and designer layer.

## License

MIT
