"""
获取100只基金在各周期的同类排名，生成GS145风格的三行格式数据
策略: 按fund type分类，逐类逐周期抓取排名
"""
import requests, re, json, time
from collections import defaultdict

EM_DATA = 'D:/1.work/project/agu-web2/scripts/em_top100.json'
OUTPUT = 'D:/1.work/project/agu-web2/scripts/em_top100_ranked.json'
URL = 'https://fund.eastmoney.com/data/rankhandler.aspx'
HEADERS = {'User-Agent': 'Mozilla/5.0 Chrome/120', 'Referer': 'https://fund.eastmoney.com/data/fundranking.html'}

with open(EM_DATA, 'r', encoding='utf-8') as f:
    em = json.load(f)
funds = em['funds']
target_codes = set(f['code'] for f in funds)

# Period parameters for sc (sort column)
# 近1周=zzf, 近1月=1yzf, 近3月=3yzf, 近6月=6yzf, 今年来=jnzf, 近1年=1nzf, 近2年=2nzf
PERIODS = [
    ('w1', 'zzf', '近1周'),
    ('m1', '1yzf', '近1月'),
    ('m3', '3yzf', '近3月'),
    ('m6', '6yzf', '近6月'),
    ('ytd', 'jnzf', '今年来'),
    ('y1', '1nzf', '近1年'),
    ('y2', '2nzf', '近2年'),
]

# Fund types to query
FT_TYPES = [
    ('gp', '股票型'),
    ('hh', '混合型'),
    ('zs', '指数型'),
    ('qdii', 'QDII'),
]

def parse_funds(text):
    """Parse rankData from eastmoney response"""
    m = re.search(r'datas:\[(.*?)\],', text, re.DOTALL)
    if not m:
        return [], 0
    
    entries = []
    current = ''
    in_quote = False
    for char in m.group(1):
        if char == '"':
            if in_quote:
                entries.append(current)
                current = ''
            in_quote = not in_quote
        elif in_quote:
            current += char
    
    all_m = re.search(r'allRecords:(\d+)', text)
    total = int(all_m.group(1)) if all_m else 0
    
    result = []
    for entry in entries:
        fields = entry.split(',')
        if len(fields) >= 15:
            result.append({'code': fields[0], 'name': fields[1]})
    
    return result, total

# For each period, for each fund type, get all pages and build rank lookup
print("Fetching rankings for each period × fund type...")
rank_data = {}  # {period: {code: {rank, total}}}

for pkey, sc, pname in PERIODS:
    print(f"\n  [{pname}] sc={sc}")
    rank_data[pkey] = {}
    
    for ft, ft_name in FT_TYPES:
        # Get first page to check total
        params = {'op': 'ph', 'dt': 'kf', 'ft': ft, 'sc': sc, 'st': 'desc',
                  'pi': '1', 'pn': '200', 'dx': '1'}
        
        try:
            resp = requests.get(URL, params=params, headers=HEADERS, timeout=15)
            page_funds, total = parse_funds(resp.text)
        except Exception as e:
            print(f"    {ft}: ERROR {e}")
            continue
        
        if total == 0:
            continue
        
        pages_needed = (total + 199) // 200  # Ceiling division
        print(f"    {ft}: {total} funds, {pages_needed} pages needed")
        
        # Get remaining pages
        all_type_funds = list(page_funds)
        for page in range(2, min(pages_needed + 1, 6)):  # Max 5 pages (1000 funds)
            try:
                params['pi'] = str(page)
                resp = requests.get(URL, params=params, headers=HEADERS, timeout=15)
                page_funds, _ = parse_funds(resp.text)
                all_type_funds.extend(page_funds)
                time.sleep(0.3)
            except:
                break
        
        # Search for our target codes and assign ranks
        for rank_idx, f in enumerate(all_type_funds):
            if f['code'] in target_codes:
                rank_data[pkey][f['code']] = {
                    'rank': rank_idx + 1,
                    'total': total,
                    'pct': f'前{round((rank_idx + 1) / total * 100)}%' if (rank_idx + 1) / total < 0.5 else f'后{round((rank_idx + 1) / total * 100)}%'
                }
        
        found = sum(1 for c in target_codes if c in rank_data[pkey])
        print(f"      Found {found} of target funds")
        time.sleep(0.3)
    
    total_found = len(rank_data[pkey])
    print(f"  Total found for {pname}: {total_found}/{len(target_codes)}")

# Save results
output = {'rank_data': rank_data, 'funds': funds}
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\nSaved to {OUTPUT}")

# Summary
for pkey, sc, pname in PERIODS:
    found = len(rank_data[pkey])
    print(f"  {pname}: {found}/{len(target_codes)} ranked")
