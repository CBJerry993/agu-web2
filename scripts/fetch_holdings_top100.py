"""
Top100基金持仓统计脚本 - 逐基金遍历前十大重仓，统计各板块股票出现频次(>=3次)
"""
import winreg
import requests
import json
import re
import time
from collections import Counter

# 路径
EM_TOP100 = 'D:/1.work/project/agu-web2/scripts/em_top100.json'
OUTPUT = 'D:/1.work/project/agu-web2/scripts/holdings_top100.json'

# 加载基金列表
with open(EM_TOP100, 'r', encoding='utf-8') as f:
    funds_data = json.load(f)
funds = funds_data['funds']
print(f'共 {len(funds)} 只基金')

# API 配置
key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment')
AK, _ = winreg.QueryValueEx(key, 'TTFUND_APIKEY')
URL = 'https://skills.tiantianfunds.com/ai-smart-skill-service/openapi/skill/invoke'
H = {'X-API-Key': AK, 'Content-Type': 'application/json'}

# 统计
stock_count = Counter()
stock_names = {}
ok, fail = 0, 0

for i, fund in enumerate(funds):
    code = fund['code']
    name = fund['name'][:20]
    try:
        resp = requests.post(URL, headers=H, json={
            'skill_id': 'FUND_HOLDING_INFO',
            '_skill_version': '1.0.0',
            'fund_id': code,
        }, timeout=30)
        
        body = resp.json()
        raw = body.get('data', {}).get('raw_result', {})
        stocks = raw.get('body', {}).get('data', {}).get('top_holdings', {}).get('stock', [])
        
        for s in stocks:
            sc = s['GPDM']   # 股票代码
            sn = s['GPJC']   # 股票简称
            stock_count[sc] += 1  # 每只基金 +1
            stock_names[sc] = sn
        
        ok += 1
    except Exception as e:
        fail += 1
        print(f'  [{i+1:3d}] {code} {name}: FAIL')
        continue
    
    # 进度
    if (i + 1) % 20 == 0:
        print(f'  [{i+1:3d}/{len(funds)}] ok={ok} fail={fail} unique={len(stock_count)}')
    
    time.sleep(0.3)

print(f'\n完成: ok={ok} fail={fail} unique={len(stock_count)}')

# 分类: 主板/创业板/科创板/美股/港股
boards = {'主板': [], '创业板': [], '科创板': [], '美股': [], '港股': []}
for sc, cnt in stock_count.most_common():
    s = str(sc)
    item = {'code': sc, 'name': stock_names[sc], 'count': cnt}
    
    if re.match(r'^[A-Za-z]', s):
        boards['美股'].append(item)
    elif s.startswith('688'):
        boards['科创板'].append(item)
    elif s.startswith(('300', '301')):
        boards['创业板'].append(item)
    elif s.startswith(('600', '601', '603', '605', '000', '001', '002', '003')):
        boards['主板'].append(item)
    elif len(s) >= 4 and s[0] in '0123456789':
        boards['港股'].append(item)

# 过滤 >=3 次，限制每板块数量
CAPS = {'主板': 16, '创业板': 16, '科创板': 12, '美股': 8, '港股': 8}
out = {}
for board in ['主板', '创业板', '科创板', '美股', '港股']:
    items = [s for s in boards[board] if s['count'] >= 3]
    out[board] = items[:CAPS[board]]
    if items:
        print(f'{board}: {len(items)} stocks >=3, kept {len(out[board])}')
        for s in out[board][:5]:
            print(f'  {s["code"]} {s["name"]} x{s["count"]}')
    else:
        print(f'{board}: 0 stocks >=3')

# 保存
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f'\n已保存: {OUTPUT}')
