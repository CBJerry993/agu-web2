"""
批量获取基金SYL_Y(今年来), 排序取Top100
"""
import winreg, requests, json, time, re
from concurrent.futures import ThreadPoolExecutor, as_completed

# Config
key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment')
APIKEY, _ = winreg.QueryValueEx(key, 'TTFUND_APIKEY')
URL = 'https://skills.tiantianfunds.com/ai-smart-skill-service/openapi/skill/invoke'
HEADERS = {'X-API-Key': APIKEY, 'Content-Type': 'application/json'}
OUTPUT = 'D:/1.work/project/agu-web2/scripts/top100_data.json'

# Step 1: Collect all unique fund codes
all_codes = set()

# 1a: CONDITION_SELECT
sort_columns = ['syl_sy', 'syl_try', 'syl_hy', 'syl_y']
page_types = [1, 2, 4, 6]
print("Collecting from CONDITION_SELECT...")
for sc in sort_columns:
    for pt in page_types:
        try:
            resp = requests.post(URL, headers=HEADERS, json={
                'skill_id': 'FUND_CONDITION_SELECT', '_skill_version': '1.0.0',
                'pageType': pt, 'page': 1, 'size': 50, 'sortColumn': sc
            }, timeout=30)
            body = resp.json().get('data',{}).get('raw_result',{}).get('body',{})
            for f in body.get('Data', []):
                all_codes.add(f['fundCode'])
            time.sleep(0.15)
        except Exception as e:
            pass

# 1b: GS145 report
print("Extracting from GS145 report...")
with open('D:/1.work/project/agu-web2/reports/gs_145fund_report.html', 'r', encoding='utf-8') as f:
    gs_codes = set(re.findall(r'fund\.eastmoney\.com/(\d+)\.html', f.read()))
    all_codes.update(gs_codes)

codes = list(all_codes)
print(f"Total unique codes: {len(codes)}")

# Step 2: Batch query FUND_BASE_INFOS
print("Batch querying FUND_BASE_INFOS for SYL_Y...")
results = {}

def get_info(code):
    try:
        resp = requests.post(URL, headers=HEADERS, json={
            'skill_id': 'FUND_BASE_INFOS', '_skill_version': '1.0.0',
            'fcode': code
        }, timeout=30)
        info = resp.json().get('data',{}).get('raw_result',{}).get('body',{}).get('data', [{}])[0]
        return code, info
    except Exception as e:
        return code, {'SHORTNAME': '', 'SYL_Y': '', 'error': str(e)}

with ThreadPoolExecutor(max_workers=5) as ex:
    futures = {ex.submit(get_info, c): c for c in codes}
    done = 0
    for f in as_completed(futures):
        code, info = f.result()
        results[code] = info
        done += 1
        if done % 50 == 0:
            print(f"  {done}/{len(codes)}")

print(f"  Done: {len(results)}")

# Step 3: Merge, sort, output
print("Sorting by SYL_Y...")
funds = []
for code, info in results.items():
    try:
        syl_y = float(info.get('SYL_Y', -999) or -999)
    except:
        syl_y = -999
    funds.append({
        'code': code,
        'name': info.get('SHORTNAME', ''),
        'fullname': info.get('FULLNAME', ''),
        'syl_y': info.get('SYL_Y', ''),
        'syl_y_val': syl_y,
        'syl_z': info.get('SYL_Z', ''),
        'syl_1n': info.get('SYL_1N', ''),
        'syl_2n': info.get('SYL_2N', ''),
        'syl_3n': info.get('SYL_3N', ''),
        'syl_6y': info.get('SYL_6Y', ''),
        'syl_jn': info.get('SYL_JN', ''),
        'syl_ln': info.get('SYL_LN', ''),
        'dwjz': info.get('DWJZ', ''),
        'jjgs': info.get('JJGS', ''),
        'fundtype': info.get('FUNDTYPE', ''),
        'ftype': info.get('FTYPE', ''),
        'sgzt': info.get('SGZT', ''),
        'rate': info.get('RATE', ''),
        'risklevel': info.get('RISKLEVEL', ''),
        'establishdate': info.get('ESTABDATE', ''),
        'fundsize': info.get('ENDNAV', ''),
    })

funds.sort(key=lambda x: x['syl_y_val'], reverse=True)
top100 = funds[:100]

print(f"\nTop 10 by YTD:")
for i, f in enumerate(top100[:10]):
    print(f"  #{i+1}: {f['code']} {f['name'][:30]} YTD={f['syl_y']}%")

print(f"YTD range: {top100[-1]['syl_y']}% ~ {top100[0]['syl_y']}%")

with open(OUTPUT, 'w', encoding='utf-8') as fp:
    json.dump(top100, fp, ensure_ascii=False, indent=2)
print(f"Saved {len(top100)} to {OUTPUT}")
