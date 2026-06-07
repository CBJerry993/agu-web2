"""
从东方财富基金排行API获取全市场今年来Top100基金数据
包含基金代码、名称、各周期收益率
"""
import requests, re, json

OUTPUT = 'D:/1.work/project/agu-web2/scripts/em_top100.json'

url = 'https://fund.eastmoney.com/data/rankhandler.aspx'
params = {
    'op': 'ph', 'dt': 'kf', 'ft': 'all', 'rs': '', 'gs': '0',
    'sc': 'jnzf', 'st': 'desc',
    'sd': '2025-01-01', 'ed': '2026-06-03',
    'pi': '1', 'pn': '100', 'dx': '1'
}
headers = {
    'User-Agent': 'Mozilla/5.0 Chrome/120',
    'Referer': 'https://fund.eastmoney.com/data/fundranking.html'
}

resp = requests.get(url, params=params, headers=headers, timeout=15)
text = resp.text

# Parse: var rankData = {datas:["...","...",...],total:...,...}
# Extract the datas array
m = re.search(r'datas:\[(.*?)\],', text, re.DOTALL)
if not m:
    print("ERROR: Could not find datas array")
    print(text[:500])
    exit()

datas_raw = m.group(1)

# Each fund entry is quoted: "field1,field2,..." 
# Split on pattern: comma followed by quote (end of one entry, start of next)
# Pattern: "," splits entries  
entries = []
current = ''
in_quote = False
for char in datas_raw:
    if char == '"':
        if in_quote:
            # End of entry
            entries.append(current)
            current = ''
        in_quote = not in_quote
    elif in_quote:
        current += char

print(f"Parsed {len(entries)} fund entries")

# Parse each entry
funds = []
for i, entry in enumerate(entries):
    fields = entry.split(',')
    if len(fields) < 16:
        continue
    
    fund = {
        'rank_ytd': i + 1,
        'code': fields[0],
        'name': fields[1],
        'date': fields[3] if len(fields) > 3 else '',
        'nav': fields[4] if len(fields) > 4 else '',
        'acc_nav': fields[5] if len(fields) > 5 else '',
        'day': fields[6] if len(fields) > 6 else '',
        'w1': fields[7] if len(fields) > 7 else '',   # 近1周
        'm1': fields[8] if len(fields) > 8 else '',   # 近1月
        'm3': fields[9] if len(fields) > 9 else '',   # 近3月
        'm6': fields[10] if len(fields) > 10 else '',  # 近6月
        'y1': fields[11] if len(fields) > 11 else '',  # 近1年
        'y2': fields[12] if len(fields) > 12 else '',  # 近2年
        'y3': fields[13] if len(fields) > 13 else '',  # 近3年
        'ytd': fields[14] if len(fields) > 14 else '', # 今年来
        'incep': fields[15] if len(fields) > 15 else '', # 成立来
    }
    funds.append(fund)

# Get total count
total_m = re.search(r'total:(\d+)', text)
total_count = int(total_m.group(1)) if total_m else len(funds)
print(f"Total market funds: {total_count}")

# Save top 100
top100 = funds[:100]
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump({'total': total_count, 'funds': top100}, f, ensure_ascii=False, indent=2)

print(f"Saved {len(top100)} funds to {OUTPUT}")
print(f"\nTop 20 by YTD:")
for f in top100[:20]:
    try:
        ytd_v = float(f['ytd'])
    except:
        ytd_v = -999
    print(f"  #{f['rank_ytd']}: {f['code']} {f['name'][:30]} YTD={f['ytd']}% w1={f['w1']}% m1={f['m1']}% m3={f['m3']}% m6={f['m6']}% y1={f['y1']}% y2={f['y2']}%")
