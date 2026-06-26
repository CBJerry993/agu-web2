"""
导出50只新高基金的前十大重仓股CSV
输出: fund_code, fund_name, stock_code, stock_name
基金名称来自2026-06-16查询结果（硬编码，避免API字段空值）
"""
import subprocess, json, os, csv, time

TTSKILL = r'C:\Users\R7000P\AppData\Local\TTFund\ttskill-base\ttskill-base-win32-x64-0.1.1\bin\ttskill.cmd'

# ── 2026-06-18 近1月创1年新高的50只A类基金 (按YTD收益排序) ──
FUND_LIST = [
    ("006502", "财通集成电路产业股票A"),
    ("014736", "创金合信专精特新股票发起A"),
    ("005825", "申万菱信智能驱动股票A"),
    ("005628", "汇安趋势动力股票A"),
    ("540010", "汇丰晋信科技先锋股票"),
    ("020356", "华夏半导体材料设备ETF联接A"),
    ("021532", "天弘半导体设备指数A"),
    ("010013", "易方达信息行业精选股票A"),
    ("020639", "广发半导体设备ETF联接A"),
    ("021893", "易方达半导体设备ETF联接A"),
    ("001105", "信澳转型创新股票A"),
    ("019632", "国泰半导体设备ETF联接A"),
    ("008382", "融通产业趋势股票"),
    ("006081", "海富通电子传媒股票A"),
    ("023828", "万家中证半导体材料设备主题ETF发起式联接A"),
    ("009491", "宝盈创新驱动股票A"),
    ("010391", "易方达战略新兴产业股票A"),
    ("019454", "华泰柏瑞中韩半导体ETF发起式联接(QDII)A"),
    ("013242", "华银优势行业股票"),
    ("009891", "融通产业趋势臻选股票A"),
    ("020839", "南方中证半导体产业指数发起A"),
    ("001956", "国联安科技动力"),
    ("020464", "招商中证半导体产业ETF发起式联接A"),
    ("012696", "同泰数字经济股票A"),
    ("021718", "华泰紫金中证半导体产业指数型发起A"),
    ("024069", "上银中证半导体产业指数发起式A"),
    ("001877", "宝盈国家安全沪港深股票A"),
    ("014854", "嘉实中证半导体指数增强发起式A"),
    ("519935", "长信创新驱动股票"),
    ("000697", "汇添富移动互联股票A"),
    ("021224", "华宝上证科创板芯片ETF发起式联接A"),
    ("001416", "嘉实事件驱动股票"),
    ("014191", "广发先进制造股票发起式A"),
    ("000411", "景顺长城优质成长股票A"),
    ("005310", "广发电子信息传媒股票A"),
    ("008009", "华商高端装备制造股票A"),
    ("006265", "红土创新新科技股票A"),
    ("501201", "红土创新科技创新股票(LOF)A"),
    ("000688", "景顺长城研究精选股票A"),
    ("008326", "东财通信A"),
    ("001048", "富国新兴产业股票A"),
    ("006751", "富国互联科技股票A"),
    ("017488", "嘉实信息产业股票发起式A"),
    ("008086", "华夏中证5G通信主题ETF联接A"),
    ("008889", "银华中证5G通信主题ETF联接A"),
    ("021933", "富国中证通信设备主题ETF发起式联接A"),
    ("020899", "天弘中证全指通信设备指数发起A"),
    ("023407", "华宝创业板人工智能ETF发起式联接A"),
    ("021988", "银河中证通信设备主题指数发起式A"),
    ("020691", "博时中证全指通信设备指数发起式A"),
]

OUTPUT = r'D:\1.work\project\agu-web2\scripts\holdings_detail.csv'
env = os.environ.copy()
env.pop('NODE_OPTIONS', None)

rows = []
ok, fail = 0, 0

print(f'导出50只基金持仓明细...')
for i, (fcode, fname) in enumerate(FUND_LIST):
    print(f'[{i+1:2d}/50] {fcode} {fname[:20]}...', end=' ')
    body = json.dumps({'fund_id': fcode}, ensure_ascii=False)
    try:
        proc = subprocess.run(
            [TTSKILL, 'invoke', 'TTFUND_HOLDING_INFO', '--action', 'query', '--body', body],
            capture_output=True, text=True, encoding='utf-8', timeout=30, env=env,
        )
        if proc.returncode != 0:
            if '429' in proc.stderr:
                print('限流等5s...', end=' ')
                time.sleep(5)
                proc = subprocess.run(
                    [TTSKILL, 'invoke', 'TTFUND_HOLDING_INFO', '--action', 'query', '--body', body],
                    capture_output=True, text=True, encoding='utf-8', timeout=30, env=env,
                )
            if proc.returncode != 0:
                print(f'失败')
                fail += 1
                continue

        raw = json.loads(proc.stdout)
        data = raw.get('data', {}).get('raw_result', {}).get('body', {}).get('data', {})
        stock_list = data.get('top_holdings', {}).get('stock', [])
        # 兼容: 也可能在 data.stock
        if not stock_list:
            stock_list = data.get('stock', [])

        count = 0
        for s in stock_list:
            sc = s.get('GPDM', '')
            sn = s.get('GPJC', '')
            if sc:
                rows.append([fcode, fname, sc, sn])
                count += 1
        print(f'{count}条')
        ok += 1

    except Exception as e:
        print(f'异常({e})')
        fail += 1

    time.sleep(0.3)

with open(OUTPUT, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['基金代码', '基金名称', '股票代码', '股票名称'])
    w.writerows(rows)

print(f'\n完成: ok={ok} fail={fail} 总记录={len(rows)}')
print(f'已保存: {OUTPUT}')
