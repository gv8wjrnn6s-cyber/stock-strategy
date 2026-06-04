import time, random, tushare as ts, pandas as pd, os, logging, json
from datetime import datetime, timedelta

TOKEN = os.environ.get('TUSHARE_TOKEN')
if not TOKEN:
    raise RuntimeError("TUSHARE_TOKEN not set")
pro = ts.pro_api(TOKEN)

if not os.path.exists('logs'): os.makedirs('logs')
logging.basicConfig(filename='logs/error.log', level=logging.WARNING,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def safe_call(func, *args, max_retries=3, **kwargs):
    for i in range(max_retries+1):
        try:
            time.sleep(random.uniform(0.5, 1.0))
            res = func(*args, **kwargs)
            return res
        except Exception as e:
            logging.warning(f"{func.__name__} retry {i}: {e}")
            if i < max_retries: time.sleep(2)
    logging.error(f"{func.__name__} failed finally")
    return None

def is_trade_day(date_str):
    cal = safe_call(pro.trade_cal, exchange='SSE', start_date=date_str, end_date=date_str)
    return cal is not None and not cal.empty and cal.iloc[0]['is_open']==1

def get_last_trade_day(today_str):
    dt = datetime.strptime(today_str,'%Y%m%d')
    for i in range(1,10):
        d = dt - timedelta(days=i)
        if is_trade_day(d.strftime('%Y%m%d')):
            return d.strftime('%Y%m%d')
    return None

def load_json(path):
    if os.path.exists(path):
        with open(path,'r') as f: return json.load(f)
    return None

def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,'w') as f: json.dump(obj, f, indent=2, default=str)
