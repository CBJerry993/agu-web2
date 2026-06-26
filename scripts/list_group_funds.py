"""
提取指定分组下的基金列表
"""
import json

with open(r"C:\Users\R7000P\.workbuddy\binaries\ttskill\result_groups.json", "r", encoding="utf-8") as f:
    result = json.load(f)

body = result["data"]["raw_result"]["body"]
groups_result = body["groups_result"]

# 找 持有新高 的 groupId
target_name = "持有新高"
target_gid = None
for g in groups_result["custom_groups"]:
    if g["groupName"] == target_name:
        target_gid = g["groupId"]
        break

# 从 query_result 中提取该分组的基金
query_result = body["query_result"]["data"]["zxActionResponse"]["zxlist"]
funds = [f for f in query_result if f.get("groupid") == target_gid]

print(f"分组「{target_name}」(groupId={target_gid})")
print(f"共 {len(funds)} 只基金\n")
for i, f in enumerate(funds, 1):
    print(f"{i:2}. [{f['fcode']}]  {f['shortname']}")
