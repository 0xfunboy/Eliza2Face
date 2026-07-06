param(
    [string]$TaskName = "ImgChart_Wallboard_Capture",
    [string]$ScriptPath = "C:\ImgChartUpload\capture-wallboard.ps1",
    [string]$HiddenWrapperPath = "C:\ImgChartUpload\run-capture-hidden.vbs",
    [int]$Minutes = 3
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $HiddenWrapperPath)) {
    $wrapper = 'Set shell = CreateObject("WScript.Shell")' + [Environment]::NewLine +
        'shell.Run "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy RemoteSigned -File ""' + $ScriptPath + '""", 0, True'
    Set-Content -LiteralPath $HiddenWrapperPath -Value $wrapper -Encoding ASCII
}

$taskCommand = "wscript.exe `"$HiddenWrapperPath`""
schtasks /Create /TN $TaskName /SC MINUTE /MO $Minutes /TR $taskCommand /F
schtasks /Run /TN $TaskName
