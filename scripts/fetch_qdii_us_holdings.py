"""
用天天基金API获取24只QDII基金的美股持仓
"""
import winreg, requests, json, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment')
APIKEY, _ = winreg.QueryValueEx(key, 'TTFUND_APIKEY')
URL = 'https://skills.tiantianfunds.com/ai-smart-skill-service/openapi/skill/invoke'
HEADERS = {'X-API-Key': APIKEY, 'Content-Type': 'application/json'}

# 24只QDII基金代码（从qdii_fund_report.html提取，去重A/C）
QDII_CODES = [
    '539002','016664','002891','457001','012920','006373','005698',
    '501225','017730','008253','100055','006555','501226','270023',
    '018229','016701','020712','017091','501312','270042','050025',
    '017144','518880','008763'
]

stock_counter = Counter()
stock_names = {}
fund_count = 0

def get_holdings(code):
    try:
        resp = requests.post(URL, headers=HEADERS, json={
            'skill_id': 'FUND_HOLDING_INFO', '_skill_version': '1.0.0',
            'fund_id': code
        }, timeout=30)
        data = resp.json()
        body = data.get('data',{}).get('raw_result',{}).get('body',{}).get('data',{})
        fname = body.get('fund_profile',{}).get('fund_name','')
        stocks = body.get('top_holdings',{}).get('stock', [])
        if not stocks: stocks = []
        return code, fname, stocks
    except Exception as e:
        return code, str(e), []

print(f"Fetching holdings for {len(QDII_CODES)} QDII funds...")
with ThreadPoolExecutor(max_workers=3) as ex:
    futures = {ex.submit(get_holdings, c): c for c in QDII_CODES}
    for f in as_completed(futures):
        code, fname, stocks = f.result()
        for s in stocks:
            if 'NEWTEXCH' in s and s['NEWTEXCH'] == '116':
                # Skip HK stocks for US analysis
                continue
            sc = s.get('GPDM', '')
            sn = s.get('GPJC', '')
            if not sc or not sn: continue
            # Only track non-Chinese stocks (letters or mixed)
            # US stocks typically have ticker symbols
            if sc.isalpha():
                stock_counter[sc] += 1
                if sc not in stock_names:
                    stock_names[sc] = sn
        fund_count += 1
        if fund_count % 5 == 0:
            print(f"  {fund_count}/{len(QDII_CODES)}")

print(f"\nDone: {fund_count}/{len(QDII_CODES)} funds, {len(stock_counter)} US stocks\n")
print("=== QDII基金美股持仓 Top 20 ===")
for code, count in stock_counter.most_common(20):
    name = stock_names.get(code, '?')
    print(f"  {code:8s} {name:35s} x{count}")

# Save result
result = [{'code': c, 'name': stock_names.get(c, '?'), 'count': n} 
          for c, n in stock_counter.most_common()]
output = 'D:/1.work/project/agu-web2/scripts/qdii_us_holdings.json'
with open(output, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\nSaved to {output}")
