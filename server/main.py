import PIL.Image
from quart import Quart, session, request, jsonify
import socketio
from quart_cors import cors
import numpy as np
from faster_whisper import WhisperModel
import wave
import asyncio
import uvicorn
import time
import sys
from collections import defaultdict
import re
from models.llm import llm_answer
from models.facial import predict
import io
from concurrent.futures import ThreadPoolExecutor

try:
    from models.diarization import DiartDiarization
except Exception as e:
    print("Diarization model not found. Please install the required dependencies.")
    sys.exit(1)

import torch
GPU_IDS = list(range(torch.cuda.device_count()))

app = Quart(__name__)
app = cors(app, allow_origin="*")

executor = ThreadPoolExecutor(max_workers=4)

try:
    sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
except Exception as e:
    print("SocketIO not installed. Please install the required dependencies.")
    sys.exit(1)

SAMPLE_RATE       = 16_000
MIN_CHUNK_SIZE    = 3               # seconds
CHUNK_SIZE        = int(SAMPLE_RATE * MIN_CHUNK_SIZE)

transcribe_queue = defaultdict(asyncio.Queue)
diarize_queue = defaultdict(asyncio.Queue)
user_tasks = defaultdict(list)


@app.route("/api/face_recognition", methods=["POST"])
async def face_recognition():
    from PIL import Image

    loop = asyncio.get_event_loop()
    files = await request.files
    image = Image.open(io.BytesIO(files.get("image").read()))

    ans = await loop.run_in_executor(executor, predict, image)

    return jsonify({"message": ans})

try:
    app = socketio.ASGIApp(sio, app)
except Exception as e:
    print("ASGIApp not found. Please install the required dependencies.")
    sys.exit(1)

@sio.event
def connect(sid, environ):
    print("Client connected")

@sio.event
def disconnect(sid):
    print("Client disconnected")

@sio.on("audio")
async def handle_audio(sid, data):
    global transcribe_queue

    try:
        pcm = np.frombuffer(data["audio_data"], dtype=np.float32)
        await transcribe_queue[sid].put(pcm)
    except Exception as e:
        print(f"Error processing audio: {e}")
        await sio.emit("error", {"message": "Error processing audio"})

useCuda = input("Use CUDA? (y/n): ").strip().lower() == "y"
model_str = input("Model name (e.g., tiny.en): ").strip()

try:
    model = WhisperModel(model_str, device="auto" if not useCuda else "cuda", compute_type="int8", device_index=GPU_IDS if useCuda else 0)
except Exception as e:
    print(f"Error loading Whisper model: {e}")
    sys.exit(1)


@sio.on("video")
async def handle_video(sid, data):
    with open(f"videos/video_{sid}.webm", 'ab') as f:
        f.write(data["video_data"])


async def diarize(sid):
    pass
    
    # try:
    #     diarizer = DiartDiarization(use_microphone=False)
    # except Exception as e:
    #     print(f"Error initializing diarizer: {e}")
    #     await sio.emit("error", {"message": "Error initializing diarizer"}, to=sid)
    #     return
    
    # while True:
    #     pcm = await diarize_queue.get()
    #     if pcm is None:
    #         diarize_queue.task_done()
    #         break

    #     res = await diarizer.diarize(pcm)

    #     print(res)

    #     diarize_queue.task_done()

def model_run(buffer, prompt=None):
    try:
        segments, info = model.transcribe(
            np.concatenate(buffer).astype(np.float32),
            language="en",
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=True,
            word_timestamps=True,
        )
    except Exception as e:
        print(f"Error during model run: {e}")
        return [], {}
    return segments, info

async def transcribe(sid):
    from collections import deque
    done = False
    last_word = 0
    window_num = 0

    prompt = []

    buffer = deque(maxlen=CHUNK_SIZE) 
    while not done:
        pcm = await transcribe_queue[sid].get()
        buffer.append(pcm)

        if pcm is None:
            done = True
            break

        if len(buffer) * 4096 <= CHUNK_SIZE and not done:
            transcribe_queue[sid].task_done()
            continue


        before = time.perf_counter()

        try:
            segments, _ = await asyncio.get_event_loop().run_in_executor(executor, model_run, buffer)
        except Exception as e:
            print(f"Error during transcription: {e}")
            await sio.emit("error", {"message": "Error during transcription"}, to=sid)
        cur = []

        for seg in segments:
            for word in seg.words:
                adjusted_start = word.start + window_num
                adjusted_end = word.end + window_num

                if adjusted_start < last_word:
                    continue

                cur.append(re.sub(r'[^A-Za-z]+', '', word.word))
                last_word = adjusted_end
        
        buffer.popleft()
        buffer.popleft()

        window_num += 0.511
        if not cur:
            transcribe_queue[sid].task_done()
            continue

        prompt += cur
        prompt = prompt[-10:]  # Keep the last 10 words as context

        await sio.emit("audio_ans", {"text": " ".join(cur)}, to=sid)

        transcribe_queue[sid].task_done()
        after= time.perf_counter()

        # Logging
        print(f"Transcription time: {after - before}, {sid}")
        with open(f"log_{model_str}.csv", "a") as f:
            f.write(f"{after - before},{' '.join(cur)}\n")

@sio.on("start")
async def start_up(sid):

    global transcribe_queue

    print("Starting up")

    transcribe_queue[sid] = asyncio.Queue()

    user_tasks[sid].append(sio.start_background_task(transcribe, sid))
    user_tasks[sid].append(sio.start_background_task(diarize, sid))

@sio.on("stop")
async def handle_stop(sid):
    global transcribe_queue, user_tasks, diarize_queue
    transcribe_queue[sid].put_nowait(None)  # Signal to stop transcription
    if user_tasks.get(sid):
        for task in user_tasks[sid]:
            if not task.done():
                task.cancel()
        await asyncio.gather(*user_tasks[sid], return_exceptions=True)

        del transcribe_queue[sid]
        del diarize_queue[sid]
        del user_tasks[sid]

    await sio.emit("stopped", {"message": "Transcription stopped"}, to=sid)

@sio.on("chat_message")
async def handle_chat_message(sid, data):
    print(f"Received chat message from {sid}: {data}")

    loop = asyncio.get_event_loop()

    def syncWrapper(*args, **kwargs):
        return asyncio.new_event_loop().run_until_complete(llm_answer(*args, **kwargs))

    await loop.run_in_executor(executor, syncWrapper, data['message'], sio, sid, data.get('history', None), data.get('transcription', None))


if __name__ == "__main__":
    try:
        uvicorn.run(app, host="0.0.0.0", port=5000)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)