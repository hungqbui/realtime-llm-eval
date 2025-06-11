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
from langchain_core.messages import AIMessageChunk

# Get all available GPU for parallel processing.
import torch
GPU_IDS = list(range(torch.cuda.device_count()))

# Initialize the Quart app and Socket.IO server
# Quart is an ASGI version of Flask, which allows for asynchronous operations, enabling better performance for I/O-bound tasks like real-time audio and video processing through concurrency and parallelism.
app = Quart(__name__)
app = cors(app, allow_origin="*")

# ThreadPoolExecutor is used to run blocking code in a separate thread, allowing the main event loop to remain responsive.
executor = ThreadPoolExecutor(max_workers=len(GPU_IDS) * 2)

# Socket.IO server is initialized with ASGI mode, allowing it to work with the Quart app.
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

SAMPLE_RATE       = 16_000
MIN_CHUNK_SIZE    = 3               # seconds
CHUNK_SIZE        = int(SAMPLE_RATE * MIN_CHUNK_SIZE)

# Transcribe queue holds audio data for each user session, allowing for asynchronous processing of audio streams.
transcribe_queue = defaultdict(asyncio.Queue)
user_tasks = defaultdict(asyncio.Task)
stop_event_list = defaultdict(asyncio.Event)

# Bind the Socket.IO server to the Quart app.
app = socketio.ASGIApp(sio, app)

@sio.event
def connect(sid, environ):
    print("Client connected")

@sio.event
def disconnect(sid):
    print("Client disconnected")

# Face recognition socket event handler
@sio.on("face_recognition")
async def face_recognition(sid, data):
    from PIL import Image

    try:
        # Get the image data from the received data and run the prediction in a separate thread to avoid blocking the event loop.
        loop = asyncio.get_event_loop()
        image = Image.open(io.BytesIO(data["image_data"]))
        ans, prob = await loop.run_in_executor(executor, predict, image)

        if prob < 0.5:
            return

        await sio.emit("face_recognition_ans", {"message": ans, "conf": prob}, to=sid)
    except Exception as e:
        print(f"Error processing image: {e}")
        await sio.emit("error", {"message": "Error processing image"}, to=sid)
        return

# Audio producer that adds audio data to the transcribe queue for each user session.
@sio.on("audio")
async def handle_audio(sid, data):
    global transcribe_queue

    try:
        pcm = np.frombuffer(data["audio_data"], dtype=np.float32)
        await transcribe_queue[sid].put(pcm)
    except Exception as e:
        print(f"Error processing audio: {e}")
        await sio.emit("error", {"message": "Error processing audio"})

# Load the Whisper model based on the provided command line arguments (to ease deployment and testing on different platform).
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--model", required=True)
parser.add_argument("--cuda", action="store_true", help="Use CUDA for GPU acceleration")
args = parser.parse_args()

useCuda = args.cuda
model_str = args.model

# Load the faster-whisper model with the specified parameters.
try:
    # Models that have been tested: distil-small.en, distil-medium.en, large-v2 (distil-small.en seems to be the most balanced)
    model = WhisperModel(model_str, device="auto" if not useCuda else "cuda", compute_type="int8", device_index=GPU_IDS if useCuda else None)
except Exception as e:
    print(f"Error loading Whisper model: {e}")
    sys.exit(1)

# Video handler that saves incoming video data to a file.
@sio.on("video")
async def handle_video(sid, data):
    with open(f"videos/video_{sid}.webm", 'ab') as f:
        f.write(data["video_data"])

# Coroutine to run the Whisper model for transcription.
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

# Asynchronous consummer that processes audio data from the transcribe queue, performs transcription, and emits the results back to the client.
async def transcribe(sid):
    from collections import deque
    done = False
    last_word = 0
    window_num = 0

    prompt = []

    # A rolling buffer to hold the audio data for transcription.
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
        
        # Chunking algorithm to ensure that the buffer is processed in manageable chunks and doesn't lose context using overlapping chunks.
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

        # Logging performance metrics for transcription.
        print(f"Transcription time: {after - before}, {sid}")
        with open(f"log_{model_str}.csv", "a") as f:
            f.write(f"{after - before},{' '.join(cur)}\n")

# Socket.IO event handler to start the transcription process for a user session.
@sio.on("start")
async def start_up(sid):

    global transcribe_queue

    print("Starting up")

    transcribe_queue[sid] = asyncio.Queue()

    user_tasks[sid] = sio.start_background_task(transcribe, sid)

# Socket.IO event handler to stop the transcription process for a user session.
@sio.on("stop")
async def handle_stop(sid):
    global transcribe_queue, user_tasks

    # Cancel the transcription task for the user session if it is running.
    if user_tasks.get(sid):
        if user_tasks[sid] and not user_tasks[sid].done():
            user_tasks[sid].cancel()
            await user_tasks[sid]

        del transcribe_queue[sid]
        del user_tasks[sid]

    await sio.emit("stopped", {"message": "Transcription stopped"}, to=sid)

# Chat message for the LLM model, which processes the incoming chat messages and streams the responses back to the client.
@sio.on("chat_message")
async def handle_chat_message(sid, data):
    print(f"Received chat message from {sid}: {data}")

    loop = asyncio.get_event_loop()

    out = await loop.run_in_executor(executor, llm_answer, data['message'], data.get('history', None), data.get('transcription', None))

    # Conditional var to handle stopping the stream based on client request.
    stop_event_list[sid] = asyncio.Event()

    async def _stream_llm(sid, out, stop_event):
        for chunk in out:
            if stop_event.is_set():
                print(f"Stream for SID {sid} cancelled by client request.")

                # This emits when the stream is stopped by the client.
                await sio.emit("stream_end", {"message": "BREAK"}, to=sid)
                return  # Exit the loop if the stop event is set
            
            # Check if the chunk is an AIMessageChunk and emit the content to the client (chunk might also be ToolMessageChunk from the search tool)
            if isinstance(chunk[0], AIMessageChunk):
                await sio.emit("chat_response", {"message": chunk[0].content}, to=sid)

        # This is emit when the stream completes
        await sio.emit("stream_end", {"message": "END"}, to=sid)

    sio.start_background_task(_stream_llm, sid, out, stop_event_list[sid])

# Handle the stop event, signaling stop chat condition var
@sio.on("stop_chat")
async def handle_stop_chat(sid):
    print(f"Stopping chat stream for {sid}")

    if sid in stop_event_list:
        stop_event_list[sid].set()
        del stop_event_list[sid]

if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=5000)