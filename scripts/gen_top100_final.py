"""
终极版: 东方财富Top100 + GS145排名数据 = 完整Top100报告
"""
import requests, re, json, datetime, sys
from collections import defaultdict

OUTPUT_JSON = 'D:/1.work/project/agu-web2/scripts/em_top100_enriched.json'
OUTPUT_HTML = 'D:/1.work/project/agu-web2/reports/top_100.html'
GS145_PATH = 'D:/1.work/project/agu-web2/reports/gs_145fund_report.html'
HOLDINGS_PATH = 'D:/1.work/project/agu-web2/scripts/holdings_data.json'
today = datetime.date.today().strftime('%Y-%m-%d')

# ============================================================
# STEP 1: Get real Top100 from eastmoney
# ============================================================
print("Step 1: Fetching eastmoney Top100...")
url = 'https://fund.eastmoney.com/data/rankhandler.aspx'
params = {
    'op': 'ph', 'dt': 'kf', 'ft': 'all', 'rs': '', 'gs': '0',
    'sc': 'jnzf', 'st': 'desc',
    'sd': '2025-01-01', 'ed': '2026-06-03',
    'pi': '1', 'pn': '100', 'dx': '1'
}
headers = {'User-Agent': 'Mozilla/5.0 Chrome/120', 'Referer': 'https://fund.eastmoney.com/data/fundranking.html'}
resp = requests.get(url, params=params, headers=headers, timeout=15)

m = re.search(r'datas:\[(.*?)\],', resp.text, re.DOTALL)
if not m:
    print("ERROR: Cannot parse eastmoney response")
    sys.exit(1)

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

total_m = re.search(r'total:(\d+)', resp.text)
total_count = int(total_m.group(1)) if total_m else 0
print(f"Got {len(entries)} funds (total market: {total_count})")

top100 = []
for i, entry in enumerate(entries[:100]):
    fields = entry.split(',')
    if len(fields) < 16:
        continue
    top100.append({
        'rank_ytd': i + 1,
        'code': fields[0],
        'name': fields[1],
        'nav': fields[4] if len(fields) > 4 else '',
        'w1': fields[7] if len(fields) > 7 else '',
        'm1': fields[8] if len(fields) > 8 else '',
        'm3': fields[9] if len(fields) > 9 else '',
        'm6': fields[10] if len(fields) > 10 else '',
        'ytd': fields[14] if len(fields) > 14 else '',
        'y1': fields[11] if len(fields) > 11 else '',
        'y2': fields[12] if len(fields) > 12 else '',
    })

# ============================================================
# STEP 2: Parse GS145 ranking data
# ============================================================
print("Step 2: Parsing GS145 ranking data...")
with open(GS145_PATH, 'r', encoding='utf-8') as f:
    gs145 = f.read()

# Parse each fund row from GS145
fund_data = {}
periods_list = ['w1', 'm1', 'm3', 'm6', 'ytd', 'y1', 'y2']

# Match rows: fund cell + data cells
row_re = re.compile(
    r'<td class="col-fund">(.*?)</td>'
    r'(.*?)</tr>', re.DOTALL
)
cell_re = re.compile(
    r'<div class="cell-ret"><span class="(?:up|dn|neutral|na)">(.*?)</span></div>'
    r'\s*<div class="cell-rank"><span class="rank-num">(.*?)</span></div>'
    r'\s*<div class="cell-pct"><span class="(?:pct-\w+|na)">(.*?)</span></div>', re.DOTALL
)
code_re = re.compile(r'fund\.eastmoney\.com/(\d+)\.html')

for match in row_re.finditer(gs145):
    fund_cell = match.group(1)
    data_cells = match.group(2)
    
    codes = code_re.findall(fund_cell)
    if not codes:
        continue
    
    primary_code = codes[0]
    
    name_match = re.search(r'<span class="fname">(.*?)</span>', fund_cell)
    if not name_match:
        continue
    name = name_match.group(1).strip()
    
    data_matches = cell_re.findall(data_cells)
    if len(data_matches) != 7:
        continue
    
    fund_data[primary_code] = {'name': name, 'codes': codes, 'returns': {}, 'ranks': {}, 'totals': {}, 'pcts': {}}
    for i, period in enumerate(periods_list):
        ret, rank_info, pct = data_matches[i]
        fund_data[primary_code]['returns'][period] = ret
        fund_data[primary_code]['pcts'][period] = pct
        parts = rank_info.split('|')
        if len(parts) == 2:
            fund_data[primary_code]['ranks'][period] = parts[0].strip()
            fund_data[primary_code]['totals'][period] = parts[1].strip()

print(f"Parsed {len(fund_data)} funds from GS145")

# ============================================================
# STEP 3: Enrich top100 with GS145 ranking data
# ============================================================
print("Step 3: Enriching top100 with ranking data...")
enriched = 0
for fund in top100:
    code = fund['code']
    if code in fund_data:
        gs = fund_data[code]
        fund['gs_name'] = gs.get('name', '')
        fund['ac_codes'] = gs.get('codes', [code])
        fund['returns'] = gs.get('returns', {})
        fund['ranks'] = gs.get('ranks', {})
        fund['totals'] = gs.get('totals', {})
        fund['pcts'] = gs.get('pcts', {})
        enriched += 1

print(f"Enriched: {enriched}/{len(top100)}")

# ============================================================
# STEP 4: Classify (same logic as GS145)
# ============================================================
def classify_pct(pct_str):
    if not pct_str or pct_str == '--':
        return None
    m = re.match(r'([前后])(\d+)%', pct_str)
    return (m.group(1), int(m.group(2))) if m else None

def classify_fund(f):
    periods = ['w1', 'm1', 'm3', 'm6', 'ytd', 'y1', 'y2']
    has_rank = all(f.get('pcts', {}).get(p, '') not in ('', '--', None) for p in periods)
    if not has_rank:
        return 'NPC'
    
    in_top_50 = 0
    in_bot_50 = 0
    w_1m_3m_in_top30 = True
    
    for p in periods:
        parsed = classify_pct(f.get('pcts', {}).get(p, ''))
        if parsed is None:
            continue
        direction, val = parsed
        if direction == '前':
            in_top_50 += 1 if val <= 50 else 0
            if p in ('w1', 'm1', 'm3') and val > 30:
                w_1m_3m_in_top30 = False
        else:
            in_bot_50 += 1
    
    if in_top_50 >= 5 and w_1m_3m_in_top30:
        return '夯'
    if in_top_50 >= 5:
        return '顶'
    if in_top_50 >= 4:
        return '人上人'
    if in_bot_50 >= 5:
        return '拉'
    return 'NPC'

categories = defaultdict(list)
for f in top100:
    f['category'] = classify_fund(f)
    categories[f['category']].append(f)

print("\nClassification (by YTD rank):")
for cat in ['夯', '顶', '人上人', '拉', 'NPC']:
    funds = categories[cat]
    if funds:
        print(f"  {cat}: {len(funds)} funds (YTD range: {funds[-1]['ytd']}~{funds[0]['ytd']}%)")
    else:
        print(f"  {cat}: 0")

# ============================================================
# STEP 5: Build fund type grouping + generate HTML
# ============================================================
def fund_type_label(f):
    name = f.get('name', '')
    gs_name = f.get('gs_name', '')
    full_name = gs_name or name
    if 'QDII' in full_name:
        return 'QDII/境外'
    if 'ETF' in full_name or 'ETF' in name:
        return '指数/ETF'
    if '指数' in full_name:
        return '指数/ETF'
    return '混合/股票'

def fmt_cell_ext(period, f):
    """Generate cell with GS145-style triple-line format using returns/ranks from GS145"""
    # Priority: GS145 parsed data > eastmoney raw data
    gs_ret = f.get('returns', {}).get(period, '')
    ret = gs_ret if gs_ret else f.get(period, '')
    
    # Normalize return
    if not ret or str(ret).strip() in ('', '--'):
        ret_str = '--'
        ret_sign = ''
    else:
        try:
            ret_str = str(ret).replace('%', '').replace('+', '')
            rv = float(ret_str)
            ret_sign = '+' if rv > 0 else ''
        except:
            ret_str = '--'
            ret_sign = ''
    
    has_rank = bool(f.get('ranks', {}).get(period, ''))
    
    if ret_str == '--':
        return '<td><div class="cell-ret"><span class="na">--</span></div></td>'
    
    rv = float(ret_str) if ret_str != '--' else 0
    cls = 'up' if rv > 0 else ('dn' if rv < 0 else 'neutral')
    
    html = f'<td><div class="cell-ret"><span class="{cls}">{ret_sign}{ret_str}%</span></div>'
    
    if has_rank:
        rank = f.get('ranks', {}).get(period, '--')
        total = f.get('totals', {}).get(period, '--')
        pct = f.get('pcts', {}).get(period, '--')
        
        if rank and rank != '--':
            html += f'<div class="cell-rank"><span class="rank-num">{rank} | {total}</span></div>'
        else:
            html += '<div class="cell-rank"><span class="rank-num">-- | --</span></div>'
        
        if pct and pct != '--':
            is_top = '前' in pct
            pct_num = int(re.search(r'(\d+)', pct).group(1)) if re.search(r'(\d+)', pct) else 50
            pct_cls = 'pct-top' if (is_top and pct_num <= 10) else ('pct-good' if is_top else ('pct-mid' if pct_num <= 50 else 'pct-bad'))
            html += f'<div class="cell-pct"><span class="{pct_cls}">{pct}</span></div>'
        else:
            html += '<div class="cell-pct"><span class="na">--</span></div>'
    else:
        html += '<div class="cell-rank"><span class="rank-num">-- | --</span></div><div class="cell-pct"><span class="na">--</span></div>'
    
    html += '</td>'
    return html

def build_row(f, idx):
    cls = 'row-even' if idx % 2 == 0 else 'row-odd'
    ac_codes = f.get('ac_codes', [f['code']])
    name = f.get('gs_name', f.get('name', ''))
    
    code_links = '/'.join(f'<a href="https://fund.eastmoney.com/{c}.html" target="_blank">{c}</a>' for c in ac_codes)
    cells = ''.join(fmt_cell_ext(p, f) for p in periods_list)
    return f'<tr class="{cls}"><td class="col-fund">{code_links} <span class="fname">{name}</span></td>{cells}</tr>'

# Build sections
cat_config = {
    '夯': ('c0392b', '#fdecea', '≥5周期前50%且近1W/1M/3M全前30%', '顶尖'),
    '顶': ('e67e22', '#fef3e2', '≥5周期前50%且近1W/1M/3M全前50%', '优秀'),
    '人上人': ('27ae60', '#e8f5e9', '≥4周期前50%', '良好'),
    '拉': ('8e44ad', '#f3e5f5', '5周期全后50%', '警示'),
    'NPC': ('888', '#f5f5f5', '不满足其他条件', '普通'),
}

sections_html = ''
for cat in ['夯', '顶', '人上人', '拉', 'NPC']:
    funds = categories[cat]
    if not funds:
        continue
    
    color, bg, desc, label = cat_config[cat]
    
    # Group by type
    type_groups = defaultdict(list)
    for f in funds:
        type_groups[fund_type_label(f)].append(f)
    
    tables = []
    for ftype, group in type_groups.items():
        rows = ''.join(build_row(f, i) for i, f in enumerate(group))
        tables.append(f'''<span class="type-badge">{ftype} · {len(group)}只</span>
<div class="table-wrap">
<table class="fund-table">
<thead><tr><th>基金（代码+简称）</th><th>近1周</th><th>近1月</th><th>近3月</th><th>近6月</th><th>今年来</th><th>近1年</th><th>近2年</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</div>''')
    
    sections_html += f'''
  <div class="section-title" style="border-left-color:#{color}">
    {cat} · {label}
    <span class="badge" style="background:{bg};color:#{color}">{len(funds)}只 · {desc}</span>
  </div>
  <div class="type-blocks">{''.join(tables)}</div>'''

# Holdings
us_descs = {
    'LITE': 'Lumentum，全球领先的光通信激光器与3D传感供应商，苹果Face ID核心器件商。',
    'GOOG': '谷歌母公司Alphabet，全球搜索引擎与AI霸主，旗下拥有YouTube、Android和云计算。',
    'TSM': '台积电，全球最大芯片代工厂，制程技术领先，苹果、英伟达、AMD均为其核心客户。',
    'WDC': '西部数据，全球硬盘与闪存存储巨头，数据中心存储解决方案核心供应商。',
    'COHR': 'Coherent，全球激光与光子系统领导者，光通信及半导体设备核心零部件供应商。',
    'MU': '美光科技，全球DRAM与NAND闪存三巨头之一，AI算力存储核心供应商。',
    'INTC': '英特尔，全球CPU与半导体龙头，推进IDM2.0战略向芯片代工领域转型。',
    'NFLX': '奈飞，全球流媒体娱乐霸主，以原创内容加订阅模式重塑影视行业格局。',
    'ASML': '阿斯麦，全球唯一EUV极紫外光刻机供应商，芯片制造不可替代的核心设备。',
}

with open(HOLDINGS_PATH, 'r', encoding='utf-8') as f:
    holdings = json.load(f)

holdings_html = ''
for board, title, color in [('主板','主板重仓股','#1a5fac'),('创业板','创业板重仓股','#e67e22'),('科创板','科创板重仓股','#8e44ad'),('美股','美股重仓股 (Top8)','#c0392b')]:
    items = holdings.get(board, [])
    if not items:
        continue
    rows = []
    for item in items:
        bar = '█' * min(item['count'], 10) + ('░' * max(0, 10 - item['count']))
        if board == '美股':
            desc = us_descs.get(item['code'], '')
            rows.append(f'<tr><td class="stock-code">{item["code"]}</td><td class="stock-name">{item["name"]}</td><td class="stock-freq"><span class="freq-bar">{bar}</span> <span class="freq-num">{item["count"]}次</span></td><td class="stock-desc">{desc}</td></tr>')
        else:
            rows.append(f'<tr><td class="stock-code">{item["code"]}</td><td class="stock-name">{item["name"]}</td><td class="stock-freq"><span class="freq-bar">{bar}</span> <span class="freq-num">{item["count"]}次</span></td></tr>')
    holdings_html += f'''
<div class="holdings-section">
  <div class="holdings-title" style="border-left-color:{color}">{title}</div>
  <table class="holdings-table"><thead><tr><th>股票代码</th><th>股票简称</th><th>出现频次</th>{'<th>概念介绍</th>' if board=='美股' else ''}</tr></thead><tbody>{"".join(rows)}</tbody></table>
</div>'''

# Stats
stats_cards = f'''
    <div class="stat-card blue">
      <div class="val">{len(top100)}</div><div class="lbl">基金总数</div>
    </div>
    <div class="stat-card red">
      <div class="val">{len(categories['夯'])}</div><div class="lbl">夯 · 顶尖</div>
    </div>
    <div class="stat-card orange">
      <div class="val">{len(categories['顶'])}</div><div class="lbl">顶 · 优秀</div>
    </div>
    <div class="stat-card green">
      <div class="val">{len(categories['人上人'])}</div><div class="lbl">人上人 · 良好</div>
    </div>
    <div class="stat-card purple">
      <div class="val">{len(categories['拉'])}</div><div class="lbl">拉 · 警示</div>
    </div>
    <div class="stat-card gray">
      <div class="val">{len(categories['NPC'])}</div><div class="lbl">NPC · 普通</div>
    </div>'''

# Build final HTML
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>全市场Top100基金收益排行 · {today}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system,'PingFang SC','Microsoft YaHei',sans-serif; background: #f0f3f8; color: #1a2035; font-size: 12px; }}
  .page-header {{ background: linear-gradient(135deg,#8b1a1a 0%,#c0392b 50%,#d94f3a 100%); color: white; padding: 22px 28px 18px; position: relative; overflow: hidden; }}
  .page-header::after {{ content: ''; position: absolute; right: -60px; top: -60px; width: 200px; height: 200px; border-radius: 50%; background: rgba(255,255,255,0.06); }}
  .page-header h1 {{ font-size: 20px; font-weight: 700; letter-spacing: 1px; }}
  .page-header .subtitle {{ font-size: 14px; opacity: 0.85; margin-top: 6px; }}
  .page-header .update-time {{ font-size: 13px; opacity: 0.7; margin-top: 3px; text-align: right; }}
  .main {{ padding: 16px; max-width: 1200px; margin: 0 auto; }}
  .stats-row {{ display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }}
  .stat-card {{ background: white; border-radius: 10px; padding: 12px 16px; flex: 1; min-width: 100px; box-shadow: 0 1px 6px rgba(0,0,0,0.08); border-top: 3px solid; text-align: center; }}
  .stat-card .val {{ font-size: 22px; font-weight: 700; line-height: 1.2; }}
  .stat-card .lbl {{ font-size: 11px; margin-top: 3px; }}
  .stat-card.red {{ border-color: #c0392b; }} .stat-card.red .val,.stat-card.red .lbl {{ color: #c0392b; }}
  .stat-card.orange {{ border-color: #e67e22; }} .stat-card.orange .val,.stat-card.orange .lbl {{ color: #e67e22; }}
  .stat-card.green {{ border-color: #27ae60; }} .stat-card.green .val,.stat-card.green .lbl {{ color: #27ae60; }}
  .stat-card.purple {{ border-color: #8e44ad; }} .stat-card.purple .val,.stat-card.purple .lbl {{ color: #8e44ad; }}
  .stat-card.gray {{ border-color: #888; }} .stat-card.gray .val,.stat-card.gray .lbl {{ color: #888; }}
  .stat-card.blue {{ border-color: #1a5fac; }} .stat-card.blue .val,.stat-card.blue .lbl {{ color: #1a5fac; }}
  .section-title {{ display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 10px; margin: 24px 0 14px; font-size: 20px; font-weight: 800; color: #0d2b6e; letter-spacing: 2px; border-left: 5px solid; padding: 4px 12px; background: white; border-radius: 6px; }}
  .section-title .badge {{ font-size: 12px; padding: 3px 12px; border-radius: 20px; font-weight: 600; margin-left: 10px; letter-spacing: 0.5px; }}
  .type-blocks {{ display: flex; flex-direction: column; gap: 10px; }}
  .type-badge {{ display: inline-block; background: #e8f0fe; color: #1a5fac; font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 6px; margin-bottom: 6px; }}
  .table-wrap {{ overflow-x: auto; }}
  .fund-table {{ width: 100%; min-width: 980px; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 6px rgba(0,0,0,0.07); font-size: 13px; table-layout: fixed; }}
  .fund-table thead tr {{ background: linear-gradient(90deg,#0d2b6e,#1a5fac); color: white; }}
  .fund-table thead th {{ padding: 9px 5px; font-size: 11px; font-weight: 600; text-align: center; white-space: nowrap; letter-spacing: 0.3px; border-right: 1px solid rgba(255,255,255,0.15); }}
  .fund-table thead th:last-child {{ border-right: none; }}
  .fund-table thead th:first-child {{ width: 31%; text-align: left; padding-left: 12px; }}
  .fund-table tbody tr {{ border-bottom: 1px solid #f0f3f8; transition: background 0.15s; }}
  .fund-table tbody tr:last-child {{ border-bottom: none; }}
  .fund-table tbody tr:hover {{ background: #f6f9ff !important; }}
  .fund-table tbody tr.row-even {{ background: #fafbfe; }}
  .fund-table tbody tr.row-odd {{ background: #fff; }}
  .fund-table td {{ padding: 5px 4px; text-align: center; vertical-align: middle; border-right: 1px solid #f0f3f8; line-height: 1.5; }}
  .fund-table th:nth-child(n+2), .fund-table td:nth-child(n+2) {{ width: 9.85%; }}
  .fund-table td:last-child {{ border-right: none; }}
  .fund-table td:first-child {{ width: 31%; text-align: left; padding-left: 14px; border-right: none; }}
  .col-fund {{ font-size: 13px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }}
  .col-fund a {{ font-weight: 700; margin-right: 4px; color: #1a5fac; font-size: 13px; text-decoration: none; line-height: 1.35; }}
  .col-fund .fname {{ color: #1a2035; font-weight: 600; }}
  .cell-ret {{ font-size: 15px; font-weight: 700; }}
  .cell-rank {{ font-size: 12px; color: #666; margin-top: 2px; }}
  .cell-pct {{ font-size: 12px; margin-top: 2px; }}
  .up {{ color: #e63946; }} .dn {{ color: #2ba84a; }} .neutral {{ color: #888; font-weight: 600; }} .na {{ color: #ccc; font-size: 10px; }}
  .pct-top {{ color: #c0392b; font-weight: 700; }}
  .pct-good {{ color: #d94f3a; background: #fdecea; padding: 0 2px; border-radius: 2px; }}
  .pct-mid {{ color: #2e7d32; background: #e8f5e9; padding: 0 2px; border-radius: 2px; }}
  .pct-bad {{ color: #1a7a3c; font-weight: 700; }}
  .rank-num {{ color: #555; font-family: monospace; font-size: 12px; }}
  .note-bar {{ display: flex; gap: 12px; flex-wrap: wrap; padding: 8px 16px; font-size: 11px; color: #888; background: #fafbfe; border-top: 1px solid #f0f3f8; border-radius: 0 0 8px 8px; }}
  .holdings-section {{ margin-bottom: 20px; }}
  .holdings-title {{ display: flex; align-items: center; margin: 24px 0 8px; font-size: 18px; font-weight: 700; color: #1a2035; border-left: 5px solid; padding: 4px 12px; background: white; border-radius: 6px; }}
  .holdings-table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 6px rgba(0,0,0,0.07); font-size: 13px; }}
  .holdings-table thead tr {{ background: linear-gradient(90deg,#1a2035,#2c3e50); color: white; }}
  .holdings-table thead th {{ padding: 8px 10px; font-size: 11px; font-weight: 600; text-align: left; }}
  .holdings-table tbody tr {{ border-bottom: 1px solid #f0f3f8; }}
  .holdings-table tbody tr:hover {{ background: #f6f9ff; }}
  .holdings-table td {{ padding: 6px 10px; vertical-align: middle; }}
  .stock-code {{ font-family: monospace; font-weight: 700; color: #1a5fac; width: 90px; }}
  .stock-name {{ font-weight: 600; width: 120px; }}
  .stock-freq {{ min-width: 160px; }}
  .stock-desc {{ font-size: 11px; color: #718097; line-height: 1.5; max-width: 320px; }}
  .freq-bar {{ font-family: monospace; color: #c0392b; letter-spacing: 2px; font-size: 10px; }}
  .freq-num {{ margin-left: 8px; font-weight: 700; color: #c0392b; }}
  .page-footer {{ text-align: center; color: #aaa; font-size: 10px; padding: 16px; margin-top: 8px; }}
  .data-note {{ background: #fef9e7; border: 1px solid #f9e79f; border-radius: 6px; padding: 10px 16px; margin: 20px 0; font-size: 12px; color: #7d6608; }}
  @media (max-width:1100px) {{ .fund-table {{ font-size: 11px; }} .col-fund,.col-fund a,.col-fund .fname {{ font-size: 11px; }} .cell-ret {{ font-size: 12px; }} }}
</style>
</head>
<body>
<div class="page-header">
  <h1>🏆 全市场Top100基金收益排行</h1>
  <div class="subtitle">今年以来收益率排名 · 全市场{total_count}只基金Top100 · 夯/顶/人上人/拉/NPC五级分类 · 涨幅 &amp; 同类排名</div>
  <div class="update-time">净值更新：{today} &nbsp;|&nbsp; 数据来源：东方财富天天基金 &nbsp;|&nbsp; 生成于 {today}</div>
</div>
<div class="main">
  <div class="stats-row">{stats_cards}</div>
  <div class="data-note">⚠️ 排名数据来源：GS145精选池已覆盖{enriched}/{len(top100)}只基金的同类排名。余下{len(top100)-enriched}只缺少同类排名数据（显示为 -- | --）。基金排名按东方财富今年来收益降序排列。</div>
  {sections_html}
  <div class="section-title" style="border-left-color:#1a5fac;color:#1a5fac">📊 重仓股持仓透视</div>
  {holdings_html}
</div>
<div class="page-footer">数据来源：东方财富天天基金 &nbsp;|&nbsp; 涨幅颜色：红涨绿跌（A股惯例）&nbsp;|&nbsp; 各分类内按今年来降序排列 &nbsp;|&nbsp; 持仓数据截至2026Q1季报 &nbsp;|&nbsp; AI生成仅供参考 &nbsp;|&nbsp; {today}</div>
</body></html>'''

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html)

# Also save enriched JSON
with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump({'total_market': total_count, 'funds': top100}, f, ensure_ascii=False, indent=2)

print(f"\nDone! HTML: {OUTPUT_HTML}")
print(f"Enriched JSON: {OUTPUT_JSON}")
print(f"Ranking coverage: {enriched}/{len(top100)}")
