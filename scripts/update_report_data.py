"""
Update report JSON data without WorkBuddy.

The HTML files under reports/ are templates. This script fetches current fund
returns/ranks from Eastmoney and rewrites:

- reports/gs145_data.json
- reports/qdii_data.json
- reports/top100_data.json
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
TODAY = _dt.date.today().strftime("%Y-%m-%d")

API = "https://fund.eastmoney.com/data/rankhandler.aspx"
TTFUND_API = "https://skills.tiantianfunds.com/ai-smart-skill-service/openapi/skill/invoke"
HEADERS = {
    "User-Agent": "Mozilla/5.0 Chrome/120",
    "Referer": "https://fund.eastmoney.com/data/fundranking.html",
}
TTFUND_PERIOD_FIELDS = {
    "w1": "Z",
    "m1": "M",
    "m3": "Q",
    "m6": "HY",
    "ytd": "SY",
    "y1": "Y",
    "y2": "TWY",
}

PERIODS = [
    ("w1", "zzf", "近1周"),
    ("m1", "1yzf", "近1月"),
    ("m3", "3yzf", "近3月"),
    ("m6", "6yzf", "近6月"),
    ("ytd", "jnzf", "今年来"),
    ("y1", "1nzf", "近1年"),
    ("y2", "2nzf", "近2年"),
]
RET_INDEX = {"w1": 7, "m1": 8, "m3": 9, "m6": 10, "y1": 11, "y2": 12, "ytd": 14}
FUND_TYPES = [
    ("gp", "股票型"),
    ("hh", "混合型"),
    ("zs", "指数/ETF"),
    ("qdii", "QDII/境外"),
    ("zq", "债券型"),
    ("bb", "保本型"),
    ("fof", "FOF"),
    ("hb", "货币型"),
    ("all", "其他"),
]
TYPE_TO_FT = {
    "股票": "gp",
    "混合": "hh",
    "指数": "zs",
    "ETF": "zs",
    "QDII": "qdii",
    "境外": "qdii",
    "债": "zq",
    "FOF": "fof",
    "货币": "hb",
}
PAGE_CACHE: dict[tuple[str, str, int], tuple[list[list[str]], int]] = {}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_rankhandler_entries(text: str) -> tuple[list[list[str]], int]:
    match = re.search(r"datas:\[(.*?)\],", text, re.DOTALL)
    if not match:
        return [], 0

    entries: list[str] = []
    current = ""
    in_quote = False
    for ch in match.group(1):
        if ch == '"':
            if in_quote:
                entries.append(current)
                current = ""
            in_quote = not in_quote
        elif in_quote:
            current += ch

    total = 0
    for key in ("allRecords", "total"):
        total_match = re.search(rf"{key}:(\d+)", text)
        if total_match:
            total = int(total_match.group(1))
            break

    return [entry.split(",") for entry in entries], total


def fetch_page(ft: str, sc: str, page: int, page_size: int = 200) -> tuple[list[list[str]], int]:
    cache_key = (ft, sc, page)
    if cache_key in PAGE_CACHE:
        return PAGE_CACHE[cache_key]

    params = {
        "op": "ph",
        "dt": "kf",
        "ft": ft,
        "sc": sc,
        "st": "desc",
        "pi": str(page),
        "pn": str(page_size),
        "dx": "1",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=20) as response:
        text = response.read().decode("utf-8", errors="replace")
    result = parse_rankhandler_entries(text)
    PAGE_CACHE[cache_key] = result
    return result


def type_to_ft(type_label: str | None) -> str:
    label = type_label or ""
    for keyword, ft in TYPE_TO_FT.items():
        if keyword in label:
            return ft
    return "all"


def fetch_fund_dataset(
    target_codes: set[str],
    top_n: int | None = None,
    type_by_code: dict[str, str] | None = None,
) -> tuple[list[dict], dict]:
    """Return latest returns/ranks for target codes.

    If top_n is provided, the target list is replaced with the latest top N by YTD.
    """
    if top_n is not None:
        fields, _ = fetch_page("all", "jnzf", 1, top_n)
        target_codes = {row[0] for row in fields if len(row) > 14}

    funds: dict[str, dict] = {}
    ranks: dict[str, dict[str, dict]] = {period: {} for period, _, _ in PERIODS}

    for period, sc, _label in PERIODS:
        ft_targets: dict[str, set[str]] = defaultdict(set)
        if type_by_code:
            for code in target_codes:
                ft_targets[type_to_ft(type_by_code.get(code))].add(code)
        else:
            for code in target_codes:
                ft_targets["unknown"].add(code)

        scan_plan = [(ft, label, ft_targets[ft]) for ft, label in FUND_TYPES if ft in ft_targets]
        if "unknown" in ft_targets:
            scan_plan = [(ft, label, set(ft_targets["unknown"])) for ft, label in FUND_TYPES]

        for ft, type_label, wanted in scan_plan:
            remaining = set(wanted)
            if not remaining:
                continue

            page = 1
            while True:
                try:
                    rows, total = fetch_page(ft, sc, page)
                except Exception as exc:
                    print(f"[WARN] {period}/{ft}/p{page}: {exc}")
                    break

                if not rows:
                    break

                for idx, row in enumerate(rows):
                    if len(row) < 15:
                        continue
                    code = row[0]
                    if code not in target_codes:
                        continue

                    fund = funds.setdefault(
                        code,
                        {
                            "code": code,
                            "name": row[1],
                            "type": type_label,
                            "returns": {},
                        },
                    )
                    if ft != "all":
                        fund["type"] = type_label
                    for pkey, _psc, _plabel in PERIODS:
                        ret_idx = RET_INDEX[pkey]
                        if len(row) > ret_idx and row[ret_idx] not in ("", "--"):
                            fund["returns"][pkey] = row[ret_idx]

                    if code not in ranks[period]:
                        rank = (page - 1) * 200 + idx + 1
                        ranks[period][code] = {"rank": rank, "total": total, "type": type_label}
                    remaining.discard(code)

                if not remaining:
                    break
                if total <= page * 200:
                    break
                if page >= 60:
                    break
                page += 1
                time.sleep(0.03)

            time.sleep(0.03)

    ordered = [funds[code] for code in target_codes if code in funds]
    for fund in ordered:
        fund["ytdValue"] = parse_float(fund["returns"].get("ytd", "-999"))
    ordered.sort(key=lambda item: item["ytdValue"], reverse=True)
    return ordered, ranks


def parse_float(value: str | int | float | None) -> float:
    try:
        return float(str(value).replace("%", "").replace("+", ""))
    except Exception:
        return -999.0


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[idx : idx + size] for idx in range(0, len(items), size)]


def ttfund_condition_select(payload: dict) -> list[dict]:
    api_key = os.environ.get("TTFUND_APIKEY")
    if not api_key:
        raise RuntimeError("TTFUND_APIKEY is not set")

    body = {
        "skill_id": "FUND_CONDITION_SELECT",
        "_skill_version": "1.2.0",
        "pageType": 1,
        "rankSy": "1",
        **payload,
    }
    request = urllib.request.Request(
        TTFUND_API,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
            "User-Agent": HEADERS["User-Agent"],
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        result = json.loads(response.read().decode("utf-8", errors="replace"))

    raw_body = result.get("data", {}).get("raw_result", {}).get("body", {})
    return raw_body.get("Data") or raw_body.get("data") or []


def normalize_ttfund_item(item: dict) -> dict:
    info = item.get("info") or {}
    code = str(item.get("fundCode") or info.get("FCODE") or "").zfill(6)
    returns: dict[str, str] = {}
    for period, field in TTFUND_PERIOD_FIELDS.items():
        value = info.get(f"SYL_{field}")
        if value not in (None, ""):
            returns[period] = str(value)
    return {
        "code": code,
        "name": item.get("fundName") or info.get("SHORTNAME") or code,
        "type": item.get("ftype") or "其他",
        "returns": returns,
        "_ttfund_info": info,
    }


def fetch_ttfund_dataset(target_codes: set[str], top_n: int | None = None) -> tuple[list[dict], dict]:
    items: list[dict] = []
    if top_n is not None:
        page_num = 50
        page = 1
        while len(items) < top_n:
            batch = ttfund_condition_select(
                {
                    "pageIndex": page,
                    "pageNum": page_num,
                    "orderField": "5_10_-1",
                }
            )
            if not batch:
                break
            items.extend(batch)
            if len(batch) < page_num:
                break
            page += 1
        items = items[:top_n]
    else:
        codes = sorted(target_codes)
        for batch in chunked(codes, 50):
            items.extend(
                ttfund_condition_select(
                    {
                        "pageIndex": 1,
                        "pageNum": len(batch),
                        "fcode": ",".join(batch),
                    }
                )
            )
            time.sleep(0.05)

    funds: list[dict] = []
    ranks: dict[str, dict[str, dict]] = {period: {} for period, _, _ in PERIODS}
    for item in items:
        fund = normalize_ttfund_item(item)
        if not fund["code"]:
            continue
        info = fund.pop("_ttfund_info")
        funds.append(fund)
        for period, field in TTFUND_PERIOD_FIELDS.items():
            rank = parse_float(info.get(f"SYLRANK_{field}"))
            total = parse_float(info.get(f"SYLFNUM_{field}"))
            if rank != -999.0 and total != -999.0:
                ranks[period][fund["code"]] = {
                    "rank": int(rank),
                    "total": int(total),
                    "type": fund.get("type", "其他"),
                }

    funds.sort(key=lambda item: parse_float(item["returns"].get("ytd")), reverse=True)
    return funds, ranks


def fill_w1_ranks_from_eastmoney(
    funds: list[dict],
    ranks: dict[str, dict[str, dict]],
    type_by_code: dict[str, str] | None = None,
) -> None:
    target_codes = {fund["code"] for fund in funds if fund["code"] not in ranks.get("w1", {})}
    if not target_codes:
        return

    try:
        rows, total = fetch_page("all", "zzf", 1, 20000)
    except Exception as exc:
        print(f"[WARN] w1/all: {exc}")
        rows, total = [], 0

    for idx, row in enumerate(rows):
        if len(row) < 15:
            continue
        code = row[0]
        if code not in target_codes:
            continue
        ranks.setdefault("w1", {})[code] = {
            "rank": idx + 1,
            "total": total or len(rows),
            "type": "全部",
        }
        target_codes.discard(code)

    if not target_codes:
        return

    inferred_type_by_code = {fund["code"]: fund.get("type", "") for fund in funds}
    if type_by_code:
        inferred_type_by_code.update(type_by_code)

    ft_targets: dict[str, set[str]] = defaultdict(set)
    for code in target_codes:
        ft_targets[type_to_ft(inferred_type_by_code.get(code))].add(code)

    scan_plan = [(ft, label, ft_targets[ft]) for ft, label in FUND_TYPES if ft in ft_targets]
    if not scan_plan:
        scan_plan = [(ft, label, set(target_codes)) for ft, label in FUND_TYPES]

    for ft, type_label, wanted in scan_plan:
        remaining = set(wanted)
        if not remaining:
            continue

        page = 1
        while True:
            try:
                rows, total = fetch_page(ft, "zzf", page)
            except Exception as exc:
                print(f"[WARN] w1/{ft}/p{page}: {exc}")
                break

            if not rows:
                break

            for idx, row in enumerate(rows):
                if len(row) < 15:
                    continue
                code = row[0]
                if code not in remaining:
                    continue

                ranks.setdefault("w1", {})[code] = {
                    "rank": (page - 1) * 200 + idx + 1,
                    "total": total,
                    "type": type_label,
                }
                remaining.discard(code)

            if not remaining:
                break
            if total <= page * 200:
                break
            if page >= 60:
                break
            page += 1
            time.sleep(0.03)


def fetch_latest_fund_dataset(
    target_codes: set[str],
    top_n: int | None = None,
    type_by_code: dict[str, str] | None = None,
) -> tuple[list[dict], dict]:
    try:
        funds, ranks = fetch_ttfund_dataset(target_codes, top_n=top_n)
        fill_w1_ranks_from_eastmoney(funds, ranks, type_by_code=type_by_code)
        return funds, ranks
    except Exception as exc:
        print(f"[WARN] TTFUND API unavailable, falling back to Eastmoney: {exc}")
        return fetch_fund_dataset(target_codes, top_n=top_n, type_by_code=type_by_code)


def parse_funds_from_sections(html: str) -> list[dict]:
    funds: list[dict] = []
    type_label = "其他"
    token_re = re.compile(r'<span class="type-badge">([^<]+)</span>|<tr[^>]*>\s*<td class="col-fund">(.*?)</td>', re.DOTALL)
    for match in token_re.finditer(html):
        if match.group(1):
            type_label = re.sub(r"\s*·.*$", "", match.group(1)).strip()
            continue

        cell = match.group(2) or ""
        codes = re.findall(r"fund\.eastmoney\.com/(\d+)\.html", cell)
        name_match = re.search(r'<span class="fname">(.*?)</span>', cell, re.DOTALL)
        if not codes or not name_match:
            continue
        name = re.sub(r"<.*?>", "", name_match.group(1)).strip()
        funds.append({"codes": codes, "code": codes[0], "name": name, "type": type_label})
    return funds


def parse_qdii_funds(tbody_html: str) -> list[dict]:
    funds: list[dict] = []
    for match in re.finditer(r'<td class="col-fund">(.*?)</td>', tbody_html, re.DOTALL):
        cell = match.group(1)
        code_match = re.search(r"fund\.eastmoney\.com/(\d+)\.html", cell)
        name_match = re.search(r'<span class="fname">(.*?)</span>', cell, re.DOTALL)
        if not code_match or not name_match:
            continue
        funds.append(
            {
                "code": code_match.group(1),
                "codes": [code_match.group(1)],
                "name": re.sub(r"<.*?>", "", name_match.group(1)).strip(),
                "type": "QDII/境外",
            }
        )
    return funds


def classify_fund(fund: dict, ranks: dict) -> str:
    top_50 = 0
    bottom_50 = 0
    short_term_top_30 = True
    code = fund["code"]
    for period, _sc, _label in PERIODS:
        rank_info = ranks.get(period, {}).get(code)
        if not rank_info or not rank_info.get("rank") or not rank_info.get("total"):
            continue
        percentile = rank_info["rank"] / rank_info["total"]
        if percentile <= 0.5:
            top_50 += 1
            if period in ("w1", "m1", "m3") and percentile > 0.3:
                short_term_top_30 = False
        else:
            bottom_50 += 1
    if top_50 >= 5 and short_term_top_30:
        return "夯"
    if top_50 >= 5:
        return "顶"
    if top_50 >= 4:
        return "人上人"
    if bottom_50 >= 5:
        return "拉"
    return "NPC"


def pct_label(rank: int, total: int) -> tuple[str, str]:
    pct = rank / total if total else 1
    label = f"前{round(pct * 100)}%" if pct < 0.5 else f"后{round(pct * 100)}%"
    css = "pct-top" if pct <= 0.1 else ("pct-good" if pct < 0.5 else ("pct-mid" if pct <= 0.75 else "pct-bad"))
    return label, css


def return_span(value: str | None) -> str:
    parsed = parse_float(value)
    if parsed == -999.0:
        return '<span class="na">--</span>'
    sign = "+" if parsed > 0 else ""
    css = "up" if parsed > 0 else ("dn" if parsed < 0 else "neutral")
    return f'<span class="{css}">{sign}{parsed:.2f}%</span>'


def period_cell(code: str, value: str | None, period: str, ranks: dict) -> str:
    html = f'<td><div class="cell-ret">{return_span(value)}</div>'
    rank_info = ranks.get(period, {}).get(code)
    if rank_info and rank_info.get("rank") and rank_info.get("total"):
        label, css = pct_label(rank_info["rank"], rank_info["total"])
        html += f'<div class="cell-rank"><span class="rank-num">{rank_info["rank"]} | {rank_info["total"]}</span></div>'
        html += f'<div class="cell-pct"><span class="{css}">{label}</span></div>'
    elif rank_info and rank_info.get("total"):
        html += f'<div class="cell-rank"><span class="rank-num">-- | {rank_info["total"]}</span></div><div class="cell-pct"><span class="na">--</span></div>'
    else:
        html += '<div class="cell-rank"><span class="rank-num">-- | --</span></div><div class="cell-pct"><span class="na">--</span></div>'
    return html + "</td>"


def fund_links(fund: dict) -> str:
    return "/".join(
        f'<a href="https://fund.eastmoney.com/{code}.html" target="_blank">{code}</a>'
        for code in fund.get("codes", [fund["code"]])
    )


def build_row(fund: dict, idx: int, ranks: dict) -> str:
    cls = "row-even" if idx % 2 == 0 else "row-odd"
    returns = fund.get("returns", {})
    cells = "".join(period_cell(fund["code"], returns.get(period), period, ranks) for period, _sc, _label in PERIODS)
    return f'<tr class="{cls}"><td class="col-fund">{fund_links(fund)} <span class="fname">{fund["name"]}</span></td>{cells}</tr>'


def build_sections(funds: list[dict], ranks: dict, include_sort_marker: bool = False) -> tuple[str, str]:
    cats: dict[str, list[dict]] = defaultdict(list)
    for fund in funds:
        fund["cat"] = classify_fund(fund, ranks)
        cats[fund["cat"]].append(fund)

    cat_cfg = {
        "夯": ("c0392b", "#fdecea", "≥5周期前50%且近1W/1M/3M全前30%", "顶尖"),
        "顶": ("e67e22", "#fef3e2", "≥5周期前50%", "优秀"),
        "人上人": ("27ae60", "#e8f5e9", "≥4周期前50%", "良好"),
        "拉": ("8e44ad", "#f3e5f5", "≥5周期后50%", "警示"),
        "NPC": ("888", "#f5f5f5", "其他", "普通"),
    }
    sections: list[str] = []
    for cat in ("夯", "顶", "人上人", "拉", "NPC"):
        grouped: dict[str, list[dict]] = defaultdict(list)
        for fund in cats.get(cat, []):
            grouped[fund.get("type", "其他")].append(fund)
        if not grouped:
            continue

        color, bg, desc, label = cat_cfg[cat]
        type_blocks: list[str] = []
        for type_label, group in grouped.items():
            rows = "".join(build_row(fund, idx, ranks) for idx, fund in enumerate(group))
            ytd_head = ' class="sort-col">今年来 ▼' if include_sort_marker else ">今年来"
            type_blocks.append(
                f'''<span class="type-badge">{type_label} · {len(group)}只</span>
<div class="table-wrap">
<table class="fund-table">
<thead><tr><th>基金（代码+简称）</th><th>近1周</th><th>近1月</th><th>近3月</th><th>近6月</th><th{ytd_head}</th><th>近1年</th><th>近2年</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</div>'''
            )

        sections.append(
            f'''
  <div class="section-title" style="border-left-color:#{color}">
    {cat} · {label}
    <span class="badge" style="background:{bg};color:#{color}">{len(cats[cat])}只 · {desc}</span>
  </div>
  <div class="type-blocks">{''.join(type_blocks)}</div>'''
        )

    stats_html = f'''    <div class="stat-card blue">
      <div class="val">{len(funds)}</div><div class="lbl">基金总数</div>
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
    return stats_html, "".join(sections)


def merge_source_metadata(source: list[dict], fetched: list[dict]) -> list[dict]:
    fetched_by_code = {fund["code"]: fund for fund in fetched}
    merged: list[dict] = []
    for item in source:
        fetched_item = fetched_by_code.get(item["code"])
        if not fetched_item:
            merged.append({**item, "returns": {}})
            continue
        merged.append({**fetched_item, "codes": item.get("codes", [item["code"]]), "name": item.get("name") or fetched_item["name"], "type": item.get("type") or fetched_item.get("type", "其他")})
    return merged


def update_gs145() -> None:
    current = read_json(REPORTS / "gs145_data.json")
    source = parse_funds_from_sections(current.get("sectionsHtml", ""))
    type_by_code = {item["code"]: item.get("type", "") for item in source}
    fetched, ranks = fetch_latest_fund_dataset({item["code"] for item in source}, type_by_code=type_by_code)
    funds = merge_source_metadata(source, fetched)
    stats, sections = build_sections(funds, ranks)
    write_json(
        REPORTS / "gs145_data.json",
        {
            "updateDate": TODAY,
            "generateDate": TODAY,
            "fundCount": len(funds),
            "statsHtml": stats,
            "sectionsHtml": sections,
        },
    )
    print(f"GS145 updated: {len(funds)} funds")


def update_top100() -> None:
    source, ranks = fetch_latest_fund_dataset(set(), top_n=100)
    stats, sections = build_sections(source, ranks, include_sort_marker=True)
    current = read_json(REPORTS / "top100_data.json")
    write_json(
        REPORTS / "top100_data.json",
        {
            "updateDate": TODAY,
            "generateDate": TODAY,
            "fundCount": len(source),
            "statsHtml": stats,
            "sectionsHtml": sections,
            "holdingsHtml": current.get("holdingsHtml", ""),
        },
    )
    print(f"Top100 updated: {len(source)} funds")


def build_qdii_tbody(funds: list[dict], ranks: dict) -> str:
    rows: list[str] = []
    for idx, fund in enumerate(funds, start=1):
        cls = "row-even" if idx % 2 else "row-odd"
        returns = fund.get("returns", {})
        ytd = parse_float(returns.get("ytd"))
        ytd_text = f"{'+' if ytd > 0 else ''}{ytd:.2f}%" if ytd != -999 else "--"
        cells = "".join(period_cell(fund["code"], returns.get(period), period, ranks) for period, _sc, _label in PERIODS)
        rows.append(
            f'''    <tr class="{cls}">
      <td>{idx}</td>
      <td class="col-fund">{fund_links(fund)} <span class="fname">{fund["name"]}</span><span class="fund-code">{fund["code"]}</span></td>
      <td class="ret-ytd">{ytd_text}</td>
      {cells}
    </tr>'''
        )
    return "\n".join(rows)


def update_qdii() -> None:
    current = read_json(REPORTS / "qdii_data.json")
    source = parse_qdii_funds(current.get("tbodyHtml", ""))
    type_by_code = {item["code"]: item.get("type", "QDII/境外") for item in source}
    fetched, ranks = fetch_latest_fund_dataset({item["code"] for item in source}, type_by_code=type_by_code)
    funds = merge_source_metadata(source, fetched)
    funds.sort(key=lambda item: parse_float(item.get("returns", {}).get("ytd")), reverse=True)
    up_count = sum(1 for item in funds if parse_float(item.get("returns", {}).get("w1")) > 0)
    down_count = sum(1 for item in funds if parse_float(item.get("returns", {}).get("w1")) < 0)
    top3 = [{"code": item["code"], "name": item["name"], "ytd": item.get("returns", {}).get("ytd", "")} for item in funds[:3]]
    stats = f'''    <div class="stat-card blue">
      <div class="val">{len(funds)}</div>
      <div class="lbl">基金总数</div>
    </div>
    <div class="stat-card red">
      <div class="val">{up_count}</div>
      <div class="lbl">近1周上涨</div>
    </div>
    <div class="stat-card green">
      <div class="val">{down_count}</div>
      <div class="lbl">近1周下跌</div>
    </div>'''
    write_json(
        REPORTS / "qdii_data.json",
        {
            "updateDate": TODAY,
            "generateDate": TODAY,
            "fundCount": len(funds),
            "statsHtml": stats,
            "tbodyHtml": build_qdii_tbody(funds, ranks),
            "holdingsHtml": current.get("holdingsHtml", ""),
            "top3": top3,
        },
    )
    print(f"QDII updated: {len(funds)} funds")


def main() -> None:
    targets = set(sys.argv[1:] or ["gs145", "qdii", "top100"])
    if "gs145" in targets:
        update_gs145()
    if "qdii" in targets:
        update_qdii()
    if "top100" in targets:
        update_top100()


if __name__ == "__main__":
    main()
