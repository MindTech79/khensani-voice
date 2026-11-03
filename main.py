from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, io, hashlib, urllib.request
import soundfile as sf

app = FastAPI(title="Khensani Voice Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CACHE_DIR = "./cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# --- Kokoro model auto-download ---
MODEL_PATH = "kokoro-v1.0.onnx"
VOICES_PATH = "voices.bin"

KOKORO_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"

def ensure_models():
    if not os.path.exists(MODEL_PATH):
        print(f"Downloading {MODEL_PATH}...")
        urllib.request.urlretrieve(f"{KOKORO_BASE}/kokoro-v1.0.onnx", MODEL_PATH)
        print("Model downloaded.")
    if not os.path.exists(VOICES_PATH):
        print(f"Downloading {VOICES_PATH}...")
        urllib.request.urlretrieve(f"{KOKORO_BASE}/voices-v1.0.bin", VOICES_PATH)
        print("Voices downloaded.")

ensure_models()

print("Loading Kokoro TTS...")
from kokoro_onnx import Kokoro
tts = Kokoro(MODEL_PATH, VOICES_PATH)
print("Kokoro TTS ready — voice: af_heart")

# --- rest of your code stays the same ---
def cache_path(text: str) -> str:
    key = hashlib.md5(text.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{key}.wav")

class SynthRequest(BaseModel):
    text: str
    speed: float = 0.95

@app.post("/synthesize")
async def synthesize(req: SynthRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="No text provided")

    path = cache_path(req.text)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return Response(content=f.read(), media_type="audio/wav")

    try:
        samples, sample_rate = tts.create(
            req.text,
            voice="af_heart",
            speed=req.speed,
            lang="en-us"
        )
        buf = io.BytesIO()
        sf.write(buf, samples, sample_rate, format="WAV")
        buf.seek(0)
        audio_bytes = buf.read()

        with open(path, "wb") as f:
            f.write(audio_bytes)

        return Response(content=audio_bytes, media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok", "engine": "kokoro-tts", "voice": "af_heart"}
