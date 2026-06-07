"""
获取全市场今年以来收益Top100基金
Step 1: CONDITION_SELECT 拉取广泛基金池 (近6月排序)
Step 2: FUND_BASE_INFOS 批量获取今年来收益
Step 3: 按SYL_Y排序,取Top100,输出JSON
"""
import winreg
import requests
import json
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# === Config ===
key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment')
APIKEY, _ = winreg.QueryValueEx(key, 'TTFUND_APIKEY')
URL = 'https://skills.tiantianfunds.com/ai-smart-skill-service/openapi/skill/invoke'
HEADERS = {'X-API-Key': APIKEY, 'Content-Type': 'application/json'}
OUTPUT = 'D:/1.work/project/agu-web2/scripts/top100_data.json'

# === Step 1: Get broad fund pool ===
print("Step 1: Fetching broad fund pool...")
all_funds = {}
page_types = [1, 2, 4, 6]  # 股票型,偏股混合,灵活配置,平衡混合
sort_columns = ['syl_hy', 'syl_y']  # 近6月, 近1年

for pt in page_types:
    for sc in sort_columns:
        for page in range(1, 4):  # pages 1-3
            try:
                resp = requests.post(URL, headers=HEADERS, json={
                    'skill_id': 'FUND_CONDITION_SELECT',
                    '_skill_version': '1.0.0',
                    'pageType': pt,
                    'page': page,
                    'size': 50,
                    'sortColumn': sc
                }, timeout=30)
                data = resp.json()
                funds = data.get('data',{}).get('raw_result',{}).get('body',{}).get('Data', [])
                for f in funds:
                    code = f['fundCode']
                    if code not in all_funds:
                        all_funds[code] = {
                            'code': code,
                            'name': f.get('fundName',''),
                            'fundtype': f.get('fundtype',''),
                            'sySyl': f.get('sySyl',''),
                            'trySyl': f.get('trySyl',''),
                            'hySyl': f.get('hySyl',''),
                            'yearSyl': f.get('yearSyl',''),
                            'daySyl': f.get('daySyl',''),
                            'company': f.get('company',''),
                            'sylRank_sy': f.get('sylRank_sy',''),
                            'sylNum_sy': f.get('sylNum_sy',''),
                            'sylRank_try': f.get('sylRank_try',''),
                            'sylNum_try': f.get('sylNum_try',''),
                            'sylRank_hy': f.get('sylRank_hy',''),
                            'sylNum_hy': f.get('sylNum_hy',''),
                            'sylRank_y': f.get('sylRank_y',''),
                            'sylNum_y': f.get('sylNum_y',''),
                        }
                print(f"  pt={pt} sc={sc} page={page}: got {len(funds)} funds, total unique={len(all_funds)}")
            except Exception as e:
                print(f"  pt={pt} sc={sc} page={page}: ERROR {e}")
            time.sleep(0.3)

print(f"\nTotal unique funds collected: {len(all_funds)}")

# === Step 2: Batch get YTD ===
print("\nStep 2: Fetching YTD (SYL_Y) for each fund...")
codes = list(all_funds.keys())
results = {}

def get_ytd(code):
    try:
        resp = requests.post(URL, headers=HEADERS, json={
            'skill_id': 'FUND_BASE_INFOS',
            '_skill_version': '1.0.0',
            'fcode': code
        }, timeout=30)
        data = resp.json()
        info = data.get('data',{}).get('raw_result',{}).get('body',{}).get('data', [{}])[0]
        return code, {
            'syl_y': info.get('SYL_Y', ''),       # 今年来
            'syl_z': info.get('SYL_Z', ''),       # 近1周
            'syl_2n': info.get('SYL_2N', ''),     # 近2年
            'syl_ln': info.get('SYL_LN', ''),     # 成立以来
            'dwjz': info.get('DWJZ', ''),         # 单位净值
            'jjgs': info.get('JJGS', ''),         # 基金公司
            'shortname': info.get('SHORTNAME', ''),# 基金简称
            'fullname': info.get('FULLNAME', ''),  # 基金全称
            'ftype': info.get('FTYPE', ''),        # 基金类型名称
            'sgzt': info.get('SGZT', ''),          # 申购状态
            'rate': info.get('RATE', ''),           # 费率
            'risklevel': info.get('RISKLEVEL', ''), # 风险等级
            'establishdate': info.get('ESTABDATE', ''), # 成立日期
            'fundsize': info.get('ENDNAV', ''),    # 基金规模
        }
    except Exception as e:
        return code, {'syl_y': '', 'error': str(e)}

# Use thread pool for parallel requests (5 concurrent)
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(get_ytd, code): code for code in codes}
    done = 0
    for future in as_completed(futures):
        code, data = future.result()
        results[code] = data
        done += 1
        if done % 20 == 0:
            print(f"  Progress: {done}/{len(codes)}")

print(f"  Done: {len(results)} funds queried")

# === Step 3: Merge and sort ===
print("\nStep 3: Merging data and sorting by YTD...")
merged = []
for code, fund in all_funds.items():
    ytd_info = results.get(code, {})
    syl_y = ytd_info.get('syl_y', '')
    try:
        syl_y_val = float(syl_y) if syl_y != '' and syl_y is not None else -999
    except (ValueError, TypeError):
        syl_y_val = -999
    
    merged.append({
        **fund,
        **ytd_info,
        'syl_y_val': syl_y_val
    })

# Sort by YTD descending
merged.sort(key=lambda x: x['syl_y_val'], reverse=True)

# Take top 100
top100 = merged[:100]

# === Output ===
print(f"\nTop 100 funds by YTD:")
for i, f in enumerate(top100[:10]):
    print(f"  #{i+1}: {f['code']} {f['name'][:30]} YTD={f.get('syl_y','?')}%")

# Save to JSON
output_data = []
for i, f in enumerate(top100):
    output_data.append({
        'rank': i+1,
        'code': f['code'],
        'name': f.get('shortname', f.get('name', '')),
        'fullname': f.get('fullname', f.get('name', '')),
        'ftype': f.get('ftype', ''),
        'fundtype': f.get('fundtype', ''),
        'company': f.get('jjgs', f.get('company', '')),
        'dwjz': f.get('dwjz', ''),
        'fundsize': f.get('fundsize', ''),
        'syl_y': f.get('syl_y', ''),          # 今年来
        'syl_z': f.get('syl_z', f.get('daySyl', '')),  # 近1周
        'sySyl': f.get('sySyl', ''),          # 近1月
        'trySyl': f.get('trySyl', ''),        # 近3月
        'hySyl': f.get('hySyl', ''),          # 近6月
        'yearSyl': f.get('yearSyl', ''),      # 近1年
        'syl_2n': f.get('syl_2n', ''),        # 近2年
        'syl_ln': f.get('syl_ln', ''),        # 成立以来
        'sylRank_sy': f.get('sylRank_sy', ''),
        'sylNum_sy': f.get('sylNum_sy', ''),
        'sylRank_try': f.get('sylRank_try', ''),
        'sylNum_try': f.get('sylNum_try', ''),
        'sylRank_hy': f.get('sylRank_hy', ''),
        'sylNum_hy': f.get('sylNum_hy', ''),
        'sylRank_y': f.get('sylRank_y', ''),
        'sylNum_y': f.get('sylNum_y', ''),
        'sgzt': f.get('sgzt', ''),
        'risklevel': f.get('risklevel', ''),
        'rate': f.get('rate', ''),
    })

with open(OUTPUT, 'w', encoding='utf-8') as f_out:
    json.dump(output_data, f_out, ensure_ascii=False, indent=2)

print(f"\nSaved {len(output_data)} funds to {OUTPUT}")
print(f"YTD range: {output_data[-1].get('syl_y','?')}% ~ {output_data[0].get('syl_y','?')}%")
