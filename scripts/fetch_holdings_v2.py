"""
更新100只Top100基金持仓数据
"""
import winreg, requests, json, time, re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment')
APIKEY, _ = winreg.QueryValueEx(key, 'TTFUND_APIKEY')
URL = 'https://skills.tiantianfunds.com/ai-smart-skill-service/openapi/skill/invoke'
HEADERS = {'X-API-Key': APIKEY, 'Content-Type': 'application/json'}
INPUT = 'D:/1.work/project/agu-web2/scripts/em_top100.json'
OUTPUT = 'D:/1.work/project/agu-web2/scripts/holdings_top100.json'

with open(INPUT, 'r', encoding='utf-8') as f:
    funds = json.load(f)['funds']

codes = [f['code'] for f in funds]
print(f"Fetching holdings for {len(codes)} funds...")

all_stocks = {}
stock_counter = Counter()

def get_holdings(code):
    try:
        resp = requests.post(URL, headers=HEADERS, json={
            'skill_id': 'FUND_HOLDING_INFO', '_skill_version': '1.0.0',
            'fund_id': code
        }, timeout=30)
        body = resp.json().get('data',{}).get('raw_result',{}).get('body',{}).get('data',{})
        stocks = body.get('top_holdings',{}).get('stock', [])
        return code, stocks if stocks else []
    except:
        return code, []

with ThreadPoolExecutor(max_workers=3) as ex:
    futures = {ex.submit(get_holdings, c): c for c in codes}
    done = 0
    for f in as_completed(futures):
        code, stocks = f.result()
        for s in stocks:
            sc = s['GPDM']
            sn = s['GPJC']
            stock_counter[sc] += 1
            if sc not in all_stocks:
                all_stocks[sc] = {'name': sn, 'exchange': s.get('NEWTEXCH','')}
        done += 1
        if done % 20 == 0:
            print(f"  {done}/{len(codes)}")

print(f"Done: {done}/{len(codes)}, {len(stock_counter)} unique stocks")

# Classify
def cls(code, ex):
    s = str(code)
    if ex == '116': return '港股'
    if re.match(r'^[A-Za-z]', s): return '美股'
    if s.startswith('688'): return '科创板'
    if s.startswith(('300','301')): return '创业板'
    if s.startswith(('600','601','603','605','000','001','002','003')): return '主板'
    return '其他'

boards = {'主板':[], '创业板':[], '科创板':[], '美股':[], '港股':[], '其他':[]}
for sc, cnt in stock_counter.most_common():
    b = cls(sc, all_stocks.get(sc,{}).get('exchange',''))
    boards[b].append({'code': sc, 'name': all_stocks.get(sc,{}).get('name',''), 'count': cnt})

for b in ['主板','创业板','科创板','美股','港股']:
    items = boards[b]
    print(f"\n{b} ({len(items)} stocks):")
    for it in items[:8]:
        print(f"  {it['code']} {it['name'][:20]} x{it['count']}")

# Save (top 20 for 主板/创业板/科创板, top 8 for 美股)
out = {}
for b in ['主板','创业板','科创板']:
    out[b] = boards[b][:20]
out['美股'] = boards['美股'][:12]  # Get a few more for descriptions
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"\nSaved to {OUTPUT}")
