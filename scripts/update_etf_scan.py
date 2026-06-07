"""
ETF均线多空扫描 - 写入本地JSON供HTML轮询展示
在 iquant 环境中运行，每5分钟调用一次 update_etf_data() 即可
"""

import json
import os
from datetime import datetime

OUTPUT = 'D:/1.work/project/agu-web2/data/etf_scan.json'

def update_etf_data(bull_list, bear_list, total_etf_count=None):
    """
    bull_list: [{'rank':1, 'strength':'0.04%', 'maCount':6, 'name':'上证指数ETF', 'code':'530060', 'price':1.009, 'change':'+0.60%'}, ...]
    bear_list: [{'rank':1, 'strength':'-0.01%', 'maCount':6, 'name':'标普信息科', 'code':'161128', 'price':7.174, 'change':'-1.47%'}, ...]
    total_etf_count: 扫描的总ETF数量，用于计算百分比；如果为None则用bull+bear

    示例用法（在 iquant 中）：
    from update_etf_scan import update_etf_data
    update_etf_data(bull_etfs, bear_etfs, total_count=200)
    """
    now = datetime.now()
    bull_count = len(bull_list)
    bear_count = len(bear_list)
    total = total_etf_count or (bull_count + bear_count) or 200

    data = {
        'updateTime': now.strftime('%Y-%m-%d %H:%M:%S'),
        'nextScan': (now.replace(second=0, microsecond=0)).strftime('%Y-%m-%d %H:%M:%S'),
        'summary': {
            'bullCount': bull_count,
            'bullPct': f'{bull_count/total*100:.1f}%',
            'bearCount': bear_count,
            'bearPct': f'{bear_count/total*100:.1f}%',
        },
        'bullETFs': bull_list,
        'bearETFs': bear_list,
    }

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'[{now}] ETF扫描已更新: 多头{bull_count} 空头{bear_count} -> {OUTPUT}')


# ========== iquant 集成示例（注释掉，实际使用时取消注释）==========
"""
# 在 iquant 的策略或定时任务中：
import iquant as iq

def scan_etf_ma():
    bull, bear = [], []
    # iquant 的 ETF 池
    etf_pool = iq.get_etf_pool()  # 假设获取全部 ETF
    
    for etf in etf_pool:
        code = etf.code
        name = etf.name[:8]
        price = etf.close
        change_pct = etf.change_pct
        
        # 计算均线排列强度
        mas = [etf.ma5, etf.ma10, etf.ma20, etf.ma60, etf.ma120, etf.ma250]
        ma_up = all(mas[i] > mas[i+1] for i in range(len(mas)-1) if mas[i] and mas[i+1])
        ma_down = all(mas[i] < mas[i+1] for i in range(len(mas)-1) if mas[i] and mas[i+1])
        
        # 计算有效均线数（非None）
        valid_mas = sum(1 for m in mas if m is not None)
        
        if ma_up:
            strength_pct = (price - mas[0]) / mas[0] * 100 if mas[0] else 0
            bull.append({
                'rank': 0,
                'strength': f'{strength_pct:+.2f}%',
                'maCount': valid_mas,
                'name': name,
                'code': code,
                'price': price,
                'change': f'{change_pct:+.2f}%',
            })
        elif ma_down:
            strength_pct = (price - mas[-1]) / mas[-1] * 100 if mas[-1] else 0
            bear.append({
                'rank': 0,
                'strength': f'{strength_pct:+.2f}%',
                'maCount': valid_mas,
                'name': name,
                'code': code,
                'price': price,
                'change': f'{change_pct:+.2f}%',
            })
    
    # 按强度排序
    bull.sort(key=lambda x: float(x['strength'].rstrip('%')), reverse=True)
    bear.sort(key=lambda x: float(x['strength'].rstrip('%')))
    
    for i, item in enumerate(bull): item['rank'] = i + 1
    for i, item in enumerate(bear): item['rank'] = i + 1
    
    # 写入本地文件
    from update_etf_scan import update_etf_data
    update_etf_data(bull[:50], bear[:50], total_etf_count=len(etf_pool))

# iquant 定时任务：每5分钟
# iq.run_periodic(scan_etf_ma, interval=300)
"""
