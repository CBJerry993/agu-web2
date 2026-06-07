"""补全缺失排名 - 简化版"""
import requests, re, json, time, sys, traceback

try:
    INPUT = 'D:/1.work/project/agu-web2/scripts/em_top100_ranked.json'
    URL = 'https://fund.eastmoney.com/data/rankhandler.aspx'
    HEADERS = {'User-Agent': 'Mozilla/5.0 Chrome/120', 'Referer': 'https://fund.eastmoney.com/data/fundranking.html'}
    PERIOD_SC = {'w1':'zzf','m1':'1yzf','m3':'3yzf','m6':'6yzf','ytd':'jnzf','y1':'1nzf','y2':'2nzf'}
    FT = [('gp','gp'),('hh','hh'),('zs','zs'),('qdii','qdii')]
    PERIODS = ['w1','m1','m3','m6','ytd','y1','y2']

    with open(INPUT, 'r', encoding='utf-8') as f:
        data = json.load(f)

funds = data['funds']
rd = data['rank_data']

# Find missing combos (only where return EXISTS)
missing = []
for f in funds:
    code = f['code']
    for p in PERIODS:
        if code not in rd.get(p, {}):
            ret = f.get(p, '')
            if ret and str(ret).strip() not in ('', '--', '%'):
                missing.append((code, p))

print(f"Missing: {len(missing)} combos")
for code, p in missing[:5]:
    print(f"  {code} {p}")

# Search for each missing combo
found = 0
for code, p in missing:
    sc = PERIOD_SC[p]
    for ft, _ in FT:
        for page in range(1, 21):
            try:
                params = {'op':'ph','dt':'kf','ft':ft,'sc':sc,'st':'desc','pi':str(page),'pn':'200','dx':'1'}
                resp = requests.get(URL, params=params, headers=HEADERS, timeout=15)
                
                m = re.search(r'datas:\[(.*?)\],', resp.text, re.DOTALL)
                if not m: break
                
                entries = []
                cur = ''; iq = False
                for ch in m.group(1):
                    if ch == '"':
                        if iq: entries.append(cur); cur = ''
                        iq = not iq
                    elif iq: cur += ch
                
                all_m = re.search(r'allRecords:(\d+)', resp.text)
                total = int(all_m.group(1)) if all_m else 0
                
                for idx, entry in enumerate(entries):
                    ec = entry.split(',')[0]
                    if ec == code:
                        rank = (page - 1) * 200 + idx + 1
                        pv = rank / total
                        pct = f'前{round(pv*100)}%' if pv < 0.5 else f'后{round(pv*100)}%'
                        if p not in rd: rd[p] = {}
                        rd[p][code] = {'rank': rank, 'total': total, 'pct': pct}
                        found += 1
                        print(f'  OK {code} {p}: rank={rank}/{total} ({pct}) ft={ft} page={page}')
                        break
                else:
                    time.sleep(0.15)
                    continue
                break  # found, next combo
            except Exception as e:
                pass
            time.sleep(0.15)
        else:
            continue
        break  # found in this ft

# Save
with open(INPUT, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"\nFound {found}/{len(missing)} new rankings. Saved.")

except Exception as e:
    with open('D:/1.work/project/agu-web2/scripts/patch_error.txt', 'w') as ef:
        ef.write(traceback.format_exc())
    print(f"ERROR: {e}")
    sys.exit(1)
