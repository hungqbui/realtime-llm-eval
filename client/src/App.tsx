import { useState, useEffect, useRef } from 'react'
import { socket } from './utils/socket'; 
import './App.css'

function App() {

  const audioCtx = useRef<AudioContext | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const processor = useRef<ScriptProcessorNode | null>(null);
  const input = useRef<MediaStreamAudioSourceNode | null>(null);
  const pcmChunks = useRef<Int16Array[]>([]);
  const stream = useRef<MediaStream | null>(null);
  const [answer, setAnswer] = useState<string>("");
  const canvas = useRef<HTMLCanvasElement | null>(null);
  const timeRef = useRef<number>(0);

  useEffect(() => {
    socket.on("connect", () => {
      console.log("Connected to server");
    });

    socket.on("disconnect", () => {
      console.log("Disconnected from server");
    });

    socket.on("audio_ans", (data : any) => {
      setAnswer(prev => prev + data["text"]);
      console.log(`Time taken to update client: ${performance.now() - timeRef.current}`);
    })

    return () => {
      socket.off("connect");
      socket.off("disconnect");
      socket.off("audio_ans");
    }

  }, []);
  function drawFloat32Wave(canvas : HTMLCanvasElement, floatArray: Float32Array) {
    const ctx = canvas.getContext('2d') as CanvasRenderingContext2D;
    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);
    ctx.beginPath();
    ctx.lineWidth = 2;
    ctx.strokeStyle = 'lime';

    const step = width / floatArray.length;
    for (let i = 0; i < floatArray.length; i++) {
      const x = i * step;
      const y = height / 2 - (floatArray[i] * height / 2);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }

    ctx.stroke();
  }

  const startRecording = async () => {
    stream.current = await navigator.mediaDevices.getUserMedia({ audio: true });

    audioCtx.current = new AudioContext({ sampleRate: 16000 });
    audioCtx.current.resume();

    input.current = audioCtx.current.createMediaStreamSource(stream.current);
    processor.current = audioCtx.current.createScriptProcessor(4096, 1, 1);
    
    processor.current.onaudioprocess = async (e) => {
      const data = e.inputBuffer.getChannelData(0);
      drawFloat32Wave(canvas.current as HTMLCanvasElement, data);
      const int16 = convertFloat32ToInt16(data);
      pcmChunks.current.push(int16);
      
      timeRef.current = performance.now(); 
      sendChunkToServer(data);
    };
    input.current?.connect(processor.current);
    processor.current?.connect(audioCtx.current.destination);
    setIsRecording(true);
    socket.emit("start")
  }

  function convertFloat32ToInt16(buffer : Float32Array) {
    let l = buffer.length;
    let result = new Int16Array(l);
    for (let i = 0; i < l; i++) {
      result[i] = Math.round(buffer[i] * 0x7FFF);
    }
    return result;
  }

  const stopRecording = () => {
    processor.current?.disconnect();
    input.current?.disconnect();
    audioCtx.current?.close();
    stream.current?.getTracks().forEach(track => track.stop());

    socket.emit("stop")

    setIsRecording(false);
  }

  function sendChunkToServer(int16Chunk : any) {
    const blob = new Blob([int16Chunk], { type: 'application/octet-stream' });

    // const response = await fetch("/api/transcribe", {
    //   method: "POST",
    //   headers: {
    //     "Content-Type": "application/octet-stream",
    //   },
    //   body: blob,
    // })

    socket.emit("audio", {
      "audio_data": blob,
      "session_id": "1234",
    });

  }

  return (
    <>
      <button onClick={async () => {
        if (!isRecording) startRecording();
        else stopRecording();
      }}>
        { isRecording ? "Stop" : "Start" }
      </button>
      <p>Answer: {answer}</p>
      <canvas ref={canvas} width={800} height={400} style={{ border: "1px solid black" }} />
    </>
  )
}

export default App
