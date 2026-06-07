import requests, re, json, time

INPUT = 'D:/1.work/project/agu-web2/scripts/em_top100_ranked.json'
URL = 'https://fund.eastmoney.com/data/rankhandler.aspx'
H = {'User-Agent': 'Mozilla/5.0 Chrome/120', 'Referer': 'https://fund.eastmoney.com/data/fundranking.html'}
PS = {'w1':'zzf','m1':'1yzf','m3':'3yzf','m6':'6yzf','ytd':'jnzf','y1':'1nzf','y2':'2nzf'}
FT = [('gp','gp'),('hh','hh'),('zs','zs'),('qdii','qdii')]
PERIODS = ['w1','m1','m3','m6','ytd','y1','y2']

data = json.load(open(INPUT, 'r', encoding='utf-8'))
funds = data['funds']
rd = data['rank_data']

missing = []
for f in funds:
    code = f['code']
    for p in PERIODS:
        if code not in rd.get(p,{}):
            ret = f.get(p,'')
            if ret and str(ret).strip() not in ('','--','%'):
                missing.append((code, p))

print(f'Missing combos: {len(missing)}')
found = 0
for i, (code, p) in enumerate(missing):
    sc = PS[p]
    done = False
    for ft, fn in FT:
        if done: break
        for pg in range(1, 21):
            try:
                resp = requests.get(URL, params={'op':'ph','dt':'kf','ft':ft,'sc':sc,'st':'desc','pi':str(pg),'pn':'200','dx':'1'}, headers=H, timeout=15)
                m = re.search(r'datas:\[(.*?)\],', resp.text, re.DOTALL)
                if not m: break
                entries = []; cur = ''; iq = False
                for ch in m.group(1):
                    if ch == '"':
                        if iq: entries.append(cur); cur = ''
                        iq = not iq
                    elif iq: cur += ch
                total = int((re.search(r'allRecords:(\d+)', resp.text) or [None, '0']).group(1))
                for idx, e in enumerate(entries):
                    if e.split(',')[0] == code:
                        rk = (pg-1)*200 + idx + 1
                        pv = rk / total
                        pct = f'前{round(pv*100)}%' if pv < 0.5 else f'后{round(pv*100)}%'
                        if p not in rd: rd[p] = {}
                        rd[p][code] = {'rank': rk, 'total': total, 'pct': pct}
                        found += 1
                        print(f'  [{i+1}/{len(missing)}] {code} {p}: rk={rk}/{total} {pct} ({fn} p{pg})')
                        done = True
                        break
                if done: break
                time.sleep(0.15)
            except:
                break
            time.sleep(0.15)

json.dump(data, open(INPUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'Done: {found}/{len(missing)} found. Saved.')
