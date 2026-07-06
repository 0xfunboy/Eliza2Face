# Deployment Guide

This repo is a clean source/documentation copy of the current Windows deployment. It is not a one-click installer yet, because production depends on local Windows services, Cloudflare tunnel credentials, and secrets that must not be committed.

## 1. Base Folders

Production uses:

```text
C:\Eliza2Face
C:\Eliza2Face\eliza2face
C:\Eliza2Face\venv
C:\Eliza2Face\tools\nssm.exe
C:\ImgChartUpload
C:\imgchart
```

## 2. TTS

Copy:

```text
src/tts/* -> C:\Eliza2Face\eliza2face\
```

Create a venv and install requirements. On the RTX 5060 Ti machine, use a CUDA-compatible PyTorch build.

The app must bind only to loopback:

```text
127.0.0.1:7870
```

Register `kokoro-tts` with NSSM and set:

```text
HF_HOME=C:\Eliza2Face\hf-cache
HF_HUB_DISABLE_SYMLINKS_WARNING=1
PYTHONUNBUFFERED=1
KOKORO_API_KEY=<secret>
```

Only set `HF_TOKEN` if you explicitly want it on the machine.

## 3. Caddy

Use `config/templates/Caddyfile.template` as a starting point.

Generate hashes:

```powershell
caddy hash-password --plaintext "<password>"
```

Production Caddy listens on `:8790`, receives HTTP from cloudflared, and proxies to:

```text
127.0.0.1:7870  TTS
127.0.0.1:8890  ImgChart
```

## 4. Cloudflare

Use the sanitized templates:

```text
config/templates/cloudflared-kokoro.yml
config/templates/cloudflared-imgchart.yml
```

Do not commit:

```text
*.json tunnel credentials
cert.pem
API tokens
```

If a DNS record already exists, update it to the tunnel CNAME rather than creating a duplicate.

## 5. ImgChart

Copy:

```text
src/imgchart/server.py -> C:\ImgChartUpload\server.py
scripts/windows/capture-wallboard.ps1 -> C:\ImgChartUpload\capture-wallboard.ps1
```

Then from an elevated shell:

```powershell
scripts\windows\install-imgchart-service.ps1
scripts\windows\create-wallboard-task.ps1
```

ImgChart writes uploaded images to:

```text
C:\imgchart
```

The wallboard screenshot task writes:

```text
C:\ImgChartUpload\wallboard.png
```

## 6. Verification

```powershell
Get-Service kokoro-tts,caddy-kokoro,cloudflared-kokoro,imgchart-upload,cloudflared-imgchart
curl.exe https://imgchart.airewardrop.xyz/latest
curl.exe -I https://imgchart.airewardrop.xyz/img/latest.jpg
curl.exe -u "upload:<password>" https://ftp.airewardrop.xyz/
```

Expected:

```text
ftp without auth -> 401
ftp with auth    -> 200
imgchart viewer  -> 200
```
