"""
稳健批量获取基金SYL_Y，排序取Top100（解决并发限流问题）
"""
import winreg, requests, json, time, re
from concurrent.futures import ThreadPoolExecutor, as_completed

key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment')
APIKEY, _ = winreg.QueryValueEx(key, 'TTFUND_APIKEY')
URL = 'https://skills.tiantianfunds.com/ai-smart-skill-service/openapi/skill/invoke'
HEADERS = {'X-API-Key': APIKEY, 'Content-Type': 'application/json'}
OUTPUT = 'D:/1.work/project/agu-web2/scripts/top100_data.json'

# Step 1: Collect codes
all_codes = set()

# 1a: CONDITION_SELECT
sort_cols = ['syl_sy', 'syl_try', 'syl_hy', 'syl_y']
for sc in sort_cols:
    for pt in [1, 2, 4, 6]:
        try:
            resp = requests.post(URL, headers=HEADERS, json={
                'skill_id': 'FUND_CONDITION_SELECT', '_skill_version': '1.0.0',
                'pageType': pt, 'page': 1, 'size': 50, 'sortColumn': sc
            }, timeout=30)
            body = resp.json().get('data',{}).get('raw_result',{}).get('body',{})
            for f in body.get('Data', []):
                all_codes.add(f['fundCode'])
            time.sleep(0.2)
        except: pass

# 1b: GS145
with open('D:/1.work/project/agu-web2/reports/gs_145fund_report.html', 'r', encoding='utf-8') as f:
    gs_codes = set(re.findall(r'fund\.eastmoney\.com/(\d+)\.html', f.read()))
    all_codes.update(gs_codes)

codes = list(all_codes)
print(f"Total codes: {len(codes)}")

# Step 2: Batch query with retry (2 workers to avoid rate limits)
print("Querying FUND_BASE_INFOS (2 concurrent, with retry)...")
results = {}
failed = []

def get_info_with_retry(code, max_retries=3):
    for attempt in range(max_retries):
        try:
            resp = requests.post(URL, headers=HEADERS, json={
                'skill_id': 'FUND_BASE_INFOS', '_skill_version': '1.0.0',
                'fcode': code
            }, timeout=30)
            data = resp.json()
            info = data.get('data',{}).get('raw_result',{}).get('body',{}).get('data', [{}])[0]
            syl_y = info.get('SYL_Y', '')
            if syl_y and syl_y.strip():
                return code, info, True
            else:
                # Empty SYL_Y, retry
                time.sleep(0.5)
        except Exception as e:
            time.sleep(0.5)
    return code, {}, False

with ThreadPoolExecutor(max_workers=2) as ex:
    futures = {ex.submit(get_info_with_retry, c): c for c in codes}
    done = 0
    success = 0
    for f in as_completed(futures):
        code, info, ok = f.result()
        if ok:
            results[code] = info
            success += 1
        else:
            failed.append(code)
        done += 1
        if done % 30 == 0:
            print(f"  {done}/{len(codes)} (success={success})")

print(f"Done: {success} valid, {len(failed)} failed")

# Step 3: Retry failed codes sequentially
if failed:
    print(f"Retrying {len(failed)} failed codes sequentially...")
    for i, code in enumerate(failed):
        ret_code, ret_info, ret_ok = get_info_with_retry(code, max_retries=2)
        if ret_ok:
            results[ret_code] = ret_info
        if i % 20 == 0:
            print(f"  retry: {i}/{len(failed)}")

# Step 4: Sort and output
funds = []
for code, info in results.items():
    try:
        syl_y = float(info.get('SYL_Y', -999) or -999)
    except:
        syl_y = -999
    
    # Only include if SYL_Y is valid (not -999 and not empty)
    syl_y_str = info.get('SYL_Y', '')
    if not syl_y_str or syl_y_str.strip() == '':
        continue
    
    funds.append({
        'code': code,
        'name': info.get('SHORTNAME', ''),
        'fullname': info.get('FULLNAME', ''),
        'syl_y': syl_y_str,
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
        'risklevel': info.get('RISKLEVEL', ''),
    })

funds.sort(key=lambda x: x['syl_y_val'], reverse=True)
top100 = funds[:100]

print(f"\nTotal valid funds: {len(funds)}, Top100: {len(top100)}")
print(f"YTD range: {top100[-1]['syl_y']}% ~ {top100[0]['syl_y']}%")

for i, f in enumerate(top100[:10]):
    print(f"  #{i+1}: {f['code']} {f['name'][:30]} YTD={f['syl_y']}%")

with open(OUTPUT, 'w', encoding='utf-8') as fp:
    json.dump(top100, fp, ensure_ascii=False, indent=2)
print(f"Saved to {OUTPUT}")
