"""
探测天天基金自选分组结构
调用 FUND_FAVOR_ZX 接口，打印完整的 groupList 和 zxlist 结构
"""
import os, json, requests

APIKEY = os.environ.get("TTFUND_APIKEY", "")
URL = "https://skills.tiantianfunds.com/ai-smart-skill-service/openapi/skill/invoke"

headers = {
    "X-API-Key": APIKEY,
    "Content-Type": "application/json"
}

payload = {
    "skill_id": "FUND_FAVOR_ZX",
    "_skill_version": "1.0.0",
    "zx_query": {}
}

print("=" * 60)
print("调用 FUND_FAVOR_ZX，获取自选分组结构...")
print("=" * 60)

resp = requests.post(URL, headers=headers, json=payload, timeout=30)
result = resp.json()

# 完整原始响应
print("\n【原始响应 - 根级别 key】")
print(json.dumps({k: type(v).__name__ for k, v in result.items()}, ensure_ascii=False, indent=2))

# 深入到 body
body = result.get("data", {}).get("raw_result", {}).get("body", {})
print("\n【body 的 key】")
print(json.dumps({k: type(v).__name__ for k, v in body.items()}, ensure_ascii=False, indent=2))

# ============ 核心：groupList ============
group_list = body.get("groupList", [])
print(f"\n{'=' * 60}")
print(f"【groupList】共 {len(group_list)} 个分组")
print(f"{'=' * 60}")

for i, g in enumerate(group_list):
    print(f"\n分组 {i+1}: {json.dumps(g, ensure_ascii=False, indent=2)}")

# ============ 自选基金列表 ============
# 可能在多个位置，逐一排查
for key in ["zxlist", "Data", "data", "funds"]:
    val = body.get(key, None)
    if val is not None:
        print(f"\n{'=' * 60}")
        print(f"【body.{key}】共 {len(val) if isinstance(val, list) else '非列表'} 条")
        print(f"{'=' * 60}")
        if isinstance(val, list) and len(val) > 0:
            print(f"第一条示例: {json.dumps(val[0], ensure_ascii=False, indent=2)}")

# 把完整响应写文件方便仔细看
output_file = "D:/1.work/project/agu-web2/data/favor_groups_raw.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\n完整原始响应已写入: {output_file}")
