"""
用QDII基金的真实美股持仓更新qdii_fund_report.html
"""
import json, re

HOLDINGS = 'D:/1.work/project/agu-web2/scripts/qdii_us_holdings.json'
QDII_HTML = 'D:/1.work/project/agu-web2/reports/qdii_fund_report.html'

with open(HOLDINGS, 'r', encoding='utf-8') as f:
    us_stocks = json.load(f)

# Filter >=3
us_stocks = [it for it in us_stocks if it['count'] >= 3]

stock_descs = {
    'TSM': '台积电(TSMC)，全球最大芯片代工厂，3nm/2nm制程领先，苹果/英伟达/AMD核心客户，AI芯片产能关键。',
    'NVDA': '英伟达(NVIDIA)，全球AI GPU绝对霸主，H200/B200算力芯片垄断AI训练与推理市场，市值全球前二。',
    'LITE': 'Lumentum，全球领先的光通信激光器与3D传感芯片供应商，800G/1.6T光模块核心器件，苹果Face ID提供商。',
    'GLW': '康宁(Corning)，全球特种玻璃巨头，光纤光缆+显示玻璃+移动设备面板全产业链覆盖，AI数据中心光纤需求受益。',
    'TSEM': 'Tower半导体，以色列特色工艺晶圆代工厂，射频/电源管理/图像传感器芯片代工，英特尔有意收购。',
}

if not us_stocks:
    print("No US stocks with count >= 3")
    exit(1)

max_count = max(it['count'] for it in us_stocks)

rows_html = ''
for it in us_stocks:
    pct = int(it['count'] / max_count * 100) if max_count else 0
    bar_color = '#c0392b' if pct > 60 else ('#e67e22' if pct > 30 else '#95a5a6')
    d = stock_descs.get(it['code'], f"{it['name']}，美股上市公司。")
    rows_html += f'''    <tr>
      <td class="stock-code">{it['code']}</td>
      <td class="stock-name">{it['name']}</td>
      <td class="stock-freq">
        <div class="freq-bar-wrap"><div class="freq-bar-fill" style="width:{pct}%;background:{bar_color}"></div></div>
        <span class="freq-num">{it['count']}次</span>
      </td>
      <td class="stock-desc">{d}</td>
    </tr>
'''

holdings_html = f'''
  <div class="holdings-section">
    <div class="holdings-header" style="border-left:5px solid #c0392b">
      <span class="holdings-icon">🌍</span>
      <span class="holdings-title">美股重仓股</span>
      <span class="holdings-badge" style="background:#c0392b15;color:#c0392b">{len(us_stocks)}只</span>
      <span style="font-size:11px;color:#999;margin-left:4px">数据来源：天天基金 · QDII基金最新季报前十大重仓</span>
    </div>
    <div class="table-wrap" style="overflow-x:visible">
    <table class="holdings-table">
      <thead><tr><th>代码</th><th>简称</th><th>持仓集中度</th><th>概念简介</th></tr></thead>
      <tbody>
{rows_html}
      </tbody>
    </table>
    </div>
  </div>
'''

# Read QDII HTML
with open(QDII_HTML, 'r', encoding='utf-8') as f:
    html = f.read()

# Find existing holdings-section and replace it
# Pattern: from <div class="holdings-section"> to the next </div> that closes .main
old_pattern = r'\n  <div class="holdings-section">.*?</div>\s*\n</div>\n\n<div class="page-footer">'
new_replacement = holdings_html + '\n</div>\n\n<div class="page-footer">'
html = re.sub(old_pattern, new_replacement, html, flags=re.DOTALL)

with open(QDII_HTML, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Updated QDII US holdings ({len(us_stocks)} stocks, >=3 occurrences)")
for it in us_stocks:
    print(f"  {it['code']:6s} {it['name']:30s} x{it['count']}")
print(f"\nFull list (21 stocks, before filter):")
for it in json.load(open(HOLDINGS, 'r', encoding='utf-8')):
    print(f"  {it['code']:6s} {it['name']:30s} x{it['count']}")
