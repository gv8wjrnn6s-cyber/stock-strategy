import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scripts.utils import *

def fetch_all_data(today_str):
    data = {}
    # 涨停列表
    limit = get_limit(today_str)
    if limit is None or limit.empty:
        return None
    print(f"原始涨停: {len(limit)}")
    # 过滤科创板、ST
    limit = limit[~limit['ts_code'].str.startswith('688')]
    limit = limit[~limit['name'].str.contains('ST', na=False)]
    print(f"过滤后: {len(limit)}")
    # 丰富行情信息
    codes = list(limit['ts_code'])
    enrich = get_enrich(codes, today_str)
    if enrich is not None:
        limit = limit.merge(enrich, on='ts_code', how='left')
        # 一字板过滤
        if 'open' in limit.columns:
            yzb = (limit['open'] >= limit['up_limit']*0.995) & (limit['turnover_rate'] < 0.5) & (limit['open_times']==0)
            limit = limit[~yzb]
            print(f"去一字板: {len(limit)}")
        # 换手太低
        if 'turnover_rate' in limit.columns:
            limit = limit[limit['turnover_rate'] >= 2]
    data['candidates'] = limit
    # K线
    kline_dict = {}
    for code in limit['ts_code']:
        k = get_kline(code, today_str, 25)
        if k is not None: kline_dict[code] = k
    data['kline'] = kline_dict
    # 大盘
    sh = get_kline('000001.SH', today_str, 25)
    if sh is not None and len(sh)>=20:
        sh['ma20'] = sh['close'].rolling(20).mean()
        data['market_weak'] = sh.iloc[-1]['close'] < sh.iloc[-1]['ma20']
    else:
        data['market_weak'] = False
    # 概念板块
    concept = get_concept(today_str)
    data['concept_daily'] = concept
    # 龙虎榜
    top = safe_call(pro.top_list, trade_date=today_str)
    data['top_list'] = top if top is not None else pd.DataFrame()
    return data

def get_limit(trade_date):
    df = safe_call(pro.limit_list, trade_date=trade_date, limit_type='U',
                   fields='ts_code,name,close,pct_chg,float_mv,turnover_ratio,limit_amount,first_time,open_times,up_stat')
    return df

def get_enrich(ts_codes, trade_date):
    codes = ','.join(ts_codes)
    daily = safe_call(pro.daily, ts_code=codes, trade_date=trade_date,
                      fields='ts_code,open,high,low,close,pre_close,pct_chg')
    basic = safe_call(pro.daily_basic, ts_code=codes, trade_date=trade_date,
                      fields='ts_code,turnover_rate')
    if daily is None: return None
    # 涨停价获取
    up_dict = {}
    for c in ts_codes:
        lim = safe_call(pro.stk_limit, ts_code=c, trade_date=trade_date, fields='up_limit')
        if lim is not None and not lim.empty:
            up_dict[c] = lim.iloc[0]['up_limit']
        else:
            pre = daily[daily['ts_code']==c]['pre_close'].values
            up_dict[c] = round(pre[0]*1.1, 2) if len(pre) else np.nan
    daily['up_limit'] = daily['ts_code'].map(up_dict)
    if basic is not None:
        daily = daily.merge(basic[['ts_code','turnover_rate']], on='ts_code', how='left')
    else:
        daily['turnover_rate'] = np.nan
    return daily

def get_kline(code, end_date, limit=25):
    end = datetime.strptime(end_date, '%Y%m%d')
    start = end - timedelta(days=limit*3)
    df = safe_call(pro.daily, ts_code=code, start_date=start.strftime('%Y%m%d'), end_date=end_date)
    if df is not None and not df.empty:
        return df.sort_values('trade_date').tail(limit)
    return None

def get_concept(trade_date):
    cache = 'data/concept_daily.csv'
    need_update = True
    if os.path.exists(cache):
        old = pd.read_csv(cache, dtype={'concept_code':str})
        if trade_date in old['trade_date'].values:
            return old[old['trade_date']==trade_date]
    # 获取
    clist = safe_call(pro.concept, fields='code')
    if clist is None: return pd.DataFrame()
    all_ = []
    codes = [c for c in clist['code'] if c.startswith('BK')]
    for i in range(0, len(codes), 200):
        batch = ','.join(codes[i:i+200])
        d = safe_call(pro.daily, ts_code=batch, start_date=trade_date, end_date=trade_date, fields='ts_code,pct_chg')
        if d is not None: all_.append(d)
    if all_:
        res = pd.concat(all_)
        res['concept_code'] = res['ts_code'].str.replace('.BK','', regex=False)
        res = res[['concept_code','pct_chg']]
        res['trade_date'] = trade_date
        os.makedirs('data', exist_ok=True)
        if os.path.exists(cache):
            old = pd.read_csv(cache, dtype={'concept_code':str})
            old = old[old['trade_date']!=trade_date]
            new = pd.concat([old, res], ignore_index=True)
        else:
            new = res
        new.to_csv(cache, index=False)
        return res
    return pd.DataFrame()
