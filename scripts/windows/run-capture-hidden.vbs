Set shell = CreateObject("WScript.Shell")
shell.Run "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy RemoteSigned -File ""C:\ImgChartUpload\capture-wallboard.ps1""", 0, True
