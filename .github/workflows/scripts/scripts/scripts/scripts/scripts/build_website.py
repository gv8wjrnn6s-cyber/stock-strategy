import shutil, json, os
from datetime import datetime

def generate_website(today, rec):
    html = open('web/template.html', 'r', encoding='utf-8').read()
    date_show = datetime.strptime(today,'%Y%m%d').strftime('%Y-%m-%d')
    status = '弱势' if os.path.exists('data/market_weak.txt') else '正常'
    rows = ''
    for _, r in rec.iterrows():
        rows += f"<tr><td>{r['ts_code']}</td><td>{r['name']}</td><td>{r['score']:.1f}</td><td>{r['idea_buy']}</td><td>{r['stop_loss']}</td><td>中</td></tr>"
    html = html.replace('{{ROWS}}', rows)
    html = html.replace('{{DATE}}', date_show)
    html = html.replace('{{STATUS}}', status)
    net = []
    if os.path.exists('data/net_value.json'):
        with open('data/net_value.json') as f: net = json.load(f)
    net_js = json.dumps(net)
    html = html.replace('//{{NET}}', f'var netValueData = {net_js};')
    os.makedirs('docs', exist_ok=True)
    with open('docs/index.html','w', encoding='utf-8') as f:
        f.write(html)
    for fname in ['style.css','script.js']:
        if os.path.exists(f'web/{fname}'):
            shutil.copy(f'web/{fname}', f'docs/{fname}')

def generate_empty_page(today, msg):
    # 类似处理，生成空页
    pass
