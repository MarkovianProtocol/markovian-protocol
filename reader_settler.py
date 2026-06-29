"""
Markovian Protocol - Reader Pool Settler

Runs after each block's reveal window closes (block_height + 2).
For each unsettled block:
  1. Fetch actual regime from chain
  2. Score all deep reader reveals
  3. Split reader bonus pool pro-rata by prediction confidence
  4. Write kovs_earned to reader_reads + reader_kov_ledger
  5. If no correct reveals, roll pool forward to next block
"""

import json
import time
import requests
import psycopg2
import psycopg2.extras

NODE_URL        = 'https://api.quantsynth.net'
DB_URL          = 'postgresql://signal:<password>@127.0.0.1:5432/signal'
BASE_POOL_KOVS  = 5_000_000
REVEAL_WINDOW   = 2   # blocks after target before settling
REGIMES         = ['ACCUMULATION', 'MARKUP', 'DISTRIBUTION']


def get_conn():
    return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def get_chain_tip() -> dict:
    r = requests.get(f'{NODE_URL}/tip', timeout=5)
    return r.json()


def get_block_regime(height: int) -> str:
    """Fetch s_output from chain and return dominant regime."""
    r = requests.get(f'{NODE_URL}/block/{height}', timeout=5)
    block = r.json()
    s_output = json.loads(block['s_output']) if isinstance(block['s_output'], str) else block['s_output']
    return REGIMES[s_output.index(max(s_output))]


def ensure_pool_row(conn, block_height: int):
    """Create pool row for a block if it doesn't exist, inheriting any rollover."""
    cur = conn.cursor()
    existing = cur.execute(
        'SELECT 1 FROM reader_bonus_pool WHERE block_height = %s',
        (block_height,)
    )
    if cur.fetchone():
        return

    # Check if previous block rolled over to this one
    prev = cur.execute(
        '''SELECT block_height, total_kovs FROM reader_bonus_pool
           WHERE rolled_from IS NULL AND settled = TRUE
             AND correct_readers = 0
           ORDER BY block_height DESC LIMIT 1'''
    )
    # simpler: look for any existing rollover targeting this block
    cur.execute(
        '''INSERT INTO reader_bonus_pool (block_height, pool_kovs, rollover_kovs)
           VALUES (%s, %s, COALESCE(
               (SELECT total_kovs FROM reader_bonus_pool
                WHERE settled = FALSE AND rolled_from IS NULL
                ORDER BY block_height DESC LIMIT 1), 0
           ))
           ON CONFLICT (block_height) DO NOTHING''',
        (block_height, BASE_POOL_KOVS)
    )
    conn.commit()


def settle_block(conn, block_height: int) -> str:
    """Settle reader pool for one block. Returns outcome string."""
    cur = conn.cursor()

    # Get pool for this block
    cur.execute('SELECT * FROM reader_bonus_pool WHERE block_height = %s', (block_height,))
    pool = cur.fetchone()
    if not pool:
        cur.execute(
            'INSERT INTO reader_bonus_pool (block_height, pool_kovs, rollover_kovs) VALUES (%s, %s, 0)',
            (block_height, BASE_POOL_KOVS)
        )
        conn.commit()
        cur.execute('SELECT * FROM reader_bonus_pool WHERE block_height = %s', (block_height,))
        pool = cur.fetchone()

    if pool['settled']:
        return f'block {block_height}: already settled'

    # Get actual regime from chain
    try:
        actual_regime = get_block_regime(block_height)
    except Exception as e:
        return f'block {block_height}: chain lookup failed — {e}'

    # Get all revealed deep reads for this block
    cur.execute(
        '''SELECT id, wallet, predicted_regime, predicted_conf
           FROM reader_reads
           WHERE block_height = %s AND mode = %s AND revealed = TRUE''',
        (block_height, 'deep')
    )
    reveals = cur.fetchall()

    if not reveals:
        # No deep readers — roll pool forward
        next_height = block_height + 1
        cur.execute(
            '''INSERT INTO reader_bonus_pool (block_height, pool_kovs, rollover_kovs, rolled_from)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (block_height) DO UPDATE
               SET rollover_kovs = reader_bonus_pool.rollover_kovs + EXCLUDED.rollover_kovs,
                   rolled_from   = EXCLUDED.rolled_from''',
            (next_height, BASE_POOL_KOVS, pool['total_kovs'], block_height)
        )
        cur.execute(
            '''UPDATE reader_bonus_pool
               SET settled = TRUE, settled_at = %s, correct_readers = 0
               WHERE block_height = %s''',
            (int(time.time()), block_height)
        )
        conn.commit()
        return f'block {block_height}: no deep readers, {pool["total_kovs"]:,} Kovs rolled to {next_height}'

    # Score each reveal
    correct = [r for r in reveals if r['predicted_regime'] == actual_regime]
    incorrect = [r for r in reveals if r['predicted_regime'] != actual_regime]

    # Mark incorrect reads
    for r in incorrect:
        cur.execute(
            'UPDATE reader_reads SET is_correct = FALSE, kovs_earned = 0 WHERE id = %s',
            (r['id'],)
        )

    if not correct:
        # All wrong — roll pool forward
        next_height = block_height + 1
        cur.execute(
            '''INSERT INTO reader_bonus_pool (block_height, pool_kovs, rollover_kovs, rolled_from)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (block_height) DO UPDATE
               SET rollover_kovs = reader_bonus_pool.rollover_kovs + EXCLUDED.rollover_kovs,
                   rolled_from   = EXCLUDED.rolled_from''',
            (next_height, BASE_POOL_KOVS, pool['total_kovs'], block_height)
        )
        cur.execute(
            '''UPDATE reader_bonus_pool
               SET settled = TRUE, settled_at = %s, correct_readers = 0
               WHERE block_height = %s''',
            (int(time.time()), block_height)
        )
        conn.commit()
        return f'block {block_height}: {len(reveals)} deep readers, 0 correct, {pool["total_kovs"]:,} Kovs rolled to {next_height}'

    # Pro-rata split among correct reads by confidence
    total_pool  = pool['total_kovs']
    total_conf  = sum(r['predicted_conf'] or 0 for r in correct)
    now         = int(time.time())
    total_paid  = 0

    for r in correct:
        conf      = r['predicted_conf'] or 0
        share     = conf / total_conf if total_conf > 0 else 1.0 / len(correct)
        kovs      = int(total_pool * share)
        total_paid += kovs

        cur.execute(
            'UPDATE reader_reads SET is_correct = TRUE, kovs_earned = %s WHERE id = %s',
            (kovs, r['id'])
        )
        cur.execute(
            '''INSERT INTO reader_kov_ledger
               (block_height, wallet, kovs_earned, pool_total, confidence, regime, settled_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s)''',
            (block_height, r['wallet'], kovs, total_pool, conf, actual_regime, now)
        )

    # Any rounding remainder goes to highest-confidence correct reader
    remainder = total_pool - total_paid
    if remainder > 0 and correct:
        top = max(correct, key=lambda r: r['predicted_conf'] or 0)
        cur.execute(
            'UPDATE reader_reads SET kovs_earned = kovs_earned + %s WHERE id = %s',
            (remainder, top['id'])
        )
        cur.execute(
            'UPDATE reader_kov_ledger SET kovs_earned = kovs_earned + %s WHERE block_height = %s AND wallet = %s',
            (remainder, block_height, top['wallet'])
        )

    cur.execute(
        '''UPDATE reader_bonus_pool
           SET settled = TRUE, settled_at = %s, correct_readers = %s
           WHERE block_height = %s''',
        (now, len(correct), block_height)
    )
    conn.commit()

    return (f'block {block_height}: regime={actual_regime}, '
            f'{len(correct)}/{len(reveals)} correct, '
            f'{total_pool:,} Kovs distributed')


def run():
    print('Reader Pool Settler — starting')
    tip = get_chain_tip()
    current_height = tip['height']
    settle_before  = current_height - REVEAL_WINDOW

    conn = get_conn()
    cur  = conn.cursor()

    # Find all unsettled blocks within the settle window
    cur.execute(
        '''SELECT DISTINCT block_height FROM reader_reads
           WHERE mode = %s AND revealed = TRUE
             AND block_height <= %s
           UNION
           SELECT block_height FROM reader_bonus_pool
           WHERE settled = FALSE AND block_height <= %s
           ORDER BY block_height''',
        ('deep', settle_before, settle_before)
    )
    pending = [r['block_height'] for r in cur.fetchall()]

    if not pending:
        print(f'  nothing to settle (chain tip: {current_height})')
        conn.close()
        return

    for height in pending:
        result = settle_block(conn, height)
        print(f'  {result}')

    conn.close()
    print('Done.')


if __name__ == '__main__':
    run()
