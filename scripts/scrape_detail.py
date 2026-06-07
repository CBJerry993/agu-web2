"""
从每只基金的东方财富详情页抓取同类排名
来源: https://fund.eastmoney.com/{CODE}.html
"""
import requests, re, json, time

INPUT = 'D:/1.work/project/agu-web2/scripts/em_top100.json'
OUTPUT = 'D:/1.work/project/agu-web2/scripts/em_top100_ranked.json'

with open(INPUT, 'r', encoding='utf-8') as f:
    funds = json.load(f)['funds']

H = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

# Period mapping: the first 8 rank|total pairs in the HTML correspond to these periods
PERIOD_ORDER = ['w1', 'm1', 'm3', 'm6', 'ytd', 'y1', 'y2', 'y3']

def fetch_rank(code):
    try:
        resp = requests.get(f'https://fund.eastmoney.com/{code}.html', headers=H, timeout=15)
        resp.encoding = 'utf-8'
        html = resp.text
    except:
        return {}
    
    # Method 1: pipe-separated (混合型/股票型): "9 | 5220" 
    all_ranks = re.findall(r'(\d+|--)\s*\|\s*(\d{2,4})', html)
    
    if len(all_ranks) < 8:
        # Method 2: QDII format - numbers near "阶段涨幅" section
        # Find the stage performance section and extract rankings
        idx = html.find('阶段涨幅')
        if idx > 0:
            section = html[idx:idx+2000]
            # Find rank-total pairs: number followed by number (total 2-3 digits)
            all_ranks = re.findall(r'>(\d+|--)\s+(\d{2,3})\s*<', section)
    
    if len(all_ranks) < 8:
        return {}
    
    # First 8 are the stage performance rankings
    ranks = {}
    for i, period_key in enumerate(PERIOD_ORDER):
        if i >= len(all_ranks): break
        rk_str = all_ranks[i][0]
        total = int(all_ranks[i][1])
        if rk_str == '--':
            rk = None  # No ranking available
            pct = '--'
        else:
            rk = int(rk_str)
            pv = rk / total
            pct = f'前{round(pv*100)}%' if pv < 0.5 else f'后{round(pv*100)}%'
        ranks[period_key] = {'rank': rk, 'total': total, 'pct': pct}
    
    return ranks

# Fetch for all 100 funds
rd = {}
for i, fund in enumerate(funds):
    code = fund['code']
    
    # Check if we already have ranking data for this fund
    ranks = fetch_rank(code)
    for pkey, r in ranks.items():
        if pkey not in rd:
            rd[pkey] = {}
        rd[pkey][code] = r
    
    if (i + 1) % 10 == 0:
        print(f'  {i+1}/100')
    time.sleep(0.3)

# Save
with open(INPUT, 'r', encoding='utf-8') as f:
    data = json.load(f)
data['rank_data'] = rd

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# Summary
coverage = {p: len(rd.get(p, {})) for p in ['w1','m1','m3','m6','ytd','y1','y2']}
print(f'Done. Coverage: {coverage}')

# Show first fund
code = funds[0]['code']
print(f'\n{code}:')
for p in ['w1','m1','m3','m6','ytd','y1','y2']:
    r = rd.get(p, {}).get(code, {})
    if r:
        print(f'  {p}: {r["rank"]} | {r["total"]} = {r["pct"]}')
