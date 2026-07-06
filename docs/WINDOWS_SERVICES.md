# Windows Services

Services are registered with NSSM.

## Services

```text
kokoro-tts
caddy-kokoro
cloudflared-kokoro
imgchart-upload
cloudflared-imgchart
```

## Status

```powershell
Get-Service kokoro-tts,caddy-kokoro,cloudflared-kokoro,imgchart-upload,cloudflared-imgchart
```

## Restart

```powershell
Restart-Service imgchart-upload -Force
Restart-Service caddy-kokoro -Force
Restart-Service cloudflared-imgchart -Force
```

When normal `Restart-Service` fails due to NSSM/service state quirks, use NSSM directly from an elevated shell:

```powershell
C:\Eliza2Face\tools\nssm.exe restart caddy-kokoro
C:\Eliza2Face\tools\nssm.exe restart imgchart-upload
C:\Eliza2Face\tools\nssm.exe restart cloudflared-imgchart
```

## Scheduled Tasks

```powershell
schtasks /Query /TN ImgChart_Wallboard_Capture /FO LIST
schtasks /Run /TN ImgChart_Wallboard_Capture
```

`ImgChart_Wallboard_Capture` should execute:

```text
wscript.exe "C:\ImgChartUpload\run-capture-hidden.vbs"
```

The VBS wrapper starts `capture-wallboard.ps1` hidden, avoiding visible PowerShell windows on the streaming desktop.

The TTS stack also has a daily restart task in production. Keep its schedule documented on the machine if recreated.
