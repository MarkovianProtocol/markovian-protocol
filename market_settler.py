"""
Markovian Markets Settler v2

Handles three market types:
  regime     , ACCUMULATION / MARKUP / DISTRIBUTION, resolved from chain s_output
  convergence, AGREE / DISAGREE, resolved from two tickers at same block
  direction  , UP / DOWN, resolved from Tiingo price vs baseline at creation
"""

import json
import time
import datetime
import requests
import psycopg2
import psycopg2.extras

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

# ETF → Tiingo ticker (same for these)
TIINGO_TICKER = {'QQQ':'QQQ','SPY':'SPY','USO':'USO','GLD':'GLD','TLT':'TLT','FXE':'FXE'}


def get_conn():
    return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def get_chain_tip() -> dict:
    r = requests.get(f'{NODE_URL}/tip', timeout=5)
    return r.json()


def get_block(height: int) -> dict:
    r = requests.get(f'{NODE_URL}/block/{height}', timeout=5)
    return r.json()


def get_block_regime(height: int, ticker: str) -> str:
    block   = get_block(height)
    dim_key = TICKER_DIMENSION.get(ticker, 's_output')
    raw     = block.get(dim_key) or block.get('s_output')
    s       = json.loads(raw) if isinstance(raw, str) else raw
    return REGIMES[s.index(max(s))]


def get_tiingo_price(ticker: str, date_str: str) -> float:
    """Fetch closing price for ticker on date_str (YYYY-MM-DD)."""
    url = f'https://api.tiingo.com/tiingo/daily/{ticker}/prices'
    r   = requests.get(url, params={
        'startDate': date_str, 'endDate': date_str,
        'token': TIINGO_KEY
    }, timeout=10)
    data = r.json()
    if data and isinstance(data, list):
        return float(data[0].get('close') or data[0].get('adjClose') or 0)
    return 0.0


def block_to_date(timestamp: int) -> str:
    return datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')


def pari_mutuel_payout(conn, market: dict, actual_outcome: str) -> str:
    market_id = market['id']
    cur       = conn.cursor()

    cur.execute('SELECT * FROM market_positions WHERE market_id=%s', (market_id,))
    positions = cur.fetchall()

    total_pool   = sum(int(p['kovs_staked']) for p in positions)
    protocol_fee = int(total_pool * PROTOCOL_FEE_PCT)
    winner_pool  = total_pool - protocol_fee
    winners      = [p for p in positions if p['regime_bet'] == actual_outcome]
    now          = int(time.time())

    # Update market
    cur.execute(
        '''UPDATE prediction_markets
           SET status='settled', actual_regime=%s, total_pool=%s,
               protocol_fee=%s, settled_at=%s WHERE id=%s''',
        (actual_outcome, total_pool, protocol_fee, now, market_id)
    )

    if not winners:
        for p in positions:
            cur.execute('UPDATE market_positions SET payout=0 WHERE id=%s', (p['id'],))
        cur.execute(
            '''INSERT INTO market_settlements
               (market_id, actual_regime, total_pool, winner_pool, protocol_fee, winner_count, settled_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s)''',
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
        '''INSERT INTO market_settlements
           (market_id, actual_regime, total_pool, winner_pool, protocol_fee, winner_count, settled_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s)''',
        (market_id, actual_outcome, total_pool, winner_pool, protocol_fee, len(winners), now)
    )
    conn.commit()
    return f'{len(winners)}/{len(positions)} won, {winner_pool:,} Kovs distributed'


def settle_market(conn, market: dict) -> str:
    market_id   = market['id']
    ticker      = market['ticker']
    ticker2     = market.get('ticker2')
    height      = market['target_block']
    market_type = market.get('market_type', 'regime')
    cur         = conn.cursor()

    try:
        if market_type == 'direction':
            # Resolve from Tiingo price vs baseline
            block        = get_block(height)
            ts           = block.get('timestamp') or int(time.time())
            date_str     = block_to_date(ts)
            res_price    = get_tiingo_price(TIINGO_TICKER.get(ticker, ticker), date_str)
            base_price   = float(market.get('baseline_price') or 0)
            if res_price == 0 or base_price == 0:
                return f'market {market_id}: price data unavailable, retrying next cycle'
            actual_outcome = 'UP' if res_price >= base_price else 'DOWN'
            cur.execute(
                'UPDATE prediction_markets SET resolution_price=%s WHERE id=%s',
                (res_price, market_id)
            )
            conn.commit()
            label = f'{ticker} {base_price:.2f}→{res_price:.2f}'

        elif market_type == 'convergence':
            regime1        = get_block_regime(height, ticker)
            regime2        = get_block_regime(height, ticker2)
            actual_outcome = 'AGREE' if regime1 == regime2 else 'DISAGREE'
            label          = f'{ticker}={regime1} {ticker2}={regime2}'

        else:
            actual_outcome = get_block_regime(height, ticker)
            label          = ticker

    except Exception as e:
        return f'market {market_id}: lookup failed, {e}'

    result = pari_mutuel_payout(conn, market, actual_outcome)
    return f'market {market_id} ({label}): outcome={actual_outcome}, {result}'


def run():
    print('Market Settler v2, starting')
    try:
        tip = get_chain_tip()['height']
    except Exception as e:
        print(f'  chain unreachable: {e}')
        return

    conn = get_conn()
    cur  = conn.cursor()
    cur.execute(
        "SELECT * FROM prediction_markets WHERE status='open' AND target_block<=%s ORDER BY target_block",
        (tip,)
    )
    pending = cur.fetchall()
    if not pending:
        print(f'  nothing to settle (tip={tip})')
        conn.close()
        return
    for market in pending:
        print(f'  {settle_market(conn, market)}')
    conn.close()
    print('Done.')


if __name__ == '__main__':
    run()
