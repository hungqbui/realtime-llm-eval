from quart import Quart, session
import socketio
from quart_cors import cors
import numpy as np
from faster_whisper import WhisperModel
import wave
import asyncio
import uvicorn
from diart import SpeakerDiarization

app = Quart(__name__)
app = cors(app, allow_origin="*")

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

audio_queue = asyncio.Queue()
pipeline = SpeakerDiarization()
transcribe_task = None

@sio.event
def connect(sid, environ):
    print("Client connected")

@sio.event
def disconnect(sid):
    print("Client disconnected")

@sio.on("audio")
async def handle_audio(sid, data):
    global audio_queue

    try:
        pcm = np.frombuffer(data["audio_data"], dtype=np.float32)
        await audio_queue.put(pcm)
    except Exception as e:
        print(f"Error processing audio: {e}")
        await sio.emit("error", {"message": "Error processing audio"})


SAMPLE_RATE       = 16_000
MIN_CHUNK_SIZE    = 3               # seconds
CHUNK_SIZE        = int(SAMPLE_RATE * MIN_CHUNK_SIZE)

model = WhisperModel("tiny.en", device="auto", compute_type="int8")

prompt = ""

async def transcribe(sid):
    global prompt

    while True:

        buffer = np.zeros((0,), dtype=np.float32)
        while buffer.shape[0] < CHUNK_SIZE:
            if audio_queue.empty():
                await asyncio.sleep(0.01)
                continue

            pcm = await audio_queue.get()
            buffer = np.concatenate((buffer, pcm))

        annots = pipeline({'uri': sid, 'audio': buffer, 'sample_rate': SAMPLE_RATE})
        rttm = annots[0].to_rttm()
        print(rttm)
        segments, _ = model.transcribe(
            buffer,
            language="en",
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False
        )
        cur = []
        for seg in segments:
            cur.append(seg.text)

        if not cur:
            continue

        await sio.emit("audio_ans", {"text": " ".join(cur)})
        prompt += " ".join(cur) + " "
        print(prompt)
        await asyncio.sleep(0.01)

@sio.on("start")
async def start_up(sid):
    global transcribe_task, audio_queue

    audio_queue = asyncio.Queue()
    transcribe_task = asyncio.create_task(transcribe(sid))

@sio.on("stop")
async def handle_stop(sid):
    global transcribe_task, audio_queue
    # 1) cancel the running transcription Task
    if transcribe_task and not transcribe_task.done():
        transcribe_task.cancel()
        try:
            await transcribe_task
        except asyncio.CancelledError:
            pass

    audio_queue = asyncio.Queue()

    # 3) inform the client
    await sio.emit("stopped", {"message": "Transcription stopped"}, to=sid)

app = socketio.ASGIApp(sio, app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)