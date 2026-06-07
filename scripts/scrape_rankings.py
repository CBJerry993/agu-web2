"""
从每只基金东方财富详情页抓取同类排名数据
URL: https://fund.eastmoney.com/{CODE}.html
"""
import requests, re, json, time

INPUT = 'D:/1.work/project/agu-web2/scripts/em_top100.json'
OUTPUT = 'D:/1.work/project/agu-web2/scripts/em_top100_ranked.json'

with open(INPUT, 'r', encoding='utf-8') as f:
    funds = json.load(f)['funds']

H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Period name mapping in the detail page
PERIOD_MAP = {
    '近1周': 'w1', '近1月': 'm1', '近3月': 'm3', '近6月': 'm6',
    '今年来': 'ytd', '近1年': 'y1', '近2年': 'y2', '近3年': 'y3',
}

def fetch_rank(code):
    """Scrape fund detail page for ranking data"""
    try:
        resp = requests.get(f'https://fund.eastmoney.com/{code}.html', headers=H, timeout=15)
        resp.encoding = 'utf-8'
        html = resp.text
    except:
        return {}
    
    ranks = {}
    
    # Look for the stage performance table
    # Pattern: each row has <td>近1周</td> ... <td>排名 | 总数</td> ... or similar
    # The table is under class "ui-table-hover" or similar
    
    # Approach: find each period label and extract nearby ranking numbers
    for period_name, period_key in PERIOD_MAP.items():
        # Search for the period in context of ranking numbers
        # Pattern: 近1周...排名数字|总数字
        idx = html.find(period_name)
        if idx < 0:
            continue
        
        # Search around this position for ranking: "数字 | 数字" pattern
        chunk = html[idx:idx+800]
        m = re.search(r'(\d{1,4})\s*\|\s*(\d{1,4})', chunk)
        if m:
            rank = int(m.group(1))
            total = int(m.group(2))
            pv = rank / total
            pct = f'前{round(pv*100)}%' if pv < 0.5 else f'后{round(pv*100)}%'
            ranks[period_key] = {'rank': rank, 'total': total, 'pct': pct}
    
    return ranks

# Fetch for all 100 funds
rd = {}
for i, fund in enumerate(funds):
    code = fund['code']
    ranks = fetch_rank(code)
    for pkey, r in ranks.items():
        if pkey not in rd:
            rd[pkey] = {}
        rd[pkey][code] = r
    
    if (i+1) % 10 == 0:
        print(f'  {i+1}/100')
    time.sleep(0.3)

# Save
with open(INPUT, 'r', encoding='utf-8') as f:
    data = json.load(f)
data['rank_data'] = rd

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# Summary
print(f'\nDone. Coverage:')
for p in ['w1','m1','m3','m6','ytd','y1','y2']:
    c = len(rd.get(p, {}))
    print(f'  {p}: {c}/100')

# Show first fund
code = funds[0]['code']
print(f'\n{code}:')
for p in ['w1','m1','m3','m6','ytd','y1','y2']:
    r = rd.get(p, {}).get(code, {})
    if r:
        print(f'  {p}: {r["rank"]} | {r["total"]} ({r["pct"]})')
