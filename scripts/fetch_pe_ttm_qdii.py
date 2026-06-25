"""Fetch PE TTM for QDII US holdings via iwencai API."""
import json
import os
import secrets
import time
import urllib.request

API_URL = "https://openapi.iwencai.com/v1/query2data"
API_KEY = os.environ["IWENCAI_API_KEY"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "data", "pe_ttm_qdii.js")


def iwencai_query(query: str, limit: int = 50) -> list[dict]:
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
    # Load existing to get stock codes
    existing: dict[str, float] = {}
    if os.path.exists(OUTPUT):
        with open(OUTPUT, "r", encoding="utf-8") as f:
            raw = f.read()
            raw = raw.replace("var PE_TTM_QDII = ", "").rstrip(";")
            existing = json.loads(raw)

    codes = list(existing.keys()) if existing else []
    if not codes:
        print("No existing codes found, nothing to update")
        return

    print(f"Updating PE TTM for {len(codes)} US stocks...")

    pe_data: dict[str, float] = {}
    batch_size = 15
    for i in range(0, len(codes), batch_size):
        batch = codes[i : i + batch_size]
        q = " ".join(batch) + " 最新市盈率ttm"
        try:
            datas = iwencai_query(q, limit=50)
            for item in datas:
                code = item.get("股票代码", "")
                if "." in code:
                    code = code.split(".")[0]
                pe_val = item.get("市盈率(pe,ttm)[20260624]")
                if code in codes and pe_val is not None:
                    pe_data[code] = round(float(pe_val), 2)
        except Exception as e:
            print(f"  Batch {i // batch_size + 1} ERROR: {e}")
        time.sleep(0.3)

    # Individual fallback
    for c in codes:
        if c not in pe_data:
            try:
                datas = iwencai_query(f"{c} 最新市盈率ttm", limit=5)
                for item in datas:
                    code = item.get("股票代码", "")
                    if "." in code:
                        code = code.split(".")[0]
                    pe_val = item.get("市盈率(pe,ttm)[20260624]")
                    if code == c and pe_val is not None:
                        pe_data[c] = round(float(pe_val), 2)
            except Exception as e:
                print(f"  {c} fallback ERROR: {e}")
            time.sleep(0.2)

    missing = [c for c in codes if c not in pe_data]
    print(f"Coverage: {len(pe_data)}/{len(codes)}")
    if missing:
        print(f"Missing: {missing}")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(f"var PE_TTM_QDII = {json.dumps(pe_data)};")
    print(f"Written: {OUTPUT}")


if __name__ == "__main__":
    main()
