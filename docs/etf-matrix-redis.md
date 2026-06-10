# ETF matrix Redis setup

## Redis key

Use this key for the latest ETF matrix payload:

```text
agu:etf_matrix:latest
```

The value is the full JSON object currently written to `data/etf_scan.json`.

## Local iQuant environment

Set these as environment variables on the machine running iQuant:

```powershell
[Environment]::SetEnvironmentVariable("REDIS_URL", "redis://:YOUR_PASSWORD@YOUR_HOST:YOUR_PORT/0", "User")
[Environment]::SetEnvironmentVariable("ETF_MATRIX_REDIS_KEY", "agu:etf_matrix:latest", "User")
```

Restart iQuant after setting them.

## Netlify environment

In Netlify, set the same variables:

```text
REDIS_URL=redis://:YOUR_PASSWORD@YOUR_HOST:YOUR_PORT/0
ETF_MATRIX_REDIS_KEY=agu:etf_matrix:latest
```

Do not commit real Redis credentials to GitHub.

## iQuant publish snippet

After building `data`, writing `etf_scan.json`, and writing `etf_scan.js`, add:

```python
import sys as _sys

repo_scripts = 'D:/1.work/project/agu-web2/scripts'
if repo_scripts not in _sys.path:
    _sys.path.insert(0, repo_scripts)

from redis_etf_matrix import publish_etf_matrix

publish_etf_matrix(_json.dumps(data, ensure_ascii=False))
print('[{}] Redis -> agu:etf_matrix:latest'.format(time.strftime('%H:%M:%S', time.localtime(t_now))))
```
