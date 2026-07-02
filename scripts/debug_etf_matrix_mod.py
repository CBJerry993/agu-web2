# encoding: utf-8
"""
在原始 handlebar 中的 get_trend_info() 之前插入这段 debug 函数,
并在返回 BULL/BEAR 时调用它打印详细 MA 值和条件检查结果。

=== 使用方法 ===
1. 把 print_ma_detail() 函数复制到 init() 后面、handlebar() 里面 get_trend_info() 前面
2. 在 get_trend_info() 的 return 之前，当 trend 是 BULL 或 BEAR 时调用它
"""

# ========== 在 get_trend_info 前面插入这个函数 ==========
def print_ma_detail(code, trend, c_series, curr_p, ratio):
    """打印多头/空头 ETF 的均线排列细节"""
    if len(c_series) < 60:
        return
    m5  = c_series.tail(5).mean()
    m10 = c_series.tail(10).mean()
    m20 = c_series.tail(20).mean()
    m30 = c_series.tail(30).mean()
    m60 = c_series.tail(60).mean()
    p5  = c_series.iloc[:-1].tail(5).mean()
    p10 = c_series.iloc[:-1].tail(10).mean()

    name = ContextInfo.get_stock_name(code)
    tag = "BULL" if trend == "BULL" else "BEAR"

    print("\n" + "=" * 80)
    print("  [{}] {} {}  现价={:.4f} 涨跌={:+.2f}%".format(tag, code, name, curr_p, ratio))
    print("-" * 80)
    print("  MA5 ={:>10.4f}    MA10={:>10.4f}    MA20={:>10.4f}    MA30={:>10.4f}    MA60={:>10.4f}".format(m5, m10, m20, m30, m60))
    print("  p5  ={:>10.4f}    p10 ={:>10.4f}".format(p5, p10))
    print("-" * 80)

    # 逐项检查排列
    checks = [
        ("MA5  > MA10 ", m5, m10),
        ("MA10 > MA20 ", m10, m20),
        ("MA20 > MA30 ", m20, m30),
        ("MA30 > MA60 ", m30, m60),
        ("MA5  > p5   ", m5, p5),
        ("MA10 > p10  ", m10, p10),
    ]
    for label, a, b in checks:
        ok = a > b
        diff = a - b
        print("  {}: {:.4f} > {:.4f}  差值={:+.4f}  {}".format(label, a, b, diff, "[OK]" if ok else "[FAIL]"))

    cond_a = m5 > m10 > m20 > m30 > m60
    cond_b = m5 > p5 and m10 > p10
    print("-" * 80)
    print("  完整多头排列={} | m5>p5且m10>p10={} | 最终={}".format(cond_a, cond_b, tag))
    print("=" * 80)


# ========== 替换原来的 get_trend_info (在 handlebar 内部) ==========
# 原来的 get_trend_info 在原文约第 100 行附近，用下面这个替换：

def get_trend_info(code):
    if code not in data_dict or data_dict[code].empty:
        return "SIDE", 0, "0.000(0.00%)", 0.0
    c_series = data_dict[code]['close'].iloc[:-1]
    if len(c_series) < 60:
        return "SIDE", 0, "0.000(0.00%)", 0.0
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

    price_str = "{:.4f}({}{:.2f}%)".format(curr_p, '+' if ratio > 0 else '', ratio)

    trend = "SIDE"
    if (m[0] > m[1] > m[2] > m[3] > m[4]) and m[0] > p5 and m[1] > p10:
        trend = "BULL"
    elif (m[0] < m[1] < m[2] < m[3] < m[4]) and m[0] < p5 and m[1] < p10:
        trend = "BEAR"

    # ===== 新增：BULL/BEAR 时打印详细 MA 信息 =====
    if trend in ("BULL", "BEAR"):
        print_ma_detail(code, trend, c_series, curr_p, ratio)
    # ==============================================

    return trend, slope, price_str, curr_p
