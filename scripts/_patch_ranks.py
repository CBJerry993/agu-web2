import re

filepath = r'D:\1.work\project\agu-web2\scripts\update_report_data.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# ===== 1. Insert fill_ranks_from_eastmoney before fill_w1_ranks_from_eastmoney =====
marker = 'def fill_w1_ranks_from_eastmoney('
idx = content.find(marker)
if idx < 0:
    print('ERROR: Cannot find fill_w1_ranks_from_eastmoney')
    exit(1)

new_func = '''def fill_ranks_from_eastmoney(
    funds: list[dict],
    ranks: dict[str, dict[str, dict]],
    type_by_code: dict[str, str] | None = None,
    periods: list[tuple[str, str, str]] | None = None,
) -> None:
    """Fill missing rankings from Eastmoney rankhandler API for all periods.

    For each period where some funds lack ranking data, scan the Eastmoney
    rankhandler API pages to find those funds and compute their ranks.
    """
    target_periods = periods or PERIODS

    inferred_type_by_code = {fund["code"]: fund.get("type", "") for fund in funds}
    if type_by_code:
        inferred_type_by_code.update(type_by_code)

    for period_key, sort_col, period_label in target_periods:
        missing_codes = {
            fund["code"] for fund in funds
            if fund["code"] not in ranks.get(period_key, {})
        }
        if not missing_codes:
            continue

        print(f"[EM] Filling {period_label} ranks for {len(missing_codes)} funds...")

        # Step 1: Try fetching all funds in one big page
        try:
            rows, total = fetch_page("all", sort_col, 1, 20000)
        except Exception as exc:
            print(f"[WARN] {period_key}/all: {exc}")
            rows, total = [], 0

        found_in_all = set()
        for idx, row in enumerate(rows):
            if len(row) < 15:
                continue
            code = row[0]
            if code not in missing_codes:
                continue
            ranks.setdefault(period_key, {})[code] = {
                "rank": idx + 1,
                "total": total or len(rows),
                "type": "\u5168\u90e8",
            }
            found_in_all.add(code)
        missing_codes -= found_in_all

        if not missing_codes:
            continue

        # Step 2: Scan by fund type
        ft_targets: dict[str, set[str]] = defaultdict(set)
        for code in missing_codes:
            ft_targets[type_to_ft(inferred_type_by_code.get(code))].add(code)

        scan_plan = [(ft, label, ft_targets[ft]) for ft, label in FUND_TYPES if ft in ft_targets]
        if not scan_plan:
            scan_plan = [(ft, label, set(missing_codes)) for ft, label in FUND_TYPES]

        for ft, type_label, wanted in scan_plan:
            remaining = set(wanted)
            if not remaining:
                continue

            page = 1
            while True:
                try:
                    rows, total = fetch_page(ft, sort_col, page)
                except Exception as exc:
                    print(f"[WARN] {period_key}/{ft}/p{page}: {exc}")
                    break

                if not rows:
                    break

                for idx, row in enumerate(rows):
                    if len(row) < 15:
                        continue
                    code = row[0]
                    if code not in remaining:
                        continue

                    ranks.setdefault(period_key, {})[code] = {
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

            time.sleep(0.03)

        filled_count = len(found_in_all) + len({
            code for code in missing_codes if code in ranks.get(period_key, {})
        })
        total_missing = len(found_in_all) + len(missing_codes)
        print(f"[EM] {period_label}: filled {filled_count}/{total_missing}")


'''

content = content[:idx] + new_func + content[idx:]
print('1. Inserted fill_ranks_from_eastmoney before fill_w1_ranks_from_eastmoney')

# ===== 2. Replace fill_w1_ranks_from_eastmoney body with wrapper =====
# Find the function (now at a shifted position)
w1_marker = 'def fill_w1_ranks_from_eastmoney(\n'
w1_start = content.find(w1_marker)
# Find the next def after it
next_def = content.find('\ndef ', w1_start + 10)
if next_def < 0:
    next_def = len(content)

# Extract the old function text
old_w1 = content[w1_start:next_def]

new_w1 = '''def fill_w1_ranks_from_eastmoney(
    funds: list[dict],
    ranks: dict[str, dict[str, dict]],
    type_by_code: dict[str, str] | None = None,
) -> None:
    """Backward-compatible wrapper: fill only w1 rankings."""
    fill_ranks_from_eastmoney(funds, ranks, type_by_code=type_by_code, periods=[("w1", "zzf", "\u8fd11\u5468")])


'''

content = content[:w1_start] + new_w1 + content[next_def:]
print('2. Replaced fill_w1_ranks_from_eastmoney with wrapper')

# ===== 3. Change fill_w1 call in fetch_latest_fund_dataset to fill_ranks =====
old_call = 'fill_w1_ranks_from_eastmoney(funds, ranks, type_by_code=type_by_code)'
new_call = 'fill_ranks_from_eastmoney(funds, ranks, type_by_code=type_by_code)'

if old_call in content:
    content = content.replace(old_call, new_call)
    print('3. Updated call in fetch_latest_fund_dataset')
else:
    print('3. WARNING: Could not find fill_w1 call in fetch_latest_fund_dataset')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('All modifications applied!')
