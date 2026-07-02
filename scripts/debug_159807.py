# encoding: utf-8
"""
独立调试脚本 — 检测 159807 的多头排列状态
复现 iQuant 策略中 get_trend_info() 的 MA 排列判断逻辑
"""
import requests
import pandas as pd
import numpy as np
from datetime import datetime

CODE = "159807"
SECID = "0.159807"   # SZ 交易所


def fetch_5min_kline(secid, count=80):
    """从东方财富拉取 5 分钟 K 线"""
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "5",
        "fqt": "0",
        "end": "20500101",
        "lmt": str(count),
    }
    resp = requests.get(url, params=params, timeout=15, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://quote.eastmoney.com/",
    })
    data = resp.json()
    if data.get("data") is None or data["data"].get("klines") is None:
        raise Exception(f"API 返回异常: {data}")

    klines = data["data"]["klines"]
    records = []
    for line in klines:
        parts = line.split(",")
        records.append({
            "time": parts[0],
            "open":   float(parts[1]),
            "close":  float(parts[2]),
            "high":   float(parts[3]),
            "low":    float(parts[4]),
            "volume": float(parts[5]),
        })
    return pd.DataFrame(records)


def check_trend(df):
    """完全复现原策略的 MA 排列判断"""
    close = df["close"].values

    # === 关键：c_series = data_dict[code]['close'].iloc[:-1]（去掉最后一根未完成 K 线）===
    c_series = pd.Series(close[:-1])
    print(f"  原始K线: {len(close)} 根, c_series(去掉末根): {len(c_series)} 根")

    if len(c_series) < 60:
        return "SIDE", f"数据不足 ({len(c_series)} < 60)"

    # --- 各周期均线 ---
    m5  = c_series.tail(5).mean()
    m10 = c_series.tail(10).mean()
    m20 = c_series.tail(20).mean()
    m30 = c_series.tail(30).mean()
    m60 = c_series.tail(60).mean()

    # --- p5 / p10（再往前推一根的均线）---
    p5  = c_series.iloc[:-1].tail(5).mean()
    p10 = c_series.iloc[:-1].tail(10).mean()

    # --- 斜率 ---
    prev5 = c_series.iloc[:-1].tail(5).mean()
    slope = (m5 - prev5) / prev5 * 100

    # --- 当前价 ---
    curr_price = close[-1]
    last_close = close[-2] if len(close) >= 2 else curr_price
    ratio = (curr_price - last_close) / last_close * 100 if last_close > 0 else 0.0

    # ======== 打印 ========
    print("=" * 80)
    print(f"  {CODE} 易方达中证科技50ETF — 多头排列独立检测")
    print(f"  数据范围: {df['time'].iloc[0]}  ~  {df['time'].iloc[-1]}")
    print(f"  检测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    print(f"\n  [均线值]")
    print(f"  MA5  = {m5:.4f}")
    print(f"  MA10 = {m10:.4f}")
    print(f"  MA20 = {m20:.4f}")
    print(f"  MA30 = {m30:.4f}")
    print(f"  MA60 = {m60:.4f}")

    print(f"\n  [前一期对比均线]")
    print(f"  p5 (c[:-1].tail(5))   = {p5:.4f}")
    print(f"  p10(c[:-1].tail(10))  = {p10:.4f}")

    print(f"\n  [多头排列条件 — 逐条检查]")
    cond_a = m5 > m10 > m20 > m30 > m60
    rows = [
        (f"MA5({m5:.4f}) > MA10({m10:.4f})", m5 > m10),
        (f"MA10({m10:.4f}) > MA20({m20:.4f})", m10 > m20),
        (f"MA20({m20:.4f}) > MA30({m30:.4f})", m20 > m30),
        (f"MA30({m30:.4f}) > MA60({m60:.4f})", m30 > m60),
    ]
    print(f"  条件1 (MA5>MA10>MA20>MA30>MA60): {'[PASS]' if cond_a else '[FAIL]'}")
    for txt, ok in rows:
        print(f"    {txt:55s} {'[OK]' if ok else '[NO]'}")

    cond_b = m5 > p5 and m10 > p10
    print(f"\n  条件2 (MA5>p5 且 MA10>p10): {'[PASS]' if cond_b else '[FAIL]'}")
    print(f"    MA5({m5:.4f}) > p5({p5:.4f}): {'[OK]' if m5 > p5 else '[NO]'}")
    print(f"    MA10({m10:.4f}) > p10({p10:.4f}): {'[OK]' if m10 > p10 else '[NO]'}")

    # --- 空头条件 ---
    cond_c = m5 < m10 < m20 < m30 < m60
    cond_d = m5 < p5 and m10 < p10
    print(f"\n  [空头对照] 完整空头: {'[YES]' if cond_c else '[NO]'}  |  m5<p5且m10<p10: {'[YES]' if cond_d else '[NO]'}")

    # --- 判定 ---
    if cond_a and cond_b:
        trend = "BULL"
    elif cond_c and cond_d:
        trend = "BEAR"
    else:
        trend = "SIDE"

    print(f"\n  {'='*40}")
    print(f"  >>> 最终判定: {trend} <<<")
    print(f"  {'='*40}")
    print(f"  斜率: {slope:+.2f}%")
    print(f"  当前价: {curr_price:.4f}  涨跌: {ratio:+.2f}%")

    # --- 最近 20 根 c_series 收盘价(可人工核对) ---
    print(f"\n  [c_series 最后 20 根收盘价 (索引=原始K线位置)]")
    tail20 = c_series.tail(20)
    total = len(c_series)
    for i, (idx, val) in enumerate(tail20.items()):
        bar_idx = total - 20 + i
        bar_time = df["time"].iloc[bar_idx]
        markers = []
        # p5: c_series[:-1].tail(5) → 倒数第6~第2根(0-based: -5 ~ -1 of c_series[... :-1])
        # p10: c_series[:-1].tail(10) → 倒数第11~第2根
        idx_from_end = total - 1 - bar_idx   # 0 = last, 1 = second last...
        if 1 <= idx_from_end <= 5:
            markers.append("p5")
        if 1 <= idx_from_end <= 10:
            markers.append("p10")
        m = ",".join(markers)
        print(f"  [{bar_idx:3d}] {bar_time}  close={val:.4f}  {m}")

    return trend


def main():
    print(f"\n{'#'*80}")
    print(f"#  159807 易方达中证科技50ETF — 多头排列独立检测")
    print(f"{'#'*80}\n")

    try:
        df = fetch_5min_kline(SECID, count=80)
        trend = check_trend(df)
        print(f"\n>>> 结论: 159807 当前趋势 = {trend}\n")
    except Exception as e:
        import traceback
        print(f"\n[ERROR] {e}")
        traceback.print_exc()
        print("\n提示: 如果 API 拉取失败，可能是网络问题或交易时段外无数据。")


if __name__ == "__main__":
    main()
