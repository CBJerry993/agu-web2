"""
简洁版: 东方财富真实Top100 + 收益率 + 诚实标注排名数据缺失
"""
import json, datetime, re
from collections import defaultdict

EM_DATA = 'D:/1.work/project/agu-web2/scripts/em_top100.json'
GS145_PATH = 'D:/1.work/project/agu-web2/reports/gs_145fund_report.html'
HOLDINGS_PATH = 'D:/1.work/project/agu-web2/scripts/holdings_data.json'
OUTPUT = 'D:/1.work/project/agu-web2/reports/top_100.html'
today = datetime.date.today().strftime('%Y-%m-%d')

# Load data
with open(EM_DATA, 'r', encoding='utf-8') as f:
    em = json.load(f)
funds = em['funds']
total_market = em.get('total', 0)

# Parse GS145 rankings
with open(GS145_PATH, 'r', encoding='utf-8') as f:
    gs145 = f.read()

gs_ranks = {}
row_re = re.compile(r'<td class="col-fund">(.*?)</td>(.*?)</tr>', re.DOTALL)
cell_re = re.compile(r'<div class="cell-ret"><span class="(?:up|dn|neutral|na)">(.*?)</span></div>\s*<div class="cell-rank"><span class="rank-num">(.*?)</span></div>\s*<div class="cell-pct"><span class="(?:pct-\w+|na)">(.*?)</span></div>', re.DOTALL)
code_re = re.compile(r'fund\.eastmoney\.com/(\d+)\.html')

for match in row_re.finditer(gs145):
    codes = code_re.findall(match.group(1))
    if not codes:
        continue
    name_m = re.search(r'<span class="fname">(.*?)</span>', match.group(1))
    if not name_m:
        continue
    data_m = cell_re.findall(match.group(2))
    if len(data_m) != 7:
        continue
    
    periods = ['w1','m1','m3','m6','ytd','y1','y2']
    gs_ranks[codes[0]] = {
        'name': name_m.group(1).strip(),
        'codes': codes,
        'data': {p: {'ret': data_m[i][0], 'rank': data_m[i][1], 'pct': data_m[i][2]} for i, p in enumerate(periods)}
    }

# Enrich funds with GS145 data
enriched = 0
for f in funds:
    code = f['code']
    if code in gs_ranks:
        f['gs'] = gs_ranks[code]
        enriched += 1

print(f"Enriched: {enriched}/{len(funds)} with GS145 ranking data")

# Classify
def classify_pct(pct_str):
    if not pct_str or pct_str == '--': return None
    m = re.match(r'([前后])(\d+)%', pct_str)
    return (m.group(1), int(m.group(2))) if m else None

def classify(f):
    if 'gs' not in f:
        return 'NPC'
    periods = ['w1','m1','m3','m6','ytd','y1','y2']
    in_top_50, in_bot_50 = 0, 0
    w1m3_top30 = True
    for p in periods:
        pct = f['gs']['data'].get(p, {}).get('pct', '')
        parsed = classify_pct(pct)
        if not parsed: continue
        d, v = parsed
        if d == '前':
            in_top_50 += 1 if v <= 50 else 0
            if p in ('w1','m1','m3') and v > 30: w1m3_top30 = False
        else:
            in_bot_50 += 1
    if in_top_50 >= 5 and w1m3_top30: return '夯'
    if in_top_50 >= 5: return '顶'
    if in_top_50 >= 4: return '人上人'
    if in_bot_50 >= 5: return '拉'
    return 'NPC'

cats = defaultdict(list)
for f in funds:
    f['cat'] = classify(f)
    cats[f['cat']].append(f)

for cat in ['夯','顶','人上人','拉','NPC']:
    print(f"  {cat}: {len(cats[cat])}")

def fmt_cell(period, f, pidx):
    periods = ['w1','m1','m3','m6','ytd','y1','y2']
    p = periods[pidx]
    em_key = p
    ret_val = f.get(em_key, '')
    
    # Get GS145 data if available
    has_rank = 'gs' in f and p in f['gs']['data']
    gs_d = f['gs']['data'][p] if has_rank else None
    
    if has_rank:
        ret = gs_d['ret']
        rank_info = gs_d['rank']
        pct = gs_d['pct']
    else:
        ret = ret_val
        rank_info = '-- | --'
        pct = ''
    
    if not ret or str(ret).strip() in ('', '--', '%'):
        return '<td><div class="cell-ret"><span class="na">--</span></div></td>'
    
    try:
        rv = float(str(ret).replace('%','').replace('+',''))
    except:
        return '<td><div class="cell-ret"><span class="na">--</span></div></td>'
    
    sign = '+' if rv > 0 else ''
    cls = 'up' if rv > 0 else ('dn' if rv < 0 else 'neutral')
    html = f'<td><div class="cell-ret"><span class="{cls}">{sign}{rv:.2f}%</span></div>'
    
    parts = rank_info.split('|')
    rank = parts[0].strip() if len(parts) >= 1 else '--'
    total = parts[1].strip() if len(parts) >= 2 else '--'
    
    if rank != '--':
        html += f'<div class="cell-rank"><span class="rank-num">{rank} | {total}</span></div>'
    else:
        html += '<div class="cell-rank"><span class="rank-num">-- | --</span></div>'
    
    if pct and pct != '--':
        is_top = '前' in pct
        pn = int(re.search(r'(\d+)', pct).group(1)) if re.search(r'(\d+)', pct) else 50
        pcls = 'pct-top' if (is_top and pn <= 10) else ('pct-good' if is_top else ('pct-mid' if pn <= 50 else 'pct-bad'))
        html += f'<div class="cell-pct"><span class="{pcls}">{pct}</span></div>'
    else:
        html += '<div class="cell-pct"><span class="na">--</span></div>'
    
    return html + '</td>'

def fmt_name_row(f):
    gs = f.get('gs')
    if gs:
        codes = gs['codes']
        name = gs['name']
    else:
        codes = [f['code']]
        name = f.get('name', '')
    links = '/'.join(f'<a href="https://fund.eastmoney.com/{c}.html" target="_blank">{c}</a>' for c in codes)
    return f'{links} <span class="fname">{name}</span>'

def build_table(funds_list):
    rows = []
    for i, f in enumerate(funds_list):
        cls = 'row-even' if i % 2 == 0 else 'row-odd'
        cells = ''.join(fmt_cell(p, f, pi) for pi, p in enumerate(['w1','m1','m3','m6','ytd','y1','y2']))
        rows.append(f'<tr class="{cls}"><td class="col-fund">{fmt_name_row(f)}</td>{cells}</tr>')
    return '\n'.join(rows)

cat_cfg = {
    '夯': ('c0392b','#fdecea','≥5前50%且1W/1M/3M全前30%','顶尖'),
    '顶': ('e67e22','#fef3e2','≥5前50%且1W/1M/3M全前50%','优秀'),
    '人上人': ('27ae60','#e8f5e9','≥4前50%','良好'),
    '拉': ('8e44ad','#f3e5f5','5周期全后50%','警示'),
    'NPC': ('888','#f5f5f5','无排名数据或非特定','普通'),
}

secs = []
for cat in ['夯','顶','人上人','拉','NPC']:
    flist = cats[cat]
    if not flist: continue
    color, bg, desc, label = cat_cfg[cat]
    table = build_table(flist)
    secs.append(f'''
  <div class="section-title" style="border-left-color:#{color}">
    {cat} · {label}
    <span class="badge" style="background:{bg};color:#{color}">{len(flist)}只 · {desc}</span>
  </div>
  <div class="table-wrap">
  <table class="fund-table">
  <thead><tr><th>基金（代码+简称）</th><th>近1周</th><th>近1月</th><th>近3月</th><th>近6月</th><th>今年来</th><th>近1年</th><th>近2年</th></tr></thead>
  <tbody>{table}</tbody>
  </table>
  </div>''')

# Holdings section
us_d = {
    'LITE': 'Lumentum，全球领先的光通信激光器与3D传感供应商，苹果Face ID核心器件商。',
    'GOOG': '谷歌母公司Alphabet，全球搜索引擎与AI霸主，旗下YouTube/Android/云计算为核心业务。',
    'TSM': '台积电，全球最大芯片代工厂，制程技术遥遥领先，苹果/英伟达/AMD均为其客户。',
    'WDC': '西部数据，全球硬盘与闪存存储巨头，数据中心存储解决方案核心供应商。',
    'COHR': 'Coherent，全球激光与光子系统领导者，光通信及半导体设备核心零部件供应商。',
    'MU': '美光科技，全球DRAM与NAND闪存三巨头之一，AI算力存储核心供应商。',
    'INTC': '英特尔，全球CPU与半导体龙头，推进IDM2.0战略向芯片代工领域转型。',
    'NFLX': '奈飞，全球流媒体娱乐霸主，以原创内容加订阅模式重塑影视行业竞争格局。',
    'ASML': '阿斯麦，全球唯一EUV极紫外光刻机供应商，芯片制造不可替代的核心设备。',
}
with open(HOLDINGS_PATH, 'r', encoding='utf-8') as f:
    holdings = json.load(f)

hold_secs = []
for board, title, color in [('主板','主板重仓股','#1a5fac'),('创业板','创业板重仓股','#e67e22'),('科创板','科创板重仓股','#8e44ad'),('美股','美股重仓股(Top8)','#c0392b')]:
    items = holdings.get(board, [])
    if not items: continue
    rows = []
    for it in items:
        bar = '█' * min(it['count'], 10) + ('░' * max(0, 10 - it['count']))
        if board == '美股':
            d = us_d.get(it['code'], '')
            rows.append(f'<tr><td class="sc">{it["code"]}</td><td class="sn">{it["name"]}</td><td class="sf"><span class="fb">{bar}</span> <span class="fn">{it["count"]}次</span></td><td class="sd">{d}</td></tr>')
        else:
            rows.append(f'<tr><td class="sc">{it["code"]}</td><td class="sn">{it["name"]}</td><td class="sf"><span class="fb">{bar}</span> <span class="fn">{it["count"]}次</span></td></tr>')
    hold_secs.append(f'<div class="hs"><div class="ht" style="border-left-color:{color}">{title}</div><table class="htab"><thead><tr><th>股票代码</th><th>股票简称</th><th>出现频次</th>{"<th>概念介绍</th>" if board=="美股" else ""}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')

stats = f'''
    <div class="stat-card blue"><div class="val">{len(funds)}</div><div class="lbl">基金总数</div></div>
    <div class="stat-card red"><div class="val">{len(cats["夯"])}</div><div class="lbl">夯 · 顶尖</div></div>
    <div class="stat-card orange"><div class="val">{len(cats["顶"])}</div><div class="lbl">顶 · 优秀</div></div>
    <div class="stat-card green"><div class="val">{len(cats["人上人"])}</div><div class="lbl">人上人 · 良好</div></div>
    <div class="stat-card purple"><div class="val">{len(cats["拉"])}</div><div class="lbl">拉 · 警示</div></div>
    <div class="stat-card gray"><div class="val">{len(cats["NPC"])}</div><div class="lbl">NPC · 普通</div></div>'''

note = '' if enriched == len(funds) else f'<div class="data-note">⚠️ 排名数据仅覆盖{enriched}/{len(funds)}只基金（与GS145重叠部分）。其余基金显示真实收益率，排名标注为 -- | --。基金排序来源：东方财富 · 今年来收益率降序 · 全市场{total_market}只基金</div>'

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>全市场Top100基金收益排行 · {today}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;background:#f0f3f8;color:#1a2035;font-size:12px}}
.ph{{background:linear-gradient(135deg,#8b1a1a,#c0392b,#d94f3a);color:#fff;padding:22px 28px 18px;position:relative;overflow:hidden}}
.ph::after{{content:'';position:absolute;right:-60px;top:-60px;width:200px;height:200px;border-radius:50%;background:rgba(255,255,255,.06)}}
.ph h1{{font-size:20px;font-weight:700;letter-spacing:1px}}
.ph .sub{{font-size:14px;opacity:.85;margin-top:6px}}
.ph .ut{{font-size:13px;opacity:.7;margin-top:3px;text-align:right}}
.main{{padding:16px;max-width:1200px;margin:0 auto}}
.sr{{display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap}}
.stat-card{{background:#fff;border-radius:10px;padding:12px 16px;flex:1;min-width:100px;box-shadow:0 1px 6px rgba(0,0,0,.08);border-top:3px solid;text-align:center}}
.stat-card .val{{font-size:22px;font-weight:700;line-height:1.2}}
.stat-card .lbl{{font-size:11px;margin-top:3px}}
.stat-card.red{{border-color:#c0392b}}.stat-card.red .val,.stat-card.red .lbl{{color:#c0392b}}
.stat-card.orange{{border-color:#e67e22}}.stat-card.orange .val,.stat-card.orange .lbl{{color:#e67e22}}
.stat-card.green{{border-color:#27ae60}}.stat-card.green .val,.stat-card.green .lbl{{color:#27ae60}}
.stat-card.purple{{border-color:#8e44ad}}.stat-card.purple .val,.stat-card.purple .lbl{{color:#8e44ad}}
.stat-card.gray{{border-color:#888}}.stat-card.gray .val,.stat-card.gray .lbl{{color:#888}}
.stat-card.blue{{border-color:#1a5fac}}.stat-card.blue .val,.stat-card.blue .lbl{{color:#1a5fac}}
.st{{display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:10px;margin:24px 0 14px;font-size:20px;font-weight:800;color:#0d2b6e;letter-spacing:2px;border-left:5px solid;padding:4px 12px;background:#fff;border-radius:6px}}
.st .badge{{font-size:12px;padding:3px 12px;border-radius:20px;font-weight:600;margin-left:10px;letter-spacing:.5px}}
.tw{{overflow-x:auto}}
.ft{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.07);font-size:13px}}
.ft thead tr{{background:linear-gradient(90deg,#0d2b6e,#1a5fac);color:#fff}}
.ft thead th{{padding:9px 5px;font-size:11px;font-weight:600;text-align:center;white-space:nowrap;letter-spacing:.3px;border-right:1px solid rgba(255,255,255,.15)}}
.ft thead th:last-child{{border-right:none}}
.ft thead th:first-child{{text-align:left;padding-left:12px}}
.ft tbody tr{{border-bottom:1px solid #f0f3f8;transition:background .15s}}
.ft tbody tr:last-child{{border-bottom:none}}
.ft tbody tr:hover{{background:#f6f9ff!important}}
.ft tbody tr.row-even{{background:#fafbfe}}
.ft tbody tr.row-odd{{background:#fff}}
.ft td{{padding:5px 4px;text-align:center;vertical-align:middle;border-right:1px solid #f0f3f8;line-height:1.5}}
.ft td:nth-child(n+2){{width:72px;min-width:72px}}
.ft td:last-child{{border-right:none}}
.ft td:first-child{{text-align:left;padding-left:14px;border-right:none}}
.cf{{font-size:14px}}
.cf a{{font-weight:700;margin-right:6px;color:#1a5fac;font-size:15px;text-decoration:none}}
.cf .fname{{font-weight:600;color:#1a2035}}
.cr{{font-size:15px;font-weight:700}}
.crk{{font-size:12px;color:#666;margin-top:2px}}
.cp{{font-size:12px;margin-top:2px}}
.up{{color:#e63946}}.dn{{color:#2ba84a}}.neutral{{color:#888;font-weight:600}}.na{{color:#ccc;font-size:10px}}
.pt{{color:#c0392b;font-weight:700}}
.pg{{color:#d94f3a;background:#fdecea;padding:0 2px;border-radius:2px}}
.pm{{color:#2e7d32;background:#e8f5e9;padding:0 2px;border-radius:2px}}
.pb{{color:#1a7a3c;font-weight:700}}
.rn{{color:#555;font-family:monospace;font-size:12px}}
.data-note{{background:#fef9e7;border:1px solid #f9e79f;border-radius:6px;padding:10px 16px;margin:20px 0;font-size:12px;color:#7d6608}}
.hs{{margin-bottom:20px}}
.ht{{display:flex;align-items:center;margin:24px 0 8px;font-size:18px;font-weight:700;color:#1a2035;border-left:5px solid;padding:4px 12px;background:#fff;border-radius:6px}}
.htab{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.07);font-size:13px}}
.htab thead tr{{background:linear-gradient(90deg,#1a2035,#2c3e50);color:#fff}}
.htab thead th{{padding:8px 10px;font-size:11px;font-weight:600;text-align:left}}
.htab tbody tr{{border-bottom:1px solid #f0f3f8}}
.htab tbody tr:hover{{background:#f6f9ff}}
.htab td{{padding:6px 10px;vertical-align:middle}}
.sc{{font-family:monospace;font-weight:700;color:#1a5fac;width:90px}}
.sn{{font-weight:600;width:120px}}
.sf{{min-width:160px}}
.sd{{font-size:11px;color:#718097;line-height:1.5;max-width:320px}}
.fb{{font-family:monospace;color:#c0392b;letter-spacing:2px;font-size:10px}}
.fn{{margin-left:8px;font-weight:700;color:#c0392b}}
.pf{{text-align:center;color:#aaa;font-size:10px;padding:16px;margin-top:8px}}
@media(max-width:1100px){{.ft{{font-size:11px}}.cf,.cf a,.cf .fname{{font-size:11px}}.cr{{font-size:12px}}}}
</style></head><body>
<div class="ph">
<h1>🏆 全市场Top100基金收益排行</h1>
<div class="sub">今年以来收益率排名 · 全市场{total_market}只基金Top100 · 夯/顶/人上人/拉/NPC五级分类</div>
<div class="ut">净值更新：{today} &nbsp;|&nbsp; 数据来源：东方财富天天基金 &nbsp;|&nbsp; 生成于 {today}</div>
</div>
<div class="main">
<div class="sr">{stats}</div>
{note}
{''.join(secs)}
<div class="st" style="border-left-color:#1a5fac;color:#1a5fac">📊 重仓股持仓透视</div>
{''.join(hold_secs)}
</div>
<div class="pf">数据来源：东方财富天天基金 &nbsp;|&nbsp; 涨幅红涨绿跌(A股惯例) &nbsp;|&nbsp; 按今年来降序排列 &nbsp;|&nbsp; 持仓截至2026Q1季报 &nbsp;|&nbsp; AI生成仅供参考 &nbsp;|&nbsp; {today}</div>
</body></html>'''

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"\nGenerated: {OUTPUT}")
print(f"Top YTD: {funds[0]['code']} {funds[0]['name']} {funds[0]['ytd']}%")
print(f"Bottom YTD: {funds[-1]['code']} {funds[-1]['name']} {funds[-1]['ytd']}%")
