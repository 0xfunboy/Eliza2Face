# Cloudflare Tunnel

Production uses Cloudflare Tunnel rather than opening HTTP/FTP ports on the router.

## Hostnames

```text
tts.airewardrop.xyz      -> kokoro tunnel
tts-api.airewardrop.xyz  -> kokoro tunnel
ftp.airewardrop.xyz      -> imgchart tunnel
imgchart.airewardrop.xyz -> imgchart tunnel
```

## Tunnel Configs

Do not commit tunnel credential JSON files.

Sanitized examples are in:

```text
config/templates/cloudflared-kokoro.yml
config/templates/cloudflared-imgchart.yml
```

## Important Operational Note

If a hostname already has a DNS record, `cloudflared tunnel route dns` may fail with Cloudflare error `1003`.

In that case update the existing DNS record to:

```text
<tunnel-id>.cfargotunnel.com
```

as a proxied CNAME.
