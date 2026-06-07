"""
完整版Top100 HTML生成器 (含收益表格 + 持仓统计)
"""
import json, datetime

INPUT = 'D:/1.work/project/agu-web2/scripts/top100_data.json'
HOLDINGS = 'D:/1.work/project/agu-web2/scripts/holdings_data.json'
OUTPUT = 'D:/1.work/project/agu-web2/reports/top_100.html'

with open(INPUT, 'r', encoding='utf-8') as f:
    funds = json.load(f)
with open(HOLDINGS, 'r', encoding='utf-8') as f:
    holdings = json.load(f)

today = datetime.date.today().strftime('%Y-%m-%d')

# US stock descriptions (20-30字)
us_descs = {
    'LITE': 'Lumentum，全球领先的光通信激光器与3D传感供应商，苹果Face ID核心器件商。',
    'GOOG': '谷歌母公司Alphabet，全球搜索引擎与AI霸主，旗下有YouTube/Android/云计算。',
    'TSM': '台积电，全球最大芯片代工厂，制程技术领先，苹果/英伟达/AMD均为其客户。',
    'WDC': '西部数据，全球硬盘与闪存存储巨头，数据中心存储解决方案核心供应商。',
    'COHR': 'Coherent，全球激光与光子系统领导者，光通信/半导体设备核心零部件供应商。',
    'MU': '美光科技，全球DRAM与NAND闪存三巨头之一，AI算力存储核心供应商。',
    'INTC': '英特尔，全球CPU与半导体龙头，推进IDM2.0战略转型芯片代工领域。',
    'NFLX': '奈飞，全球流媒体娱乐霸主，原创内容+订阅模式重塑影视行业格局。',
    'ASML': '阿斯麦，全球唯一EUV极紫外光刻机供应商，芯片制造不可替代的核心设备。',
}

def fmt_ret(val, prefix=''):
    if val is None:
        return '<span class="na">--</span>'
    if isinstance(val, (int, float)):
        v = val
        cls = 'up' if v > 0 else ('dn' if v < 0 else 'neutral')
        return f'<span class="{cls}">{prefix}{v}%</span>'
    val_str = str(val).strip()
    if not val_str or val_str == '%':
        return '<span class="na">--</span>'
    try:
        v = float(val_str)
        cls = 'up' if v > 0 else ('dn' if v < 0 else 'neutral')
        return f'<span class="{cls}">{prefix}{val_str}%</span>'
    except:
        return f'<span class="na">--</span>'

# Build fund rows
rows = []
for i, f in enumerate(funds):
    cls = 'row-even' if i % 2 == 0 else 'row-odd'
    code = f['code']
    name = f['name']
    rows.append(f'''<tr class="{cls}"><td class="col-fund"><a href="https://fund.eastmoney.com/{code}.html" target="_blank">{code}</a> <span class="fname">{name}</span></td>
<td><div class="cell-ret">{fmt_ret(f.get('syl_z',''))}</div></td>
<td><div class="cell-ret">{fmt_ret(f.get('syl_jn',''))}</div></td>
<td><div class="cell-ret">{fmt_ret(f.get('syl_3n',''))}</div></td>
<td><div class="cell-ret">{fmt_ret(f.get('syl_6y',''))}</div></td>
<td><div class="cell-ret">{fmt_ret(f.get('syl_y',''))}</div></td>
<td><div class="cell-ret">{fmt_ret(f.get('syl_1n',''))}</div></td>
<td><div class="cell-ret">{fmt_ret(f.get('syl_2n',''))}</div></td>
</tr>''')

positive = sum(1 for f in funds if f['syl_y_val'] > 0)
negative = sum(1 for f in funds if f['syl_y_val'] <= 0)
avg_ytd = sum(f['syl_y_val'] for f in funds) / len(funds) if funds else 0

# Build holdings section
def build_holdings_section():
    sections = []
    board_config = [
        ('主板', '主板重仓股', '#1a5fac', '沪深主板市场股票'),
        ('创业板', '创业板重仓股', '#e67e22', '深圳创业板市场股票'),
        ('科创板', '科创板重仓股', '#8e44ad', '上海科创板市场股票'),
        ('美股', '美股重仓股 (Top8)', '#c0392b', '美国市场股票'),
    ]
    
    for board, title, color, desc in board_config:
        items = holdings.get(board, [])
        if not items:
            continue
        
        stock_rows = []
        for item in items:
            freq_bar = '█' * min(item['count'], 10) + ('░' * max(0, 10 - item['count']))
            if board == '美股':
                desc_text = us_descs.get(item['code'], '')
                stock_rows.append(f'''<tr>
<td class="stock-code">{item['code']}</td>
<td class="stock-name">{item['name']}</td>
<td class="stock-freq"><span class="freq-bar">{freq_bar}</span> <span class="freq-num">{item['count']}次</span></td>
<td class="stock-desc">{desc_text}</td>
</tr>''')
            else:
                stock_rows.append(f'''<tr>
<td class="stock-code">{item['code']}</td>
<td class="stock-name">{item['name']}</td>
<td class="stock-freq"><span class="freq-bar">{freq_bar}</span> <span class="freq-num">{item['count']}次</span></td>
</tr>''')
        
        sections.append(f'''
<div class="holdings-section">
  <div class="holdings-title" style="border-left-color:{color}">{title}</div>
  <p class="holdings-sub">{desc} · 共{len(items)}只</p>
  <div class="table-wrap">
  <table class="holdings-table">
    <thead><tr>
      <th>股票代码</th><th>股票简称</th><th>出现频次</th>
      {'''<th>概念介绍</th>''' if board == '美股' else ''}
    </tr></thead>
    <tbody>{''.join(stock_rows)}</tbody>
  </table>
  </div>
</div>''')
    
    return '\n'.join(sections)

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>全市场Top100基金收益排行 · {today}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f0f3f8; color: #1a2035; font-size: 12px; }}

  .page-header {{
    background: linear-gradient(135deg, #8b1a1a 0%, #c0392b 50%, #e74c3c 100%);
    color: white; padding: 22px 28px 18px; position: relative; overflow: hidden;
  }}
  .page-header::after {{ content: ''; position: absolute; right: -60px; top: -60px; width: 200px; height: 200px; border-radius: 50%; background: rgba(255,255,255,0.06); }}
  .page-header h1 {{ font-size: 20px; font-weight: 700; letter-spacing: 1px; }}
  .page-header .subtitle {{ font-size: 14px; opacity: 0.85; margin-top: 6px; }}
  .page-header .update-time {{ font-size: 13px; opacity: 0.7; margin-top: 3px; text-align: right; }}

  .main {{ padding: 16px; max-width: 1200px; margin: 0 auto; }}

  .stats-row {{ display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }}
  .stat-card {{ background: white; border-radius: 10px; padding: 12px 16px; flex: 1; min-width: 120px; box-shadow: 0 1px 6px rgba(0,0,0,0.08); border-top: 3px solid; text-align: center; }}
  .stat-card .val {{ font-size: 22px; font-weight: 700; line-height: 1.2; }}
  .stat-card .lbl {{ font-size: 11px; margin-top: 3px; }}
  .stat-card.red    {{ border-color: #c0392b; }} .stat-card.red .val,.stat-card.red .lbl    {{ color: #c0392b; }}
  .stat-card.orange {{ border-color: #e67e22; }} .stat-card.orange .val,.stat-card.orange .lbl {{ color: #e67e22; }}
  .stat-card.green  {{ border-color: #27ae60; }} .stat-card.green .val,.stat-card.green .lbl  {{ color: #27ae60; }}
  .stat-card.blue   {{ border-color: #1a5fac; }} .stat-card.blue .val,.stat-card.blue .lbl   {{ color: #1a5fac; }}
  .stat-card.purple {{ border-color: #8e44ad; }} .stat-card.purple .val,.stat-card.purple .lbl {{ color: #8e44ad; }}

  .section-title {{
    display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 10px;
    margin: 24px 0 14px;
    font-size: 20px; font-weight: 800; color: #8b1a1a;
    letter-spacing: 2px;
    border-left: 5px solid #c0392b;
    padding: 4px 12px;
    background: white;
    border-radius: 6px;
  }}

  .table-wrap {{ overflow-x: auto; }}

  .fund-table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 6px rgba(0,0,0,0.07); font-size: 13px; }}
  .fund-table thead tr {{ background: linear-gradient(90deg, #8b1a1a, #c0392b); color: white; }}
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

  .up {{ color: #e63946; }}
  .dn {{ color: #2ba84a; }}
  .neutral {{ color: #888; font-weight: 600; }}
  .na {{ color: #ccc; font-size: 10px; }}

  /* Holdings section */
  .holdings-section {{ margin-bottom: 20px; }}
  .holdings-title {{
    display: flex; align-items: center;
    margin: 24px 0 6px;
    font-size: 18px; font-weight: 700; color: #1a2035;
    border-left: 5px solid;
    padding: 4px 12px;
    background: white;
    border-radius: 6px;
  }}
  .holdings-sub {{ font-size: 12px; color: #718097; padding: 0 20px; margin-bottom: 8px; }}

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

  .update-note {{ background: #fef9e7; border: 1px solid #f9e79f; border-radius: 6px; padding: 10px 16px; margin: 20px 0; font-size: 12px; color: #7d6608; }}

  @media (max-width: 1100px) {{ .fund-table {{ font-size: 11px; }} .col-fund, .col-fund a, .col-fund .fname {{ font-size: 11px; }} .cell-ret {{ font-size: 12px; }} }}
</style>
</head>
<body>

<div class="page-header">
  <h1>🏆 全市场Top100基金收益排行</h1>
  <div class="subtitle">今年以来收益率排名 · 覆盖GS145精选池及市场头部基金</div>
  <div class="update-time">净值更新：{today} &nbsp;|&nbsp; 数据来源：天天基金 &nbsp;|&nbsp; 生成于 {today}</div>
</div>

<div class="main">

  <div class="stats-row">
    <div class="stat-card blue">
      <div class="val">100</div>
      <div class="lbl">基金总数</div>
    </div>
    <div class="stat-card red">
      <div class="val">{positive}</div>
      <div class="lbl">今年来盈利</div>
    </div>
    <div class="stat-card green">
      <div class="val">{negative}</div>
      <div class="lbl">今年来亏损</div>
    </div>
    <div class="stat-card orange">
      <div class="val">{avg_ytd:+.2f}%</div>
      <div class="lbl">平均收益率</div>
    </div>
  </div>

  <!-- Fund Performance Table -->
  <div class="section-title">📈 今年以来收益排行 Top100</div>

  <div class="table-wrap">
  <table class="fund-table">
  <thead><tr><th>基金（代码+简称）</th><th>近1周</th><th>近1月</th><th>近3月</th><th>近6月</th><th>今年来</th><th>近1年</th><th>近2年</th></tr></thead>
  <tbody>
{''.join(rows)}
  </tbody>
  </table>
  </div>

  <!-- Holdings Section -->
  <div class="section-title" style="border-left-color:#1a5fac;color:#1a5fac">📊 重仓股持仓透视</div>
  
  <div class="update-note">
    ⚠️ 持仓数据基于基金最新季报（截至2026-03-31），每季度更新一次。以下统计按股票在100只基金中出现的次数排序。
  </div>

  {build_holdings_section()}

</div>

<div class="page-footer">
  数据来源：天天基金 &nbsp;|&nbsp; 涨幅颜色：红涨绿跌（中国A股惯例）&nbsp;|&nbsp;
  按今年来收益率降序排列 &nbsp;|&nbsp; 数据范围：GS145精选池 + 市场头部基金 &nbsp;|&nbsp; 报告由AI自动生成，仅供参考 &nbsp;|&nbsp; {today}
</div>

</body>
</html>'''

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"HTML generated: {OUTPUT}")
print(f"Funds: {len(funds)}, +{positive}/-{negative}, Avg YTD: {avg_ytd:+.2f}%")
total_stocks = sum(len(holdings.get(b, [])) for b in ['主板','创业板','科创板','美股'])
print(f"Holdings: {total_stocks} stocks across 4 boards")
