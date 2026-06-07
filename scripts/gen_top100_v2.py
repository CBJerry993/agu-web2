"""
从GS145报告解析基金排名数据，结合Top100池子，生成符合GS145风格的新报告。
包含: 收益率+排名+百分位 三行格式, 五级分类, 持仓透视
"""
import re, json, datetime
from collections import defaultdict

GS145_PATH = 'D:/1.work/project/agu-web2/reports/gs_145fund_report.html'
TOPPOOL_PATH = 'D:/1.work/project/agu-web2/scripts/top100_data.json'
HOLDINGS_PATH = 'D:/1.work/project/agu-web2/scripts/holdings_data.json'
OUTPUT = 'D:/1.work/project/agu-web2/reports/top_100.html'

today = datetime.date.today().strftime('%Y-%m-%d')

# ============================================================
# Part 1: Parse GS145 report for ALL ranking data
# ============================================================
print("Parsing GS145 report...")
with open(GS145_PATH, 'r', encoding='utf-8') as f:
    gs145 = f.read()

# Parse fund rows: each <tr> in tbody contains fund data
# Pattern: code links + name + 7 data columns
fund_data = {}  # fund_code -> {returns, ranks, totals, pcts for all 7 periods}

# Find all tbody blocks and the section/type context
sections = re.split(r'<div class="section-title".*?</div>', gs145)

# Parse each <tr> in tbody
row_pattern = re.compile(
    r'<a href="https://fund\.eastmoney\.com/(\d+)\.html"[^>]*>(\d+)</a>'
    r'.*?<span class="fname">(.*?)</span>'
    r'(.*?)</tr>', re.DOTALL
)

# Better approach: find all fund rows with their full content
# Each row: class="col-fund">...CODE/CODE...fname... then 7x cell-ret/cell-rank/cell-pct
row_re = re.compile(
    r'<td class="col-fund">(.*?)</td>'
    r'(.*?)</tr>'
)

# Capture individual cell content
cell_re = re.compile(
    r'<div class="cell-ret"><span class="(?:up|dn|neutral|na)">(.*?)</span></div>'
    r'\s*<div class="cell-rank"><span class="rank-num">(.*?)</span></div>'
    r'\s*<div class="cell-pct"><span class="(?:pct-\w+|na)">(.*?)</span></div>'
)

code_re = re.compile(r'fund\.eastmoney\.com/(\d+)\.html[^>]*>(\d+)</a>')

for match in row_re.finditer(gs145):
    fund_cell = match.group(1)
    data_cells = match.group(2)
    
    # Extract codes (primary)
    codes = code_re.findall(fund_cell)
    if not codes:
        continue
    
    primary_code = codes[0][0]  # A class code
    all_codes = [c[0] for c in codes]
    
    # Extract name
    name_match = re.search(r'<span class="fname">(.*?)</span>', fund_cell)
    if not name_match:
        continue
    name = name_match.group(1).strip()
    
    # Extract 7 data cells
    data_matches = cell_re.findall(data_cells)
    if len(data_matches) != 7:
        continue
    
    # Periods: 近1周, 近1月, 近3月, 近6月, 今年来, 近1年, 近2年
    periods = ['1w', '1m', '3m', '6m', 'ytd', '1y', '2y']
    
    fund_data[primary_code] = {
        'codes': all_codes,
        'name': name,
        'returns': {},
        'ranks': {},
        'totals': {},
        'pcts': {},
    }
    
    for i, period in enumerate(periods):
        ret, rank_info, pct = data_matches[i]
        fund_data[primary_code]['returns'][period] = ret
        fund_data[primary_code]['pcts'][period] = pct
        
        # Parse rank: "39 | 1076" or "-- | --"
        rank_parts = rank_info.split('|')
        if len(rank_parts) == 2:
            fund_data[primary_code]['ranks'][period] = rank_parts[0].strip()
            fund_data[primary_code]['totals'][period] = rank_parts[1].strip()

print(f"Parsed {len(fund_data)} funds from GS145")

# ============================================================
# Part 2: Build fund pool with classification
# ============================================================
# Load our prior top pool
with open(TOPPOOL_PATH, 'r', encoding='utf-8') as f:
    toppool = {f['code']: f for f in json.load(f)}

# Merge: prioritize GS145 data (has ranking), supplement with pool data
merged = {}
for code in toppool:
    if code in fund_data:
        # Has ranking data from GS145
        merged[code] = {'code': code, **toppool[code], **fund_data[code]}
    else:
        # No GS145 ranking data
        merged[code] = {'code': code, **toppool[code]}

# Also add any GS145 funds not in pool (in case)
for code, gs_fund in fund_data.items():
    if code not in merged:
        merged[code] = {'code': code, 'syl_y_val': -999, **gs_fund}

print(f"Total merged: {len(merged)}")

# Classification logic (same as GS145)
# 夯: >=5 thresholds in top 50% AND 1W/1M/3M all top 30%
# 顶: >=5 thresholds in top 50% AND 1W/1M/3M all top 50%
# 人上人: >=4 thresholds in top 50%
# 拉: all 5 thresholds in bottom 50%
# NPC: others

def classify_pct(pct_str):
    """Parse percentile: '前37%' -> ('top', 37), '后48%' -> ('bot', 48)"""
    if not pct_str or pct_str == '--':
        return None
    m = re.match(r'([前后])(\d+)%', pct_str)
    if m:
        return (m.group(1), int(m.group(2)))
    return None

def classify_fund(f):
    """Classify fund into 夯/顶/人上人/拉/NPC"""
    periods = ['1w', '1m', '3m', '6m', 'ytd', '1y', '2y']
    has_rank = all(f.get('pcts', {}).get(p, '') not in ('', '--', None) for p in periods)
    
    if not has_rank:
        return 'NPC'  # No data -> NPC
    
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
            if p in ('1w', '1m', '3m') and val > 30:
                w_1m_3m_in_top30 = False
        else:
            in_bot_50 += 1
    
    # 夯
    if in_top_50 >= 5 and w_1m_3m_in_top30:
        return '夯'
    # 顶
    if in_top_50 >= 5:
        return '顶'
    # 人上人
    if in_top_50 >= 4:
        return '人上人'
    # 拉
    if in_bot_50 >= 5:
        return '拉'
    
    return 'NPC'

# Classify all funds
categories = defaultdict(list)
all_funds_list = list(merged.values())
# Sort by YTD descending, take top 100
all_funds_list.sort(key=lambda x: (x.get('syl_y_val', -999) or -999), reverse=True)
top100 = all_funds_list[:100]

for f in top100:
    cat = classify_fund(f)
    f['category'] = cat
    categories[cat].append(f)

# Sort within each category by YTD descending
for cat in categories:
    categories[cat].sort(key=lambda x: (x.get('syl_y_val', -999) or -999), reverse=True)

print("Classification:")
for cat in ['夯', '顶', '人上人', '拉', 'NPC']:
    print(f"  {cat}: {len(categories[cat])} funds")

# ============================================================
# Part 3: Build HTML (following GS145 style exactly)
# ============================================================

# Fund type classification
def fund_type_label(f):
    ftype = f.get('ftype', f.get('fundtype', ''))
    name = f.get('name', '')
    if 'QDII' in name:
        return 'QDII/境外'
    if ftype and ('债券' in str(ftype) or '债' in str(ftype)):
        return '债券型'
    if ftype and '短债' in str(ftype):
        return '短债'
    if 'ETF' in name or f.get('fundtype') in ('004', '005'):
        return '指数/ETF'
    if f.get('fundtype') == '001':
        return '股票型'
    if f.get('fundtype') == '002':
        return '混合型'
    return '其他'

def fmt_cell(period, f, has_rank=True):
    """Generate a single data cell: ret + rank + pct"""
    ret = f.get('returns', {}).get(period, '')
    if not ret:
        ret = {
            '1w': f.get('syl_z', ''), '1m': f.get('syl_jn', ''),
            '3m': f.get('syl_3n', ''), '6m': f.get('syl_6y', ''),
            'ytd': f.get('syl_y', ''), '1y': f.get('syl_1n', ''),
            '2y': f.get('syl_2n', '')
        }.get(period, '')
    
    if not ret or str(ret).strip() in ('', '--'):
        return '<td><div class="cell-ret"><span class="na">--</span></div></td>'
    
    try:
        rv = float(str(ret).replace('%', '').replace('+', ''))
    except:
        return f'<td><div class="cell-ret"><span class="na">--</span></div></td>'
    
    cls = 'up' if rv > 0 else ('dn' if rv < 0 else 'neutral')
    sign = '+' if rv > 0 else ''
    ret_html = f'<div class="cell-ret"><span class="{cls}">{sign}{rv:.2f}%</span></div>'
    
    if has_rank:
        rank = f.get('ranks', {}).get(period, '--')
        total = f.get('totals', {}).get(period, '--')
        pct = f.get('pcts', {}).get(period, '--')
        
        rank_part = ''
        pct_part = ''
        
        if rank and rank != '--':
            rank_part = f'<div class="cell-rank"><span class="rank-num">{rank} | {total}</span></div>'
        
        if pct and pct != '--':
            # Determine pct class
            is_top = '前' in pct
            pct_num = int(re.search(r'(\d+)', pct).group(1)) if re.search(r'(\d+)', pct) else 50
            if is_top:
                pct_cls = 'pct-top' if pct_num <= 10 else 'pct-good'
            else:
                pct_cls = 'pct-mid' if pct_num <= 50 else 'pct-bad'
            pct_part = f'<div class="cell-pct"><span class="{pct_cls}">{pct}</span></div>'
        else:
            pct_part = '<div class="cell-pct"><span class="na">--</span></div>'
        
        return f'<td>{ret_html}{rank_part}{pct_part}</td>'
    else:
        return f'<td>{ret_html}<div class="cell-rank"><span class="rank-num">-- | --</span></div><div class="cell-pct"><span class="na">--</span></div></td>'

def build_fund_row(f, idx):
    cls = 'row-even' if idx % 2 == 0 else 'row-odd'
    codes = f.get('codes', [f['code']])
    name = f.get('name', '')
    
    # Build code links (A/C pair)
    code_links = []
    for c in codes:
        code_links.append(f'<a href="https://fund.eastmoney.com/{c}.html" target="_blank">{c}</a>')
    code_str = '/'.join(code_links)
    
    has_rank = bool(f.get('returns'))
    periods = ['1w', '1m', '3m', '6m', 'ytd', '1y', '2y']
    cells = ''.join(fmt_cell(p, f, has_rank) for p in periods)
    
    return f'<tr class="{cls}"><td class="col-fund">{code_str} <span class="fname">{name}</span></td>{cells}</tr>'

# Build sections
cat_config = {
    '夯': ('c0392b', '#fdecea', '≥5周期前50%且近1W/1M/3M全前30%'),
    '顶': ('e67e22', '#fef3e2', '≥5周期前50%且近1W/1M/3M全前50%'),
    '人上人': ('27ae60', '#e8f5e9', '≥4周期前50%'),
    '拉': ('8e44ad', '#f3e5f5', '5周期全后50%'),
    'NPC': ('888', '#f5f5f5', '不满足其他条件'),
}

def build_section(cat):
    funds = categories[cat]
    if not funds:
        return ''
    
    color, bg, desc = cat_config[cat]
    
    # Group by fund type
    type_groups = defaultdict(list)
    for f in funds:
        type_groups[fund_type_label(f)].append(f)
    
    # Build tables by type
    tables = []
    for ftype, group in type_groups.items():
        rows = ''.join(build_fund_row(f, i) for i, f in enumerate(group))
        table = f'''<span class="type-badge">{ftype} · {len(group)}只</span>
<div class="table-wrap">
<table class="fund-table">
<thead><tr><th>基金（代码+简称）</th><th>近1周</th><th>近1月</th><th>近3月</th><th>近6月</th><th>今年来</th><th>近1年</th><th>近2年</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</div>'''
        tables.append(table)
    
    return f'''
  <div class="section-title" style="border-left-color:#{color}">
    {cat} · {'顶尖' if cat=='夯' else ('优秀' if cat=='顶' else ('良好' if cat=='人上人' else ('警示' if cat=='拉' else '普通')))}
    <span class="badge" style="background:{bg};color:#{color}">{len(funds)}只 · {desc}</span>
  </div>
  <div class="type-blocks">{''.join(tables)}</div>'''

# Holdings section (fixed with descriptions)
us_descs = {
    'LITE': 'Lumentum，全球领先的光通信激光器与3D传感供应商，苹果Face ID核心器件商。',
    'GOOG': '谷歌母公司Alphabet，全球搜索引擎与AI霸主，旗下拥有YouTube、Android和云计算业务。',
    'TSM': '台积电，全球最大芯片代工厂，制程技术领先，苹果、英伟达、AMD均为其核心客户。',
    'WDC': '西部数据，全球硬盘与闪存存储巨头，数据中心存储解决方案核心供应商。',
    'COHR': 'Coherent，全球激光与光子系统领导者，光通信及半导体设备核心零部件供应商。',
    'MU': '美光科技，全球DRAM与NAND闪存三巨头之一，AI算力存储核心供应商。',
    'INTC': '英特尔，全球CPU与半导体龙头，正推进IDM2.0战略向芯片代工领域转型。',
    'NFLX': '奈飞，全球流媒体娱乐霸主，以原创内容加订阅模式重塑影视行业竞争格局。',
    'ASML': '阿斯麦，全球唯一EUV极紫外光刻机供应商，芯片制造环节不可替代的核心设备。',
}

with open(HOLDINGS_PATH, 'r', encoding='utf-8') as f:
    holdings = json.load(f)

def build_holdings_section():
    holdings_html = ''
    for board, title, color in [('主板', '主板重仓股', '#1a5fac'), ('创业板', '创业板重仓股', '#e67e22'), ('科创板', '科创板重仓股', '#8e44ad'), ('美股', '美股重仓股 (Top8)', '#c0392b')]:
        items = holdings.get(board, [])
        if not items:
            continue
        
        stock_rows = []
        for item in items:
            freq_bar = '█' * min(item['count'], 10) + ('░' * max(0, 10 - item['count']))
            if board == '美股':
                desc = us_descs.get(item['code'], '')
                stock_rows.append(f'''<tr>
<td class="stock-code">{item['code']}</td>
<td class="stock-name">{item['name']}</td>
<td class="stock-freq"><span class="freq-bar">{freq_bar}</span> <span class="freq-num">{item['count']}次</span></td>
<td class="stock-desc">{desc}</td>
</tr>''')
            else:
                stock_rows.append(f'''<tr>
<td class="stock-code">{item['code']}</td>
<td class="stock-name">{item['name']}</td>
<td class="stock-freq"><span class="freq-bar">{freq_bar}</span> <span class="freq-num">{item['count']}次</span></td>
</tr>''')
        
        holdings_html += f'''
<div class="holdings-section">
  <div class="holdings-title" style="border-left-color:{color}">{title}</div>
  <table class="holdings-table">
    <thead><tr><th>股票代码</th><th>股票简称</th><th>出现频次</th>{'<th>概念介绍</th>' if board=='美股' else ''}</tr></thead>
    <tbody>{''.join(stock_rows)}</tbody>
  </table>
</div>'''
    return holdings_html

# Stats
total = len(top100)

html_header = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>全市场Top100基金收益排行 · {today}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f0f3f8; color: #1a2035; font-size: 12px; }}

  .page-header {{
    background: linear-gradient(135deg, #8b1a1a 0%, #c0392b 50%, #d94f3a 100%);
    color: white; padding: 22px 28px 18px; position: relative; overflow: hidden;
  }}
  .page-header::after {{ content: ''; position: absolute; right: -60px; top: -60px; width: 200px; height: 200px; border-radius: 50%; background: rgba(255,255,255,0.06); }}
  .page-header h1 {{ font-size: 20px; font-weight: 700; letter-spacing: 1px; }}
  .page-header .subtitle {{ font-size: 14px; opacity: 0.85; margin-top: 6px; }}
  .page-header .update-time {{ font-size: 13px; opacity: 0.7; margin-top: 3px; text-align: right; }}

  .main {{ padding: 16px; max-width: 1200px; margin: 0 auto; }}

  .stats-row {{ display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }}
  .stat-card {{ background: white; border-radius: 10px; padding: 12px 16px; flex: 1; min-width: 100px; box-shadow: 0 1px 6px rgba(0,0,0,0.08); border-top: 3px solid; text-align: center; }}
  .stat-card .val {{ font-size: 22px; font-weight: 700; line-height: 1.2; }}
  .stat-card .lbl {{ font-size: 11px; margin-top: 3px; }}
  .stat-card.red    {{ border-color: #c0392b; }} .stat-card.red .val,.stat-card.red .lbl    {{ color: #c0392b; }}
  .stat-card.orange {{ border-color: #e67e22; }} .stat-card.orange .val,.stat-card.orange .lbl {{ color: #e67e22; }}
  .stat-card.green  {{ border-color: #27ae60; }} .stat-card.green .val,.stat-card.green .lbl  {{ color: #27ae60; }}
  .stat-card.purple {{ border-color: #8e44ad; }} .stat-card.purple .val,.stat-card.purple .lbl {{ color: #8e44ad; }}
  .stat-card.gray   {{ border-color: #888; }} .stat-card.gray .val,.stat-card.gray .lbl   {{ color: #888; }}
  .stat-card.blue   {{ border-color: #1a5fac; }} .stat-card.blue .val,.stat-card.blue .lbl   {{ color: #1a5fac; }}

  .section-title {{
    display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 10px;
    margin: 24px 0 14px;
    font-size: 20px; font-weight: 800; color: #0d2b6e;
    letter-spacing: 2px;
    border-left: 5px solid;
    padding: 4px 12px;
    background: white;
    border-radius: 6px;
  }}
  .section-title .badge {{ font-size: 12px; padding: 3px 12px; border-radius: 20px; font-weight: 600; margin-left: 10px; letter-spacing: 0.5px; }}

  .type-blocks {{ display: flex; flex-direction: column; gap: 10px; }}
  .type-badge {{ display: inline-block; background: #e8f0fe; color: #1a5fac; font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 6px; margin-bottom: 6px; }}

  .table-wrap {{ overflow-x: auto; }}

  .fund-table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 6px rgba(0,0,0,0.07); font-size: 13px; }}
  .fund-table thead tr {{ background: linear-gradient(90deg, #0d2b6e, #1a5fac); color: white; }}
  .fund-table thead th {{ padding: 9px 5px; font-size: 11px; font-weight: 600; text-align: center; white-space: nowrap; letter-spacing: 0.3px; border-right: 1px solid rgba(255,255,255,0.15); }}
  .fund-table thead th:last-child {{ border-right: none; }}
  .fund-table thead th:first-child {{ text-align: left; padding-left: 12px; }}
  .fund-table tbody tr {{ border-bottom: 1px solid #f0f3f8; transition: background 0.15s; }}
  .fund-table tbody tr:last-child {{ border-bottom: none; }}
  .fund-table tbody tr:hover {{ background: #f6f9ff !important; }}
  .fund-table tbody tr.row-even {{ background: #fafbfe; }}
  .fund-table tbody tr.row-odd {{ background: #fff; }}
  .fund-table td {{ padding: 5px 4px; text-align: center; vertical-align: middle; border-right: 1px solid #f0f3f8; line-height: 1.5; }}
  .fund-table td:nth-child(n+2) {{ width: 72px; min-width: 72px; }}
  .fund-table td:last-child {{ border-right: none; }}
  .fund-table td:first-child {{ text-align: left; padding-left: 14px; border-right: none; }}

  .col-fund {{ font-size: 14px; }}
  .col-fund a {{ font-weight: 700; margin-right: 6px; color: #1a5fac; font-size: 15px; text-decoration: none; }}
  .col-fund .fname {{ font-weight: 600; color: #1a2035; }}

  .cell-ret {{ font-size: 15px; font-weight: 700; }}
  .cell-rank {{ font-size: 12px; color: #666; margin-top: 2px; }}
  .cell-pct {{ font-size: 12px; margin-top: 2px; }}

  .up {{ color: #e63946; }}
  .dn {{ color: #2ba84a; }}
  .neutral {{ color: #888; font-weight: 600; }}
  .na {{ color: #ccc; font-size: 10px; }}

  .pct-top  {{ color: #c0392b; font-weight: 700; }}
  .pct-good {{ color: #d94f3a; background: #fdecea; padding: 0 2px; border-radius: 2px; }}
  .pct-mid  {{ color: #2e7d32; background: #e8f5e9; padding: 0 2px; border-radius: 2px; }}
  .pct-bad  {{ color: #1a7a3c; font-weight: 700; }}

  .rank-num {{ color: #555; font-family: monospace; font-size: 12px; }}

  .note-bar {{
    display: flex; gap: 12px; flex-wrap: wrap;
    padding: 8px 16px; font-size: 11px; color: #888;
    background: #fafbfe; border-top: 1px solid #f0f3f8; border-radius: 0 0 8px 8px;
  }}

  /* Holdings */
  .holdings-section {{ margin-bottom: 20px; }}
  .holdings-title {{
    display: flex; align-items: center;
    margin: 24px 0 8px;
    font-size: 18px; font-weight: 700; color: #1a2035;
    border-left: 5px solid;
    padding: 4px 12px;
    background: white;
    border-radius: 6px;
  }}
  .holdings-table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 6px rgba(0,0,0,0.07); font-size: 13px; }}
  .holdings-table thead tr {{ background: linear-gradient(90deg, #1a2035, #2c3e50); color: white; }}
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

  @media (max-width: 1100px) {{ .fund-table {{ font-size: 11px; }} .col-fund, .col-fund a, .col-fund .fname {{ font-size: 11px; }} .cell-ret {{ font-size: 12px; }} }}
</style>
</head>
<body>

<div class="page-header">
  <h1>🏆 全市场Top100基金收益排行</h1>
  <div class="subtitle">今年以来收益率排名 · 夯/顶/人上人/拉/NPC五级分类 · 涨幅 &amp; 同类排名</div>
  <div class="update-time">净值更新：{today} &nbsp;|&nbsp; 数据来源：天天基金 &nbsp;|&nbsp; 生成于 {today}</div>
</div>

<div class="main">

  <div class="stats-row">
    <div class="stat-card blue">
      <div class="val">{total}</div>
      <div class="lbl">基金总数</div>
    </div>
    <div class="stat-card red">
      <div class="val">{len(categories['夯'])}</div>
      <div class="lbl">夯 · 顶尖</div>
    </div>
    <div class="stat-card orange">
      <div class="val">{len(categories['顶'])}</div>
      <div class="lbl">顶 · 优秀</div>
    </div>
    <div class="stat-card green">
      <div class="val">{len(categories['人上人'])}</div>
      <div class="lbl">人上人 · 良好</div>
    </div>
    <div class="stat-card purple">
      <div class="val">{len(categories['拉'])}</div>
      <div class="lbl">拉 · 警示</div>
    </div>
    <div class="stat-card gray">
      <div class="val">{len(categories['NPC'])}</div>
      <div class="lbl">NPC · 普通</div>
    </div>
  </div>

{build_section('夯')}
{build_section('顶')}
{build_section('人上人')}
{build_section('拉')}
{build_section('NPC')}

  <!-- Holdings Section -->
  <div class="section-title" style="border-left-color:#1a5fac;color:#1a5fac">📊 重仓股持仓透视</div>
  {build_holdings_section()}

</div>

<div class="page-footer">
  数据来源：天天基金 &nbsp;|&nbsp; 涨幅颜色：红涨绿跌（中国A股惯例）&nbsp;|&nbsp;
  各分类内按今年来收益率降序排列 &nbsp;|&nbsp; 持仓数据截至2026Q1季报 &nbsp;|&nbsp; 报告由AI自动生成，仅供参考 &nbsp;|&nbsp; {today}
</div>

</body>
</html>'''

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html_header)

print(f"\nDone! Output: {OUTPUT}")
print(f"Total: {total} funds (top 100 by YTD)")
for cat in ['夯', '顶', '人上人', '拉', 'NPC']:
    print(f"  {cat}: {len(categories[cat])}")
