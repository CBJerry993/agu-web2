$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repo

$logDir = Join-Path $repo ".workbuddy"
$logPath = Join-Path $logDir "publish_gs_qdii.log"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Write-Log {
  param([string]$Message)
  $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  "$stamp $Message" | Tee-Object -FilePath $logPath -Append
}

$files = @(
  "pages/gs145.html",
  "pages/qdii.html",
  "reports/gs_145fund_report.html",
  "reports/qdii_fund_report.html"
)

Write-Log "Starting GS145/QDII publish"

git add -- $files

git diff --cached --quiet -- $files
if ($LASTEXITCODE -eq 0) {
  Write-Log "No GS145/QDII changes to publish"
  exit 0
}

$date = Get-Date -Format "yyyy-MM-dd"
git commit -m "Update GS145 and QDII reports $date"
git pull --rebase --autostash origin main
git push

Write-Log "Published GS145/QDII changes"
