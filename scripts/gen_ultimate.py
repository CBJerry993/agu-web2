"""
终极版: GS145完整CSS + 真实排名 + 更新持仓
"""
import json, datetime, re
from collections import defaultdict

EM_RANKED = 'D:/1.work/project/agu-web2/scripts/em_top100_ranked.json'
HOLDINGS_PATH = 'D:/1.work/project/agu-web2/scripts/holdings_top100.json'
OUTPUT = 'D:/1.work/project/agu-web2/reports/top_100.html'
today = datetime.date.today().strftime('%Y-%m-%d')

with open(EM_RANKED, 'r', encoding='utf-8') as f:
    data = json.load(f)
with open(HOLDINGS_PATH, 'r', encoding='utf-8') as f:
    holdings = json.load(f)

funds = data['funds']
rank_data = data['rank_data']
periods = ['w1','m1','m3','m6','ytd','y1','y2']
period_labels = ['近1周','近1月','近3月','近6月','今年来','近1年','近2年']

# ==================== CLASSIFY ====================
def classify(f):
    code = f['code']
    in_top_50, in_bot_50 = 0, 0
    w1m3_top30 = True
    for p in periods:
        if code not in rank_data.get(p,{}): continue
        r = rank_data[p][code]
        if r['rank'] is None: continue
        pct_val = r['rank'] / r['total']
        if pct_val <= 0.5:
            in_top_50 += 1
            if p in ('w1','m1','m3') and pct_val > 0.3: w1m3_top30 = False
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

# ==================== CELL BUILDER ====================
def fmt_cell(period_key, f):
    code = f['code']
    ret_val = f.get(period_key, '')
    has_ret = ret_val and str(ret_val).strip() not in ('', '--', '%')
    
    # Build return line
    if has_ret:
        try:
            rv = float(str(ret_val).replace('%','').replace('+',''))
            sign = '+' if rv > 0 else ''
            rcls = 'up' if rv > 0 else ('dn' if rv < 0 else 'neutral')
            html = f'<td><div class="cell-ret"><span class="{rcls}">{sign}{rv:.2f}%</span></div>'
        except:
            html = '<td><div class="cell-ret"><span class="na">--</span></div>'
    else:
        html = '<td><div class="cell-ret"><span class="na">--</span></div>'
    
    # Build rank + pct (independent of return)
    if code in rank_data.get(period_key, {}):
        r = rank_data[period_key][code]
        rk = r['rank']
        if rk is None:
            html += f'<div class="cell-rank"><span class="rank-num">-- | {r["total"]}</span></div>'
            html += '<div class="cell-pct"><span class="na">--</span></div>'
        else:
            html += f'<div class="cell-rank"><span class="rank-num">{rk} | {r["total"]}</span></div>'
            pct_val = rk / r['total']
            is_top = pct_val < 0.5
            pcls = 'pct-top' if pct_val <= 0.1 else ('pct-good' if is_top else ('pct-mid' if pct_val <= 0.5 else 'pct-bad'))
            pct_str = r['pct']
            if pct_str.startswith('Q'): pct_str = '前' + pct_str[1:] + '%'
            elif pct_str.startswith('H'): pct_str = '后' + pct_str[1:] + '%'
            html += f'<div class="cell-pct"><span class="{pcls}">{pct_str}</span></div>'
    else:
        html += '<div class="cell-rank"><span class="rank-num">-- | --</span></div><div class="cell-pct"><span class="na">--</span></div>'
    
    return html + '</td>'

def build_rows(flist):
    rows = []
    for i, f in enumerate(flist):
        cls = 'row-even' if i % 2 == 0 else 'row-odd'
        cells = ''.join(fmt_cell(p, f) for p in periods)
        rows.append(f'<tr class="{cls}"><td class="col-fund"><a href="https://fund.eastmoney.com/{f["code"]}.html" target="_blank">{f["code"]}</a> <span class="fname">{f["name"]}</span></td>{cells}</tr>')
    return '\n'.join(rows)

# ==================== SECTIONS ====================
cat_cfg = {
    '夯': ('c0392b','#fdecea','≥5周期前50%且近1W/1M/3M全前30%','顶尖'),
    '顶': ('e67e22','#fef3e2','≥5周期前50%且近1W/1M/3M全前50%','优秀'),
    '人上人': ('27ae60','#e8f5e9','≥4周期前50%','良好'),
    '拉': ('8e44ad','#f3e5f5','5周期全后50%','警示'),
    'NPC': ('888','#f5f5f5','不满足条件或无数据','普通'),
}

secs = []
for cat in ['夯','顶','人上人','拉','NPC']:
    flist = cats[cat]
    if not flist: continue
    color, bg, desc, label = cat_cfg[cat]
    rows = build_rows(flist)
    secs.append(f'''
  <div class="section-title" style="border-left-color:#{color}">
    {cat} · {label}
    <span class="badge" style="background:{bg};color:#{color}">{len(flist)}只 · {desc}</span>
  </div>
  <div class="table-wrap">
  <table class="fund-table">
  <thead><tr><th>基金（代码+简称）</th><th>近1周</th><th>近1月</th><th>近3月</th><th>近6月</th><th class="sort-col">今年来 ▼</th><th>近1年</th><th>近2年</th></tr></thead>
  <tbody>{rows}</tbody>
  </table>
  </div>''')

# ==================== HOLDINGS ====================
stock_descs = {
    # ========== 主板 ==========
    '002384': '东山精密，全球领先的柔性电路板(FPC)/PCB制造商，苹果核心供应商，布局LED封装与新能源。',
    '600487': '亨通光电，国内光纤光缆行业龙头，布局海洋通信、硅光模块与量子通信，全产业链覆盖。',
    '601869': '长飞光纤，全球光纤光缆产能第一，预制棒技术领先，受益5G+东数西算光纤需求爆发。',
    '002837': '英维克，国内精密温控龙头，数据中心液冷+储能温控双轮驱动，客户覆盖头部云厂商。',
    '002463': '沪电股份，高端PCB制造商，企业通信板和汽车板为核心，深度受益AI服务器升级需求。',
    '600105': '永鼎股份，光通信综合方案商，光纤光缆+光芯片+超导三线布局，旗下拥有光芯片子公司。',
    '600183': '生益科技，全球覆铜板(CCL)龙头，高频高速产品受益5G和服务器升级需求。',
    '600176': '中国巨石，全球玻纤行业龙头，产能规模和技术水平世界领先，产品广泛用于风电/汽车/建筑。',
    '600522': '中天科技，光纤通信与海缆龙头，海洋工程+新能源+光纤三大板块，海缆市占率领先。',
    '603256': '宏和科技，高端电子布制造商，超薄/极薄电子布技术领先，是覆铜板和PCB上游关键材料。',
    '001309': '德明利，存储芯片模组方案商，布局NAND Flash与DRAM分销及自有品牌SSD产品。',
    '603929': '亚翔集成，半导体/光电洁净室工程服务商，为芯片厂提供无尘车间设计施工一体化方案。',
    '600498': '烽火通信，光通信国家队，光传输+光纤光缆+光接入全布局，中国信科集团旗下。',
    '603618': '杭电股份，电线电缆制造商，特种电缆和光纤复合架空地线为主要业务，电网建设受益标的。',
    '600345': '长江通信，光通信设备与光纤传感方案商，中国信科集团旗下，布局光传输与智慧交通。',
    '000070': '特发信息，光纤光缆综合服务商，军工信息化+光通信双主线，深圳国资背景。',
    '002916': '深南电路，国内PCB行业龙头之一，封装基板技术领先，华为/中兴核心供应商。',
    '603986': '兆易创新，国产MCU和NOR Flash龙头，布局DRAM和RISC-V，国产替代核心标的。',
    '600183': '生益科技，全球覆铜板(CCL)龙头，高频高速产品受益5G和服务器升级需求。',
    '603228': '景旺电子，国内PCB制造强者，柔性板/刚挠结合板技术领先，汽车电子+消费电子客户广泛。',
    '000973': '佛塑科技，高分子功能薄膜龙头，锂电隔膜+偏光膜+电容膜三大高端材料布局，新能源材料受益标的。',
    '002796': '世嘉科技，精密箱体系统方案商，电梯轿厢+5G滤波器双轮驱动，储能温控柜新增长点。',
    # ========== 创业板 ==========
    '300308': '中际旭创，全球光模块龙头，800G/1.6T高速光模块批量出货，英伟达/谷歌核心供应商。',
    '300502': '新易盛，国内光模块龙头之一，400G/800G光模块快速放量，深度受益AI算力爆发的光互联需求。',
    '300548': '长芯博创(长芯盛)，光芯片与光器件方案商，布局硅光集成与高速光模块核心芯片。',
    '300394': '天孚通信，光器件精密制造龙头，光引擎/光模块结构件核心供应商，英伟达产业链受益标的。',
    '300207': '欣旺达，消费电子电池龙头，布局动力+储能电池第二曲线，苹果/华为核心供应商。',
    '300438': '鹏辉能源，储能电池龙头，户用储能+工商业储能双轮驱动，海外出货占比高。',
    '300476': '胜宏科技，PCB制造商，高多层板/HDI板技术领先，布局AI服务器和汽车电子PCB。',
    '301358': '湖南裕能，磷酸铁锂正极材料龙头，宁德时代核心供应商，市占率行业第一。',
    '300620': '光库科技，铌酸锂调制器龙头，光纤激光器+光通信核心器件，薄膜铌酸锂受益高速光模块。',
    '300757': '罗博特科，光伏电池自动化设备龙头，TOPCon/HJT电池片自动化产线核心供应商。',
    '301308': '江波龙，存储品牌与方案商，旗下雷克沙品牌+企业级SSD双线发力，受益存储国产化。',
    '300475': '香农芯创，电子元器件分销平台，代理存储/模拟/传感器芯片，布局国产替代赛道。',
    '301377': '鼎泰高科，PCB微型钻针龙头，钻针/铣刀市占率领先，受益AI服务器PCB需求升级。',
    '301200': '大族数控，PCB专用设备龙头，激光钻孔/成型设备市占率国内第一。',
    # ========== 科创板 ==========
    '688498': '源杰科技，国产光芯片龙头，25G/50G/100G EML/DFB光芯片核心供应商，受益高速光模块国产化。',
    '688048': '长光华芯，高功率半导体激光芯片龙头，工业激光+激光雷达+光通信三大领域布局。',
    '688525': '佰维存储，存储芯片模组与嵌入式存储方案商，布局消费级/企业级SSD和工业存储。',
    '688008': '澜起科技，内存接口芯片全球龙头，DDR5新品放量，PCIe Retimer芯片受益AI服务器。',
    '688630': '芯碁微装，直写光刻设备龙头，PCB/IC载板/先进封装曝光设备国产化核心标的。',
    '688521': '芯原股份，一站式芯片设计服务(IP+设计)，布局AI芯片与数据中心芯片定制服务。',
    '688195': '腾景科技，精密光学元件与模组厂商，光通信滤光片/光学镜头核心供应商。',
    '688717': '艾罗能源，户用储能逆变器龙头，欧洲市场份额领先，布局工商储与地面电站逆变器。',
    '688205': '德科立，光模块与光放大器方案商，400G/800G光模块及光传输子系统核心供应商。',
    '688150': '莱特光电，OLED终端材料龙头，打破海外垄断，京东方/华星光电核心供应商。',
    '688167': '炬光科技，高功率半导体激光器及光学器件商，泛半导体+汽车激光雷达双赛道布局。',
    '688766': '普冉股份，NOR Flash和EEPROM存储器芯片设计商，消费电子+物联网市场持续放量。',
    '688627': '精智达，新型显示器件检测设备龙头，布局Mini/Micro-LED和半导体检测设备。',
    '688183': '生益电子，高端PCB制造商，布局5G基站+服务器+汽车PCB，生益科技旗下子公司。',
    '688313': '仕佳光子，光通信芯片与器件商，PLC分路器全球市占率领先，布局AWG和DFB激光器芯片。',
    # ========== 美股 ==========
    'TSM': '台积电(TSMC)，全球最大芯片代工厂，3nm/2nm制程领先，苹果/英伟达/AMD核心客户。',
    'NVDA': '英伟达(NVIDIA)，全球AI GPU绝对霸主，H200/B200算力芯片垄断AI训练市场。',
    'LITE': 'Lumentum，全球领先的光通信激光器与3D传感芯片供应商，苹果Face ID核心器件提供商。',
    'COHR': 'Coherent，全球领先的光子学与激光器巨头，整合II-VI后覆盖光通信/激光/SiC全产业链。',
    'AVGO': '博通(Broadcom)，全球半导体与基础设施软件巨头，AI网络芯片与定制化ASIC领导者。',
    'TSEM': 'Tower半导体，以色列特色工艺晶圆代工厂，射频/电源管理/图像传感器芯片代工。',
    'JOYY': '欢聚(JOYY)，全球音视频社交平台，Bigo Live直播和Likee短视频出海业务为主。',
    'JP3684400009': '日东纺(Nitto Boseki)，日本电子玻纤布龙头，覆铜板核心原材料供应商，受益AI服务器PCB需求。',
    # ========== 港股 ==========
    '06869': '长飞光纤光缆(H股)，全球光纤光缆产能第一，预制棒技术领先，A+H两地上市。',
}
hold_secs = []
board_configs = [
    ('主板', '主板重仓股', '#1a5fac', '📊'),
    ('创业板', '创业板重仓股', '#e67e22', '🚀'),
    ('科创板', '科创板重仓股', '#8e44ad', '💎'),
    ('港股', '港股重仓股', '#c0392b', '🏢'),
    ('美股', '美股重仓股', '#c0392b', '🌍'),
]
for board, title, color, icon in board_configs:
    items = holdings.get(board, [])
    if not items: continue
    # Filter: only show stocks with count >= 3
    items = [it for it in items if it['count'] >= 3]
    if not items: continue
    items = items[:12] if board=='美股' else items[:20]
    max_count = max(it['count'] for it in items)
    rows = []
    for it in items:
        pct_width = int(it['count'] / max_count * 100) if max_count else 0
        d = stock_descs.get(it['code'], '')
        # Bar color based on count intensity
        bar_color = '#c0392b' if pct_width > 60 else ('#e67e22' if pct_width > 30 else '#95a5a6')
        desc_col = f'<td class="stock-desc">{d}</td>' if d else '<td class="stock-desc no-desc">—</td>'
        rows.append(f'''<tr>
<td class="stock-code">{it['code']}</td>
<td class="stock-name">{it['name']}</td>
<td class="stock-freq">
  <div class="freq-bar-wrap"><div class="freq-bar-fill" style="width:{pct_width}%;background:{bar_color}"></div></div>
  <span class="freq-num">{it['count']}次</span>
</td>{desc_col}
</tr>''')
    hold_secs.append(f'''
<div class="holdings-section">
  <div class="holdings-header" style="border-left:5px solid {color}">
    <span class="holdings-icon">{icon}</span>
    <span class="holdings-title">{title}</span>
    <span class="holdings-badge" style="background:{color}15;color:{color}">{len(items)}只</span>
  </div>
  <div class="table-wrap">
  <table class="holdings-table">
    <thead><tr><th>代码</th><th>简称</th><th>持仓集中度</th><th>概念简介</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
  </div>
</div>''')

# ==================== STATS ====================
stats = f'''
    <div class="stat-card blue">
      <div class="val">100</div><div class="lbl">基金总数</div>
    </div>
    <div class="stat-card red">
      <div class="val">{len(cats["夯"])}</div><div class="lbl">夯 · 顶尖</div>
    </div>
    <div class="stat-card orange">
      <div class="val">{len(cats["顶"])}</div><div class="lbl">顶 · 优秀</div>
    </div>
    <div class="stat-card green">
      <div class="val">{len(cats["人上人"])}</div><div class="lbl">人上人 · 良好</div>
    </div>
    <div class="stat-card purple">
      <div class="val">{len(cats["拉"])}</div><div class="lbl">拉 · 警示</div>
    </div>
    <div class="stat-card gray">
      <div class="val">{len(cats["NPC"])}</div><div class="lbl">NPC · 普通</div>
    </div>'''

# Coverage note
coverage_parts = []
for p in periods:
    c = len(rank_data[p])
    l = period_labels[periods.index(p)]
    coverage_parts.append(f'{l}{c}/100')
note = ''

# ==================== FINAL HTML ====================
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
    background: linear-gradient(135deg, #0d2b6e 0%, #1a5fac 50%, #0d8fd9 100%);
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
  .stat-card.red    {{ border-color: #c0392b; }}
  .stat-card.red .val,    .stat-card.red .lbl    {{ color: #c0392b; }}
  .stat-card.orange {{ border-color: #e67e22; }}
  .stat-card.orange .val, .stat-card.orange .lbl {{ color: #e67e22; }}
  .stat-card.green  {{ border-color: #27ae60; }}
  .stat-card.green .val,  .stat-card.green .lbl  {{ color: #27ae60; }}
  .stat-card.purple {{ border-color: #8e44ad; }}
  .stat-card.purple .val, .stat-card.purple .lbl {{ color: #8e44ad; }}
  .stat-card.gray   {{ border-color: #888; }}
  .stat-card.gray .val,   .stat-card.gray .lbl   {{ color: #888; }}
  .stat-card.blue   {{ border-color: #1a5fac; }}
  .stat-card.blue .val,   .stat-card.blue .lbl   {{ color: #1a5fac; }}

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

  .table-wrap {{ overflow-x: auto; }}

  .fund-table {{ width: 100%; min-width: 980px; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 6px rgba(0,0,0,0.07); font-size: 13px; table-layout: fixed; }}
  .fund-table thead tr {{ background: linear-gradient(90deg, #0d2b6e, #1a5fac); color: white; }}
  .fund-table thead th {{ padding: 9px 5px; font-size: 11px; font-weight: 600; text-align: center; white-space: nowrap; letter-spacing: 0.3px; border-right: 1px solid rgba(255,255,255,0.15); }}
  .fund-table thead th:last-child {{ border-right: none; }}
  .fund-table thead th.sort-col {{ background: rgba(255,255,255,0.2); text-shadow: 0 0 8px rgba(255,255,255,0.5); font-size: 12px; border-bottom: 3px solid #f9e79f; }}
  .fund-table thead th:first-child {{ width: 31%; text-align: left; padding-left: 12px; }}
  .fund-table tbody tr {{ border-bottom: 1px solid #f0f3f8; transition: background 0.15s; }}
  .fund-table tbody tr:last-child {{ border-bottom: none; }}
  .fund-table tbody tr:hover {{ background: #f6f9ff !important; transform: translateX(6px); box-shadow: 0 2px 12px rgba(26,95,172,0.10); transition: all 0.2s ease; }}
  .fund-table tbody tr {{ transition: all 0.2s ease; }}
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

  /* Holdings section - redesigned */
  .holdings-section {{
    margin-bottom: 28px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 16px rgba(0,0,0,0.06);
    overflow: hidden;
  }}
  .holdings-header {{
    display: flex; align-items: center;
    padding: 14px 20px;
    background: linear-gradient(135deg, #f8f9fc, #fff);
    border-bottom: 1px solid #f0f3f8;
    gap: 10px;
  }}
  .holdings-icon {{ font-size: 22px; }}
  .holdings-title {{
    font-size: 17px; font-weight: 800; color: #1a2035;
    letter-spacing: 0.5px;
  }}
  .holdings-badge {{
    font-size: 11px; padding: 3px 10px; border-radius: 12px;
    font-weight: 600; margin-left: auto;
  }}

  .holdings-table {{
    width: 100%; border-collapse: collapse;
    font-size: 13px; table-layout: auto;
  }}
  .holdings-table thead tr {{
    background: linear-gradient(90deg, #1a2035, #2c3e50);
    color: white;
  }}
  .holdings-table thead th {{
    padding: 10px 12px; font-size: 11px; font-weight: 600;
    text-align: left; letter-spacing: 0.5px;
  }}
  .holdings-table thead th:first-child {{ width: 80px; }}
  .holdings-table thead th:nth-child(2) {{ width: 100px; }}
  .holdings-table thead th:nth-child(3) {{ width: 170px; }}
  .holdings-table tbody tr {{
    border-bottom: 1px solid #f0f3f8;
    transition: all 0.2s ease;
  }}
  .holdings-table tbody tr:last-child {{ border-bottom: none; }}
  .holdings-table tbody tr:hover {{
    background: linear-gradient(90deg, #f6f9ff, #fafbfe);
    transform: translateX(8px);
    box-shadow: 0 2px 12px rgba(26,95,172,0.10);
  }}
  .holdings-table td {{
    padding: 10px 12px; vertical-align: middle;
  }}
  .stock-code {{
    font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
    font-weight: 700; color: #1a5fac; font-size: 13px;
  }}
  .stock-name {{ font-weight: 600; color: #1a2035; font-size: 13px; }}
  
  .stock-freq {{ 
    display: flex; align-items: center; gap: 10px;
  }}
  .freq-bar-wrap {{
    flex: 1; height: 16px; background: #f0f3f8;
    border-radius: 8px; overflow: hidden;
    max-width: 100px;
  }}
  .freq-bar-fill {{
    height: 100%; border-radius: 8px;
    transition: width 0.4s ease;
    min-width: 4px;
  }}
  .freq-num {{
    font-weight: 700; font-size: 13px; color: #1a2035;
    white-space: nowrap;
  }}
  
  .stock-desc {{
    font-size: 12px; color: #5a6a85; line-height: 1.55;
    padding-right: 8px;
  }}
  .stock-desc.no-desc {{
    color: #ccc; font-style: italic; font-size: 11px;
  }}

  .page-footer {{ text-align: center; color: #aaa; font-size: 10px; padding: 16px; margin-top: 8px; }}

  .holdings-section .table-wrap {{ overflow-x: visible; }}

  @media (max-width: 1100px) {{ .fund-table {{ font-size: 11px; }} .col-fund, .col-fund a, .col-fund .fname {{ font-size: 11px; }} .cell-ret {{ font-size: 12px; }} }}
</style>
</head>
<body>

<div class="page-header">
  <h1>🏆 全市场Top100基金收益排行</h1>
  <div class="subtitle">今年以来收益率排名 · 全市场基金Top100 · 夯/顶/人上人/拉/NPC五级分类 · 涨幅 &amp; 同类排名</div>
  <div class="update-time">净值更新：{today} &nbsp;|&nbsp; 数据来源：东方财富天天基金 &nbsp;|&nbsp; 生成于 {today}</div>
</div>

<div class="main">

  <div class="stats-row">{stats}</div>

{note}

{''.join(secs)}

{''.join(hold_secs)}

</div>

<div class="page-footer">
  数据来源：东方财富天天基金 &nbsp;|&nbsp; 涨幅颜色：红涨绿跌（中国A股惯例）&nbsp;|&nbsp;
  各分类内按今年来收益率降序排列 &nbsp;|&nbsp; 持仓数据截至2026Q1季报 &nbsp;|&nbsp; 报告由AI自动生成，仅供参考 &nbsp;|&nbsp; {today}
</div>

</body>
</html>'''

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Generated: {OUTPUT}")
for cat in ['夯','顶','人上人','拉','NPC']:
    print(f"  {cat}: {len(cats[cat])}")
print(f"\nHoldings: 主板{len(holdings.get('主板',[]))} 创业板{len(holdings.get('创业板',[]))} 科创板{len(holdings.get('科创板',[]))} 美股{len(holdings.get('美股',[]))}")
