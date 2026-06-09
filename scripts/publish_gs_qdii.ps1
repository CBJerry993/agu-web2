$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repo

$logDir = Join-Path $repo ".workbuddy"
$logPath = Join-Path $logDir "publish_reports_data.log"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Write-Log {
  param([string]$Message)
  $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  "$stamp $Message" | Tee-Object -FilePath $logPath -Append
}

$files = @(
  "pages/gs145.html",
  "pages/qdii.html",
  "pages/top100.html",
  "reports/gs_145fund_report.html",
  "reports/qdii_fund_report.html",
  "reports/top_100.html",
  "reports/gs145_data.json",
  "reports/qdii_data.json",
  "reports/top100_data.json"
)

Write-Log "Starting reports data publish"

$pythonCandidates = @(
  "C:\Users\R7000P\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe",
  "python",
  "py"
)
$python = $null
foreach ($candidate in $pythonCandidates) {
  try {
    $resolved = Get-Command $candidate -ErrorAction Stop
    $python = $resolved.Source
    break
  } catch {
  }
}
if (-not $python) {
  throw "Python not found. Cannot update report data."
}

Write-Log "Updating report JSON via $python"
$env:TTFUND_APIKEY = [Environment]::GetEnvironmentVariable("TTFUND_APIKEY", "User")
& $python (Join-Path $repo "scripts\update_report_data.py") 2>&1 | Tee-Object -FilePath $logPath -Append
if ($LASTEXITCODE -ne 0) {
  throw "Report JSON update failed with exit code $LASTEXITCODE"
}

git add -- $files

git diff --cached --quiet -- $files
if ($LASTEXITCODE -eq 0) {
  Write-Log "No report data changes to publish"
  exit 0
}

$date = Get-Date -Format "yyyy-MM-dd"
git commit -m "Update report data $date"
git pull --rebase --autostash origin main
git push

Write-Log "Published report data changes"
