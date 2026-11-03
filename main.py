from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, io, hashlib
import soundfile as sf

app = FastAPI(title="Khensani Voice Server")

# Allow your Luvuno/Khensani frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lock to your domain after testing
    allow_methods=["*"],
    allow_headers=["*"],
)

CACHE_DIR = "./cache"
os.makedirs(CACHE_DIR, exist_ok=True)

print("Loading Kokoro TTS...")
from kokoro_onnx import Kokoro
tts = Kokoro("kokoro-v1.0.onnx", "voices.bin")
print("Kokoro TTS ready — voice: af_heart")

def cache_path(text: str) -> str:
    key = hashlib.md5(text.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{key}.wav")

class SynthRequest(BaseModel):
    text: str
    speed: float = 0.95  # Slightly slower for NotebookLM warmth

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
            voice="af_heart",  # Grade A female voice [citation:5]
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