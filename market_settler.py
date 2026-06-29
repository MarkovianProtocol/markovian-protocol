#!/usr/bin/env python3
"""
Markovian Markets Settler v3

Changes from v2:
  - Processes status IN ('open','closed'), v2 only caught 'open'
  - Regime oracle: majority vote across 3 surrounding blocks (tamper-resistant)
  - Writes to market_accuracy for calibration tracking
  - Handles zero-pool markets (just marks settled, no payout)
"""

import json, time, datetime, requests, psycopg2, psycopg2.extras

NODE_URL         = 'https://api.quantsynth.net'
DB_URL           = 'postgresql://signal:<password>@127.0.0.1:5432/signal'
TIINGO_KEY       = 'f3fe5c650324da38f08f160f21d099e5c2a11b83'
PROTOCOL_FEE_PCT = 0.02
REGIMES          = ['ACCUMULATION', 'MARKUP', 'DISTRIBUTION']

TICKER_DIMENSION = {
    'QQQ': 'equity_s_output', 'SPY': 'equity_s_output',
    'USO': 'oil_s_output',    'GLD': 'gold_s_output',
    'TLT': 'rates_s_output',  'FXE': 'fx_s_output',
}
TIINGO_TICKER = {'QQQ':'QQQ','SPY':'SPY','USO':'USO','GLD':'GLD',
                 'TLT':'TLT','FXE':'FXE','XLE':'XLE','ARKK':'ARKK','XOP':'XOP'}


def get_conn():
    return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def setup_tables(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_accuracy (
            id              SERIAL PRIMARY KEY,
            settled_at      TIMESTAMPTZ DEFAULT NOW(),
            market_id       INT,
            market_type     TEXT,
            ticker          TEXT,
            ticker2         TEXT,
            actual_outcome  TEXT,
            had_positions   BOOLEAN,
            total_pool      BIGINT,
            oracle_method   TEXT,    -- 'majority_vote', 'tiingo_price', 'single_block'
            oracle_detail   TEXT
        )
    """)
    conn.commit()


def get_block(height: int) -> dict:
    try:
        r = requests.get(f'{NODE_URL}/block/{height}', timeout=5)
        return r.json()
    except Exception:
        return {}


def get_single_block_regime(height: int, ticker: str) -> str | None:
    block   = get_block(height)
    dim_key = TICKER_DIMENSION.get(ticker, 's_output')
    raw     = block.get(dim_key) or block.get('s_output')
    if not raw:
        return None
    s = json.loads(raw) if isinstance(raw, str) else raw
    return REGIMES[s.index(max(s))]


def get_regime_majority_vote(height: int, ticker: str) -> tuple[str, str]:
    """
    Oracle isolation: majority vote across 3 blocks (height-1, height, height+1).
    Returns (regime, method_detail), harder to game than single block.
    """
    votes = []
    for h in [height - 1, height, height + 1]:
        r = get_single_block_regime(h, ticker)
        if r:
            votes.append(r)

    if not votes:
        return None, 'no blocks available'

    counts = {}
    for v in votes:
        counts[v] = counts.get(v, 0) + 1
    winner = max(counts, key=counts.get)
    detail = f'vote {counts} over blocks {height-1}-{height+1}'
    return winner, detail


def get_tiingo_price(ticker: str, date_str: str) -> float:
    url = f'https://api.tiingo.com/tiingo/daily/{ticker}/prices'
    try:
        r    = requests.get(url, params={'startDate': date_str, 'endDate': date_str,
                                          'token': TIINGO_KEY}, timeout=10)
        data = r.json()
        if data and isinstance(data, list):
            return float(data[0].get('close') or data[0].get('adjClose') or 0)
    except Exception:
        pass
    return 0.0


def block_to_date(timestamp: int) -> str:
    return datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')


def log_accuracy(conn, market, actual_outcome, oracle_method, oracle_detail):
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO market_accuracy
            (market_id, market_type, ticker, ticker2, actual_outcome,
             had_positions, total_pool, oracle_method, oracle_detail)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT DO NOTHING
        """, (
            market['id'], market.get('market_type'), market['ticker'],
            market.get('ticker2'), actual_outcome,
            int(market.get('total_pool') or 0) > 0,
            int(market.get('total_pool') or 0),
            oracle_method, oracle_detail
        ))
        conn.commit()
    except Exception as e:
        print(f"  accuracy log error: {e}")
        conn.rollback()


def pari_mutuel_payout(conn, market: dict, actual_outcome: str) -> str:
    market_id = market['id']
    cur       = conn.cursor()

    cur.execute('SELECT * FROM market_positions WHERE market_id=%s', (market_id,))
    positions = cur.fetchall()

    if not positions:
        cur.execute(
            "UPDATE prediction_markets SET status='settled', actual_regime=%s, settled_at=%s WHERE id=%s",
            (actual_outcome, int(time.time()), market_id)
        )
        conn.commit()
        return '0 positions, marked settled, no payouts'

    total_pool   = sum(int(p['kovs_staked']) for p in positions)
    protocol_fee = int(total_pool * PROTOCOL_FEE_PCT)
    winner_pool  = total_pool - protocol_fee
    winners      = [p for p in positions if p['regime_bet'] == actual_outcome]
    now          = int(time.time())

    cur.execute(
        """UPDATE prediction_markets
           SET status='settled', actual_regime=%s, total_pool=%s,
               protocol_fee=%s, settled_at=%s WHERE id=%s""",
        (actual_outcome, total_pool, protocol_fee, now, market_id)
    )

    if not winners:
        for p in positions:
            cur.execute('UPDATE market_positions SET payout=0 WHERE id=%s', (p['id'],))
        cur.execute(
            """INSERT INTO market_settlements
               (market_id, actual_regime, total_pool, winner_pool, protocol_fee, winner_count, settled_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (market_id, actual_outcome, total_pool, 0, total_pool, 0, now)
        )
        conn.commit()
        return f'0 winners, {total_pool:,} Kovs to protocol'

    total_stake = sum(int(p['kovs_staked']) for p in winners)
    total_paid  = 0
    for p in winners:
        share  = int(p['kovs_staked']) / total_stake
        payout = int(winner_pool * share)
        total_paid += payout
        cur.execute('UPDATE market_positions SET payout=%s WHERE id=%s', (payout, p['id']))

    remainder = winner_pool - total_paid
    if remainder > 0:
        top = max(winners, key=lambda p: int(p['kovs_staked']))
        cur.execute('UPDATE market_positions SET payout=payout+%s WHERE id=%s', (remainder, top['id']))

    for p in positions:
        if p['regime_bet'] != actual_outcome:
            cur.execute('UPDATE market_positions SET payout=0 WHERE id=%s', (p['id'],))

    cur.execute(
        """INSERT INTO market_settlements
           (market_id, actual_regime, total_pool, winner_pool, protocol_fee, winner_count, settled_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        (market_id, actual_outcome, total_pool, winner_pool, protocol_fee, len(winners), now)
    )
    conn.commit()
    return f'{len(winners)}/{len(positions)} won, {winner_pool:,} Kovs distributed'


def settle_market(conn, market: dict, tip: int) -> str:
    market_id   = market['id']
    ticker      = market['ticker']
    ticker2     = market.get('ticker2')
    height      = market['target_block']
    market_type = market.get('market_type', 'regime')
    cur         = conn.cursor()

    oracle_method = 'unknown'
    oracle_detail = ''

    try:
        if market_type == 'direction':
            block     = get_block(height)
            ts        = block.get('timestamp') or int(time.time())
            date_str  = block_to_date(ts)
            res_price = get_tiingo_price(TIINGO_TICKER.get(ticker, ticker), date_str)
            base_price = float(market.get('baseline_price') or 0)
            if res_price == 0 or base_price == 0:
                return f'market {market_id}: price data unavailable'
            actual_outcome = 'UP' if res_price >= base_price else 'DOWN'
            cur.execute('UPDATE prediction_markets SET resolution_price=%s WHERE id=%s',
                        (res_price, market_id))
            conn.commit()
            oracle_method = 'tiingo_price'
            oracle_detail = f'{ticker} {base_price:.2f}→{res_price:.2f}'

        elif market_type == 'convergence':
            # Use majority vote for both tickers
            regime1, det1 = get_regime_majority_vote(height, ticker)
            regime2, det2 = get_regime_majority_vote(height, ticker2)
            if not regime1 or not regime2:
                return f'market {market_id}: block data unavailable'
            actual_outcome = 'AGREE' if regime1 == regime2 else 'DISAGREE'
            oracle_method  = 'majority_vote'
            oracle_detail  = f'{ticker}={regime1} {ticker2}={regime2}'

        else:  # regime
            actual_outcome, oracle_detail = get_regime_majority_vote(height, ticker)
            if not actual_outcome:
                return f'market {market_id}: block data unavailable'
            oracle_method = 'majority_vote'

    except Exception as e:
        return f'market {market_id}: lookup failed, {e}'

    log_accuracy(conn, market, actual_outcome, oracle_method, oracle_detail)
    result = pari_mutuel_payout(conn, market, actual_outcome)
    return f'market {market_id} [{market_type}/{ticker}]: outcome={actual_outcome} | {result} | oracle={oracle_detail}'


def run():
    print('Market Settler v3, starting')
    try:
        tip = requests.get(f'{NODE_URL}/tip', timeout=5).json()['height']
        print(f'  chain tip: {tip}')
    except Exception as e:
        print(f'  chain unreachable: {e}')
        return

    conn = get_conn()
    setup_tables(conn)

    cur = conn.cursor()
    # v3 fix: catch both 'open' and 'closed' markets past their target block
    cur.execute("""
        SELECT * FROM prediction_markets
        WHERE status IN ('open','closed') AND target_block <= %s
        ORDER BY target_block
    """, (tip,))
    pending = cur.fetchall()

    if not pending:
        print(f'  nothing to settle (tip={tip})')
        conn.close()
        return

    print(f'  {len(pending)} markets to settle')
    for market in pending:
        result = settle_market(conn, market, tip)
        print(f'  {result}')

    conn.close()
    print('Done.')


if __name__ == '__main__':
    run()
