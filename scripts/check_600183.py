"""查找持有生益科技(600183)的基金"""
import subprocess, json, os, time

TTSKILL = r'C:\Users\R7000P\AppData\Local\TTFund\ttskill-base\ttskill-base-win32-x64-0.1.1\bin\ttskill.cmd'
FUND_CODES = ['006502','008326','006265','020899','020691','001956','010013','007817','008382','006081',
              '010391','005825','000411','001877','008086','014191','540010','008889','021933','021988',
              '019454','012696','006751','001105','519935','501201','001048','017488','000697','013242',
              '008009','009891','000688','014736','023407','005310','001040','009491','019071','020775',
              '019236','024069','021532','021718','020839','014854','020356','023828','020639','021893']
TARGET = '600183'

env = os.environ.copy()
env.pop('NODE_OPTIONS', None)
print('查找持有生益科技(600183)的基金...')
print()
found = []

for i, fcode in enumerate(FUND_CODES):
    body = json.dumps({'fund_id': fcode}, ensure_ascii=False)
    try:
        proc = subprocess.run(
            [TTSKILL, 'invoke', 'TTFUND_HOLDING_INFO', '--action', 'query', '--body', body],
            capture_output=True, text=True, encoding='utf-8', timeout=30, env=env,
        )
        if proc.returncode != 0:
            if '429' in proc.stderr:
                time.sleep(3)
                continue
            continue
        raw = json.loads(proc.stdout)
        data = raw.get('data', {}).get('raw_result', {}).get('body', {}).get('data', {})
        stocks = data.get('top_holdings', {}).get('stock', [])
        fname = data.get('info', {}).get('SHORTNAME', '') or ''

        for s in stocks:
            if s.get('GPDM') == TARGET:
                pct = s.get('PCTNV', '?')
                found.append((fcode, fname, pct))
                print(f'[{i+1:2d}/50] ✅ {fcode} {fname}  生益科技 占净值{pct}%')
                break
    except Exception as e:
        pass

print()
if found:
    print(f'共 {len(found)} 只基金持有生益科技:')
    for c, n, p in found:
        print(f'  {c} {n} ({p}%)')
else:
    print('未找到持有生益科技的基金')
