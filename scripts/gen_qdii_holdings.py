import json

descs = {
    'TSM': '台积电(TSMC)，全球最大芯片代工厂，3nm/2nm制程领先，苹果/英伟达/AMD核心客户，AI芯片产能关键。',
    'NVDA': '英伟达(NVIDIA)，全球AI GPU绝对霸主，H200/B200算力芯片垄断AI训练与推理市场，市值全球前二。',
    'MU': '美光科技，全球DRAM与NAND闪存三巨头之一，HBM高带宽存储是AI算力核心，数据中心存储龙头。',
    'LITE': 'Lumentum，全球光通信激光器与3D传感龙头，800G/1.6T光模块核心器件，苹果Face ID提供商。',
    'AVGO': '博通(Broadcom)，全球半导体与基础设施软件巨头，AI网络芯片与定制ASIC数据中心解决方案领导者。',
    'GLW': '康宁(Corning)，全球特种玻璃巨头，光纤光缆+显示玻璃+移动设备面板全产业链，AI数据中心光纤受益。',
    'SNDK': 'SanDisk，全球闪存存储方案领导者，为数据中心和企业级SSD提供NAND闪存与控制器解决方案。',
    'ASML': '阿斯麦(ASML)，全球唯一EUV极紫外光刻机供应商，尖端芯片制造不可替代，单台售价超3亿欧元。',
    'COHR': 'Coherent，全球激光与光子系统领导者，光通信+半导体设备核心零部件，800G光模块关键供应商。',
    'GOOGL': '谷歌(Alphabet A股)，全球搜索引擎与AI霸主，Gemini大模型+YouTube+云计算构建全生态帝国。',
    'GOOG': '谷歌(Alphabet C股)，与GOOGL同属Alphabet，无投票权但经济权益相同，均为谷歌母公司股份。',
    'INTC': '英特尔(Intel)，全球CPU与半导体龙头，推进IDM2.0战略向芯片代工转型，18A工艺是关键。',
    'LRCX': '拉姆研究(Lam Research)，全球半导体刻蚀与沉积设备龙头，3D NAND和先进逻辑芯片核心供应商。',
    'TSEM': 'Tower半导体，以色列特色工艺晶圆代工厂，射频/电源管理/图像传感器芯片代工，英特尔拟收购。',
    'AMZN': '亚马逊(Amazon)，全球电商与云计算AWS霸主，AI基础设施投资全球领先，物流网络覆盖全球。',
    'AMD': 'AMD，全球CPU与GPU双线巨头，EPYC服务器芯片性能领先，MI300系列AI加速卡正面挑战英伟达。',
}

with open('D:/1.work/project/agu-web2/scripts/qdii_holdings.json', 'r', encoding='utf-8') as f:
    stocks = json.load(f)

max_count = stocks[0]['count'] if stocks else 1

rows = []
for s in stocks:
    bar_pct = int(s['count'] / max_count * 100)
    bar_color = '#c0392b' if bar_pct >= 60 else '#e67e22' if bar_pct >= 40 else '#f39c12'
    desc = descs.get(s['code'], '')
    rows.append(f'''    <tr>
      <td class="stock-code">{s['code']}</td>
      <td class="stock-name">{s['name']}</td>
      <td class="stock-freq">
        <div class="freq-bar-wrap"><div class="freq-bar-fill" style="width:{bar_pct}%;background:{bar_color}"></div></div>
        <span class="freq-num">{s['count']}次</span>
      </td>
      <td class="stock-desc">{desc}</td>
    </tr>''')

new_section = f'''
  <div class="holdings-section">
    <div class="holdings-header" style="border-left:5px solid #c0392b">
      <span class="holdings-icon">🌍</span>
      <span class="holdings-title">美股重仓股</span>
      <span class="holdings-badge" style="background:#c0392b15;color:#c0392b">{len(stocks)}只</span>
      <span style="font-size:11px;color:#999;margin-left:4px">数据来源：天天基金 · QDII基金最新季报前十大重仓 · 出现≥3次</span>
    </div>
    <div class="table-wrap" style="overflow-x:visible">
    <table class="holdings-table">
      <thead><tr><th>代码</th><th>简称</th><th>持仓集中度</th><th>概念简介</th></tr></thead>
      <tbody>
{''.join(rows)}
      </tbody>
    </table>
    </div>
  </div>'''

with open('D:/1.work/project/agu-web2/scripts/qdii_holdings_html.txt', 'w', encoding='utf-8') as f:
    f.write(new_section)
print(f'Generated {len(stocks)} stock rows')
