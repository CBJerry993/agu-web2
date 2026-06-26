"""
近1月创近1年新高的基金查询脚本 (A类去重版, 按今年以来收益排序)

逻辑：
1. 调用 TTFUND_CONDITION_SELECT 获取股票型+混合型基金 top N（按近1年收益倒序）
2. 逐只调用 TTFUND_BASE_INFOS 获取近1年净值历史
3. 判断近1月内是否有净值创1年新高
4. 过滤掉 C/E/D/I 等非A份额，按基名唯一化
5. 按今年以来收益(SYL_Z)倒序排列，输出 Top 50
6. 保存JSON供页面消费
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta

TTSKILL_CMD = os.path.expandvars(
    r"%LOCALAPPDATA%\TTFund\ttskill-base\ttskill-base-win32-x64-0.1.1\bin\ttskill.cmd"
)


def ttfund_invoke(skill_id: str, payload: dict) -> dict:
    """调用 ttskill CLI 通用函数"""
    body_json = json.dumps(payload, ensure_ascii=False)
    env = os.environ.copy()
    env.pop("NODE_OPTIONS", None)
    try:
        proc = subprocess.run(
            [TTSKILL_CMD, "invoke", skill_id, "--action", "query", "--body", body_json],
            capture_output=True, text=True, encoding="utf-8", timeout=60, env=env,
        )
        if proc.returncode != 0:
            print(f"[ERR] {skill_id}: exit={proc.returncode} {proc.stderr[:200]}")
            return {}
        return json.loads(proc.stdout).get("data", {}).get("raw_result", {}).get("body", {})
    except Exception as e:
        print(f"[ERR] {skill_id}: {e}")
        return {}


def query_funds_all(page_index: int, top_n: int = 50) -> list[dict]:
    """查询全类型基金列表(不分rsfType), 按近1年收益倒序, 支持翻页"""
    body = {
        "pageIndex": page_index,
        "pageNum": top_n,
        "orderField": "5_6_-1",  # 近1年收益率倒序
        "establishPeriod": "2",   # 成立满1年
        "abnormal": "2",          # 不排除异常值(避免误杀正常高波动基金如001170)
        "isSale": "1",            # 代销
        "rankSy": "1",            # 外透排行
    }
    raw = ttfund_invoke("TTFUND_CONDITION_SELECT", body)
    data = raw.get("Data") or raw.get("data") or []
    # 只保留股票型(001)和混合型(002)
    filtered = []
    for f in data:
        info = f.get("info") or {}
        ftype = str(info.get("FUNDTYPE") or "")
        if ftype in ("001", "002"):
            filtered.append(f)
    print(f"  page {page_index}: {len(data)} returned, {len(filtered)} kept (stock/hybrid only)")
    return filtered


def get_nav_history(fcode: str) -> list[dict]:
    """获取基金近1年净值历史"""
    body = {"fcode": fcode, "nav_range": "n"}
    raw = ttfund_invoke("TTFUND_BASE_INFOS", body)
    if not raw:
        return []
    expansion = raw.get("expansion", {})
    comprehensive = expansion.get("comprehensive_info", {})
    nav_history = comprehensive.get("nav_history", {})
    items = nav_history.get("items", [])
    return items


def find_new_highs(items: list[dict]) -> list[tuple[str, float]]:
    """
    在净值列表中找出近1月内创1年新高的记录。
    返回 [(日期, 累计净值), ...]
    """
    if not items:
        return []

    parsed = []
    for item in items:
        date_str = item.get("FSRQ", "")
        ljjz = item.get("LJJZ", "")
        if not date_str or not ljjz:
            continue
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            nav = float(ljjz)
            parsed.append((date, nav, date_str))
        except (ValueError, TypeError):
            continue

    if len(parsed) < 2:
        return []

    parsed.sort(key=lambda x: x[0])

    one_month_ago = parsed[-1][0] - timedelta(days=35)

    new_highs = []
    for i, (date, nav, date_str) in enumerate(parsed):
        if date < one_month_ago:
            continue
        one_year_before = date - timedelta(days=370)
        max_in_year = -float("inf")
        for j, (d2, n2, _) in enumerate(parsed):
            if one_year_before <= d2 < date:
                if n2 > max_in_year:
                    max_in_year = n2
        if nav > max_in_year:
            new_highs.append((date_str, nav))

    return new_highs


def get_ytd_return(item: dict) -> float:
    """从条件选基结果中提取今年以来收益率(SYL_SY)"""
    info = item.get("info") or {}
    val = info.get("SYL_SY") or ""
    try:
        return float(val)
    except (ValueError, TypeError):
        return -9999


def get_year_return(item: dict) -> float:
    """从条件选基结果中提取近1年收益率"""
    info = item.get("info") or {}
    val = info.get("SYL_Y") or ""
    try:
        return float(val)
    except (ValueError, TypeError):
        return -9999


def calc_ytd_from_nav(items: list[dict]) -> float:
    """从净值历史列表中计算今年以来收益率(LJJZ 累计净值)"""
    if not items:
        return -9999
    # 找出2026年第一天的净值
    year_start_nav = None
    latest_item = items[-1]
    try:
        latest_nav = float(latest_item.get("LJJZ", 0))
    except (ValueError, TypeError):
        return -9999

    for item in items:
        date_str = item.get("FSRQ", "")
        if date_str.startswith("2026-01"):
            try:
                year_start_nav = float(item.get("LJJZ", 0))
            except (ValueError, TypeError):
                continue
            break  # 第一个2026年的净值就是年初净值
    # 如果没有2026-01的数据，试2026-02
    if not year_start_nav:
        for item in items:
            date_str = item.get("FSRQ", "")
            if date_str.startswith("2026-02"):
                try:
                    year_start_nav = float(item.get("LJJZ", 0))
                except (ValueError, TypeError):
                    continue
                break

    if not year_start_nav or year_start_nav <= 0:
        return -9999

    return ((latest_nav - year_start_nav) / year_start_nav) * 100


def get_fund_name(item: dict) -> str:
    info = item.get("info") or {}
    return info.get("SHORTNAME") or item.get("fundName") or ""


def get_fund_code(item: dict) -> str:
    info = item.get("info") or {}
    code = str(info.get("FCODE") or item.get("fundCode") or "").zfill(6)
    return code


_SHARE_SUFFIXES = frozenset(("A", "C", "E", "D", "I", "H", "Y", "O"))


def is_a_share(name: str) -> bool:
    if not name:
        return False
    suffix = name[-1]
    if suffix == "A":
        return True
    if suffix in _SHARE_SUFFIXES:
        return False
    return True


def extract_base_name(name: str) -> str:
    if not name:
        return ""
    if name[-1] in _SHARE_SUFFIXES:
        return name[:-1].rstrip()
    return name.strip()


def main():
    print("=" * 60)
    print("查询近1月创1年新高的基金 (按今年以来收益排序)")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # 1. 获取全类型基金, Python侧按FUNDTYPE过滤股票型+混合型, 取Top100
    print("\n[1/3] 获取基金列表(全类型, 翻页取Top100)...")
    all_funds = []
    seen = set()
    for pg in (1, 2):
        page_funds = query_funds_all(pg, 50)
        for f in page_funds:
            code = get_fund_code(f)
            if code not in seen:
                seen.add(code)
                all_funds.append(f)

    all_funds.sort(key=get_year_return, reverse=True)
    candidates = all_funds[:100]
    print(f"\n  去重后共 {len(all_funds)} 只, 取前 {len(candidates)} 只作为候选")

    # 同时建立 代码→YTD 映射 (从CONDITION_SELECT的SYL_SY)
    ytd_map = {}
    for f in candidates:
        code = get_fund_code(f)
        ytd_map[code] = get_ytd_return(f)

    # 2. 逐个查净值
    print("\n[2/3] 逐个查询净值历史...")
    # tuple: (code, name, year_return, ytd_return, new_high_date, new_high_nav, cur_date, cur_nav, pct_from_high)
    qualifying = []
    for idx, fund in enumerate(candidates):
        code = get_fund_code(fund)
        name = get_fund_name(fund)
        year_ret = get_year_return(fund)
        ytd_ret = ytd_map.get(code, -9999)
        print(f"  [{idx+1}/{len(candidates)}] {code} {name} (近1年:{year_ret:+.2f}% YTD:{ytd_ret:+.2f}%)...", end=" ")

        items = get_nav_history(code)
        if not items:
            print("无净值数据")
            continue

        new_highs = find_new_highs(items)
        if not new_highs:
            print("无新高")
            continue

        latest_high = new_highs[-1]

        last_item = items[-1]
        cur_date = last_item.get("FSRQ", "")
        cur_nav_str = last_item.get("LJJZ", "")
        try:
            cur_nav = float(cur_nav_str)
        except (ValueError, TypeError):
            print(f"异常: {cur_nav_str}")
            continue

        high_nav = latest_high[1]
        pct_from_high = ((cur_nav - high_nav) / high_nav) * 100

        # YTD优先用CONDITION_SELECT的SYL_SY，缺失时从净值历史兜底
        if ytd_ret <= -9998:
            ytd_ret = calc_ytd_from_nav(items)

        print(f"[OK] 新高! 日期={latest_high[0]} YTD={ytd_ret:+.2f}%")
        qualifying.append((code, name, year_ret, ytd_ret, latest_high[0], high_nav,
                           cur_date, cur_nav, pct_from_high))

    print(f"\n  净值查询完成, 共 {len(qualifying)} 只基金创1年新高")

    # A类去重 + 基名唯一化
    print("\n  --- A类去重 ---")
    a_only = [f for f in qualifying if is_a_share(f[1])]
    print(f"  过滤C/E/D/I类: {len(qualifying)} → {len(a_only)}")

    base_name_map: dict[str, tuple] = {}
    for f in a_only:
        base = extract_base_name(f[1])
        if base not in base_name_map or f[3] > base_name_map[base][3]:  # 保留YTD最高的
            base_name_map[base] = f

    deduped = list(base_name_map.values())
    # 按今年以来收益倒序
    deduped.sort(key=lambda x: x[3], reverse=True)
    print(f"  基名去重: {len(a_only)} → {len(deduped)}")

    # 3. 输出结果
    top50 = deduped[:50]
    print("\n" + "=" * 130)
    print(f"[3/3] 结果: 近1月创1年新高的基金 (A类, 按YTD排序, Top {len(top50)})")
    print("=" * 130)

    print(f"\n{'序号':<4} {'代码':<8} {'名称':<38} {'YTD收益':<11} {'近1年收益':<11} {'当前日期':<11} {'当前净值':<10} {'新高日期':<11} {'新高净值':<10} {'距新高':<8}")
    print("-" * 130)
    for i, (code, name, year_ret, ytd_ret, high_date, high_nav, cur_date, cur_nav, pct) in enumerate(top50, 1):
        ytd_str = f"{ytd_ret:+.2f}%"
        yr_str = f"{year_ret:+.2f}%"
        nav_str = f"{cur_nav:.4f}"
        high_nav_str = f"{high_nav:.4f}"
        pct_str = f"{pct:+.2f}%"
        print(f"{i:<4} {code:<8} {name:<38} {ytd_str:<11} {yr_str:<11} {cur_date:<11} {nav_str:<10} {high_date:<11} {high_nav_str:<10} {pct_str:<8}")

    print(f"\n共 {len(top50)} 只符合条件的A类基金")

    # 保存JSON
    output = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "funds": []
    }
    for code, name, year_ret, ytd_ret, high_date, high_nav, cur_date, cur_nav, pct in top50:
        output["funds"].append({
            "code": code,
            "name": name,
            "ytd_return": round(ytd_ret, 2),
            "year_return": round(year_ret, 2),
            "high_date": high_date,
            "high_nav": round(high_nav, 4),
            "cur_date": cur_date,
            "cur_nav": round(cur_nav, 4),
            "pct_from_high": round(pct, 2),
        })

    json_path = os.path.join(os.path.dirname(__file__), "..", "data", "new_high_funds.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n已保存JSON: {json_path}")

    # 同时保存一份JS变量版本
    js_path = os.path.join(os.path.dirname(__file__), "..", "data", "new_high_funds.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("var NEW_HIGH_FUNDS_DATA = ")
        f.write(json.dumps(output, ensure_ascii=False))
        f.write(";")
    print(f"已保存JS: {js_path}")


if __name__ == "__main__":
    main()
