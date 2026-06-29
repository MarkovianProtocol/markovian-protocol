# The Markovian Protocol
## A Proof-of-Intelligence Protocol Powered by Markov State Transition

Version 1.0 - June 2026
Markovian Protocol Research

---

## Abstract

The oracle problem is a symptom of a deeper infrastructure gap.

Every protocol that processes external data requires a trusted intermediary to bring it on-chain. Whether decentralized or institutional, that intermediary is a trust surface that can be manipulated, bribed, or taken offline. Oracle exploitation accounted for over $400 million in documented losses in 2022 alone, across protocols that had taken significant steps toward decentralization.

The underlying cause is that blockchains have no native mechanism for verifying that a computation was performed correctly on specific data at a specific point in time. Without that mechanism, external data feeds are structurally required. HTTP transmits data. SSL encrypts it. SHA-256 hashes it. OAuth authenticates identity. Digital signatures authenticate messages. None of these prove that a specific computational process executed on specific data at a specific point in time and produced a specific result. That guarantee does not exist. Every system that requires it falls back to oracles, audit logs, institutional trust, and the assumption that nobody altered the inputs.

The Markovian Protocol provides that guarantee for computations derived entirely from chain state. The starting state vector for every block is determined by the previous block hash. No external feed enters the computation. No oracle is present. The settlement is the computation itself, committed via BN128 Schnorr zero-knowledge proof and anchored permanently to the Bitcoin chain. Any party can verify the result independently, at any time, without trusting any institution.

The Markovian Protocol functions as a computational process authentication layer.

Every block, a hidden Markov matrix M is published by the protocol. Miners find the optimal state path through M using the Viterbi algorithm, given a public observation sequence derived from the previous block hash. A zero-knowledge proof binds the input, the computation, and the output simultaneously. The proof commits to M, the observation sequence, and the resulting state path. No miner can produce a valid proof without executing the algorithm correctly. No miner can reuse a proof from a prior block. The computation is cryptographically bound to the block.

The result is permanently anchored to the Bitcoin chain via OP_RETURN. Any party can verify the proof independently, at any time, without trusting any institution. The public verifier is live.

This constitutes the base protocol. The security model is sound; the proof construction is tight.

On top of it: an inference marketplace. External parties submit HMM inference problems as the block computation. Miners solve real problems as proof of work. The ZK proof verifies correct execution and is permanently on-chain. Genomics pipelines, financial risk models, clinical trial statistics, regulatory compliance models, scientific reproducibility. One protocol provides a single standard for every domain requiring proof that a computation was performed correctly on specific data.

The coin, MKV, is the access token to the standard. Demand for verifiable computation drives demand for MKV. The chain accumulates security as the standard becomes infrastructure.

The work function is computationally bounded. The trust is mathematically guaranteed. The archive is the deliverable.

---

## 1. The Problem

There are four authentication problems the internet has needed to solve.

The internet has solved three of the four fundamental authentication problems: identity (SSL, OAuth, PKI), ownership (Bitcoin, digital signatures), and message integrity (hash chains, digital signatures). The fourth problem, verifying that a specific computation was performed correctly on specific data at a specific point in time, remains structurally unsolved.

The gap is not academic. A genomics company publishes a model result. No external party can verify the model was not adjusted after seeing the data. A bank submits a risk model to regulators. No auditor can verify it ran on pre-trade data rather than post-trade data. A pharmaceutical company publishes a clinical trial outcome. No review board can verify the statistical model predates the unblinded results. The current answer is audit logs, institutional reputation, and trust. These fail silently.

The Markovian Protocol addresses this structural gap.

Nakamoto consensus established that making block production expensive and verification cheap creates a trustless ledger. The Markovian Protocol extends this insight: making computation verifiable and the proof permanent creates a trustless record of process. The security model derives from Nakamoto consensus. The output class is novel.

SHA-256 hashing produces nothing beyond the security it purchases. Miners burn electricity and discard the result. The Markovian Protocol uses the Viterbi algorithm as its work function. The result is not discarded. It is a ZK-verified computational proof, anchored permanently, verifiable by anyone.

Prior attempts at useful proof-of-work failed on determinism or trust. The Markovian Protocol addresses both. Markov state transition is deterministic, identical inputs produce identical outputs on any hardware. Zero-knowledge proofs make verification trustless and instantaneous. The computation is bounded. The proof is exact. The record is permanent.

---

## 2. Prior Art

Prior attempts at useful proof-of-work fall into three categories, each failing on a common underlying constraint.

**ML Training as PoW**

PoGO (arxiv:2504.07540, 2025) uses quantized gradient descent with Merkle proofs to prove miners are training large-scale models. Verification cost is less than training cost. The approach has been demonstrated at GPT-3 scale, 175 billion parameters.

The constraint is non-determinism. The same gradient step on the same data produces different floating point outputs on different hardware due to parallel operation ordering. No single verifier can confirm a block is correct without re-executing it. PoGO falls back to probabilistic sampling, approximating rather than proving correctness. Blocks require hours. The system cannot operate at Bitcoin-cadence block times.

Non-determinism is not a defect in PoGO's implementation. It is a property of floating point arithmetic under parallel computation. There is no patch.

**Validator-Scored Intelligence**

Bittensor (TAO, 2022) is the largest deployed proof-of-intelligence network. 4,096 active nodes provide model outputs. Validators score those outputs using other models. Rewards distribute via Yuma Consensus, a sigmoid-threshold mechanism requiring more than 50% of network stake to confirm a ranking.

The protocol's own paper states the constraint directly: "The blockchain does not trust rankings from any individual peer on the network, but rather trusts the collective rankings from all participating peers."

Output quality is subjective by construction. Useful embeddings for one validator may score poorly with another depending on training alignment. There is no objective standard. There is no single verifier. Correctness is consensus of opinion.

Proof of Useful Intelligence (PoUI, arxiv:2504.17539, 2025) is structurally identical. Workers execute AI tasks, validators score outputs, rewards flow from agreement. Output correctness is not cryptographically verified. Social consensus is substituted for cryptographic proof.

**General Optimization PoUW**

The formal security literature (arxiv:2405.19027, Cao et al., 2024) identifies the core trade-off explicitly: useful problems have structure that can be exploited. The more computationally valuable the work function, the harder it is to construct as a secure puzzle. Useful work and hard puzzles are in tension. The literature proposes matrix multiplication as a candidate work function. The construction is technically correct. The anchor to real-world data is absent.

**Common Failure Mode**

Every prior system arrives at one of two failure modes.

Non-determinism: useful computation produces different outputs on different hardware. Probabilistic approximation is not proof. Blocks cannot be independently verified. The network is required to trust validators, miners, or statistical sampling. Trust re-enters the system.

Subjective scoring: output quality is evaluated by other models or validator committees. Correctness is consensus of opinion rather than mathematical fact. The protocol cannot distinguish a competent miner from a colluding coalition without sufficient voting stake.

PoGO is non-deterministic by construction. Bittensor and PoUI are subjective by design. Neither constraint is resolvable within the respective architecture.

---

## 3. The Protocol

### 3.1 The Transition Matrix

The Markovian Protocol is built around a 3x3 stochastic transition matrix M encoding the probability of transitions between three economic regime states:

- State 0: Accumulation, capital accumulation phase, low volatility, range-bound price action
- State 1: Markup, directional price discovery, expanding participation, trend confirmation
- State 2: Distribution, late-cycle behavior, deteriorating market internals, capital rotation out

M is published by the protocol. Every node holds an identical copy. Every miner uses the same matrix. There is no ambiguity in the validity condition.

### 3.2 The Starting Vector

The starting state vector s is derived deterministically from the previous block hash via extraction function φ. φ partitions the 256-bit hash into three 8-byte segments. Each segment is interpreted as a big-endian unsigned 64-bit integer. The three values are normalized by dividing each by their sum, producing a valid 3-dimensional probability simplex: three non-negative values summing exactly to 1.0.

The function is collision-resistant by construction. Any change to the block hash produces a different starting vector. The starting vector requires no external data, no oracle, and no off-chain input. It is derived entirely from the chain state.

### 3.3 The Work Function

Given M and s, the miner:

1. Computes s_N = M^N * s, applying the transition matrix N times to the starting vector
2. Combines s_N with a nonce value to produce an input string
3. Hashes the input string
4. Checks whether the hash meets the current difficulty target

The miner iterates nonce values until a valid hash is found. This is the search problem, identical in structure to Bitcoin mining, different in computation. The protocol targets a 60-second block time. Initial transition depth N is 1,000 steps at genesis.

### 3.4 Dual Proof-of-Work

The Markovian Protocol supports two parallel mining paths. The primary path uses the Markov state transition work function described above. The secondary path uses RandomX, a CPU-optimized algorithm resistant to ASIC specialization. Both paths produce valid blocks. Both earn Kovs at protocol-defined rates. Bitcoin miners may merge mine MKV via Auxiliary Proof of Work, no additional hardware, no additional electricity.

The dual architecture distributes security across hardware types and mining communities, reducing concentration risk at the consensus layer.

### 3.5 Zero-Knowledge Verification

Every valid block submission includes a ZK proof demonstrating:

- The miner used the canonical matrix M
- The miner used the correct starting vector s derived from the previous block hash
- The miner computed exactly N transition steps
- The output vector s_N is correctly derived

The proof system uses BN128 elliptic curve Pedersen commitments combined with Schnorr sigma proofs. Commitment binds the computation to the canonical inputs. The sigma proof demonstrates correct execution without revealing intermediate state. Any node can verify the proof in milliseconds without re-executing the computation.

**Layered Proof Architecture**

The proof system is structured in four independent layers. Each layer is verifiable independently of the others.

Layer 1, Matrix provenance: GENESIS_M is committed via Pedersen commitment against a deterministic hash of 29,795 market observations across five instruments spanning 2000 to present. The training hash is published. Any party can reproduce it from the same dataset. The commitment cannot be opened to a different matrix without invalidating the proof.

Layer 2, Computation correctness: each Markov transition step carries a Schnorr sigma proof on BN128. One proof per output component, three per step, N proofs per block. Verification does not require re-computation. A single invalid transition invalidates the block.

Layer 3, Input provenance: signal synthesis commits to its inputs before execution. Gate state, price data, regime vector, and agent outputs are hashed and committed prior to synthesis. The input commitment is linked to the output Merkle root in a single provenance record. The two cannot be constructed independently.

Layer 4, Miner credibility: regime predictions are committed on-chain prior to resolution via SHA256(address, ticker, predicted regime, target block, nonce). At resolution the chain compares the committed prediction against the actual observed regime. Governance weight is derived from on-chain prediction history, not declared by the participant.

The entire system rests on a single security assumption: discrete logarithm hardness over BN128. The assumption holds that, given a point Q on the BN128 curve and a generator G, it is computationally infeasible to find k such that Q = kG. No polynomial-time algorithm is known. The assumption has resisted the cryptographic community since 1976. Breaking any layer of the Markovian proof system requires solving this problem. Curve parameters and generator points are fixed at genesis and committed to the protocol specification. They do not change without a governance vote that itself requires a new ZK proof of correct parameterization.

### 3.6 Difficulty Adjustment

The network targets a 60-second block time. Every 2,016 blocks, the protocol measures actual block time against target and adjusts N, the transition depth, accordingly. Higher N requires more computation per mining attempt. Lower N requires less. The adjustment window mirrors Bitcoin's two-week retarget cycle, adapted to the 60-second target.

### 3.7 What Proof-of-Intelligence Means

Proof-of-intelligence is not a claim about the miner. It is a claim about the validity condition.

In Bitcoin, a hash is valid if it has sufficient leading zeros. The target is arbitrary. It carries no information about markets, regimes, or economic structure. The work is discarded the moment it is verified. The network state after the block is identical to its state before, except for the ledger entry.

In the Markovian Protocol, a hash is valid only if it encodes a state transition consistent with the canonical matrix M. M is not an arbitrary target. It is an empirically derived model of market regime dynamics, fitted to fifteen years of price data, updated through Byzantine fault tolerant governance, and committed to the chain with zero-knowledge proof. The validity boundary is derived from structured reasoning about market dynamics.

Miners do not perform the reasoning. They search for valid transitions within a boundary the protocol has defined. The reasoning is in the matrix. The matrix is the product of the governance process.

This is the precise sense in which the work is proof-of-intelligence: not that computation is intelligent, but that the standard of correctness is derived from an intelligence process rather than an arbitrary numerical target. The miner proves it found a true transition. The protocol determined what true means.

**Proof as a Function of Intelligence**

Validator-scored intelligence networks define useful output, then route that definition through consensus. The validator vote becomes the proof. Consensus of opinion does not constitute a cryptographic guarantee. It is subject to the same failure modes as any social mechanism: coordination, capture, and drift under adversarial pressure.

The Markovian Protocol separates the two claims. The intelligence is encoded in M, an empirical model derived from market data and ratified by governance. The proof verifies that M was applied correctly to the inputs in evidence. The miner's intent is not evaluated. The computation either satisfies the proof or it does not.

No deployed proof-of-intelligence network submits this claim to cryptographic verification. The Markovian Protocol does.

**The Archive as Competitive Moat**

A quant fund can train its own Hidden Markov Model on price data. The computation is not proprietary. The math is well-documented. The model they produce is private, unverified, and has no history anyone else can inspect.

The archive cannot be replicated.

Fifteen years of verified, ZK-proven, Merkle-anchored regime history compounds daily. Each block adds a labeled data point with a cryptographic lineage terminating in a Bitcoin block hash. The archive is not a static export. It is a live ledger of every regime classification the protocol has produced, each with a provenance chain no party can alter.

Reproducing the archive requires running the protocol from genesis. There is no shortcut. A fund that trains its own HMM has a model. The Markovian archive is a verified historical record that no single institution produced or controls. Any party can reconstruct it from the chain and confirm every entry is correct. No vendor, no database, and no institution can make that claim.

---

## 3.8 The Reader Layer

The mining layer produces the verified archive. Interpretation of archive state is a separate protocol layer.

**Light Reading**

As of protocol v1.0, light reading is bundled into the mining work function. Every miner that submits an accepted block automatically classifies the resulting regime state and posts that classification on-chain. No additional setup. No external API. The classification is the argmax of s_output, computed locally from work already performed.

Every miner's light reads accumulate as a permanent on-chain participation record. Accuracy against the canonical regime compounds over time. The record cannot be revised.

**Deep Reading**

A deep reader brings their own transition matrix.

The protocol's canonical M is an empirical model derived from fifteen years of market data, fitted via Hidden Markov estimation, and ratified by validator governance. It is the network's best current model. It is not the only model.

A deep reader trains their own M on their own data and commits a signed regime prediction before the target block mines. The commitment is a hash of the predicted regime, target block height, and a secret nonce. After the block mines, the deep reader reveals the prediction. The chain compares it against the observed s_output and scores it.

If the model outperforms the canonical M, the record reflects it. If it underperforms, the record reflects that too. The chain does not evaluate the model. It records the output and scores the prediction.

**Reader Bonus Pool**

Each block generates a reader bonus pool of 5,000,000 Kovs reserved for validated deep readers of that block. Deep readers who correctly called the regime split the pool pro-rata, weighted by prediction confidence. There is no cap on the number of deep readers per block. The pool is fixed per block. The share is smaller as more deep readers participate.

Total Kov issuance per block: 50,000,000 to the miner. Up to 5,000,000 distributed to validated deep readers. A miner who also participates as a deep reader receives both.

**Canonical M**

The canonical M is not a public participant role. It is an institutional access tier.

The protocol operates a synthesis layer combining verified chain state, archive depth, and multi-model regime signals into a unified market intelligence output. This layer is not open to the public network. It runs on protocol infrastructure.

Institutional buyers and quantitative funds access canonical M via a credentialed API, priced in BTC. Every output carries a ZK proof committing to the inputs used, the models applied, and the execution trace. Buyers receive the signal and the proof.

The public network produces the archive. Canonical M produces the product.

**The Tournament**

Multiple deep readers applying independent models to the same block produce a convergence signal. When models trained on different datasets and different frequencies agree on MARKUP, the confidence is not the confidence of one model. It is the confidence of a distributed computation that arrived at the same conclusion from different starting points.

Divergence is equally informative. A split read across deep readers signals genuine regime ambiguity. The spread between agreement and disagreement becomes a confidence metric available to any downstream system.

The probability structure is concrete. If each deep reader operates independently and carries a 20% individual error rate, ten deep readers converging on the same regime has a combined false-convergence probability below 0.20^10. Less than one in ten billion. The signal is not ten opinions. It is a distributed computation with a falsifiable error bound.

The scoreboard is public. Every deep reader's accuracy record is on-chain and verifiable. It cannot be revised.

**Reader Incentives**

Light readers accumulate a participation record. That record is the basis for advanced access tiers as the protocol matures.

Deep readers earn from the reader bonus pool: 5,000,000 Kovs per block, pro-rata on prediction accuracy. Deep readers that consistently outperform the canonical M earn governance weight proportional to their demonstrated edge. In Phase 5, archive licensing revenue distributes to network participants proportional to contribution and verified accuracy. The incentive is a fee stream tied to demonstrated performance, not declared intent.

Early deep readers accumulate accuracy records before the reader network is dense. That record is the genesis position.

**Deep Reader Mechanics**

The commit-reveal cycle operates on a per-block basis.

Before a target block mines, the deep reader applies their own M to the current block's s_input and derives a predicted regime. They submit a commitment:

```
commitment = SHA256(predicted_regime | target_height | wallet | nonce)
```

The commitment is posted to the chain before the target block mines. The prediction is locked. It cannot be changed.

After the target block mines, the deep reader reveals: predicted_regime, nonce. The chain verifies the revealed values hash to the committed hash. If verification fails, the reveal is rejected. The reader receives nothing.

If verification passes, the chain fetches s_output from the target block and derives the actual regime via argmax. The prediction is scored.

**Scoring**

Scoring is confidence-weighted. A correct prediction earns a score equal to the reader's stated confidence at commitment time. An incorrect prediction earns zero.

If the deep reader committed MARKUP at 0.85 confidence and MARKUP was the actual regime, their score is 0.85. If they committed MARKUP at 0.85 and the actual regime was DISTRIBUTION, their score is 0.

This structure punishes overconfident wrong calls and rewards accurate conviction. A reader who always commits 1.0 confidence and is frequently wrong earns less per correct call than a reader who commits calibrated confidence and is frequently right.

**Pro-Rata Pool Split**

Each block generates a reader bonus pool of 5,000,000 Kovs. Among all deep readers who correctly called the regime for that block, the pool splits pro-rata by confidence score.

Example: block 115,477, actual regime MARKUP, three correct deep readers.

| Reader | Confidence | Share | Kovs |
|--------|-----------|-------|------|
| A | 0.85 | 39.2% | 1,958,525 |
| B | 0.72 | 33.2% | 1,658,986 |
| C | 0.60 | 27.6% | 1,382,488 |
| Total | 2.17 | 100% | 5,000,000 |

Any remainder from integer division goes to the highest-confidence correct reader.

**Rollover**

If no deep readers submitted a correct reveal for a block, the pool rolls forward. The next block's pool is 5,000,000 plus the accumulated rollover. Unclaimed pools compound across consecutive blocks where all readers were wrong or absent. A single correct call on a block with a large accumulated rollover pays out the full accumulated amount.

The rollover mechanism makes deep reading more attractive during periods of genuine regime ambiguity, exactly the periods where an accurate model has the most edge.

**The Separation of Computation and Intelligence**

Miners prove the computation happened correctly. Deep readers prove an independent intelligence is sound.

The two claims are independent. A miner with perfect ZK proofs and no understanding of markets produces valid blocks. A deep reader with a superior model produces accurate predictions. The protocol needs both. Neither replaces the other.

Miners compute state. Deep readers interpret state. Canonical M synthesizes state. The archive accumulates all three. The coin prices the combination.



---


## 4. The Coin

Name: Markoin
Ticker: MKV
Base unit: Kov (1 MKV = 100,000,000 Kovs)

The supply is dynamic. There is no cap. There is no halving schedule. Emission is tied to verified network output, governance cycle accuracy, archive depth, validator participation, and commodity volatility. High volatility and active governance cycles produce higher emission. Stable, low-governance periods produce lower emission. The supply reflects the demonstrated output of the network.

Each Kov in circulation represents a unit of verified, ZK-proven, Merkle-rooted computation that the network produced and the governance layer ratified. Emission is evidence of work performed, not a schedule imposed in advance.

Standard UTXO model. Wallets hold Kovs. Transactions are signed, broadcast to the network, and included in blocks by miners.

Kovs enter circulation through four paths: mining (performing and proving real computation), deep reading (committing and revealing verified regime predictions), and protocol-defined deposit routes for BTC, ETH, and XMR. Every Kov has a corresponding on-chain event that produced it. There is no issuance by decree, no team allocation, no minting without work or verified exchange.

### 4.1 Commodity Anchoring

The Markovian Protocol models economic regime transitions driven by real commodity flows. Oil supply shocks trigger distribution regimes. Gold accumulation signals risk-off markup. Copper expansion precedes economic growth phases. The protocol measures these transitions directly.

The Markoin derives value from signal accuracy on real-world commodity flows, not supply constraint. As the governance model improves, the signal becomes more accurate. As the signal becomes more accurate, the archive becomes more useful. Utility drives demand. Demand prices the coin.

### 4.2 Token Economics, Fisher's Equation of Exchange

The Kov economy is governed by Irving Fisher's Equation of Exchange:

**MV = PT**

- **M**, Kovs in circulation. Dynamic supply tied to verified network output. Emission rate is a governance parameter.
- **V**, Velocity. The rate at which Kovs change hands to access archive data.
- **P**, Price. Cost of archive access denominated in Kovs.
- **T**, Transactions. Archive queries, data pulls, governance votes.

As the archive deepens, T grows. Archive depth is the primary demand driver. Fisher's equation requires V and P to absorb the difference.

In most token systems, velocity collapses as holders accumulate. The Markovian Protocol addresses this structurally. Archive access requires Kovs to be staked for the duration of the session. Staking is enforced at the protocol layer: archive access calls require a valid staked position in the calling wallet. No stake, no call. The floor on V is not behavioral. It is a protocol rule.

The emission function has defined bounds. A governance parameter caps maximum emission at 2x the trailing 30-day average rate. A floor maintains minimum emission at the rate required to keep miner participation above the network security threshold. Emission runaway is not possible without an explicit governance vote to remove the cap, which itself requires a BFT supermajority and a 2,016-block time-lock. The bounds are visible on-chain at all times.

### 4.3 The BTC Settlement Layer

Settlement currency: Bitcoin.

Data buyers pay in BTC. Bitcoin is the universal settlement layer, the most trusted, most liquid, most decentralized asset in existence. The protocol requires no fiat bridge. It uses the one that already exists.

When a data sale occurs, BTC enters the protocol. Network participants who contributed verified work, miners, validators, contributors, receive a proportional share of archive access fees based on Kovs staked. The distribution mechanism is fee-sharing, not issuance. Kovs are the access and governance instrument. BTC is the settlement instrument.

The closed loop:

1. Archive depth grows with every block mined.
2. Archive utility drives T upward.
3. BTC from archive access fees flows to network participants.
4. Staking demand increases to participate in fee distribution.
5. V stabilizes. Fisher holds. P reflects genuine demand.

Early miners earn Kovs at the lowest acquisition cost. The archive has not yet proven its depth. When the first institutional buyer pays BTC for access, every participant with staked Kovs receives a share of that fee immediately. The incentive is a fee stream, not a narrative.

MKV is priced by demand. Settled in Bitcoin. Earned by verified work.

### 4.4 Treasury Reserve Floor

Kov classes differ in their backing and treasury claims.

Three classes exist:

**Mined Kovs.** Created by computational work. Backed by electricity, hardware, and time. No treasury claim.

**Purchased Kovs.** Issued against BTC deposit at 1,000 Kovs per satoshi. Every satoshi received enters the protocol treasury and stays there until the corresponding Kovs are redeemed.

**Faucet Kovs.** Promotional. Distributed to bootstrap participation. No treasury backing.

The protocol treasury holds BTC at 1B7xDcg1kVSAP3EFumoNui2pmChd7q2t1w. This address is public. The balance is verifiable without trusting anyone.

The floor is simple: while treasury reserves cover outstanding purchased Kovs, those Kovs are redeemable at the purchase rate. Treasury BTC divided by purchased Kovs outstanding equals the hard floor. If you bought at 1,000 Kovs per satoshi, the treasury holds that satoshi against your claim.

Mined Kovs have no floor. Their value is what the market assigns. This is correct. Mined supply reflects earned value. Purchased supply is pegged by construction.

The protocol does not guarantee a price. It guarantees a floor while reserves hold.


---

## 5. The Governance Layer

### 5.1 Matrix Governance

The transition matrix M is a protocol parameter subject to update. Validators propose revised matrix weights based on validated historical signal data. The network votes. A BFT supermajority of 2/3 or more approves or rejects. Ratified updates activate after a mandatory time-lock delay.

The matrix improves with the archive. Each governance cycle has access to more verified regime history than the last. The protocol's model of market structure converges toward accuracy over time.

### 5.2 Byzantine Fault Tolerance

Governance uses BFT consensus. Up to 1/3 of validators may be malicious or offline without compromising the result. As long as 2/3 of validators are honest, correct matrix updates pass and malicious proposals fail.

### 5.3 Commit-Reveal Voting

Validators submit a cryptographic hash of their vote in the commit phase. Votes are revealed only after the commit window closes. No validator can observe the emerging consensus and adjust their position accordingly. Strategic position changes are not possible.

### 5.4 Time-Lock Activation

Ratified matrix updates do not activate immediately. A mandatory delay of 2,016 blocks provides the network with a review window. Any node that identifies a compromised matrix update can exit or fork before activation.

### 5.5 Validator Credibility

Validator voting weight is proportional to historical accuracy. Nodes whose proposed matrix updates improved network performance earn greater governance influence. Credibility is derived from on-chain prediction history. It cannot be purchased or declared.

---

## 6. Multi-Chain Architecture

The protocol uses three independent chains, each serving a distinct function.

**Bitcoin, the anchor.**

Every block the Markovian Protocol produces is committed to Bitcoin via OP_RETURN. A 28-byte Merkle root, prefixed with the MKV magic bytes, is embedded permanently in the Bitcoin chain. Every regime classification the protocol has ever produced can be independently verified against the Bitcoin chain, in sequence, by any party, permanently. The archive cannot be rewritten. The provenance cannot be forged.

Direct BTC deposits are accepted. Send BTC to the protocol address with an OP_RETURN containing `MKV:YOUR_ADDRESS`. The deposit watcher detects the transaction. After three confirmations, Kovs are issued at the protocol rate.

**Ethereum, the oracle.**

The Markovian Protocol's regime classifications, ZK proofs, and Merkle roots are posted on-chain via the MarkovianOracle smart contract. Any Ethereum application can query live regime state for any covered instrument and build regime-gated logic against it.

The oracle contract accepts `updateBatch()` calls from the protocol's reporter address. The BN128 Pedersen commitment hash is included in every batch. The data is cryptographically linked to the source computation.

`lockAndMint()` is the Ethereum-native participation path. Lock ETH in the oracle contract for a defined period. The contract issues Kovs proportional to the amount locked and the lock duration. The lock expires, ETH returns. The Kovs remain.

**Monero, the private settlement rail.**

Bitcoin transactions are permanently visible. Institutional buyers acquiring regime signal on a covered instrument are revealing a position. That purchase is alpha-sensitive. It will not be made on a public ledger.

XMR is accepted. Cryptographic proof of payment is the only credential required. No account, no email, no identity. The protocol does not record who paid.

**Unified Kov Issuance.**

All Kov issuance routes through a single ledger regardless of origin chain. BTC deposit, ETH lock-and-mint, XMR payment, and direct mining all record to the same table. BTC is the primary settlement instrument. The source chain transaction hash serves as the deduplication key. Double issuance is not possible.

Issuance rates reflect the properties of each instrument. Rates are governance parameters, adjustable by validator supermajority as the network matures.

---



---

## 6.8 Verifiable AI Inference: The Input Integrity Gap

The field called verifiable AI, zkML, provable inference, trustless model execution, has attracted significant capital and research effort. The goal is correct: AI systems that produce outputs no one can tamper with. The implementations share a structural flaw.

**What zkML systems prove.**

EZKL wraps arbitrary neural networks in Halo2 circuits. Modulus Labs does the same with StarkWare. Risc Zero runs PyTorch inside a RISC-V zkVM and produces a ZK proof of execution. Each of these systems proves one thing: the computation ran correctly on the inputs it received.

They do not prove the inputs were not corrupted before execution began.

If a fraud detection model receives manipulated transaction data before inference, the ZK proof confirms the model ran correctly on manipulated data. The proof is valid. The result is fraudulent. The attack surface is not the computation. It is the data pipeline feeding the computation. Every zkML system in production today has this vulnerability. It is not a bug in their implementation. It is a structural gap in the approach.

**What Markovian proves.**

The starting state vector for every Markovian block is derived deterministically from the previous block hash. The observation sequence is a function of chain state. No external data feed enters the inference computation at any point.

This means the inputs cannot be corrupted before execution. There is no data pipeline. There is no external source. The chain state is the input, and the chain state is incorruptible by construction.

Every Markovian block is a ZK-proven AI inference where input integrity is structural rather than assumed. The BN128 Schnorr proof commits the Viterbi execution. The block hash pins the starting state. Any verifier reproducing the computation from the same block hash gets the same result. The proof is deterministic, immediate, and requires no trusted intermediary.

**The competitive distinction.**

zkVMs prove execution integrity. Markovian proves execution integrity plus input integrity, for the specific case where the computation is derived from chain state. These are different guarantees.

A zkML system that proves a credit model ran correctly cannot prevent a lender from feeding it pre-selected applicants. A Markovian inference cannot be fed pre-selected inputs because it has no input channel to manipulate. The economic regime state is what the chain says it is.

This is not a general-purpose AI proving system. It does not replace EZKL for arbitrary neural networks. For computations that can be derived from chain state, it provides a stronger guarantee than any existing zkML approach because it removes the trust assumption at the data layer rather than hardening it.

**AI inference as proof of work.**

In every prior blockchain, proof of work produces entropy. SHA-256 hashes have no value outside the consensus mechanism. Markovian's proof of work is an HMM inference. The output of every block is a verified economic regime classification, cryptographically bound to the block hash and permanently anchored to the Bitcoin chain.

The inference record and the consensus mechanism are the same object.

This has not been done before. Mining and useful AI inference have been proposed together but always failed at the binding problem: when external value exceeds block reward, miners pursue the work independent of chain integrity. The ZK proof solves this. A valid Markovian proof cannot be produced for a different block context. The inference is cryptographically bound to this block hash, this chain height, this moment. The work and the ledger are inseparable.

**The regulatory context.**

The EU AI Act requires traceability of high-risk AI decisions. Current AI systems provide logs. Logs can be altered. A ZK proof anchored to Bitcoin cannot be. For regulated industries, financial risk, clinical trials, insurance underwriting, credit scoring, the difference between a log and a proof is the difference between a compliance claim and a compliance guarantee.

Markovian is the first system where that guarantee is produced as a byproduct of consensus. Every block mines the chain and produces an auditable AI inference record simultaneously. No additional infrastructure is required for the audit trail. It is the protocol.

**What this opens.**

Any party that requires proof of correct AI inference on incorruptible inputs has no current solution. Markovian provides one for the computation class it covers. The inference marketplace in Phase 5 extends this to external problem submissions, where submitters lock MKV and receive ZK-proven inference results bound to the block hash at submission time.

The input integrity problem is not solved in the general case. For chain-state-derived computation, it is solved structurally. That structural solution is the foundation the verifiable AI field has been missing.


---

## 7. Security Model

**Precomputation Attack:** The starting vector s is derived from the previous block hash, which is unknown until the block is mined. Precomputed transition tables map to a starting state that does not exist until that moment. An attacker precomputing against all possible future block hashes faces a search space equivalent to brute-forcing SHA-256. The nonce challenge is fresh every block.

**Approximation Attack:** ZK proofs commit to the exact output of M^N * s. An approximation that differs from the canonical result by even a single value produces a commitment that fails Layer 2 verification. The proof does not demonstrate proximity. It demonstrates equality. There is no partial credit.

**Guessing Attack:** At N transition steps, s_N converges toward the stationary distribution of M. The convergence path through N intermediate states is not enumerable without performing the computation. Guessing the output without applying M correctly is equivalent to guessing the discrete log of a BN128 commitment. The ZK proof catches it.

**Matrix Manipulation Attack:** The genesis M is Pedersen-committed against a published training hash. Any substituted matrix produces a proof that fails Layer 1 verification. A validator wishing to change M has one path: propose a governance update, acquire a 2/3 BFT supermajority, survive the 2,016-block time-lock review period. Unilateral substitution is not possible.

**51% Attack:** Same as Bitcoin. A miner controlling 51% of hash power can reorder or suppress blocks. It cannot produce invalid ZK proofs and cannot forge a regime classification. The data layer is protected even when the consensus layer is under attack.

**Long-Range Attack:** Every block's Merkle root is anchored to the Bitcoin chain via OP_RETURN. An attacker acquiring old validator keys cannot silently rewrite archive history. Doing so requires rewriting the corresponding Bitcoin blocks. Bitcoin's security model protects the Markovian archive's provenance chain.

**Governance Capture:** Four independent defenses operate simultaneously. A 2/3 BFT supermajority threshold requires capturing two-thirds of weighted validator stake. Commit-reveal voting prevents bandwagon manipulation during the commit window. The 2,016-block time-lock provides an exit window for any node that detects a compromised update. Fork rights provide the ultimate check: any participant can reject a malicious matrix and continue on the prior one. Circumventing all four against an active participant base is not a realistic attack surface.

---

## 8. Roadmap

Phase 1, Specification: white paper, math specification, protocol v1.0, community formation.

Phase 2, Testnet: PoW function, ZK proof system, P2P networking, block explorer.

Phase 3, Governance: validator registration, first matrix governance cycle, BFT implementation.

Phase 4, Mainnet: genesis block, wallet release, MKV issuance begins.

Phase 5, Data Marketplace: archive API launch, BTC settlement layer live, institutional access tiers, fee distribution to network participants begins.

---

## 9. Conclusion

Bitcoin answered the double-spend problem with energy expenditure. The work is real. The output is a secure ledger.

The Markovian Protocol answers the same security requirements with structured computation, the mathematics of state transition, verified by zero-knowledge proofs, governed by Byzantine fault tolerant consensus, and compounding in accuracy over time as the archive deepens.

The work is not discarded. It is verified, archived, and accumulated. The protocol grows more accurate with every block it produces. The supply reflects the cumulative output of the network.

The smallest unit is a Kov. Every Kov is cryptographic evidence that the network produced a verified regime classification. The protocol determined what valid means.

---

## 6.5 Verifiable Inference Markets

Every block in the Markovian Protocol runs a Viterbi computation. The hidden Markov matrix M is applied to an observation sequence derived from the block hash. The result is a verified state path. The ZK proof confirms correct execution.

In the base protocol, M is generated by the protocol itself. The computation is real. The answer is provably correct. But the problem being solved is random. No external party submitted it. No external party benefits from the result.

This changes in Phase 5.

**The problem with prior useful proof-of-work.**

Primecoin. Gridcoin. Curecoin. Each attempted to make mining produce something valuable. Each failed at the same point.

When the external value of the work exceeds the block reward, miners pursue the work regardless of chain integrity. Security decouples from the ledger. Transaction validity becomes secondary. The alignment breaks because the work and the chain are loosely coupled. A miner can solve the useful problem without mining a valid block.

SHA-256 cannot fix this. Hashing has no structure. There is nothing to bind.

**The ZK binding solution.**

Markovian can fix this. The ZK proof does not only verify that Viterbi was executed. It commits to the block hash, the M matrix, the observation sequence, and the output state path simultaneously. A valid proof for block N cannot be produced for block N-1 or any other context. The computation is cryptographically bound to the block.

This makes useful proof-of-work structurally sound for the first time.

**The three-layer structure.**

**Protocol Layer.** The Markovian chain. Consensus, ZK proofs, MKV ledger. Does not know what problem it is solving. Does not change. This is the trust machine.

**Inference Marketplace.** An application protocol on top of the chain. External parties submit HMM inference problems, lock MKV in escrow, and receive verified results when the block is mined. The marketplace handles problem routing, escrow logic, and settlement. Multiple competing marketplace implementations can run simultaneously. The protocol layer is indifferent to them.

**Vertical Applications.** Genomics pipelines, financial analytics platforms, anomaly detection systems. These applications submit problems to the marketplace and consume the verified results. They do not interact with the chain directly. They do not need to understand Viterbi or ZK proofs.

**Who buys verified inference.**

Hidden Markov models are not an academic exercise. They are the core primitive behind gene prediction (GENSCAN, Augustus, HMMer), market regime detection, network intrusion detection, and speech recognition. Each of these domains has established commercial buyers who currently pay for computation without cryptographic proof of correctness.

A genomics company submits a gene sequence analysis problem. A hedge fund submits a regime classification problem on proprietary price data. An insurance actuary submits a risk state inference problem. Each locks MKV, receives a ZK-verified result, and can prove to any third party that the computation was executed correctly. The proof is permanent and public. The input data can remain private.

**MKV demand loop.**

Every problem submitted to the marketplace requires MKV. Miners earn MKV block rewards plus MKV problem fees. The more commercially valuable problems route through the chain, the greater the demand for MKV, the more valuable mining becomes, the more security the chain accumulates.

This is a positive feedback loop that does not exist in Bitcoin. Bitcoin's security is proportional to the price of electricity. Markovian's security is proportional to the utility of verified inference. As the inference marketplace grows, the base protocol becomes more secure without any changes to the consensus layer.

**Extension to probabilistic graphical models.**

The Viterbi algorithm is one inference method on one model class. The ZK proof system is not limited to it.

Bayesian networks, hidden semi-Markov models, factorial HMMs, conditional random fields, and dynamic Bayesian networks all operate on the same principle: infer hidden state from observable evidence. Each can be represented as a structured computation with a verifiable output.

A future protocol upgrade extending the proof system to the broader class of probabilistic graphical models expands the inference marketplace to cover medical diagnosis, supply chain risk modeling, climate state inference, and any domain where hidden state must be inferred from observable data.

The chain becomes a general-purpose verifiable inference engine. Not a ledger with a side computation. A trust machine for probabilistic reasoning.

**What does not change.**

The base protocol does not change. The consensus mechanism does not change. MKV remains the only currency. No new tokens are issued per vertical. The marketplace is additive. The trust machine runs underneath it regardless of whether any problems are submitted.

The base layer works like Bitcoin. The inference marketplace is the business built on top of the trust machine.


---

## 6.6 The Verifiable Computation Standard

The Markovian Protocol is a blockchain. It is also something the internet does not have.

HTTP is a standard for transmitting data. SSL/TLS is a standard for encrypting it. SHA-256 is a standard for hashing it. JWT is a standard for authenticating identity.

There is no standard for verifying that a computation was performed correctly on a specific dataset at a specific point in time.

This is the gap the Markovian Protocol fills.

**The problem with institutional trust.**

A genomics company publishes a gene prediction result. No external party can verify the model was not adjusted after seeing the data. A bank submits a risk model to regulators. No auditor can verify the model ran on Monday's data rather than Tuesday's after the position moved. A pharmaceutical company publishes a clinical trial outcome. No review board can verify the statistical model was not recalibrated after unblinding.

The current answer is audit logs, institutional reputation, and trust. These fail silently. Logs can be altered. Institutions have incentives. Trust is not proof.

**The standard procedure.**

The Markovian Protocol defines a five-step standard for committing and verifying any computation.

One. The submitting party locks the dataset and model parameters in a cryptographic commitment before execution begins. The input is sealed before the output is known.

Two. Markovian miners execute the computation as proof of work. The hidden Markov matrix M encodes the model. The observation sequence encodes the dataset. The Viterbi algorithm produces the result.

Three. A zero-knowledge proof binds the input commitment to the output state path. The proof verifies that this model ran on this data and produced this result. Not a different model. Not different data.

Four. The result and proof are posted on-chain. The Merkle root is anchored to the Bitcoin chain via OP_RETURN. The record is permanent. It cannot be altered, removed, or backdated.

Five. Any third party verifies the proof independently, at any time, without trusting any institution. The public verifier is live at api.quantsynth.net/verify.

**What this replaces.**

This is not a crypto product. It is infrastructure. The same category as SSL certificates: something every institution eventually requires whether or not they understand the cryptography.

A regulator requiring cryptographic proof of model execution. A clinical trial board requiring proof that the statistical model predates the outcome data. An exchange requiring proof that a risk engine ran on pre-trade data. A scientific journal requiring proof of computational reproducibility.

None of these require the submitting party to understand zero-knowledge proofs, hidden Markov models, or blockchain consensus. They require a verifiable result and a proof. The protocol provides both.

**The standardization path.**

Protocols become standards when they solve a problem that institutions cannot solve any other way. SSL became the standard for web encryption because the alternative was plain text transmission of passwords. HTTPS became mandatory. Nobody debated it.

Verifiable computation will follow the same path. The question is which protocol defines the standard.

The ZKProof standardization body, NIST post-quantum cryptography working groups, and ISO data provenance committees are the bodies that transform a protocol into the protocol. The Markovian construction, BN128 Pedersen commitments with Schnorr sigma proofs over Viterbi execution, is a concrete candidate for that standardization process.

**A single chain provides a single standard across all verticals without issuing new tokens per use case.**

Every vertical that requires verifiable computation runs through the same protocol. Genomics, financial risk, clinical trials, regulatory compliance, scientific reproducibility. MKV is the access token to the standard. Demand for the standard drives demand for the token. The chain accumulates security as the standard becomes infrastructure.

The work function is computationally bounded. The trust is mathematically guaranteed. The archive is the deliverable.


---

## 6.7 Scope and Limits of the Guarantee

The Markovian Protocol makes one claim. The computation was executed correctly on these specific inputs. The model did not change after seeing the results. The output is mathematically bound to the input. That binding is permanent and verifiable by any party, at any time, without trusting any institution.

That is the guarantee. Nothing more.

**What the protocol does not prove.**

The inputs were honest.

Fabricated data can be committed to the chain as easily as real data. The zero-knowledge proof verifies correct execution of the Viterbi algorithm on whatever was submitted. A cherry-picked observation sequence, a backdated dataset, a filtered patient cohort, each produces a valid proof. The inputs were fraudulent. The proof is technically correct. The distinction matters.

This is the oracle problem. It is not unique to the Markovian Protocol. It exists in every system that computes on externally supplied data. Chainlink is an entire company addressing just this for decentralized finance price feeds. No blockchain solves it from within the consensus layer alone.

**What partially addresses it.**

Three complementary layers can extend the guarantee toward data authenticity. None of them are the Markovian Protocol. All of them compose with it.

Signed data sources. When data originates from a device or institution that cryptographically signs its outputs, a genomic sequencer with hardware attestation, a regulated exchange with a signed feed, a sensor operating inside a secure enclave, that signature is bundled into the Markovian commitment. The on-chain proof then binds: this data came from this signed source, and this computation ran on it. The chain verifies the signature alongside the computation. Fabrication requires compromising the signing key, not just the submitter's intent.

Trusted Execution Environments. Intel SGX and AMD SEV produce hardware attestations proving that a specific computation ran in an isolated environment on data pulled directly from a source, without the operator being able to alter either. Bundled with a Markovian ZK proof, a TEE attestation proves data origin and computation correctness simultaneously. The DECO protocol from Cornell demonstrates this approach for private web data.

Multi-party commitment. Requiring independent institutions to commit to the same dataset separately before any results are computed raises the cost of fabrication from individual misconduct to coordinated collusion. When three independent parties each produce a Markovian proof showing the same result from independently committed data, the on-chain record of all three is permanent. Collusion is not impossible. It becomes auditable.

**What the protocol does catch.**

Cherry-picking across runs. A submitter testing five models against the same dataset looking for a favorable outcome produces five on-chain records. The pattern is visible. What was invisible in private computation becomes an auditable history of model selection. The economics of fraud change even when data authenticity cannot be fully guaranteed.

Post-hoc model adjustment. The commitment seals the model before execution. Any model altered after seeing preliminary results produces a different commitment. The chain records both. Adjustment is detectable.

Backdated results. The Merkle root is anchored to the Bitcoin chain. The timestamp is the Bitcoin block time. Claims that a computation preceded its on-chain commitment are falsifiable against the permanent record.

**The court reporter analogy.**

A court reporter guarantees the transcript is exactly what was said. They cannot guarantee the witnesses told the truth. The transcript is provably accurate. The content may not be.

The Markovian Protocol is the court reporter. It proves the model ran on the data submitted. It does not prove the data submitted was the right data.

Stating this clearly is not a limitation to apologize for. It is the precise scope of a real guarantee. Systems that overstate their guarantees fail under scrutiny. Systems that state their guarantees exactly earn the trust of the people who matter.

The complementary layers exist. They compose with this protocol. The full stack, signed sources plus TEE attestation plus multi-party commitment plus Markovian proof, addresses data authenticity at a level no prior system has achieved. The Markovian Protocol provides the foundation. The stack builds from there.
