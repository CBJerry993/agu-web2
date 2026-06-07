"""
Top100日更脚本 - 一键生成最新报告
步骤: 拉基金列表 → 拉排名 → 拉持仓(仅季度) → 生成HTML → 检查完整性
"""
import requests, re, json, time, datetime, sys

today = datetime.date.today().strftime('%Y-%m-%d')
DATA_DIR = 'D:/1.work/project/agu-web2/scripts'
OUTPUT = 'D:/1.work/project/agu-web2/reports/top_100.html'
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

# ======================== STEP 4: Generate HTML ========================
print('[4/4] Generating HTML...')

# CSS (GS145-style blue header)
css = '''*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;background:#f0f3f8;color:#1a2035;font-size:12px}
.ph{background:linear-gradient(135deg,#0d2b6e 0%,#1a5fac 50%,#0d8fd9 100%);color:#fff;padding:22px 28px 18px;position:relative;overflow:hidden}
.ph::after{content:'';position:absolute;right:-60px;top:-60px;width:200px;height:200px;border-radius:50%;background:rgba(255,255,255,.06)}
.ph h1{font-size:20px;font-weight:700;letter-spacing:1px}
.ph .sub{font-size:14px;opacity:.85;margin-top:6px}
.ph .ut{font-size:13px;opacity:.7;margin-top:3px;text-align:right}
.main{padding:16px;max-width:1200px;margin:0 auto}
.sr{display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap}
.scard{background:#fff;border-radius:10px;padding:12px 16px;flex:1;min-width:120px;box-shadow:0 1px 6px rgba(0,0,0,.08);border-top:3px solid;text-align:center}
.scard .val{font-size:22px;font-weight:700;line-height:1.2}
.scard .lbl{font-size:11px;margin-top:3px}
.scard.red{border-color:#c0392b}.scard.red .val,.scard.red .lbl{color:#c0392b}
.scard.orange{border-color:#e67e22}.scard.orange .val,.scard.orange .lbl{color:#e67e22}
.scard.green{border-color:#27ae60}.scard.green .val,.scard.green .lbl{color:#27ae60}
.scard.purple{border-color:#8e44ad}.scard.purple .val,.scard.purple .lbl{color:#8e44ad}
.scard.gray{border-color:#888}.scard.gray .val,.scard.gray .lbl{color:#888}
.scard.blue{border-color:#1a5fac}.scard.blue .val,.scard.blue .lbl{color:#1a5fac}
.st{display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:10px;margin:24px 0 14px;font-size:20px;font-weight:800;color:#0d2b6e;letter-spacing:2px;border-left:5px solid;padding:4px 12px;background:#fff;border-radius:6px}
.st .badge{font-size:12px;padding:3px 12px;border-radius:20px;font-weight:600;margin-left:10px;letter-spacing:.5px}
.tw{overflow-x:auto}
.ft{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.07);font-size:13px}
.ft thead tr{background:linear-gradient(90deg,#0d2b6e,#1a5fac);color:#fff}
.ft thead th{padding:9px 5px;font-size:11px;font-weight:600;text-align:center;white-space:nowrap;letter-spacing:.3px;border-right:1px solid rgba(255,255,255,.15)}
.ft thead th:last-child{border-right:none}
.ft thead th:first-child{text-align:left;padding-left:12px}
.ft tbody tr{border-bottom:1px solid #f0f3f8;transition:background .15s}
.ft tbody tr:last-child{border-bottom:none}
.ft tbody tr:hover{background:#f6f9ff!important}
.ft tbody tr.re{background:#fafbfe}
.ft tbody tr.ro{background:#fff}
.ft td{padding:5px 4px;text-align:center;vertical-align:middle;border-right:1px solid #f0f3f8;line-height:1.5}
.ft td:nth-child(n+2){width:72px;min-width:72px}
.ft td:last-child{border-right:none}
.ft td:first-child{text-align:left;padding-left:14px;border-right:none}
.cf{font-size:14px;max-width:380px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cf a{font-weight:700;margin-right:6px;color:#1a5fac;font-size:15px;text-decoration:none}
.cf .fn{font-weight:600;color:#1a2035}
.cr{font-size:15px;font-weight:700}
.crk{font-size:12px;color:#666;margin-top:2px}
.cp{font-size:12px;margin-top:2px}
.up{color:#e63946}.dn{color:#2ba84a}.neutral{color:#888;font-weight:600}.na{color:#ccc;font-size:10px}
.pt{color:#c0392b;font-weight:700}
.pg{color:#d94f3a;background:#fdecea;padding:0 2px;border-radius:2px}
.pm{color:#2e7d32;background:#e8f5e9;padding:0 2px;border-radius:2px}
.pb{color:#1a7a3c;font-weight:700}
.rn{color:#555;font-family:monospace;font-size:12px}
.nb{display:flex;gap:12px;flex-wrap:wrap;padding:8px 16px;font-size:11px;color:#888;background:#fafbfe;border-top:1px solid #f0f3f8;border-radius:0 0 8px 8px}
.pf{text-align:center;color:#aaa;font-size:10px;padding:16px;margin-top:8px}
@media(max-width:1100px){.ft{font-size:11px}.cf,.cf a,.cf .fn{font-size:11px}.cr{font-size:12px}}'''

def cell(period_key, f):
    code = f['code']
    ret = f.get(period_key, '')
    if not ret or str(ret).strip() in ('', '--', '%'):
        return '<td><div class="cr"><span class="na">--</span></div></td>'
    try:
        rv = float(str(ret).replace('%','').replace('+',''))
        sign = '+' if rv > 0 else ''
        cls = 'up' if rv > 0 else ('dn' if rv < 0 else 'neutral')
        h = f'<td><div class="cr"><span class="{cls}">{sign}{rv:.2f}%</span></div>'
    except:
        return '<td><div class="cr"><span class="na">--</span></div></td>'
    
    if code in rd.get(period_key, {}):
        r = rd[period_key][code]
        h += f'<div class="crk"><span class="rn">{r["rank"]} | {r["total"]}</span></div>'
        pv = r['rank'] / r['total']
        is_top = pv < 0.5
        pc = 'pt' if pv <= 0.1 else ('pg' if is_top else ('pm' if pv <= 0.5 else 'pb'))
        h += f'<div class="cp"><span class="{pc}">{r["pct"]}</span></div>'
    else:
        h += '<div class="crk"><span class="rn">-- | --</span></div><div class="cp"><span class="na">--</span></div>'
    return h + '</td>'

def rows(flist):
    r = []
    for i, f in enumerate(flist):
        cls = 're' if i%2==0 else 'ro'
        cs = ''.join(cell(p, f) for p in ['w1','m1','m3','m6','ytd','y1','y2'])
        r.append(f'<tr class="{cls}"><td class="cf"><a href="https://fund.eastmoney.com/{f["code"]}.html" target="_blank">{f["code"]}</a> <span class="fn">{f["name"]}</span></td>{cs}</tr>')
    return '\n'.join(r)

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

stats = f'''<div class="scard blue"><div class="val">100</div><div class="lbl">基金总数</div></div>
<div class="scard red"><div class="val">{len(cats['夯'])}</div><div class="lbl">夯 · 顶尖</div></div>
<div class="scard orange"><div class="val">{len(cats['顶'])}</div><div class="lbl">顶 · 优秀</div></div>
<div class="scard green"><div class="val">{len(cats['人上人'])}</div><div class="lbl">人上人 · 良好</div></div>
<div class="scard purple"><div class="val">{len(cats['拉'])}</div><div class="lbl">拉 · 警示</div></div>
<div class="scard gray"><div class="val">{len(cats['NPC'])}</div><div class="lbl">NPC · 普通</div></div>'''

# Check coverage
missing = []
for f in funds:
    code = f['code']
    for p in ['w1','m1','m3','m6','ytd','y1','y2']:
        if code not in rd.get(p,{}):
            ret = f.get(p,'')
            if ret and str(ret).strip() not in ('','--','%'):
                missing.append((code, f['name'][:20], p))

note = ''
if missing:
    note = f'<div class="nb">⚠️ {len(missing)}项排名缺失(有收益无排名)，主要是近1年/近2年新基金成立时间不足。具体: {json.dumps(missing[:5], ensure_ascii=False)}...</div>'

html = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Top100 基金排行 · {today}</title><style>{css}</style></head><body>
<div class="ph"><h1>🏆 全市场Top100基金收益排行</h1><div class="sub">今年以来收益率排名 · 夯/顶/人上人/拉/NPC五级分类 · 涨幅 & 同类排名</div><div class="ut">净值更新：{today} &nbsp;|&nbsp; 数据来源：东方财富天天基金 &nbsp;|&nbsp; 生成于 {today}</div></div>
<div class="main"><div class="sr">{stats}</div>{note}{"".join(secs)}</div>
<div class="pf">数据来源：东方财富天天基金 &nbsp;|&nbsp; 红涨绿跌(A股惯例) &nbsp;|&nbsp; 按今年来降序排列 &nbsp;|&nbsp; AI生成仅供参考 &nbsp;|&nbsp; {today}</div>
</body></html>'''

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'Done! {OUTPUT}')
print(f'Classification: 夯{len(cats["夯"])} 顶{len(cats["顶"])} 人上人{len(cats["人上人"])} 拉{len(cats["拉"])} NPC{len(cats["NPC"])}')
print(f'Coverage: {" ".join(f"{p}{len(rd.get(p,{}))}" for p in ["w1","m1","m3","m6","ytd","y1","y2"])}')
if missing:
    for c,n,p in missing[:5]:
        print(f'  MISSING: {c} {n} -> {p}')
