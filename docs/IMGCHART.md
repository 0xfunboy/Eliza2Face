# ImgChart Upload and Viewer

ImgChart replaces the old FTP-based image drop with HTTPS over Cloudflare Tunnel.

Production runtime:

- Service: `imgchart-upload`
- Local bind: `127.0.0.1:8890`
- Image directory: `C:\imgchart`
- Upload endpoint: `https://ftp.airewardrop.xyz`
- Unreal viewer endpoint: `https://imgchart.airewardrop.xyz`

## Upload

Upload is protected by HTTP Basic Auth at Caddy.

```powershell
curl.exe -u "upload:<UPLOAD_PASSWORD>" `
  -X PUT `
  --data-binary "@C:\path\chart.png" `
  "https://ftp.airewardrop.xyz/upload?filename=chart.png"
```

Supported extensions:

```text
.png .jpg .jpeg .webp .bmp .gif
```

Upload validation:

- minimum body size: 5 KB
- minimum dimensions: 320x180
- invalid JPEG/PNG signatures are rejected

This is intentional. It prevents placeholder payloads such as 1x1 PNGs or fake JPEG test blobs from being accepted as real charts.

## Viewer Behavior

The viewer supports both the new page and the legacy Unreal polling behavior.

New page:

```text
https://imgchart.airewardrop.xyz/
```

Behavior:

- displays `https://airdapp.airewardrop.xyz/wallboard` as the base page
- polls for a new image every second
- displays a new chart for 10 seconds
- returns to wallboard after 10 seconds

Legacy endpoints:

```text
/img/latest.jpg
/img/latest.png
/latest.jpg
/latest.png
/img/default.jpg
/img/default.png
```

Production note: Unreal also polls `/img/latest.jpg?t=...`. For compatibility, after the 10-second chart window expires, `/img/latest.jpg` returns the wallboard screenshot image instead of a transparent image.

## Wallboard Screenshot Fallback

Some Unreal/CEF paths do not render the live iframe correctly. The fallback is a screenshot of:

```text
https://airdapp.airewardrop.xyz/wallboard
```

Screenshot output:

```text
C:\ImgChartUpload\wallboard.png
```

It is refreshed every 3 minutes by the scheduled task:

```text
ImgChart_Wallboard_Capture
```

Scripts:

```text
scripts/windows/capture-wallboard.ps1
scripts/windows/run-capture-hidden.vbs
```

The scheduled task must launch the VBS wrapper with `wscript.exe`, not `powershell.exe` directly. This keeps the capture process fully headless on the streaming desktop.

## Local Checks

```powershell
Get-Service imgchart-upload,cloudflared-imgchart,caddy-kokoro
curl.exe https://imgchart.airewardrop.xyz/latest
curl.exe -I https://imgchart.airewardrop.xyz/img/latest.jpg
```
