<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=160&section=header&text=Eliza2Face&fontSize=50&fontColor=fff&animation=fadeIn&fontAlignY=38&desc=Eliza2Face%20is%20a%20local%20Windows%20infrastructure%20for%20AI%20avatars%20and%20live...&descAlignY=60&descSize=14" width="100%"/>

<img src="https://skillicons.dev/icons?i=py,bash,unreal,cloudflare&theme=dark" alt="Tech stack"/>

</div>

# Eliza2Face

Eliza2Face is a local Windows infrastructure for AI avatars and live agents. It turns AI-generated text into Kokoro TTS voice, produces avatar-ready WAV files for Unreal Engine or Audio2Face, and exposes visual tools like ImgChart through Caddy and Cloudflare Tunnel.

## Current Production Shape

```text
Cloudflare Tunnel
  tts.airewardrop.xyz      -> Caddy :8790 -> 127.0.0.1:7870
  tts-api.airewardrop.xyz  -> Caddy :8790 -> 127.0.0.1:7870
  ftp.airewardrop.xyz      -> Caddy :8790 -> 127.0.0.1:8890
  imgchart.airewardrop.xyz -> Caddy :8790 -> 127.0.0.1:8890

Local services
  kokoro-tts
  caddy-kokoro
  cloudflared-kokoro
  imgchart-upload
  cloudflared-imgchart
```

## Repo Layout

```text
src/tts/                 Eliza2Face/Kokoro Gradio TTS app
src/imgchart/            Upload + viewer HTTP server
scripts/windows/         Windows helper scripts
config/templates/        Sanitized service/proxy/tunnel templates
docs/                    Deployment and operation notes
```

## Components

- **Kokoro / Eliza2Face TTS**: Gradio app running locally on `127.0.0.1:7870`, proxied by Caddy, exposed as `tts.airewardrop.xyz` and `tts-api.airewardrop.xyz`.
- **ImgChart**: HTTPS upload endpoint plus Unreal-compatible image viewer/fallback, writing to `C:\imgchart`, exposed as `ftp.airewardrop.xyz` and `imgchart.airewardrop.xyz`.
- **Wallboard fallback**: scheduled headless Edge screenshot capture for Unreal/CEF paths that cannot render the live wallboard iframe.

## Important

Secrets are intentionally not committed. Do not commit:

- Cloudflare tunnel credential JSON files
- `cert.pem`
- API tokens, passwords, HF tokens, or generated Caddy password hashes tied to production
- generated WAV/image output

## Documentation

- `docs/TTS.md`
- `docs/IMGCHART.md`
- `docs/WINDOWS_SERVICES.md`
- `docs/CLOUDFLARE.md`
- `docs/SECURITY.md`
- `docs/DEPLOYMENT.md`
