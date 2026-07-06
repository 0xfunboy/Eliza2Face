# Security Notes

## Secrets

Never commit:

- Cloudflare `cert.pem`
- Cloudflare tunnel credential JSON files
- Cloudflare API tokens
- Caddyfile with production password hashes if you consider those sensitive
- TTS API key
- Basic auth passwords
- HuggingFace token

Use `.env`, a password manager, or machine-level service environment variables.

## Exposure Model

Public traffic terminates at Cloudflare and reaches this machine through `cloudflared` outbound tunnels.

No public FTP port is required.

SSH remains separate on the router mapping, using OpenSSH with public keys only.

## ImgChart

Upload is authenticated. Viewer is intentionally unauthenticated because Unreal must load it directly.

The upload server sanitizes filenames and only accepts image extensions.

## TTS

GUI and API are separated by hostname:

- GUI: Basic Auth
- API: Basic Auth plus `X-API-Key`
