"""Fetch PE TTM for all stocks in holdings_analysis.json via iwencai API."""
import json
import os
import secrets
import time
import urllib.request

API_URL = "https://openapi.iwencai.com/v1/query2data"
API_KEY = os.environ["IWENCAI_API_KEY"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def iwencai_query(query: str, limit: int = 50) -> list[dict]:
    """Call iwencai API and return datas list."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "X-Claw-Call-Type": "normal",
        "X-Claw-Skill-Id": "hithink-market-query",
        "X-Claw-Skill-Version": "1.0.0",
        "X-Claw-Plugin-Id": "none",
        "X-Claw-Plugin-Version": "none",
        "X-Claw-Trace-Id": secrets.token_hex(32),
    }
    payload = {"query": query, "page": "1", "limit": str(limit), "is_cache": "1", "expand_index": "true"}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result.get("datas", [])


def main():
    # Load stock codes from holdings_analysis.json
    ha_path = os.path.join(ROOT, "data", "holdings_analysis.json")
    with open(ha_path, "r", encoding="utf-8") as f:
        holdings = json.load(f)

    all_codes: list[str] = []
    for board in ("主板", "创业板", "科创板", "港股"):
        for s in holdings.get(board, []):
            code = s["code"]
            if code not in all_codes:
                all_codes.append(code)

    print(f"Total unique stocks: {len(all_codes)}")

    # Batch query PE TTM (max 20 stocks per query to be safe)
    pe_data: dict[str, float | None] = {}
    batch_size = 20
    for i in range(0, len(all_codes), batch_size):
        batch = all_codes[i:i + batch_size]
        q = " ".join(batch) + " 市盈率TTM"
        print(f"  Querying batch {i // batch_size + 1}: {len(batch)} stocks...")
        try:
            datas = iwencai_query(q, limit=50)
            for item in datas:
                code = item.get("股票代码", "")
                if "." in code:
                    code = code.split(".")[0]  # strip market suffix
                pe_val = item.get("最新市盈率ttm")
                if code and pe_val is not None:
                    pe_data[code] = round(float(pe_val), 2)
            print(f"    Got {len(datas)} results, {sum(1 for d in datas if d.get('股票代码','').split('.')[0] in batch)} matched")
        except Exception as e:
            print(f"    ERROR: {e}")
            # Try individual queries for failed batch
            for code in batch:
                try:
                    datas = iwencai_query(f"{code} 市盈率TTM", limit=5)
                    for item in datas:
                        raw = item.get("股票代码", "")
                        c = raw.split(".")[0] if "." in raw else raw
                        pe_val = item.get("最新市盈率ttm")
                        if c == code and pe_val is not None:
                            pe_data[code] = round(float(pe_val), 2)
                            break
                    time.sleep(0.3)
                except Exception as e2:
                    print(f"    {code} failed: {e2}")
        time.sleep(0.5)

    # Check coverage
    missing = [c for c in all_codes if c not in pe_data]
    print(f"\nCoverage: {len(pe_data)}/{len(all_codes)}")
    if missing:
        print(f"Missing: {missing}")

    # Generate JS file
    js_path = os.path.join(ROOT, "data", "pe_ttm.js")
    js_content = f"// PE TTM data from iwencai, generated {time.strftime('%Y-%m-%d %H:%M:%S')}\nvar PE_TTM_DATA = {json.dumps(pe_data, ensure_ascii=False)};"
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"\nWritten: {js_path}")

    # Also generate JSON
    json_path = os.path.join(ROOT, "data", "pe_ttm.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"date": time.strftime("%Y-%m-%d"), "data": pe_data}, f, ensure_ascii=False, indent=2)
    print(f"Written: {json_path}")


if __name__ == "__main__":
    main()
