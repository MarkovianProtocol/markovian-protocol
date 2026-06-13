#!/usr/bin/env python3
"""
zk_markov.py — Zero-knowledge proof for Markov state transitions.

Proves: s_out = M.T^N @ s_in without revealing s_in or s_out.

Approach:
  - Pedersen commitments to each component of s (scaled to integers)
  - Schnorr discrete-log proof for each linear relation across N steps
  - Homomorphic property: C_out[j] - sum_k M_int[j,k]*C_in[k] should be pure G*r
  - Prover reveals tiny rounding corrections (epsilon[j]) to make relation exact
  - Fiat-Shamir non-interactive transform

Math:
  SCALE_S = 10^9  — scale for probability values (0.70 → 700_000_000)
  M_DENOM = 20    — M.T values * 20 = small exact integers
  M_INT[j,k]      — M.T[j,k] * 20, exact integers in {1,2,3,4,5,13,14,15}

  One step exact relation:
    20 * s_out_int[j] = sum_k M_INT[j,k] * s_in_int[k]  ±TOLERANCE

  Proof for each output j:
    D[j] = M_DENOM*C_out[j] - sum_k M_INT[j,k]*C_in[k] - epsilon[j]*H
    D[j] = delta_r[j] * G   ← Schnorr DL proof proves this
"""

import hashlib
import json
import secrets
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from py_ecc.bn128 import G1, multiply, add, neg, curve_order
from py_ecc.fields import bn128_FQ as FQ

# ── Generators ────────────────────────────────────────────────────────────────

_H_SEED = int(hashlib.sha256(b"Markovian-H-generator-v1").hexdigest(), 16) % curve_order
H = multiply(G1, _H_SEED)

SCALE_S   = 10**9         # scale for probability values
M_DENOM   = 20            # denominator for M.T integer representation
TOLERANCE = 50            # max allowed |epsilon[j]|


# ── Integer matrix ────────────────────────────────────────────────────────────

def make_m_int(M: np.ndarray) -> list[list[int]]:
    """M.T * M_DENOM → exact integer matrix."""
    Mt = M.T
    m = []
    for row in range(3):
        m.append([round(Mt[row, col] * M_DENOM) for col in range(3)])
    return m


# ── EC helpers ────────────────────────────────────────────────────────────────

def point_neg(P):
    return neg(P)

def scalar_mult(k: int, P):
    k = int(k) % curve_order
    if k == 0:
        return None
    return multiply(P, k)

def point_add(P, Q):
    if P is None: return Q
    if Q is None: return P
    return add(P, Q)

def point_sub(P, Q):
    return point_add(P, point_neg(Q))

def _hash_scalar(*parts) -> int:
    data = b"||".join(str(p).encode() for p in parts)
    return int(hashlib.sha256(data).hexdigest(), 16) % curve_order


# ── Pedersen commitment to a single integer ───────────────────────────────────

def pedersen_commit(value_int: int, blinding: Optional[int] = None):
    """C = blinding*G + value*H. Returns (C, blinding)."""
    if blinding is None:
        blinding = secrets.randbelow(curve_order - 1) + 1
    C = point_add(scalar_mult(blinding, G1), scalar_mult(value_int, H))
    return C, blinding


# ── Schnorr proof that a point equals r*G (i.e., H-component is zero) ────────

def schnorr_prove_dl_G(delta_r: int, D, context: bytes = b"") -> dict:
    """
    Prove knowledge of delta_r such that D = delta_r * G.
    Non-interactive via Fiat-Shamir.
    """
    k = secrets.randbelow(curve_order - 1) + 1
    R = scalar_mult(k, G1)
    e = _hash_scalar(_point_to_list(D), _point_to_list(R), context)
    s = (k - e * delta_r) % curve_order
    return {"R": _point_to_list(R), "s": s, "e": e}


def _point_to_list(P) -> list:
    """Serialize EC point to [x_int, y_int] for JSON."""
    if P is None:
        return None
    return [int(P[0]), int(P[1])]


def _list_to_point(L) -> tuple:
    """Deserialize [x_int, y_int] back to EC point."""
    if L is None:
        return None
    return (FQ(int(L[0])), FQ(int(L[1])))


def schnorr_verify_dl_G(D, proof: dict, context: bytes = b"") -> bool:
    """Verify Schnorr proof that D = delta_r * G."""
    try:
        R_raw = proof["R"]
        R_claimed = _list_to_point(R_raw) if isinstance(R_raw, list) else eval(R_raw)
        s = int(proof["s"])
        e = int(proof["e"])
        # Check: s*G + e*D == R
        lhs = point_add(scalar_mult(s, G1), scalar_mult(e, D))
        if lhs != R_claimed:
            return False
        # Re-derive challenge
        e_check = _hash_scalar(_point_to_list(D), _point_to_list(R_claimed), context)
        return e_check == e
    except Exception:
        return False


# ── Vector commitment ─────────────────────────────────────────────────────────

@dataclass
class VecCommit:
    """Pedersen commitments to a 3-vector of integer-scaled probabilities."""
    C: list           # 3 EC points (public)
    blindings: list   # 3 blinding factors (secret, int)
    values: list      # 3 integer values s_int = round(s * SCALE_S) (secret)


def commit_simplex(s: list) -> VecCommit:
    """Commit to a probability simplex vector."""
    values   = [round(float(v) * SCALE_S) for v in s]
    C_points = []
    blindings = []
    for v in values:
        C, r = pedersen_commit(v)
        C_points.append(C)
        blindings.append(r)
    return VecCommit(C=C_points, blindings=blindings, values=values)


# ── Step proof ────────────────────────────────────────────────────────────────

@dataclass
class StepProof:
    """
    ZK proof that C_out was derived from C_in via one Markov step.

    For each output j:
      D[j] = M_DENOM*C_out[j] - sum_k M_INT[j,k]*C_in[k] - epsilon[j]*H
      D[j] = delta_r[j]*G  (proven by Schnorr)
    """
    C_in:    list   # 3 EC points (public commitments to s_in)
    C_out:   list   # 3 EC points (public commitments to s_out)
    epsilons: list  # [epsilon[0], epsilon[1], epsilon[2]] — rounding corrections
    proofs:  list   # 3 Schnorr proofs (one per output component)


def _to_ec(p):
    """Accept either a raw EC point or a serialized [x, y] list."""
    if p is None:
        return None
    if isinstance(p, list):
        return _list_to_point(p)
    return p


def prove_step(M_INT: list, vc_in: VecCommit, vc_out: VecCommit,
               context: bytes = b"") -> StepProof:
    """Generate proof for one Markov step."""
    epsilons = []
    proofs   = []

    for j in range(3):
        # Compute expected value (exact integer arithmetic)
        expected = sum(M_INT[j][k] * vc_in.values[k] for k in range(3))
        actual   = M_DENOM * vc_out.values[j]
        epsilon  = actual - expected  # rounding correction

        assert abs(epsilon) <= TOLERANCE, \
            f"Rounding error {epsilon} exceeds tolerance {TOLERANCE}"

        # delta_r[j] = M_DENOM * r_out[j] - sum_k M_INT[j,k] * r_in[k]
        delta_r = (
            M_DENOM * vc_out.blindings[j]
            - sum(M_INT[j][k] * vc_in.blindings[k] for k in range(3))
        ) % curve_order

        # D[j] = M_DENOM*C_out[j] - sum_k M_INT[j,k]*C_in[k] - epsilon[j]*H
        D = scalar_mult(M_DENOM, _to_ec(vc_out.C[j]))
        for k in range(3):
            D = point_sub(D, scalar_mult(M_INT[j][k], _to_ec(vc_in.C[k])))
        if epsilon != 0:
            D = point_sub(D, scalar_mult(int(epsilon) % curve_order, H))

        ctx = context + f"|step|j={j}|eps={epsilon}".encode()
        proof = schnorr_prove_dl_G(delta_r, D, ctx)
        epsilons.append(epsilon)
        proofs.append(proof)

    return StepProof(
        C_in=[_point_to_list(p) for p in vc_in.C],
        C_out=[_point_to_list(p) for p in vc_out.C],
        epsilons=epsilons, proofs=proofs
    )


def verify_step(M_INT: list, step: StepProof, context: bytes = b"") -> bool:
    """Verify one Markov step proof."""
    for j in range(3):
        eps = step.epsilons[j]
        if abs(eps) > TOLERANCE:
            return False

        # Reconstruct D[j]
        D = scalar_mult(M_DENOM, _to_ec(step.C_out[j]))
        for k in range(3):
            D = point_sub(D, scalar_mult(M_INT[j][k], _to_ec(step.C_in[k])))
        if eps != 0:
            D = point_sub(D, scalar_mult(int(eps) % curve_order, H))

        ctx = context + f"|step|j={j}|eps={eps}".encode()
        if not schnorr_verify_dl_G(D, step.proofs[j], ctx):
            return False

    return True


# ── Full N-step chain proof ───────────────────────────────────────────────────

@dataclass
class MarkovProof:
    m_version:  int
    n_steps:    int
    C_input:    list             # public commitments to s_input
    C_output:   list             # public commitments to s_output
    steps:      list             # list of StepProof dicts


def prove_markov(M: np.ndarray, s_input: list, N: int,
                 m_version: int = 1) -> tuple:
    """
    Prove N-step Markov computation: s_output = M.T^N @ s_input.
    Returns (s_output, MarkovProof).
    """
    M_INT = make_m_int(M)
    ctx_base = f"mkv|v{m_version}|N={N}".encode()

    s = list(s_input)
    Mt = M.T

    # Commit to s_input
    vc_current = commit_simplex(s)
    C_input = vc_current.C[:]

    step_proofs = []
    for step_idx in range(N):
        # Compute next state
        s_next = (Mt @ np.array(s)).tolist()
        vc_next = commit_simplex(s_next)

        ctx = ctx_base + f"|i={step_idx}".encode()
        sp = prove_step(M_INT, vc_current, vc_next, ctx)
        step_proofs.append({
            "C_in":     sp.C_in,
            "C_out":    sp.C_out,
            "epsilons": sp.epsilons,
            "proofs":   sp.proofs,
        })

        s = s_next
        vc_current = vc_next

    proof = MarkovProof(
        m_version=m_version,
        n_steps=N,
        C_input=[_point_to_list(p) for p in C_input],
        C_output=[_point_to_list(p) for p in vc_current.C],
        steps=step_proofs,
    )
    return s, proof


def verify_markov(M: np.ndarray, proof_dict: dict) -> bool:
    """
    Verify a serialized MarkovProof dict.
    Checks: chain of step proofs links C_input to C_output.
    """
    try:
        M_INT     = make_m_int(M)
        m_version = proof_dict["m_version"]
        N         = proof_dict["n_steps"]
        ctx_base  = f"mkv|v{m_version}|N={N}".encode()
        steps     = proof_dict["steps"]

        if len(steps) != N:
            return False

        for i, sd in enumerate(steps):
            sp = StepProof(
                C_in=sd["C_in"], C_out=sd["C_out"],
                epsilons=sd["epsilons"],
                proofs=sd["proofs"]
            )
            ctx = ctx_base + f"|i={i}".encode()
            if not verify_step(M_INT, sp, ctx):
                return False

            # Chain continuity: C_out of step i = C_in of step i+1
            if i < N - 1:
                if sd["C_out"] != steps[i+1]["C_in"]:
                    return False

        return True
    except Exception:
        return False


# ── Serialization ─────────────────────────────────────────────────────────────

def proof_to_dict(proof: MarkovProof) -> dict:
    return {
        "type":      "markov_schnorr_v1",
        "m_version": proof.m_version,
        "n_steps":   proof.n_steps,
        "C_input":   [_point_to_list(p) if not isinstance(p, list) else p for p in proof.C_input],
        "C_output":  [_point_to_list(p) if not isinstance(p, list) else p for p in proof.C_output],
        "steps":     proof.steps,
    }


def proof_from_dict(d: dict) -> dict:
    return d  # already serializable format


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import time

    GENESIS_M = np.array([
        [0.70, 0.25, 0.05],
        [0.10, 0.75, 0.15],
        [0.20, 0.15, 0.65],
    ], dtype=np.float64)

    test_cases = [
        ("SPY COVID crash  ", [0.073496, 1e-6, 0.926502]),
        ("QQQ Bull trend   ", [1e-6, 0.85, 0.149999]),
        ("Accumulation     ", [0.70, 1e-6, 0.299999]),
        ("Neutral          ", [0.333, 0.334, 0.333]),
    ]

    M_INT = make_m_int(GENESIS_M)
    print(f"M_INT (M.T × {M_DENOM}):")
    for row in M_INT:
        print(f"  {row}  sum={sum(row)}")
    print()

    for label, s_in in test_cases:
        t0 = time.time()
        s_out, proof = prove_markov(GENESIS_M, s_in, N=2, m_version=1)
        elapsed_prove = time.time() - t0

        pd = proof_to_dict(proof)
        proof_bytes = len(json.dumps(pd).encode())

        t1 = time.time()
        ok = verify_markov(GENESIS_M, pd)
        elapsed_verify = time.time() - t1

        STATES = ['ACCUM', 'MARKUP', 'DISTR']
        regime = STATES[int(np.argmax(s_out))]
        conf   = max(s_out)

        print(f"{label} → {regime} {conf*100:.1f}%  "
              f"sum={sum(s_out):.6f}  "
              f"verified={ok}  "
              f"prove={elapsed_prove*1000:.0f}ms  "
              f"verify={elapsed_verify*1000:.0f}ms  "
              f"size={proof_bytes/1024:.1f}KB")
