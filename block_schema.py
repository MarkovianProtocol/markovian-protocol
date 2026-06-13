"""
Markovian Protocol - Block Schema v0.1
June 3 2026
"""

import hashlib
import json
import time
import numpy as np
from dataclasses import dataclass, asdict
from typing import List


# Protocol Constants
PROTOCOL_VERSION   = 1
REGIME_STATES      = ['ACCUMULATION', 'MARKUP', 'DISTRIBUTION']
TARGET_BLOCK_TIME  = 60          # seconds per block (initial)
INITIAL_N          = 1000        # transition steps (difficulty)
KOVS_PER_BLOCK     = 50_000_000  # 0.5 MKV per block (genesis reward)
GENESIS_HASH       = '0' * 64

# Transition Matrix M (Genesis)
# Published by protocol. Rows = from state, Cols = to state.
# Each row sums to 1.0. Updated by governance only.
GENESIS_M = np.array([
    [0.70, 0.25, 0.05],   # from ACCUMULATION
    [0.10, 0.75, 0.15],   # from MARKUP
    [0.20, 0.15, 0.65],   # from DISTRIBUTION
], dtype=np.float64)


@dataclass
class BlockHeader:
    version:        int
    height:         int
    prev_hash:      str
    timestamp:      int
    difficulty_n:   int
    nonce:          int
    merkle_root:    str
    miner_address:  str

    def serialize(self) -> bytes:
        return json.dumps({
            'version':       self.version,
            'height':        self.height,
            'prev_hash':     self.prev_hash,
            'timestamp':     self.timestamp,
            'difficulty_n':  self.difficulty_n,
            'nonce':         self.nonce,
            'merkle_root':   self.merkle_root,
            'miner_address': self.miner_address,
        }, sort_keys=True).encode()

    def hash(self) -> str:
        return hashlib.sha256(self.serialize()).hexdigest()


@dataclass
class BlockBody:
    s_input:    List[float]   # starting vector s (derived from prev_hash)
    s_output:   List[float]   # output vector s_N = M^N * s
    n_steps:    int           # transition steps computed
    zk_proof:   str           # ZK proof of correct computation (hex)
    m_version:  int           # governance epoch of M used

    def serialize(self) -> bytes:
        return json.dumps({
            's_input':   self.s_input,
            's_output':  self.s_output,
            'n_steps':   self.n_steps,
            'zk_proof':  self.zk_proof,
            'm_version': self.m_version,
        }, sort_keys=True).encode()

    def merkle_root(self) -> str:
        return hashlib.sha256(self.serialize()).hexdigest()


@dataclass
class Block:
    header: BlockHeader
    body:   BlockBody

    def block_hash(self) -> str:
        return self.header.hash()

    def is_valid_pow(self, n_zeros: int) -> bool:
        return self.block_hash().startswith('0' * n_zeros)

    def to_dict(self) -> dict:
        return {
            'header': asdict(self.header),
            'body':   asdict(self.body),
            'hash':   self.block_hash(),
        }


def extract_s_from_hash(block_hash: str) -> np.ndarray:
    """
    Deterministically derive a probability simplex vector from a block hash.
    No oracle. No external data. Pure chain derivation.
    """
    raw = bytes.fromhex(block_hash)
    a = int.from_bytes(raw[0:8],  'big')
    b = int.from_bytes(raw[8:16], 'big')
    c = int.from_bytes(raw[16:24], 'big')
    total = a + b + c
    return np.array([a/total, b/total, c/total], dtype=np.float64)


def compute_work(M: np.ndarray, s: np.ndarray, N: int) -> np.ndarray:
    """Core PoW: apply M N times to s. s_N = M^N * s"""
    result = s.copy()
    for _ in range(N):
        result = M @ result
    return result


def create_genesis_block() -> Block:
    s_input  = [1/3, 1/3, 1/3]
    s_output = compute_work(GENESIS_M, np.array(s_input), INITIAL_N).tolist()

    body = BlockBody(
        s_input   = s_input,
        s_output  = s_output,
        n_steps   = INITIAL_N,
        zk_proof  = 'GENESIS',
        m_version = 1,
    )

    header = BlockHeader(
        version       = PROTOCOL_VERSION,
        height        = 0,
        prev_hash     = GENESIS_HASH,
        timestamp     = int(time.time()),
        difficulty_n  = INITIAL_N,
        nonce         = 0,
        merkle_root   = body.merkle_root(),
        miner_address = '135nd7CXWJ8QRjuCDkXoM5oxx9MKc7YNjN',
    )

    return Block(header=header, body=body)


CHAIN_DDL = """
CREATE TABLE IF NOT EXISTS blocks (
    height          INTEGER PRIMARY KEY,
    block_hash      TEXT    NOT NULL UNIQUE,
    prev_hash       TEXT    NOT NULL,
    timestamp       INTEGER NOT NULL,
    difficulty_n    INTEGER NOT NULL,
    nonce           INTEGER NOT NULL,
    merkle_root     TEXT    NOT NULL,
    miner_address   TEXT    NOT NULL,
    m_version       INTEGER NOT NULL,
    s_input         TEXT    NOT NULL,
    s_output        TEXT    NOT NULL,
    n_steps         INTEGER NOT NULL,
    zk_proof        TEXT    NOT NULL,
    created_at      INTEGER DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS kov_ledger (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    block_height    INTEGER NOT NULL,
    miner_address   TEXT    NOT NULL,
    kovs_earned     INTEGER NOT NULL,
    block_hash      TEXT    NOT NULL,
    FOREIGN KEY (block_height) REFERENCES blocks(height)
);

CREATE TABLE IF NOT EXISTS m_versions (
    version         INTEGER PRIMARY KEY,
    matrix_json     TEXT    NOT NULL,
    activated_at    INTEGER NOT NULL,
    governance_hash TEXT    NOT NULL,
    created_at      INTEGER DEFAULT (strftime('%s','now'))
);

CREATE INDEX IF NOT EXISTS idx_kov_miner  ON kov_ledger(miner_address);
CREATE INDEX IF NOT EXISTS idx_block_hash ON blocks(block_hash);
"""


if __name__ == '__main__':
    genesis = create_genesis_block()
    print('Genesis block created.')
    print(f'Hash:      {genesis.block_hash()}')
    print(f'S input:   {[round(x,4) for x in genesis.body.s_input]}')
    print(f'S output:  {[round(x,4) for x in genesis.body.s_output]}')
    print(f'Height:    {genesis.header.height}')
    print(f'Timestamp: {genesis.header.timestamp}')
    print()
    print('Chain DDL ready.')
