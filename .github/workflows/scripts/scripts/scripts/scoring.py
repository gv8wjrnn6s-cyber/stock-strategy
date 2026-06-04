import pandas as pd
import numpy as np
from scripts.utils import *
from scripts.fetch_data import get_kline

WEIGHTS = {
    "float_mv": 1.5,
    "seal_quality": 3,
    "time_early": 2,
    "open_times": 1.5,
    "turnover": 1,
    "concept": 2.5,
    "momentum": 0.5,
    "top_buy": 1,
    "late_penalty": -2
}

def calc_indicators(df):
    if df is None or df.empty: return None
    df = df.sort_values('trade_date')
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    exp12 = df['close'].ewm(span=12, adjust=False).mean()
    exp26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp12 - exp26
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['signal']
    df['tr'] = np.maximum(df['high']-df['low'], np.maximum(abs(df['high']-df['close'].shift(1)), abs(df['low']-df['close'].shift(1))))
    df['atr'] = df['tr'].rolling(14).mean()
    return df

def score_and_select(candidates, market_data):
    df = candidates.copy()
    df['score'] = 0.0
    kline_dict = market_data.get('kline', {})
    concept = market_data.get('concept_daily', pd.DataFrame())
    top_list = market_data.get('top_list', pd.DataFrame())
    weak = market_data.get('market_weak', False)

    # 概念前15%
    top_concepts = set()
    if not concept.empty:
        concept['rank'] = concept['pct_chg'].rank(pct=True, ascending=False)
        top_concepts = set(concept[concept['rank']<=0.15]['concept_code'])

    # 加载概念映射（简单用缓存）
    concept_map = pd.read_csv('data/concept_cache.csv') if os.path.exists('data/concept_cache.csv') else pd.DataFrame()

    for i, row in df.iterrows():
        s = 0
        code = row['ts_code']
        mv = row.get('float_mv', np.nan)
        if pd.notna(mv) and 10 <= mv <= 50:
            s += WEIGHTS['float_mv']
        # 封单质量
        seal = row.get('limit_amount', 0)
        if pd.notna(seal) and pd.notna(mv) and mv>0:
            if seal/mv > 0.15: s += WEIGHTS['seal_quality']
        # 涨停时间
        ft = str(row.get('first_time', ''))
        if ft and ft<'10:30:00': s += WEIGHTS['time_early']
        if ft and ft>'14:30:00': s += WEIGHTS['late_penalty']
        # 开板次数
        ot = row.get('open_times', None)
        if ot==0: s += WEIGHTS['open_times']
        elif ot and ot>=2: s -= 1
        # 换手率
        tr = row.get('turnover_ratio', np.nan)
        if pd.notna(tr) and 5<=tr<=25: s += WEIGHTS['turnover']
        # 概念
        if not concept_map.empty:
            con_codes = concept_map[concept_map['ts_code']==code]['concept_code'].tolist()
            if any(c in top_concepts for c in con_codes): s += WEIGHTS['concept']
        # 技术面
        if code in kline_dict:
            tech = calc_indicators(kline_dict[code])
            if tech is not None and not tech.empty:
                last = tech.iloc[-1]
                if pd.notna(last['ma5']) and pd.notna(last['ma10']) and pd.notna(last['ma20']):
                    if last['ma5'] > last['ma10'] > last['ma20']:
                        s += WEIGHTS['momentum']
        # 龙虎榜
        if not top_list.empty:
            t = top_list[top_list['ts_code']==code]
            if not t.empty:
                net = t.iloc[0].get('net_buy',0)
                if pd.notna(net) and net>0: s += WEIGHTS['top_buy']
        df.at[i,'score'] = s

    if weak: df['score'] *= 0.7
    top_n = 2 if weak else 5
    df = df.sort_values('score', ascending=False).head(top_n)

    # 生成建议
    for i, row in df.iterrows():
        code = row['ts_code']
        stop = row.get('low', row['close']*0.95)
        if code in kline_dict:
            tech = calc_indicators(kline_dict[code])
            if tech is not None and not tech.empty:
                atr = tech.iloc[-1]['atr']
                if pd.notna(atr):
                    stop = max(stop, row['close'] - atr*1.5)
        df.at[i,'stop_loss'] = round(stop, 2)
        df.at[i,'idea_buy'] = "次日开盘涨0~3%，量比>1.2"
        df.at[i,'abandon'] = "开盘30分钟涨超5%或跌超2%放弃"
        df.at[i,'hold'] = "持有2天，止盈3%，严格止损"
    return df
