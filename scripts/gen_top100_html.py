"""
从top100_data.json生成HTML报告 (参考GS145样式)
"""
import json, datetime

INPUT = 'D:/1.work/project/agu-web2/scripts/top100_data.json'
OUTPUT = 'D:/1.work/project/agu-web2/reports/top_100.html'

with open(INPUT, 'r', encoding='utf-8') as f:
    funds = json.load(f)

today = datetime.date.today().strftime('%Y-%m-%d')

def fmt_ret(val, prefix=''):
    """格式化收益率"""
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

def build_row(f, idx):
    cls = 'row-even' if idx % 2 == 0 else 'row-odd'
    code = f['code']
    name = f['name']
    return f'''<tr class="{cls}"><td class="col-fund"><a href="https://fund.eastmoney.com/{code}.html" target="_blank">{code}</a> <span class="fname">{name}</span></td>
<td><div class="cell-ret">{fmt_ret(f.get('syl_z',''))}</div></td>
<td><div class="cell-ret">{fmt_ret(f.get('syl_jn',''))}</div></td>
<td><div class="cell-ret">{fmt_ret(f.get('syl_3n',''))}</div></td>
<td><div class="cell-ret">{fmt_ret(f.get('syl_6y',''))}</div></td>
<td><div class="cell-ret">{fmt_ret(f.get('syl_y',''))}</div></td>
<td><div class="cell-ret">{fmt_ret(f.get('syl_1n',''))}</div></td>
<td><div class="cell-ret">{fmt_ret(f.get('syl_2n',''))}</div></td>
</tr>'''

rows = '\n'.join(build_row(f, i) for i, f in enumerate(funds))

positive = sum(1 for f in funds if f['syl_y_val'] > 0)
negative = sum(1 for f in funds if f['syl_y_val'] <= 0)
avg_ytd = sum(f['syl_y_val'] for f in funds) / len(funds) if funds else 0
max_ytd = funds[0]['syl_y_val'] if funds else 0
fund_types = set(f.get('fundtype','') or f.get('ftype','') for f in funds)

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

  .page-footer {{ text-align: center; color: #aaa; font-size: 10px; padding: 16px; margin-top: 8px; }}

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

  <div class="table-wrap">
  <table class="fund-table">
  <thead><tr><th>基金（代码+简称）</th><th>近1周</th><th>近1月</th><th>近3月</th><th>近6月</th><th>今年来</th><th>近1年</th><th>近2年</th></tr></thead>
  <tbody>
{rows}
  </tbody>
  </table>
  </div>

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
print(f"Funds: {len(funds)}, Positive: {positive}, Negative: {negative}, Avg: {avg_ytd:+.2f}%")
