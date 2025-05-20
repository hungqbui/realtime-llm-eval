from quart import Quart, session
import socketio
from quart_cors import cors
import numpy as np
from faster_whisper import WhisperModel
import wave
import asyncio
import uvicorn

app = Quart(__name__)
app = cors(app, allow_origin="*")

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

model = WhisperModel("tiny", device="auto", compute_type="int8")

audio_queue = asyncio.Queue()
overall_buffer = asyncio.Queue()


@sio.event
def connect(sid, environ):
    print("Client connected")

@sio.event
def disconnect(sid):
    print("Client disconnected")


@sio.on("audio")
async def handle_audio(sid, data):

    
    try:
        pcm = (np.frombuffer(data["audio_data"], dtype=np.float32) * 32768).astype(np.int16)
        await audio_queue.put(pcm)
    except Exception as e:
        print(f"Error processing audio: {e}")
        await sio.emit("error", {"message": "Error processing audio"})


async def trans():
    global decoder_state
    buffer = np.zeros(0, dtype=np.int16)
    FRAME = 16000

    while True:
        if audio_queue.empty():
            await asyncio.sleep(0.01)
            continue
        pcm = await audio_queue.get()
        await overall_buffer.put(pcm)
        # await save_audio()
        buffer = np.concatenate((buffer, pcm))
        if len(buffer) >= FRAME:
            audio = buffer
            segments, info = model.transcribe(audio, language="en", initial_prompt="", beam_size=5, word_timestamps=True, condition_on_previous_text=True)
            for segment in segments:
                print(f"Segment: {segment.text}")

async def save_audio():
    local = []
    for pcm in overall_buffer._queue:
        local.append(pcm)

    with wave.open("audio.wav", "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"".join(local))
        

async def start_up():
    loop = asyncio.get_event_loop()
    loop.create_task(trans())
    loop.create_task(save_audio())

app = socketio.ASGIApp(sio, app, on_startup=start_up)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)