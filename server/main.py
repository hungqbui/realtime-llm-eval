import PIL.Image
from quart import Quart, session, request, jsonify, Response
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
import os
from models.whisper_streaming.whisper_online import *

# Get all available GPU for parallel processing.
import torch
GPU_IDS = list(range(torch.cuda.device_count()))

# Initialize the Quart app and Socket.IO server
# Quart is an ASGI version of Flask, which allows for asynchronous operations, enabling better performance for I/O-bound tasks like real-time audio and video processing through concurrency and parallelism.
app = Quart(__name__)
app = cors(app, allow_origin="*")

import argparse

parser = argparse.ArgumentParser(description="Run the real-time ASR server.")
parser.add_argument("--model", type=str, default="small", help="Size of the Whisper model to use (e.g., 'tiny', 'base', 'small', 'medium', 'large').")

model = parser.parse_args().model

asr = FasterWhisperASR(lan="auto",modelsize=model)

# ThreadPoolExecutor is used to run blocking code in a separate thread, allowing the main event loop to remain responsive.
executor = ThreadPoolExecutor(max_workers=len(GPU_IDS) * 2)

# Socket.IO server is initialized with ASGI mode, allowing it to work with the Quart app.
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*", ping_timeout=180000, ping_interval=60000)

SAMPLE_RATE       = 16_000
MIN_CHUNK_SIZE    = 5               # seconds
CHUNK_SIZE        = int(SAMPLE_RATE * MIN_CHUNK_SIZE)

# Transcribe queue holds audio data for each user session, allowing for asynchronous processing of audio streams.
transcribe_queue = defaultdict(asyncio.Queue)
session_name = defaultdict(str)
user_tasks = defaultdict(asyncio.Task)
stop_event_list = defaultdict(asyncio.Event)
transcribe_stop_list = defaultdict(asyncio.Event)
online_map = defaultdict(OnlineASRProcessor)

@app.route('/api/get_records', methods=['GET'])
async def get_folders():
    """
    Endpoint to get the list of records in the REDCap database.
    """
    from utils.redcap import list_records
    try:
        records = list_records()

        records = list(map(lambda x: x.get("record_id"), records))  # Convert to empty dicts to avoid sending sensitive data

        return jsonify(records)
    except Exception as e:
        print(f"Error getting records: {e}")
        return jsonify({"error": "Failed to retrieve records"}), 500


@app.route("/api/delete_data/<patient_name>", methods=["DELETE"])
async def delete_data(patient_name):
    """
    Endpoint to delete all data for a specific patient from the REDCap file repository.
    """
    from utils.redcap import delete_data
    try:
        delete_data(patient_name)
        return jsonify({"message": "Data deleted successfully"}), 200
    except Exception as e:
        print(f"Error deleting data for {patient_name}: {e}")
        return jsonify({"error": "Failed to delete data"}), 500


# Bind the Socket.IO server to the Quart app.
app = socketio.ASGIApp(sio, app)

@sio.event
def connect(sid, environ):
    online_map[sid] = VACOnlineASRProcessor(MIN_CHUNK_SIZE/16000, asr=asr)
    print("Client connected")

@sio.event
def disconnect(sid, reason):
    print(f"Client disconnected {reason}")

# Face recognition socket event handler
@sio.on("face_recognition")
async def face_recognition(sid, data):
    from PIL import Image

    try:
        # Get the image data from the received data and run the prediction in a separate thread to avoid blocking the event loop.
        loop = asyncio.get_event_loop()

        top = await loop.run_in_executor(executor, predict, Image.open(io.BytesIO(data["image_data"])))
        if (not os.path.isdir(f"./videos/{session_name[sid]}")):
            os.makedirs(f"./videos/{session_name[sid]}")

        if top == "NONE":
            return
        
        with open(f"./videos/{session_name[sid]}/expressionlog.txt", 'a') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {top}\n")

        await sio.emit("face_recognition_ans", {
            "message": top
        }, to=sid)
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

# Video handler that saves incoming video data to a file.
@sio.on("video")
async def handle_video(sid, data):
    if (not os.path.isdir(f"./videos/{session_name[sid]}")):
        os.makedirs(f"./videos/{session_name[sid]}")
    with open(f"./videos/{session_name[sid]}/video_{sid}.webm", 'ab') as f:
        f.write(data["video_data"])

# Asynchronous consummer that processes audio data from the transcribe queue, performs transcription, and emits the results back to the client.
async def transcribe(sid):
    if (not os.path.isdir(f"./videos/{session_name[sid]}")):
        os.makedirs(f"./videos/{session_name[sid]}")
        
    while not transcribe_stop_list[sid].is_set():
        pcm = await transcribe_queue[sid].get()
        online_map[sid].insert_audio_chunk(pcm)
        if not pcm or transcribe_stop_list[sid].is_set():
            print(online_map[sid].finish())
            done = True
            break
        
        loop = asyncio.get_event_loop()
        ans = await loop.run_in_executor(executor, online_map[sid].process_iter)
        if ans[2]:
            with open(f"./videos/{session_name[sid]}/transcription.txt", 'a') as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ")
                f.write(f"{ans[2]}")
            await sio.emit("audio_ans", {"text": ans[2]}, to=sid)

# Socket.IO event handler to start the transcription process for a user session.
@sio.on("start")
async def start_up(sid):

    global transcribe_queue

    print("Starting up")

    transcribe_queue[sid] = asyncio.Queue()
    transcribe_stop_list[sid] = asyncio.Event()
    user_tasks[sid] = sio.start_background_task(transcribe, sid)

@sio.on("session_name")
async def handle_session_name(sid, data):
    """
    Socket.IO event handler to set the session name for a user session.
    This is used to identify the session for transcription and other operations.
    """
    global session_name

    # Store the session name in the global dictionary.
    session_name[sid] = data.get("session_name", "unnamed_session")

    print(f"Session name for {sid} set to {session_name[sid]}")

    await sio.emit("session_name_set", {"session_name": session_name[sid]}, to=sid)

# Socket.IO event handler to stop the transcription process for a user session.
@sio.on("stop")
async def handle_stop(sid):
    global transcribe_queue, user_tasks

    # Cancel the transcription task for the user session if it is running.
    if user_tasks.get(sid):
        if user_tasks[sid] and not user_tasks[sid].done():
            transcribe_queue[sid].put_nowait(None)  # Signal the transcription task to stop
            transcribe_stop_list[sid].set()  # Set the stop event to signal the task to stop
            user_tasks[sid].cancel()

        del transcribe_queue[sid]
        del user_tasks[sid]

    await sio.emit("stopped", {"message": "Transcription stopped"}, to=sid)

# Chat message for the LLM model, which processes the incoming chat messages and streams the responses back to the client.
@sio.on("chat_message")
async def handle_chat_message(sid, data):
    print(f"Received chat message from {sid}: {data}")

    from utils.redcap import get_screening_prettify, get_patient_previsit
    loop = asyncio.get_event_loop()
    screening = get_screening_prettify(session_name[sid])
    previsit = get_patient_previsit(session_name[sid])
        
    combined = {
        "screening": screening if screening["screening_complete"] == "2" else None,
        "previsit": previsit if previsit and previsit["patient_previsit_complete"] == "2" else None
    }

    if (not os.path.isdir(f"./videos/{session_name[sid]}")):
        os.makedirs(f"./videos/{session_name[sid]}")

    with open(f"./videos/{session_name[sid]}/chatlog.txt", 'a') as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - User: {data['message']}\n\n")

    out = await loop.run_in_executor(executor, llm_answer, data['message'], data.get('history', None), data.get('transcription', None), data.get("emotions", None), combined)

    # Conditional var to handle stopping the stream based on client request.
    stop_event_list[sid] = asyncio.Event()

    async def _stream_llm(sid, out, stop_event):
        with open(f"./videos/{session_name[sid]}/chatlog.txt", 'a') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - AI:")
            for chunk in out:
                if stop_event.is_set():
                    print(f"Stream for SID {sid} cancelled by client request.")

                    # This emits when the stream is stopped by the client.
                    await sio.emit("stream_end", {"message": "BREAK"}, to=sid)
                    return  # Exit the loop if the stop event is set
                
                # Check if the chunk is an AIMessageChunk and emit the content to the client (chunk might also be ToolMessageChunk from the search tool)
                if isinstance(chunk[0], AIMessageChunk):
                    f.write(f"{chunk[0].content}")
                    await sio.emit("chat_response", {"message": chunk[0].content}, to=sid)
            f.write("\n\n")
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