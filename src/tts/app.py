#!/usr/bin/env python3
# ────────────────────────────────────────────────────────────────────────────
# app.py – Kokoro TTS · Gradio GUI · WAV manager            (prod v0.1 b 2025-05)
#
#  • Unlimited-length TTS (CPU or CUDA)
#  • All audio written to ./audio_records
#  • Web UI
#      – “TTS” tab         → Generate / stream speech
#      – “WAV Manager” tab → List ▸ play ▸ download ▸ delete ▸ purge WAVs
#  • Optional HTTP Basic-Auth:
#        auth.json  →  [{"username": "...", "password": "..."}]
#        auth.env   →  one  user=pwd  per line
#    – no file  ⇒  runs without authentication
#  • Public REST endpoints remain available
# ────────────────────────────────────────────────────────────────────────────

import os, json, datetime, time               # `time` added for auto-cleanup
from pathlib import Path
from typing   import List, Tuple, Optional

import numpy as np
import torch, gradio as gr
from scipy.io import wavfile                   # kokoro already imports soundfile

# ──────────────── AUTO-CLEANUP SETTINGS (keep last 10 / 1 h) ───────────────
MAX_FILES   = 10          # keep at most N newest WAVs
MAX_AGE_SEC = 3600        # delete WAVs older than N seconds

def _cleanup(dir_: Path) -> None:
    """Delete WAVs older than MAX_AGE_SEC *or* beyond the MAX_FILES quota."""
    now   = time.time()
    wavs  = sorted(dir_.glob("*.wav"), key=lambda f: f.stat().st_mtime)

    # remove too-old files
    for f in wavs:
        if now - f.stat().st_mtime > MAX_AGE_SEC:
            try: f.unlink()
            except Exception: pass

    # enforce the “keep last N” policy
    wavs = sorted(dir_.glob("*.wav"), key=lambda f: f.stat().st_mtime)
    while len(wavs) > MAX_FILES:
        try: wavs.pop(0).unlink()              # delete oldest until quota ok
        except Exception: pass
# ────────────────────────────────────────────────────────────────────────────

# ───────────────────────── 1) INITIALISATION ───────────────────────────────
try:                                   # @spaces.GPU decorator (HF); fallback local
    import spaces
except ImportError:                    # local run → no-op stub
    class _GPU:                        # noqa: D401
        def __init__(self, duration: int = 30): ...
        def __call__(self, fn): return fn
    spaces = type("spaces_fallback", (), {"GPU": _GPU})()

from kokoro import KModel, KPipeline
import misaki
print("DEBUG  misaki:", misaki.__version__, "| CUDA:", torch.cuda.is_available())

CUDA       = torch.cuda.is_available()
CHAR_LIMIT = None                                   # full text – no truncation
AUDIO_DIR  = Path("./audio_records"); AUDIO_DIR.mkdir(exist_ok=True)

# One CPU model (always) + one GPU model (if available)
models = {g: KModel().to("cuda" if g else "cpu").eval()
          for g in ([False] + ([True] if CUDA else []))}

pipelines = {lc: KPipeline(lang_code=lc, model=False) for lc in "ab"}
pipelines["a"].g2p.lexicon.golds["kokoro"] = "kˈOkəɹO"
pipelines["b"].g2p.lexicon.golds["kokoro"] = "kˈQkəɹQ"

@spaces.GPU(duration=30)                        # “Zero-GPU” on HF Spaces
def forward_gpu(ps, ref_s, speed):
    return models[True](ps, ref_s, speed)

# ───────────────────────── 2)  TTS HELPERS ────────────────────────────────
def _now() -> str:
    """Return timestamp yyyymmdd_HHMMSS."""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def _synth(ps, ref_s, speed: float, gpu_flag: bool):
    return (forward_gpu if gpu_flag else models[False])(ps, ref_s, speed)

def generate_first(text: str,
                   voice: str = "af_jessica",
                   speed: float = 0.8,
                   use_gpu: bool = CUDA):
    """Generate first chunk only – fast preview."""
    pipe = pipelines[voice[0]]
    pack = pipe.load_voice(voice)
    for _, ps, _ in pipe(text, voice, speed):
        audio = _synth(ps, pack[len(ps) - 1], speed, use_gpu and CUDA)
        fname = AUDIO_DIR / f"audio_{_now()}.wav"
        wavfile.write(fname, 24_000, audio.numpy())
        print("[SAVE]", fname)
        _cleanup(AUDIO_DIR)                     # auto-cleanup invoked
        return (24_000, audio.numpy()), ps
    return None, ""

def generate_full(text: str,
                  voice: str = "af_jessica",
                  speed: float = 0.8,
                  use_gpu: bool = CUDA):
    """Generate the whole utterance – no duration limit."""
    pipe = pipelines[voice[0]]
    pack = pipe.load_voice(voice)
    chunks: List[np.ndarray] = []
    for _, ps, _ in pipe(text, voice, speed):
        chunks.append(_synth(ps, pack[len(ps) - 1], speed, use_gpu and CUDA).numpy())
    if not chunks:
        return None
    audio = np.concatenate(chunks)
    fname = AUDIO_DIR / f"audio_full_{_now()}.wav"
    wavfile.write(fname, 24_000, audio)
    print("[SAVE FULL]", fname)
    _cleanup(AUDIO_DIR)                         # auto-cleanup invoked
    return 24_000, audio

def tokenize_first(text: str, voice: str = "af_heart"):
    for _, ps, _ in pipelines[voice[0]](text, voice):
        return ps
    return ""

# ───────────────────────── 3)  WAV MANAGER ────────────────────────────────
def list_wavs() -> List[str]:
    return sorted(f.name for f in AUDIO_DIR.glob("*.wav"))

def load_wav_file(fname: Optional[str]):
    """Return (audio_path, file_path) for <Audio> and <File> components."""
    if not fname:                               # nothing selected / list empty
        return None, None
    fp = AUDIO_DIR / fname
    return (str(fp), str(fp)) if fp.is_file() else (None, None)

def delete_wav_file(fname: str):
    try:
        (AUDIO_DIR / fname).unlink()
    finally:
        return gr.update(choices=list_wavs(), value=None)

def purge_all(confirm: bool):
    if confirm:
        n = sum(1 for f in AUDIO_DIR.glob("*.wav") if f.unlink() or True)
        return f"Purged {n} file(s).", gr.update(choices=[], value=None)
    return "Cancelled.", gr.update()

# ───────────────────────── 4)  VOICE LIST ─────────────────────────────────
CHOICES = {
    '🇺🇸 🚺 Jessica 🤖': 'af_jessica',
    '🇺🇸 🚺 Heart ❤️':   'af_heart',
    '🇺🇸 🚺 Bella 🔥':    'af_bella',
    '🇺🇸 🚺 Nicole 🎧':   'af_nicole',
    '🇺🇸 🚺 Aoede':       'af_aoede',
    '🇺🇸 🚺 Kore':        'af_kore',
    '🇺🇸 🚺 Sarah':       'af_sarah',
    '🇺🇸 🚺 Nova':        'af_nova',
    '🇺🇸 🚺 Sky':         'af_sky',
    '🇺🇸 🚺 Alloy':       'af_alloy',
    '🇺🇸 🚺 River':       'af_river',
    '🇺🇸 🚹 Michael':     'am_michael',
    '🇺🇸 🚹 Fenrir':      'am_fenrir',
    '🇺🇸 🚹 Puck':        'am_puck',
    '🇺🇸 🚹 Echo':        'am_echo',
    '🇺🇸 🚹 Eric':        'am_eric',
    '🇺🇸 🚹 Liam':        'am_liam',
    '🇺🇸 🚹 Onyx':        'am_onyx',
    '🇺🇸 🚹 Santa':       'am_santa',
    '🇺🇸 🚹 Adam':        'am_adam',
    '🇬🇧 🚺 Emma':        'bf_emma',
    '🇬🇧 🚺 Isabella':    'bf_isabella',
    '🇬🇧 🚺 Alice':       'bf_alice',
    '🇬🇧 🚺 Lily':        'bf_lily',
    '🇬🇧 🚹 George':      'bm_george',
    '🇬🇧 🚹 Fable':       'bm_fable',
    '🇬🇧 🚹 Lewis':       'bm_lewis',
    '🇬🇧 🚹 Daniel':      'bm_daniel',
}
for v in CHOICES.values():
    pipelines[v[0]].load_voice(v)

# ───────────────────────── 5)  GRADIO UI ──────────────────────────────────
with gr.Blocks() as ui:
    # ---- TTS TAB ---------------------------------------------------------
    with gr.Tab("TTS"):
        with gr.Row():
            with gr.Column(scale=4):
                txt        = gr.Textbox(label="Input Text")
                with gr.Row():
                    drp_v   = gr.Dropdown(list(CHOICES.items()),
                                          value='af_jessica', label="Voice")
                    drp_gpu = gr.Dropdown([("GPU", True), ("CPU", False)],
                                          value=CUDA, label="Hardware",
                                          interactive=CUDA)
                sld_speed  = gr.Slider(0.5, 2.0, 1.0, 0.1, label="Speed")
                btn_first  = gr.Button("Generate", variant="primary")
                btn_full   = gr.Button("Stream Full Audio", variant="primary")
            with gr.Column(scale=3):
                aud_out = gr.Audio(label="Output", autoplay=True)
                tok_out = gr.Textbox(label="Phoneme Tokens", interactive=False)

        btn_first.click(generate_first,
                        [txt, drp_v, sld_speed, drp_gpu],
                        [aud_out, tok_out])
        btn_full.click(generate_full,
                       [txt, drp_v, sld_speed, drp_gpu],
                       aud_out)

    # ---- WAV MANAGER TAB -------------------------------------------------
    with gr.Tab("WAV Manager"):
        drp_wav  = gr.Dropdown(label="Saved WAV files", choices=list_wavs())
        aud_play = gr.Audio(label="Player", interactive=False)
        file_dl  = gr.File(label="Download")
        with gr.Row():
            b_ref = gr.Button("Refresh")
            b_del = gr.Button("Delete")
            b_pur = gr.Button("Purge All", variant="stop")
        chk_confirm = gr.Checkbox(label="Yes, delete everything")
        md_status   = gr.Markdown()

        b_ref.click(lambda: gr.update(choices=list_wavs(), value=None),
                    outputs=drp_wav)
        drp_wav.change(load_wav_file, drp_wav, [aud_play, file_dl])
        b_del.click(delete_wav_file, drp_wav, drp_wav)
        b_pur.click(purge_all, chk_confirm, [md_status, drp_wav])

# ───────────────────────── 6)  AUTH LOADING ───────────────────────────────
def _load_auth() -> Optional[List[Tuple[str, str]]]:
    creds: List[Tuple[str, str]] = []
    jf, ef = Path("auth.json"), Path("auth.env")
    if jf.is_file():
        try:
            creds = [(u["username"], u["password"])
                     for u in json.loads(jf.read_text())]
        except Exception:
            pass
    elif ef.is_file():
        for line in ef.read_text().splitlines():
            if "=" in line:
                u, p = line.split("=", 1)
                creds.append((u.strip(), p.strip()))
    return creds or None

AUTH = _load_auth()

# ───────────────────────── 7)  LAUNCH ─────────────────────────────────────
API_OPEN = True                                 # keep REST endpoints open

if __name__ == "__main__":
    ui.queue(api_open=API_OPEN).launch(
        auth       = AUTH,
        ssr_mode   = False,                     # forced off: no Node dep; auth handled by reverse proxy
        server_name="127.0.0.1",                # loopback only; exposed via Caddy on 2727/2780
        server_port=7870                        # 7860 is held by legacy WSL portproxy
    )
