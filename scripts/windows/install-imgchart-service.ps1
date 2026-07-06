param(
    [string]$InstallDir = "C:\ImgChartUpload",
    [string]$ImageDir = "C:\imgchart",
    [int]$Port = 8890
)

$ErrorActionPreference = "Stop"

$nssm = "C:\Eliza2Face\tools\nssm.exe"
$python = "C:\Program Files\Python312\python.exe"
if (-not (Test-Path $python)) {
    $python = "C:\Eliza2Face\venv\Scripts\python.exe"
}

if (-not (Test-Path $nssm)) {
    throw "NSSM not found at $nssm"
}
if (-not (Test-Path $python)) {
    throw "Python not found"
}

New-Item -ItemType Directory -Force -Path $InstallDir, "$InstallDir\logs", $ImageDir | Out-Null

if (Get-Service imgchart-upload -ErrorAction SilentlyContinue) {
    & $nssm stop imgchart-upload
    & $nssm remove imgchart-upload confirm
}

& $nssm install imgchart-upload $python "$InstallDir\server.py"
& $nssm set imgchart-upload AppDirectory $InstallDir
& $nssm set imgchart-upload DisplayName "ImgChart Upload Endpoint"
& $nssm set imgchart-upload Start SERVICE_AUTO_START
& $nssm set imgchart-upload AppStdout "$InstallDir\logs\out.log"
& $nssm set imgchart-upload AppStderr "$InstallDir\logs\err.log"
& $nssm set imgchart-upload AppRotateFiles 1
& $nssm set imgchart-upload AppEnvironmentExtra `
    "IMGCHART_DIR=$ImageDir" `
    "IMGCHART_HOST=127.0.0.1" `
    "IMGCHART_PORT=$Port" `
    "IMGCHART_DISPLAY_SECONDS=10" `
    "IMGCHART_WALLBOARD_URL=https://airdapp.airewardrop.xyz/wallboard" `
    "IMGCHART_WALLBOARD_IMAGE=$InstallDir\wallboard.png" `
    "PYTHONUNBUFFERED=1"
& $nssm set imgchart-upload AppExit Default Restart
& $nssm start imgchart-upload
