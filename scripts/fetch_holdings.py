"""
获取Top100基金持仓聚合 - 按股票出现频次统计，分板块
"""
import winreg, requests, json, time, re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment')
APIKEY, _ = winreg.QueryValueEx(key, 'TTFUND_APIKEY')
URL = 'https://skills.tiantianfunds.com/ai-smart-skill-service/openapi/skill/invoke'
HEADERS = {'X-API-Key': APIKEY, 'Content-Type': 'application/json'}

INPUT = 'D:/1.work/project/agu-web2/scripts/top100_data.json'
OUTPUT = 'D:/1.work/project/agu-web2/scripts/holdings_data.json'

with open(INPUT, 'r', encoding='utf-8') as f:
    funds = json.load(f)

codes = [f['code'] for f in funds]
print(f"Processing {len(codes)} funds...")

def get_holdings(code):
    try:
        resp = requests.post(URL, headers=HEADERS, json={
            'skill_id': 'FUND_HOLDING_INFO',
            '_skill_version': '1.0.0',
            'fund_id': code
        }, timeout=30)
        body = resp.json().get('data',{}).get('raw_result',{}).get('body',{}).get('data',{})
        stocks = body.get('top_holdings',{}).get('stock', [])
        if stocks:
            return code, stocks
        return code, []
    except Exception as e:
        return code, []

all_stocks = {}  # code -> {name, count, boards}
stock_count = Counter()

with ThreadPoolExecutor(max_workers=3) as ex:
    futures = {ex.submit(get_holdings, c): c for c in codes}
    done = 0
    for f in as_completed(futures):
        code, stocks = f.result()
        for s in stocks:
            sc = s['GPDM']
            sn = s['GPJC']
            stock_count[sc] += 1
            if sc not in all_stocks:
                all_stocks[sc] = {'name': sn, 'count': 0, 'exchange': s.get('NEWTEXCH','')}
        done += 1
        if done % 20 == 0:
            print(f"  {done}/{len(codes)}")

print(f"Done: {done}/{len(codes)} funds, {len(stock_count)} unique stocks")

# Classify by board
def classify_board(code, exchange):
    code_str = str(code)
    if exchange == '116':  # HK
        return '港股'
    # US stocks have alpha codes
    if re.match(r'^[A-Za-z]', code_str):
        return '美股'
    # A-share classification
    if code_str.startswith('688'):
        return '科创板'
    if code_str.startswith('300') or code_str.startswith('301'):
        return '创业板'
    if code_str.startswith(('600','601','603','605','000','001','002','003')):
        return '主板'
    return '其他'

boards = {'主板': [], '创业板': [], '科创板': [], '美股': [], '港股': [], '其他': []}
for sc, count in stock_count.most_common():
    board = classify_board(sc, all_stocks.get(sc, {}).get('exchange', ''))
    boards[board].append({
        'code': sc,
        'name': all_stocks.get(sc, {}).get('name', ''),
        'count': count
    })

# Print results
for board in ['主板', '创业板', '科创板', '美股', '港股', '其他']:
    items = boards[board]
    print(f"\n{board} ({len(items)} stocks):")
    for item in items[:10]:
        print(f"  {item['code']} {item['name']} x{item['count']}")

# Save
output = {}
for board in ['主板', '创业板', '科创板', '美股']:
    output[board] = boards[board][:20] if board != '美股' else boards[board][:8]

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\nSaved to {OUTPUT}")
