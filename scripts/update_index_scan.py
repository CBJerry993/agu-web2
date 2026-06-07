"""
指数均线多空扫描 - 写入本地JSON供HTML轮询展示
在 iquant 环境中运行，每5分钟调用一次 update_index_data() 即可
"""

import json
import os
from datetime import datetime

OUTPUT = 'D:/1.work/project/agu-web2/data/index_scan.json'


def update_index_data(bull_list, bear_list, total_index_count=None):
    """
    bull_list: [{'rank':1, 'strength':'+0.08%', 'maCount':6, 'name':'上证指数',
                 'code':'000001', 'point':3423.56, 'change':'+1.25%'}, ...]
    bear_list: [{'rank':1, 'strength':'-0.12%', 'maCount':6, 'name':'科创50',
                 'code':'000688', 'point':935.72, 'change':'-2.13%'}, ...]
    total_index_count: 扫描的总指数数量

    示例用法（在 iquant 中）：
    from update_index_scan import update_index_data
    update_index_data(bull_indices, bear_indices, total_index_count=20)
    """
    now = datetime.now()
    bull_count = len(bull_list)
    bear_count = len(bear_list)
    total = total_index_count or (bull_count + bear_count) or 20

    data = {
        'updateTime': now.strftime('%Y-%m-%d %H:%M:%S'),
        'nextScan': (now.replace(second=0, microsecond=0)).strftime('%Y-%m-%d %H:%M:%S'),
        'summary': {
            'bullCount': bull_count,
            'bullPct': f'{bull_count/total*100:.1f}%',
            'bearCount': bear_count,
            'bearPct': f'{bear_count/total*100:.1f}%',
            'totalScanned': total,
        },
        'bullIndices': bull_list,
        'bearIndices': bear_list,
    }

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'[{now}] 指数扫描已更新: 多头{bull_count} 空头{bear_count} -> {OUTPUT}')


# ========== iquant 集成示例（注释掉，实际使用时取消注释）==========
"""
# 在 iquant 的策略或定时任务中：
import iquant as iq

# 关注的核心指数列表
WATCH_INDICES = [
    ('000001', '上证指数'),
    ('399001', '深证成指'),
    ('000300', '沪深300'),
    ('000016', '上证50'),
    ('399006', '创业板指'),
    ('000688', '科创50'),
    ('000905', '中证500'),
    ('000852', '中证1000'),
    ('000015', '红利指数'),
    ('399986', '中证银行'),
    ('980017', '国证芯片'),
    # 港股/美股指数需要根据 iquant 支持情况添加
    # ('HSI', '恒生指数'),
    # ('IXIC', '纳斯达克'),
]

def scan_index_ma():
    bull, bear = [], []

    for code, name in WATCH_INDICES:
        idx = iq.get_index(code)  # 获取指数行情
        if not idx:
            continue

        point = idx.close     # 点位
        change_pct = idx.change_pct  # 涨跌幅

        # 计算均线排列强度 (MA5/10/20/60/120/250)
        mas = [idx.ma5, idx.ma10, idx.ma20, idx.ma60, idx.ma120, idx.ma250]
        ma_up = all(mas[i] > mas[i+1] for i in range(len(mas)-1) if mas[i] and mas[i+1])
        ma_down = all(mas[i] < mas[i+1] for i in range(len(mas)-1) if mas[i] and mas[i+1])

        # 计算有效均线数
        valid_mas = sum(1 for m in mas if m is not None)

        if ma_up:
            strength_pct = (point - mas[0]) / mas[0] * 100 if mas[0] else 0
            bull.append({
                'rank': 0,
                'strength': f'{strength_pct:+.2f}%',
                'maCount': valid_mas,
                'name': name,
                'code': code,
                'point': point,
                'change': f'{change_pct:+.2f}%',
            })
        elif ma_down:
            strength_pct = (point - mas[-1]) / mas[-1] * 100 if mas[-1] else 0
            bear.append({
                'rank': 0,
                'strength': f'{strength_pct:+.2f}%',
                'maCount': valid_mas,
                'name': name,
                'code': code,
                'point': point,
                'change': f'{change_pct:+.2f}%',
            })

    # 按强度排序
    bull.sort(key=lambda x: float(x['strength'].rstrip('%')), reverse=True)
    bear.sort(key=lambda x: float(x['strength'].rstrip('%')))

    for i, item in enumerate(bull): item['rank'] = i + 1
    for i, item in enumerate(bear): item['rank'] = i + 1

    # 写入本地文件
    from update_index_scan import update_index_data
    update_index_data(bull, bear, total_index_count=len(WATCH_INDICES))

# iquant 定时任务：每5分钟
# iq.run_periodic(scan_index_ma, interval=300)
"""
