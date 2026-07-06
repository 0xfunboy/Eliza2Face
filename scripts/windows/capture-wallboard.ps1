$ErrorActionPreference = "Continue"
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$url = "https://airdapp.airewardrop.xyz/wallboard"
$out = "C:\ImgChartUpload\wallboard.png"
$tmp = "C:\ImgChartUpload\wallboard.tmp.png"
$profile = "C:\ImgChartUpload\edge-profile"
New-Item -ItemType Directory -Force -Path (Split-Path $out), $profile | Out-Null
Remove-Item $tmp -Force -ErrorAction SilentlyContinue
$args = @(
  "--headless=new",
  "--disable-gpu",
  "--hide-scrollbars",
  "--no-first-run",
  "--window-size=1920,1080",
  "--virtual-time-budget=15000",
  "--user-data-dir=$profile",
  "--screenshot=$tmp",
  $url
)
$p = Start-Process -FilePath $edge -ArgumentList $args -PassThru -WindowStyle Hidden
if (-not $p.WaitForExit(60000)) {
  try { $p.Kill() } catch {}
  Write-Output "FAILED timeout $(Get-Date -Format s)" | Out-File "C:\ImgChartUpload\logs\wallboard-capture.log" -Append
  exit 1
}
if ((Test-Path $tmp) -and ((Get-Item $tmp).Length -gt 50000)) {
  Move-Item -Force $tmp $out
  Write-Output "OK $(Get-Date -Format s) bytes=$((Get-Item $out).Length)" | Out-File "C:\ImgChartUpload\logs\wallboard-capture.log" -Append
} else {
  Write-Output "FAILED small-or-missing $(Get-Date -Format s)" | Out-File "C:\ImgChartUpload\logs\wallboard-capture.log" -Append
  exit 1
}
