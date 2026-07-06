# TTS Service

The TTS service is the Gradio app in `src/tts/app.py`.

Production runtime:

- App directory: `C:\Eliza2Face\eliza2face`
- Venv: `C:\Eliza2Face\venv`
- Service: `kokoro-tts`
- Local bind: `127.0.0.1:7870`
- Public GUI: `https://tts.airewardrop.xyz`
- Public API: `https://tts-api.airewardrop.xyz`

## API Parameters

Voice, speed, and GPU usage are decided by the API request, not fixed in service configuration.

The Gradio endpoint accepts:

```text
text: string
voice: string, e.g. af_jessica
speed: float
use_gpu: bool
```

Language is implied by the voice prefix:

- `a...`: American English pipeline
- `b...`: British English pipeline

## Python Client Example

Use HTTP Basic Auth as an explicit header. Do not use `gradio_client.Client(..., auth=...)`, because that attempts Gradio's own login flow, while production auth is handled by Caddy.

```python
import base64
from gradio_client import Client

USER = "api"
PASSWORD = "<API_BASIC_PASSWORD>"
API_KEY = "<API_KEY>"

basic = base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()
client = Client(
    "https://tts-api.airewardrop.xyz",
    headers={
        "Authorization": f"Basic {basic}",
        "X-API-Key": API_KEY,
    },
)

wav_path = client.predict(
    "Text to synthesize.",
    "af_jessica",
    1.0,
    True,
    api_name="/generate_full",
)
print(wav_path)
```

## Unreal Audio Pipeline

Unreal reads `Z:`.

Production maps the Unreal drive to the local TTS output share:

```text
Z: -> \\<STREAMING_WORKSTATION>\AudioRecords
\\<STREAMING_WORKSTATION>\AudioRecords -> C:\Eliza2Face\eliza2face\audio_records
```

This avoids any dependency on the old external audio share.

## Verification

```powershell
Get-Service kokoro-tts
curl.exe -s -o NUL -w "%{http_code}`n" -u "tts:<GUI_PASSWORD>" https://tts.airewardrop.xyz/
```
