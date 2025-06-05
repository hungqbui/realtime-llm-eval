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

import torch
GPU_IDS = list(range(torch.cuda.device_count()))

app = Quart(__name__)
app = cors(app, allow_origin="*")

executor = ThreadPoolExecutor(max_workers=len(GPU_IDS) * 2)

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

SAMPLE_RATE       = 16_000
MIN_CHUNK_SIZE    = 3               # seconds
CHUNK_SIZE        = int(SAMPLE_RATE * MIN_CHUNK_SIZE)

transcribe_queue = defaultdict(asyncio.Queue)
user_tasks = defaultdict(asyncio.Task)


# diarize_queue = defaultdict(asyncio.Queue)
# diarizer = None



app = socketio.ASGIApp(sio, app)

@sio.event
def connect(sid, environ):
    print("Client connected")

@sio.event
def disconnect(sid):
    print("Client disconnected")

@sio.on("face_recognition")
async def face_recognition(sid, data):
    from PIL import Image


    try:
        loop = asyncio.get_event_loop()
        image = Image.open(io.BytesIO(data["image_data"]))
        ans = await loop.run_in_executor(executor, predict, image)
        await sio.emit("face_recognition_ans", {"message": ans}, to=sid)
    except Exception as e:
        print(f"Error processing image: {e}")
        await sio.emit("error", {"message": "Error processing image"}, to=sid)
        return


@sio.on("audio")
async def handle_audio(sid, data):
    global transcribe_queue

    try:
        pcm = np.frombuffer(data["audio_data"], dtype=np.float32)
        await transcribe_queue[sid].put(pcm)
    except Exception as e:
        print(f"Error processing audio: {e}")
        await sio.emit("error", {"message": "Error processing audio"})

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--model", required=True)
parser.add_argument("--cuda", action="store_true", help="Use CUDA for GPU acceleration")
args = parser.parse_args()

useCuda = args.cuda
model_str = args.model

try:
    model = WhisperModel(model_str, device="auto" if not useCuda else "cuda", compute_type="int8", device_index=GPU_IDS if useCuda else None)
except Exception as e:
    print(f"Error loading Whisper model: {e}")
    sys.exit(1)

# diarizer = DiartDiarization()

@sio.on("video")
async def handle_video(sid, data):
    with open(f"videos/video_{sid}.webm", 'ab') as f:
        f.write(data["video_data"])


# async def diarize():
#     while True:
#         pcm = await diarize_queue.get()
#         if pcm is None:
#             diarize_queue.task_done()

#             break

#         diarize_queue.task_done()

async def model_run(buffer, prompt=None):
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
            segments, _ = await model_run(buffer)
        except Exception as e:
            print(f"Error during transcription: {e}")
            await sio.emit("error", {"message": "Error during transcription"}, to=sid)
        cur = []

        for seg in segments:
            for word in seg.words:
                adjusted_start = word.start + window_num
                adjusted_end = word.end + window_num

                if adjusted_start < last_word or word.probability < 0.7:
                    continue

                cur.append(re.sub(r'[^A-Za-z]+', '', word.word))
                last_word = adjusted_end
        
        buffer.popleft()
        buffer.popleft()

        window_num += (4096 / SAMPLE_RATE) * 2 
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

    user_tasks[sid] = sio.start_background_task(transcribe, sid)

@sio.on("stop")
async def handle_stop(sid):
    global transcribe_queue, user_tasks

    if user_tasks.get(sid):
        if user_tasks[sid] and not user_tasks[sid].done():
            user_tasks[sid].cancel()
            await user_tasks[sid]

        del transcribe_queue[sid]
        del user_tasks[sid]

    # 3) inform the client
    await sio.emit("stopped", {"message": "Transcription stopped"}, to=sid)

@sio.on("chat_message")
async def handle_chat_message(sid, data):
    print(f"Received chat message from {sid}: {data}")

    loop = asyncio.get_event_loop()

    def syncWrapper(*args, **kwargs):
        return asyncio.new_event_loop().run_until_complete(llm_answer(*args, **kwargs))

    await loop.run_in_executor(executor, syncWrapper, data['message'], sio, sid, data.get('history', None), data.get('transcription', None))


if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=5000)