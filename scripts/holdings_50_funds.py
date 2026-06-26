"""
50只新高基金持仓统计脚本
- 逐只调用 TTFUND_HOLDING_INFO 获取前十大重仓
- 股票出现次数 +1，统计频次
- 分主板/创业板/科创板/其他 展示，每板块 Top10，频次>=3
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime

TTSKILL_CMD = os.path.expandvars(
    r"%LOCALAPPDATA%\TTFund\ttskill-base\ttskill-base-win32-x64-0.1.1\bin\ttskill.cmd"
)

# ─── 50 只新高基金代码（2026-06-16） ───
FUND_CODES = [
    "006502", "008326", "006265", "020899", "020691", "001956", "010013",
    "007817", "008382", "006081", "010391", "005825", "000411", "001877",
    "008086", "014191", "540010", "008889", "021933", "021988", "019454",
    "012696", "006751", "001105", "519935", "501201", "001048", "017488",
    "000697", "013242", "008009", "009891", "000688", "014736", "023407",
    "005310", "001040", "009491", "019071", "020775", "019236", "024069",
    "021532", "021718", "020839", "014854", "020356", "023828", "020639",
    "021893",
]


def invoke_holdings(fcode: str) -> list[dict]:
    """调用 TTFUND_HOLDING_INFO 获取前十大重仓"""
    body = json.dumps({"fund_id": fcode}, ensure_ascii=False)
    env = os.environ.copy()
    env.pop("NODE_OPTIONS", None)
    try:
        proc = subprocess.run(
            [TTSKILL_CMD, "invoke", "TTFUND_HOLDING_INFO", "--action", "query", "--body", body],
            capture_output=True, text=True, encoding="utf-8", timeout=30, env=env,
        )
        if proc.returncode != 0:
            print(f"    ERR: exit={proc.returncode} {proc.stderr[:100]}")
            return []
        raw = json.loads(proc.stdout)
        stock_list = (
            raw.get("data", {}).get("raw_result", {}).get("body", {})
               .get("data", {}).get("top_holdings", {}).get("stock", [])
        )
        return stock_list
    except Exception as e:
        print(f"    ERR: {e}")
        return []


def classify(code: str) -> str:
    """按代码前缀分类板块"""
    s = str(code)
    if re.match(r'^[A-Za-z]', s):
        return "其他"          # 美股/港股
    if s.startswith("688"):
        return "科创板"
    if s.startswith(("300", "301")):
        return "创业板"
    if s.startswith(("600", "601", "603", "605", "000", "001", "002", "003")):
        return "主板"
    return "其他"


def main():
    print("=" * 50)
    print("50只新高基金持仓统计")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    fund_names: dict[str, str] = {}
    stock_count = Counter()
    stock_names: dict[str, str] = {}

    ok, fail = 0, 0
    for i, code in enumerate(FUND_CODES):
        print(f"[{i+1:2d}/{len(FUND_CODES)}] {code}...", end=" ")
        stocks = invoke_holdings(code)
        if not stocks:
            print("无持仓数据")
            fail += 1
            continue

        print(f"{len(stocks)} stocks")
        for s in stocks:
            sc = s.get("GPDM", "")
            sn = s.get("GPJC", "")
            if sc:
                stock_count[sc] += 1
                stock_names[sc] = sn
        ok += 1

    print(f"\n完成: ok={ok} fail={fail} unique_stocks={len(stock_count)}")

    # 分类
    boards: dict[str, list[tuple[str, str, int]]] = {
        "主板": [], "创业板": [], "科创板": [], "其他": []
    }
    for sc, cnt in stock_count.most_common():
        board = classify(sc)
        boards[board].append((sc, stock_names.get(sc, ""), cnt))

    # 输出
    for board_name in ("主板", "创业板", "科创板", "其他"):
        items = [(c, n, cnt) for c, n, cnt in boards[board_name] if cnt >= 3]
        top10 = items[:10]
        print(f"\n{'─' * 40}")
        print(f"【{board_name}】共 {len(items)} 只 >=3, 展示 Top{min(10, len(top10))}")
        print(f"{'股票代码':<10} {'股票名称':<12} {'出现次数':<8}")
        print(f"{'─' * 30}")
        for c, n, cnt in top10:
            print(f"{c:<10} {n:<12} x{cnt}")
        if not top10:
            print("  (无符合条件的股票)")


if __name__ == "__main__":
    main()
