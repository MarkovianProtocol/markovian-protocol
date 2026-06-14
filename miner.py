"""
Markovian Protocol - Miner v0.3

Proof-of-Intelligence miner. Polls /tip for chain state, computes
Markov state transitions as work, submits ZK-proven blocks to the
public node at api.quantsynth.net.

Light read bundled: after every accepted block, miner auto-classifies
the regime from s_output and submits a read. No API keys required.
Pure local math on top of work already done.

Requirements:
    pip install requests numpy py_ecc

Usage:
    python3 miner.py --address YOUR_MKV_ADDRESS

Or set MINER_ADDRESS below and run: python3 miner.py
"""

import argparse
import hashlib
import json
import sys
import time
import requests
import numpy as np
from zk_markov import prove_markov, proof_to_dict
from block_schema import (
    Block, BlockHeader, BlockBody,
    GENESIS_M, KOVS_PER_BLOCK,
    extract_s_from_hash, compute_work,
    PROTOCOL_VERSION,
)

# ── Config ────────────────────────────────────────────────────────────────────

NODE_URL      = 'https://api.quantsynth.net'   # public bootstrap node
MINER_ADDRESS = 'YOUR_MKV_ADDRESS_HERE'        # replace with your address
LOG_INTERVAL  = 500
REGIMES       = ['ACCUMULATION', 'MARKUP', 'DISTRIBUTION']
READER_BONUS  = 5_000_000   # reserved per block for deep reader payouts (Phase 2)


# ── Node Communication ────────────────────────────────────────────────────────

def get_tip() -> dict:
    try:
        r = requests.get(f'{NODE_URL}/tip', timeout=5)
        return r.json()
    except Exception as e:
        print(f'[ERROR] /tip failed: {e}')
        return None


def get_matrix() -> np.ndarray:
    try:
        r = requests.get(f'{NODE_URL}/m', timeout=5)
        data = r.json()
        return np.array(data['matrix'], dtype=np.float64), data['version']
    except Exception:
        return GENESIS_M, 1


def submit_block(block: Block) -> dict:
    try:
        payload = block.to_dict()
        r = requests.post(f'{NODE_URL}/submit', json=payload, timeout=10)
        return r.json()
    except Exception as e:
        return {'ok': False, 'error': str(e)}


# ── Regime Classification ─────────────────────────────────────────────────────

def classify(s_vec) -> tuple:
    idx = int(np.argmax(s_vec))
    return REGIMES[idx], round(float(s_vec[idx]), 4)


def submit_light_read(block_hash: str, height: int,
                      s_output, wallet: str) -> dict:
    regime, conf = classify(s_output)
    payload = {
        'wallet':       wallet,
        'block_height': height,
        'block_hash':   block_hash,
        'reads':        {'master': {'regime': regime, 'confidence': conf}},
        'mode':         'light',
        'submitted_at': int(time.time()),
    }
    try:
        r = requests.post(f'{NODE_URL}/submit_read', json=payload, timeout=5)
        return r.json()
    except Exception as e:
        return {'ok': False, 'error': str(e)}


# ── ZK Proof (Schnorr sigma, BN128 Pedersen) ─────────────────────────────────

def generate_zk_proof(M: np.ndarray, s_input: np.ndarray,
                       s_output: np.ndarray, N: int) -> str:
    _, proof = prove_markov(M, s_input.tolist(), N, m_version=1)
    return json.dumps(proof_to_dict(proof), separators=(',', ':'))


# ── Miner Loop ────────────────────────────────────────────────────────────────

def mine():
    print('Markovian Protocol Miner v0.3')
    print(f'Address:  {MINER_ADDRESS}')
    print(f'Node:     {NODE_URL}')
    print('─' * 60)

    total_blocks = 0
    total_kovs   = 0

    while True:
        # Pull current chain state from node
        tip = get_tip()
        if not tip:
            print('[WARN] Node unreachable. Retrying in 5s...')
            time.sleep(5)
            continue

        prev_hash    = tip['hash']
        next_height  = tip['height'] + 1
        difficulty_n = tip['difficulty_n']
        difficulty_z = tip.get('difficulty', 4)
        m_version    = tip['m_version']

        # Get current M from node (respects governance updates)
        M, m_ver = get_matrix()

        # Derive s from prev_hash — deterministic, no oracle
        # ZK circuit operates at N=2 (proven depth). PoW nonce provides work.
        ZK_N     = 2
        s_input  = extract_s_from_hash(prev_hash)
        s_output = compute_work(M.T, s_input, ZK_N)
        zk_proof = generate_zk_proof(M, s_input, s_output, ZK_N)
        difficulty_n = ZK_N  # override chain N for new ZK-era blocks

        body = BlockBody(
            s_input   = s_input.tolist(),
            s_output  = s_output.tolist(),
            n_steps   = difficulty_n,
            zk_proof  = zk_proof,
            m_version = m_ver,
        )
        merkle  = body.merkle_root()
        prefix  = '0' * difficulty_z
        nonce   = 0
        t_start = time.time()

        print(f'\nMining block {next_height} | prev: {prev_hash[:16]}...')
        print(f'S input:  {[round(float(x),4) for x in s_input]}')
        print(f'S output: {[round(float(x),4) for x in s_output]}')

        while True:
            header = BlockHeader(
                version       = PROTOCOL_VERSION,
                height        = next_height,
                prev_hash     = prev_hash,
                timestamp     = int(time.time()),
                difficulty_n  = difficulty_n,
                nonce         = nonce,
                merkle_root   = merkle,
                miner_address = MINER_ADDRESS,
            )

            if header.hash().startswith(prefix):
                block  = Block(header=header, body=body)
                result = submit_block(block)

                if result.get('ok'):
                    elapsed       = time.time() - t_start
                    total_blocks += 1
                    total_kovs   += KOVS_PER_BLOCK
                    blk_hash      = header.hash()
                    print(f'BLOCK ACCEPTED  height={next_height}')
                    print(f'  Hash:    {blk_hash}')
                    print(f'  Nonce:   {nonce:,}')
                    print(f'  Time:    {elapsed:.2f}s')
                    print(f'  Kovs:    +{KOVS_PER_BLOCK:,}  (session total: {total_kovs:,})')
                    print(f'  MKV:     {total_kovs/100_000_000:.4f}')
                    # Light read — regime classification bundled into every accepted block
                    read_resp    = submit_light_read(blk_hash, next_height, s_output, MINER_ADDRESS)
                    regime, conf = classify(s_output)
                    print(f'  Regime:  {regime} ({conf:.2f})  read={read_resp.get("ok", False)}')
                else:
                    # Block rejected — chain moved, re-poll tip
                    print(f'[REJECTED] {result.get("error")} — re-syncing...')
                break

            nonce += 1
            if nonce % LOG_INTERVAL == 0:
                elapsed = time.time() - t_start
                rate    = nonce / elapsed if elapsed > 0 else 0
                print(f'  nonce={nonce:,}  rate={rate:.0f}/s', end='\r')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Markovian Protocol Miner')
    parser.add_argument('--address', default=MINER_ADDRESS, help='Your MKV wallet address')
    parser.add_argument('--node', default=NODE_URL, help='Node URL (default: api.quantsynth.net)')
    args = parser.parse_args()
    if args.address == 'YOUR_MKV_ADDRESS_HERE':
        print('ERROR: set --address YOUR_MKV_ADDRESS or edit MINER_ADDRESS in this file')
        sys.exit(1)
    MINER_ADDRESS = args.address
    NODE_URL = args.node
    mine()
