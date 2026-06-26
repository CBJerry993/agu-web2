"""
解析天天基金自选分组结果
"""
import json

with open(r"C:\Users\R7000P\.workbuddy\binaries\ttskill\result_groups.json", "r", encoding="utf-8") as f:
    result = json.load(f)

body = result["data"]["raw_result"]["body"]
groups_result = body.get("groups_result", {})

print("=" * 70)
print("你的天天基金自选分组结构")
print("=" * 70)

# 1. 自定义分组
custom_groups = groups_result.get("custom_groups", [])
print(f"\n【自定义分组】共 {len(custom_groups)} 个")
print("-" * 40)
if custom_groups:
    for g in custom_groups:
        print(f"  分组名: {g.get('groupname', '?')}")
        print(f"  分组ID: {g.get('groupid', '?')}")
        print(f"  基金数: {g.get('count', len(g.get('zxlist', [])))}")
        fund_list = g.get("zxlist", [])
        for f in fund_list:
            print(f"    [{f.get('fcode', '?')}] {f.get('shortname', '?')}")
        print()
else:
    print("  (无自定义分组)")

# 2. 默认分组（系统分组）
default_groups = groups_result.get("default_groups", {})
print(f"\n【默认系统分组】")
print("-" * 40)
for group_name, fund_list in default_groups.items():
    if fund_list:
        names = [f.get("shortname", "?") for f in fund_list]
        print(f"  {group_name}: {len(fund_list)}只 -> {', '.join(names[:5])}{'...' if len(names) > 5 else ''}")

# 3. 持仓分组
hold_group = groups_result.get("hold_group", [])
print(f"\n【持仓分组】共 {len(hold_group)} 只")
print("-" * 40)
for f in hold_group:
    print(f"  [{f.get('fcode', '?')}] {f.get('shortname', '?')}")

# 4. 按 groupid 统计
print(f"\n{'=' * 70}")
print("按 groupId 归类分析")
print("=" * 70)

# 从 query_result 中提取所有基金及其 groupid
query_result = body.get("query_result", {}).get("data", {}).get("zxActionResponse", {}).get("zxlist", [])
group_map = {}
for f in query_result:
    gid = f.get("groupid", -1)
    if gid not in group_map:
        group_map[gid] = []
    group_map[gid].append(f)

# 建立 groupid -> 分组名 映射
gid_name = {}
for g in custom_groups:
    gid_name[g.get("groupid")] = g.get("groupname", "?")

print(f"\n总基金数: {len(query_result)}")
for gid, funds in sorted(group_map.items()):
    gname = gid_name.get(gid, "默认分组(未归类)" if gid == -1 else f"未知分组({gid})")
    print(f"\n  groupId={gid} 「{gname}」 - {len(funds)}只:")
    for f in funds:
        print(f"    [{f['fcode']}] {f['shortname']}")
