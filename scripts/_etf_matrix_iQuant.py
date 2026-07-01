# encoding:gbk
import pandas as pd
import numpy as np
import time

# 双账本独立计数
fund_persistence_dict = {}
index_persistence_dict = {}
last_executed_minute = -1

def get_disp_width(s):
    return sum(2 if ord(c) > 127 else 1 for c in s)

def truncate_and_pad(s, width):
    if get_disp_width(s) <= width:
        return s + ' ' * (width - get_disp_width(s))
    res, cur_w = "", 0
    for char in s:
        w = 2 if ord(char) > 127 else 1
        if cur_w + w > width: break
        res += char
        cur_w += w
    return res + ' ' * (width - cur_w)

def update_logic(persistence_table, code, current_type):
    if code not in persistence_table:
        persistence_table[code] = {"type": "SIDE", "count": 0}
    if current_type != "SIDE" and persistence_table[code]["type"] == current_type:
        persistence_table[code]["count"] += 1
    elif current_type != "SIDE":
        persistence_table[code]["type"] = current_type
        persistence_table[code]["count"] = 1
    else:
        persistence_table[code]["type"] = "SIDE"
        persistence_table[code]["count"] = 0
    return persistence_table[code]["count"]

def calc_boll_gap(close_series, trend, current_price):
    """布林带偏离百分比
    BULL多头: (上轨-现价)/上轨*100 → 负值=突破上轨→红色
    BEAR空头: (现价-下轨)/下轨*100 → 负值=跌破下轨→红色
    """
    if close_series is None or len(close_series) < 20:
        return '--'
    try:
        arr = np.array([float(v) for v in close_series[-20:]], dtype=float)
        ma20 = np.mean(arr)
        std20 = np.std(arr, ddof=1)
        upper = ma20 + 2 * std20
        lower = ma20 - 2 * std20
        if trend == 'BULL':
            if upper == 0: return '--'
            return '{:+.2f}%'.format((upper - current_price) / upper * 100)
        elif trend == 'BEAR':
            if lower == 0: return '--'
            return '{:+.2f}%'.format((current_price - lower) / lower * 100)
    except:
        pass
    return '--'

def init(ContextInfo):
    # 易方达基金池（剔除35只低成交额ETF，2026-07-01过滤后保留123只）
    ContextInfo.raw_codes_yi = [
        "159001", "159105", "159138", "159140", "159150", "159175", "159181", "159196",
        "159222", "159255", "159259", "159263", "159299", "159316", "159361", "159369",
        "159530", "159532", "159540", "159545", "159558", "159565", "159566", "159572",
        "159597", "159606", "159633", "159686", "159696", "159715", "159781", "159787",
        "159788", "159798", "159807", "159819", "159837", "159847", "159901", "159915",
        "159934", "161116", "161119", "161125", "161126", "161127", "161128", "161129",
        "161130", "180605", "502003", "502048", "506002", "508033", "510100", "510310",
        "510580", "510900", "511110", "511800", "512010", "512030", "512070", "512090",
        "512560", "512570", "513000", "513010", "513040", "513050", "513070", "513090",
        "513200", "513320", "513850", "515110", "515180", "515810", "516070", "516080",
        "516090", "516310", "516350", "516510", "516570", "516590", "520810", "520850",
        "520870", "530060", "530100", "530180", "551500", "560160", "560390", "562900",
        "562910", "562920", "562930", "562950", "562960", "562970", "562990", "563000",
        "563010", "563020", "563030", "563050", "563080", "563090", "563530", "563700",
        "588020", "588080", "588210", "588270", "588500", "588550", "588730", "589030",
        "589130", "589800", "589960"
    ]

    # 其他品牌基金池
    ContextInfo.raw_codes_other = [
        "513310", "159866", "513080", "513030", "159687", "520830",
        "159329", "159941", "159561", "159529", "159518",
        "159869", "562510"   # 游戏ETF华夏 + 旅游ETF华夏 (2026-07-01新增)
    ]

    stocks_yi = [c + ".SZ" if c[0] in "1" else c + ".SH" for c in ContextInfo.raw_codes_yi]
    stocks_other = [c + ".SZ" if c[0] in "1" else c + ".SH" for c in ContextInfo.raw_codes_other]

    ContextInfo.my_stocks = stocks_yi + stocks_other
    ContextInfo.index_etf_list = ["510050.SH", "510300.SH", "159903.SZ", "560510.SH", "159949.SZ", "159915.SZ", "588000.SH"]

    ContextInfo.set_universe(list(set(ContextInfo.my_stocks + ContextInfo.index_etf_list)))
    print(">>> ETF矩阵已就绪：基金{}只 + 指数{}只 (已剔除35只低成交额)".format(
        len(ContextInfo.my_stocks), len(ContextInfo.index_etf_list)))

def handlebar(ContextInfo):
    global last_executed_minute
    if not ContextInfo.is_last_bar(): return
    now_struct = time.localtime()

    if now_struct.tm_min % 5 == 0 and now_struct.tm_min != last_executed_minute:
        last_executed_minute = now_struct.tm_min
        all_targets = list(set(ContextInfo.my_stocks + ContextInfo.index_etf_list))

        # --- 5分钟数据（MA均线排列检测）---
        data_dict = ContextInfo.get_market_data_ex(['close'], all_targets, period='5m', count=80)
        tick_data = ContextInfo.get_full_tick(all_targets)

        # --- 日线数据（布林带·日）---
        daily_data = {}
        try:
            daily_data = ContextInfo.get_market_data(['close'], all_targets, period='1d', count=30, dividend_type='none')
        except Exception as e:
            print('[WARN] 日线数据获取失败: {}'.format(e))

        # --- 周线数据（布林带·周）---
        weekly_data = {}
        try:
            weekly_data = ContextInfo.get_market_data(['close'], all_targets, period='1w', count=30, dividend_type='none')
        except Exception as e:
            print('[WARN] 周线数据获取失败: {}'.format(e))

        def get_trend_info(code):
            if code not in data_dict or data_dict[code].empty: return "SIDE", 0, "0.000(0.00%)", 0.0
            c_series = data_dict[code]['close'].iloc[:-1]
            if len(c_series) < 60: return "SIDE", 0, "0.000(0.00%)", 0.0
            m = [c_series.tail(n).mean() for n in [5, 10, 20, 30, 60]]
            p5, p10 = c_series.iloc[:-1].tail(5).mean(), c_series.iloc[:-1].tail(10).mean()
            slope = (m[0] - p5) / p5 * 100

            curr_p, ratio = 0.0, 0.0
            if code in tick_data:
                curr_p = tick_data[code].get('lastPrice', 0.0)
                lc = tick_data[code].get('lastClose', 0.0)
                ratio = (curr_p - lc) / lc * 100 if lc > 0 else 0.0
            else:
                curr_p = c_series.iloc[-1]
                ratio = 0.0

            price_str = "{:.4f}({}{:.2f}%)".format(curr_p, '+' if ratio>0 else '', ratio)

            trend = "SIDE"
            if (m[0] > m[1] > m[2] > m[3] > m[4]) and m[0] > p5 and m[1] > p10:
                trend = "BULL"
            elif (m[0] < m[1] < m[2] < m[3] < m[4]) and m[0] < p5 and m[1] < p10:
                trend = "BEAR"

            return trend, slope, price_str, curr_p

        # 分类处理
        f_bull, f_bear, i_bull, i_bear = [], [], [], []

        # 基金池处理
        for s in ContextInfo.my_stocks:
            t, slp, p_info, curr_p = get_trend_info(s)
            cnt = update_logic(fund_persistence_dict, s, t)

            raw_name = ContextInfo.get_stock_name(s)
            display_name = raw_name  # 不再加[易]前缀

            # 布林带偏离（多头→上轨，空头→下轨）
            daily_boll = '--'
            weekly_boll = '--'
            if t in ('BULL', 'BEAR') and curr_p > 0:
                if s in daily_data and not daily_data[s].empty:
                    d_close = daily_data[s]['close'].values
                    daily_boll = calc_boll_gap(d_close, t, curr_p)
                if s in weekly_data and not weekly_data[s].empty:
                    w_close = weekly_data[s]['close'].values
                    weekly_boll = calc_boll_gap(w_close, t, curr_p)

            item = {
                'cnt': cnt,
                'n': "[{}] {}".format(cnt, display_name),
                's': s[:6],
                'slp': slp,
                'p': p_info,
                'bollDailyGap': daily_boll,
                'bollWeeklyGap': weekly_boll,
            }
            if t == "BULL": f_bull.append(item)
            elif t == "BEAR": f_bear.append(item)

        # 指数池处理
        for s in ContextInfo.index_etf_list:
            t, slp, p_info, curr_p = get_trend_info(s)
            cnt = update_logic(index_persistence_dict, s, t)

            daily_boll = '--'
            weekly_boll = '--'
            if t in ('BULL', 'BEAR') and curr_p > 0:
                if s in daily_data and not daily_data[s].empty:
                    d_close = daily_data[s]['close'].values
                    daily_boll = calc_boll_gap(d_close, t, curr_p)
                if s in weekly_data and not weekly_data[s].empty:
                    w_close = weekly_data[s]['close'].values
                    weekly_boll = calc_boll_gap(w_close, t, curr_p)

            item = {
                'cnt': cnt,
                'n': "[{}] {}".format(cnt, ContextInfo.get_stock_name(s)),
                's': s[:6],
                'slp': slp,
                'p': p_info,
                'bollDailyGap': daily_boll,
                'bollWeeklyGap': weekly_boll,
            }
            if t == "BULL": i_bull.append(item)
            elif t == "BEAR": i_bear.append(item)

        # 排序
        f_bull.sort(key=lambda x: (x['cnt'], x['slp']), reverse=True)
        f_bear.sort(key=lambda x: (x['cnt'], -x['slp']), reverse=True)
        i_bull.sort(key=lambda x: (x['cnt'], x['slp']), reverse=True)
        i_bear.sort(key=lambda x: (x['cnt'], -x['slp']), reverse=True)

        # ------------------ 打印区 ------------------
        time_str = time.strftime('%H:%M:%S', now_struct)
        print("\n" + "#"*90 + " NEW SCAN @ " + time_str + " " + "#"*90)

        f_sum = "基金池 | 多头:{}只({:.1f}%) | 空头:{}只({:.1f}%)".format(
            len(f_bull), len(f_bull)/len(ContextInfo.my_stocks)*100,
            len(f_bear), len(f_bear)/len(ContextInfo.my_stocks)*100)
        i_sum = "指数池 | 多头:{}只({:.1f}%) | 空头:{}只({:.1f}%)".format(
            len(i_bull), len(i_bull)/len(ContextInfo.index_etf_list)*100,
            len(i_bear), len(i_bear)/len(ContextInfo.index_etf_list)*100)
        print(truncate_and_pad(f_sum, 126) + " || " + i_sum)

        W_F = 62
        W_I = 56
        DIV, SEP = " || ", " | "

        print("-" * 260)
        h_f = truncate_and_pad("排名 强度 | [n] 名称 | 代码 | 价格(涨跌)", W_F)
        h_i = truncate_and_pad("强度 | [n] 名称 | 代码 | 价格(涨跌)", W_I)
        print(h_f + SEP + h_f + DIV + h_i + SEP + h_i)
        print("-" * 260)

        for i in range(20):
            def fmt_f(lst, idx):
                if idx >= len(lst): return ""
                d = lst[idx]
                return "{:<2} {:>6.2f}%".format(idx+1, d['slp']) + SEP + truncate_and_pad(d['n'], 18) + SEP + "{} ".format(d['s']) + SEP + "{}".format(d['p'])

            def fmt_i(lst, idx):
                if idx >= len(lst): return ""
                d = lst[idx]
                return "{:>6.2f}%".format(d['slp']) + SEP + truncate_and_pad(d['n'], 16) + SEP + "{} ".format(d['s']) + SEP + "{}".format(d['p'])

            row = truncate_and_pad(fmt_f(f_bull, i), W_F) + SEP + truncate_and_pad(fmt_f(f_bear, i), W_F) + DIV + \
                  truncate_and_pad(fmt_i(i_bull, i), W_I) + SEP + fmt_i(i_bear, i)
            print(row)
        print("-" * 260 + "\n")

        # ==================== JSON + JS 写入 ====================
        import json as _json, os as _os, subprocess as _sp

        def _parse_price(p_str):
            try:
                price_s, chg_s = p_str.split('(')
                return float(price_s), chg_s.rstrip(')')
            except:
                return 0.0, "0.00%"

        def _parse_name(n_str):
            idx = n_str.find('] ')
            return n_str[idx+2:] if idx >= 0 else n_str

        bull_etfs = []
        for i, it in enumerate(f_bull):
            pr, ch = _parse_price(it['p'])
            bull_etfs.append({
                'rank': i+1,
                'strength': '{:+.2f}%'.format(it['slp']),
                'maCount': it['cnt'],
                'name': _parse_name(it['n']),
                'code': it['s'],
                'price': pr,
                'change': ch,
                'bollDailyGap': it.get('bollDailyGap', '--'),
                'bollWeeklyGap': it.get('bollWeeklyGap', '--'),
            })

        bear_etfs = []
        for i, it in enumerate(f_bear):
            pr, ch = _parse_price(it['p'])
            bear_etfs.append({
                'rank': i+1,
                'strength': '{:+.2f}%'.format(it['slp']),
                'maCount': it['cnt'],
                'name': _parse_name(it['n']),
                'code': it['s'],
                'price': pr,
                'change': ch,
                'bollDailyGap': it.get('bollDailyGap', '--'),
                'bollWeeklyGap': it.get('bollWeeklyGap', '--'),
            })

        bull_idx = []
        for i, it in enumerate(i_bull):
            _, ch = _parse_price(it['p'])
            bull_idx.append({
                'rank': i+1,
                'strength': '{:+.2f}%'.format(it['slp']),
                'maCount': it['cnt'],
                'name': _parse_name(it['n']),
                'code': it['s'],
                'change': ch,
                'bollDailyGap': it.get('bollDailyGap', '--'),
                'bollWeeklyGap': it.get('bollWeeklyGap', '--'),
            })

        bear_idx = []
        for i, it in enumerate(i_bear):
            _, ch = _parse_price(it['p'])
            bear_idx.append({
                'rank': i+1,
                'strength': '{:+.2f}%'.format(it['slp']),
                'maCount': it['cnt'],
                'name': _parse_name(it['n']),
                'code': it['s'],
                'change': ch,
                'bollDailyGap': it.get('bollDailyGap', '--'),
                'bollWeeklyGap': it.get('bollWeeklyGap', '--'),
            })

        total_etf = len(ContextInfo.my_stocks)
        t_now = time.time()
        data = {
            'updateTime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t_now)),
            'nextScan': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t_now + 300)),
            'summary': {
                'bullCount': len(f_bull),
                'bullPct': '{:.1f}%'.format(len(f_bull)/total_etf*100) if total_etf else '0%',
                'bearCount': len(f_bear),
                'bearPct': '{:.1f}%'.format(len(f_bear)/total_etf*100) if total_etf else '0%',
                'totalScanned': total_etf,
            },
            'bullETFs': bull_etfs,
            'bearETFs': bear_etfs,
            'bullIndices': bull_idx,
            'bearIndices': bear_idx,
        }

        data_dir = 'D:/1.work/project/agu-web2/data'
        _os.makedirs(data_dir, exist_ok=True)

        js_path = data_dir + '/etf_scan.js'
        with open(js_path, 'w', encoding='utf-8') as jf:
            jf.write('var ETF_MATRIX_DATA = ')
            _json.dump(data, jf, ensure_ascii=False)
            jf.write(';')

        json_path = data_dir + '/etf_scan.json'
        with open(json_path, 'w', encoding='utf-8') as jf:
            _json.dump(data, jf, ensure_ascii=False)

        # 上传到火山云服务器
        ssh_key = r'C:\Users\R7000P\.ssh\volcano'
        server = 'root@115.190.196.211:/var/www/agu-web2/data'

        kwargs = {}
        if hasattr(_sp, 'STARTUPINFO'):
            si = _sp.STARTUPINFO()
            si.dwFlags |= _sp.STARTF_USESHOWWINDOW
            si.wShowWindow = _sp.SW_HIDE
            kwargs['startupinfo'] = si
        if hasattr(_sp, 'CREATE_NO_WINDOW'):
            kwargs['creationflags'] = _sp.CREATE_NO_WINDOW

        for fname in ['etf_scan.js', 'etf_scan.json']:
            try:
                _sp.run(['scp', '-i', ssh_key, data_dir + '/' + fname, server + '/' + fname],
                        check=True, timeout=30, **kwargs)
            except Exception as e:
                print('[WARN] SCP {} 上传失败: {}'.format(fname, e))

        print('[{}] 本地写入 + 火山云上传 OK (ETF多头{} 空头{} | 指数多头{} 空头{})'.format(
            time.strftime('%H:%M:%S', time.localtime(t_now)),
            len(bull_etfs), len(bear_etfs), len(bull_idx), len(bear_idx)))
