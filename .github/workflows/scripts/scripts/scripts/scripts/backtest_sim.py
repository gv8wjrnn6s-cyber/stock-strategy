import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scripts.utils import *
from scripts.scoring import WEIGHTS

CASH = 100000.0

def run_simulation_and_optimize(today_str, prev_rec_file, market_data):
    positions = load_json('data/pos.json') or {}
    trades = pd.read_csv('data/trades.csv') if os.path.exists('data/trades.csv') else pd.DataFrame()

    # 处理现有持仓
    sell_list = []
    for code, pos in positions.items():
        kline = get_kline(code, today_str, 1)
        if kline is None: continue
        k = kline.iloc[0]
        buy = pos['buy_price']
        stop = pos['stop_loss']
        days = (datetime.strptime(today_str,'%Y%m%d') - datetime.strptime(pos['buy_date'],'%Y%m%d')).days
        sell_price = None
        reason = ''
        if k['low'] <= stop: sell_price, reason = stop, '止损'
        elif days >= 2: sell_price, reason = k['close'], '到期'
        elif k['high']/buy -1 >= 0.03: sell_price, reason = buy*1.03, '止盈'
        if sell_price:
            shares = pos['shares']
            cost_buy = shares*buy*1.00025
            cost_sell = shares*sell_price*0.99875
            profit = cost_sell - cost_buy
            pct = (sell_price/buy-1)*100
            new = pd.DataFrame([{
                'buy_date': pos['buy_date'], 'sell_date': today_str, 'ts_code': code,
                'name':pos['name'], 'buy_price':buy, 'sell_price':sell_price,
                'shares':shares, 'profit':profit, 'return_pct':pct, 'days':days,
                'win': 1 if profit>0 else 0, 'reason':reason
            }])
            trades = pd.concat([trades, new], ignore_index=True)
            sell_list.append(code)
    for c in sell_list: del positions[c]

    # 买入新推荐
    if prev_rec_file and os.path.exists(prev_rec_file):
        recs = load_json(prev_rec_file)
        if recs:
            recs_df = pd.DataFrame(recs)
            used = sum(p['buy_price']*p['shares'] for p in positions.values())
            cash = CASH - used
            max_per = CASH * 0.15  # 凯利简化
            for _, rec in recs_df.iterrows():
                if cash < 5000: break
                code = rec['ts_code']
                if code in positions: continue
                kline = get_kline(code, today_str, 1)
                if kline is None: continue
                open_p = kline.iloc[0]['open']
                prev_close = rec.get('close', None)
                if prev_close is None: continue
                chg = (open_p/prev_close - 1)*100
                if 0 <= chg <= 3:
                    shares = int(min(max_per, cash) / open_p / 100) * 100
                    if shares >= 100:
                        cost = shares * open_p * 1.00025
                        if cost <= cash:
                            positions[code] = {
                                'buy_price': open_p, 'shares': shares,
                                'stop_loss': rec.get('stop_loss', open_p*0.95),
                                'buy_date': today_str, 'name': rec.get('name','')
                            }
                            cash -= cost

    save_json('data/pos.json', positions)
    trades.to_csv('data/trades.csv', index=False)

    # 净值
    total_mv = 0
    for code, pos in positions.items():
        k = get_kline(code, today_str, 1)
        if k is not None: total_mv += k.iloc[0]['close'] * pos['shares']
    used_pos = sum(p['buy_price']*p['shares'] for p in positions.values())
    asset = (CASH - used_pos) + total_mv
    net = round(asset/CASH, 4)
    net_data = load_json('data/net_value.json') or []
    net_data.append({'date': datetime.strptime(today_str,'%Y%m%d').strftime('%Y-%m-%d'), 'net_value': net})
    save_json('data/net_value.json', net_data)

def get_kline(code, end, limit=1):
    df = safe_call(pro.daily, ts_code=code, start_date=end, end_date=end)
    return df
