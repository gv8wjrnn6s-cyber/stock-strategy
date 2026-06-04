#!/usr/bin/env python3
"""
主入口：依次运行数据获取、评分、模拟、网页生成
"""
import sys, os, shutil, json
from datetime import datetime, timedelta

# 强制输出实时日志
print("开始执行主程序...")

TODAY = (datetime.now() - timedelta(hours=8)).strftime('%Y%m%d')  # 北京时间

# 检查交易日
from scripts.utils import is_trade_day
if not is_trade_day(TODAY):
    print(f"{TODAY} 非交易日，退出")
    sys.exit(0)

# 防重复运行
done_file = 'data/last_run_date.txt'
os.makedirs('data', exist_ok=True)
if os.path.exists(done_file):
    with open(done_file) as f:
        if f.read().strip() == TODAY:
            print("今日已运行过，退出")
            sys.exit(0)

# 数据获取
print("1/5 获取数据...")
from scripts.fetch_data import fetch_all_data
data = fetch_all_data(TODAY)
if data is None or data['candidates'].empty:
    print("无候选股，生成空网页")
    from scripts.build_website import generate_empty_page
    generate_empty_page(TODAY, "无符合条件的涨停股")
    with open(done_file, 'w') as f: f.write(TODAY)
    sys.exit(0)

# 评分
print("2/5 评分选股...")
from scripts.scoring import score_and_select
recommend = score_and_select(data['candidates'], data)

# 保存推荐记录
rec_path = f'data/daily_recommend/{TODAY}.json'
os.makedirs(os.path.dirname(rec_path), exist_ok=True)
recommend.to_json(rec_path, orient='records', force_ascii=False)

# 模拟交易（处理昨天推荐）
prev_day = (datetime.strptime(TODAY, '%Y%m%d') - timedelta(days=1)).strftime('%Y%m%d')
prev_rec = f'data/daily_recommend/{prev_day}.json' if os.path.exists(f'data/daily_recommend/{prev_day}.json') else None
print("3/5 模拟交易...")
from scripts.backtest_sim import run_simulation_and_optimize
run_simulation_and_optimize(TODAY, prev_rec, data)

# 生成网页
print("4/5 生成网页...")
from scripts.build_website import generate_website
generate_website(TODAY, recommend)

# 标记完成
with open(done_file, 'w') as f:
    f.write(TODAY)

# 拷贝数据到 docs
print("5/5 部署...")
if os.path.exists('data/net_value.json'):
    shutil.copy('data/net_value.json', 'docs/net_value.json')

print("全过程完成！")
