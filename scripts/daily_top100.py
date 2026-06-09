"""
Top100日更脚本 - 模板+数据分离方案
步骤: 拉基金列表 → 拉排名 → 拉持仓(仅季度) → 分类 → 输出top100_data.json
HTML模板 (top_100.html) 通过JS加载此JSON渲染页面，自动化永远不碰模板
"""
from pathlib import Path
import requests, re, json, time, datetime, sys

today = datetime.date.today().strftime('%Y-%m-%d')
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'scripts'
OUTPUT = ROOT / 'reports' / 'top_100.html'
PAGE_OUTPUT = ROOT / 'pages' / 'top100.html'
H = {'User-Agent': 'Mozilla/5.0 Chrome/120', 'Referer': 'https://fund.eastmoney.com/data/fundranking.html'}
API = 'https://fund.eastmoney.com/data/rankhandler.aspx'

# ======================== STEP 1: Fund list ========================
print('[1/4] Fetching Top100 fund list...')
resp = requests.get(API, params={'op':'ph','dt':'kf','ft':'all','sc':'jnzf','st':'desc','pi':'1','pn':'100','dx':'1'}, headers=H, timeout=15)
m = re.search(r'datas:\[(.*?)\],', resp.text, re.DOTALL)
if not m: print('ERROR: No data'); sys.exit(1)

entries = []; cur = ''; iq = False
for ch in m.group(1):
    if ch == chr(34):
        if iq: entries.append(cur); cur = ''
        iq = not iq
    elif iq: cur += ch

funds = []
for i, e in enumerate(entries[:100]):
    f = e.split(',')
    if len(f) < 16: continue
    funds.append({
        'rank_ytd': i+1, 'code': f[0], 'name': f[1],
        'w1': f[7], 'm1': f[8], 'm3': f[9], 'm6': f[10],
        'y1': f[11], 'y2': f[12], 'ytd': f[14],
    })

print(f'  Got {len(funds)} funds. Top: {funds[0]["code"]} YTD={funds[0]["ytd"]}%')

# ======================== STEP 2: Rankings ========================
print('[2/4] Fetching rankings...')
PS = {'w1':'zzf','m1':'1yzf','m3':'3yzf','m6':'6yzf','ytd':'jnzf','y1':'1nzf','y2':'2nzf'}
FT = ['hh','gp','zs','qdii']
target = set(f['code'] for f in funds)
rd = {}

for p, sc in PS.items():
    all_codes = []; total = 0
    
    for ft in FT:
        ft_codes = []
        pg = 1
        while pg <= 50:
            url = f'{API}?op=ph&dt=kf&ft={ft}&sc={sc}&st=desc&pi={pg}&pn=200&dx=1'
            try:
                resp = requests.get(url, headers=H, timeout=15)
            except: break
            t = resp.text
            if 'ErrCode:-999' in t: time.sleep(0.3); continue
            
            start = t.find('datas:[') + 7
            if start < 7: break
            end = t.find('],', start)
            if end < 0: break
            
            entries = []; cur = ''; iq = False
            for ch in t[start:end]:
                if ch == chr(34):
                    if iq: entries.append(cur); cur = ''
                    iq = not iq
                elif iq: cur += ch
            if not entries: break
            
            if total == 0:
                # Use type-specific count: hh_count, gp_count, zs_count, qdii_count
                ckeys = {'hh':'hh_count','gp':'gp_count','zs':'zs_count','qdii':'qdii_count'}
                ck = ckeys.get(ft, 'hh_count')
                tm = t.find(ck + ':') + len(ck) + 1
                if tm > len(ck):
                    comma = t.find(',', tm)
                    total = int(t[tm:comma]) if comma > 0 else 0
            
            ft_codes.extend(e.split(',')[0] for e in entries)
            pg += 1
            time.sleep(0.05)
        
        all_codes.extend(ft_codes)
    
    if p not in rd: rd[p] = {}
    for i, c in enumerate(all_codes):
        if c in target and c not in rd[p]:
            rk = i + 1; pv = rk / total if total else 0.5
            pct = '前%d%%' % round(pv*100) if pv < 0.5 else '后%d%%' % round(pv*100)
            rd[p][c] = {'rank': rk, 'total': total, 'pct': pct}
    
    print(f'  {p}: {len(rd[p])}/{len(target)}')

# ======================== STEP 3: Classification ========================
print('[3/4] Classifying...')
cats = {'夯':[], '顶':[], '人上人':[], '拉':[], 'NPC':[]}
for f in funds:
    code = f['code']
    in_top_50 = in_bot_50 = 0
    w1m3_top30 = True
    for p in ['w1','m1','m3','m6','ytd','y1','y2']:
        if code not in rd.get(p,{}): continue
        pct_val = rd[p][code]['rank'] / rd[p][code]['total']
        if pct_val <= 0.5:
            in_top_50 += 1
            if p in ('w1','m1','m3') and pct_val > 0.3: w1m3_top30 = False
        else:
            in_bot_50 += 1
    
    if in_top_50 >= 5 and w1m3_top30: cat = '夯'
    elif in_top_50 >= 5: cat = '顶'
    elif in_top_50 >= 4: cat = '人上人'
    elif in_bot_50 >= 5: cat = '拉'
    else: cat = 'NPC'
    f['cat'] = cat
    cats[cat].append(f)

# ======================== STEP 4: Output JSON ========================
print('[4/4] Output JSON data...')

# Build stats HTML
stats_html = f'''<div class="scard blue"><div class="val">100</div><div class="lbl">基金总数</div></div>
<div class="scard red"><div class="val">{len(cats['夯'])}</div><div class="lbl">夯 · 顶尖</div></div>
<div class="scard orange"><div class="val">{len(cats['顶'])}</div><div class="lbl">顶 · 优秀</div></div>
<div class="scard green"><div class="val">{len(cats['人上人'])}</div><div class="lbl">人上人 · 良好</div></div>
<div class="scard purple"><div class="val">{len(cats['拉'])}</div><div class="lbl">拉 · 警示</div></div>
<div class="scard gray"><div class="val">{len(cats['NPC'])}</div><div class="lbl">NPC · 普通</div></div>'''

# Build sections HTML (reuse existing secs generation logic)
ccfg = {
    '夯': ('c0392b','#fdecea','5前50%且1W/1M/3M全前30%','顶尖'),
    '顶': ('e67e22','#fef3e2','5前50%','优秀'),
    '人上人': ('27ae60','#e8f5e9','4前50%','良好'),
    '拉': ('8e44ad','#f3e5f5','5后50%','警示'),
    'NPC': ('888','#f5f5f5','其他','普通'),
}

secs = []
for cat in ['夯','顶','人上人','拉','NPC']:
    if not cats[cat]: continue
    cl, bg, desc, lb = ccfg[cat]
    secs.append(f'''<div class="st" style="border-left-color:#{cl}">{cat} · {lb}<span class="badge" style="background:{bg};color:#{cl}">{len(cats[cat])}只 · {desc}</span></div>
<div class="tw"><table class="ft"><thead><tr><th>基金（代码+简称）</th><th>近1周</th><th>近1月</th><th>近3月</th><th>近6月</th><th>今年来</th><th>近1年</th><th>近2年</th></tr></thead><tbody>{rows(cats[cat])}</tbody></table></div>''')

# Check coverage
missing = []
for f in funds:
    code = f['code']
    for p in ['w1','m1','m3','m6','ytd','y1','y2']:
        if code not in rd.get(p,{}):
            ret = f.get(p,'')
            if ret and str(ret).strip() not in ('','--','%'):
                missing.append((code, f['name'][:20], p))

note_html = ''
if missing:
    note_html = f'<div class="nb">⚠️ {len(missing)}项排名缺失(有收益无排名)，主要是近1年/近2年新基金成立时间不足。具体: {json.dumps(missing[:5], ensure_ascii=False)}...</div>'

sections_html = note_html + ''.join(secs)

# Output JSON
output_data = {
    "updateDate": today,
    "generateDate": today,
    "fundCount": 100,
    "statsHtml": stats_html,
    "sectionsHtml": sections_html,
}

DATA_DIR = ROOT / 'reports'
DATA_DIR.mkdir(parents=True, exist_ok=True)
data_json = DATA_DIR / 'top100_data.json'

with open(data_json, 'w', encoding='utf-8') as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print(f'Data JSON: {data_json}')
print(f'Classification: 夯{len(cats["夯"])} 顶{len(cats["顶"])} 人上人{len(cats["人上人"])} 拉{len(cats["拉"])} NPC{len(cats["NPC"])}')
print(f'Coverage: {" ".join(f"{p}{len(rd.get(p,{}))}" for p in ["w1","m1","m3","m6","ytd","y1","y2"])}')
if missing:
    for c,n,p in missing[:5]:
        print(f'  MISSING: {c} {n} -> {p}')
