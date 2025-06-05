
import React, { useState, useEffect, useRef } from 'react'
import { socket } from './utils/socket'; 
import './App.css'
import ChatBox from './components/ChatBox';
import TranscriptionBox from './components/TranscriptionBox';
import EmotionWheel from './components/EmotionWheel';

function App() {

  const [isRecording, setIsRecording] = useState(false);
  const [transcription, setTranscription] = useState<any[]>([]);
  const [title, setTitle] = useState<string>("");
  const [titleSet, setTitleSet] = useState<boolean>(false);
  const [messages, setMessages] = useState<any[]>([]);
  const [message, setMessage] = useState<string>("");
  const [emotions, setEmotions] = useState<any[]>([]);
  const [waitingForResponse, setWaitingForResponse] = useState<boolean>(false);
  const [fullText, setFullText] = useState<string>("");
  
  const audioCtx = useRef<AudioContext | null>(null);
  const processor = useRef<ScriptProcessorNode | null>(null);
  const input = useRef<MediaStreamAudioSourceNode | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const vidRecorder = useRef<MediaRecorder | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const fullTextRef = useRef<string>("");
  const fullTextTimeRef = useRef<string>("");
  const vidRef = useRef<HTMLVideoElement | null>(null);
  const timeRef = useRef<string>("");

  const getCurrentTime = () => {
    const date = new Date();
    return `${date.getHours()}:${date.getMinutes()}`;
  }

  useEffect(() => {

    socket.on("connect", () => {
      console.log("Connected to server");
    });

    socket.on("disconnect", () => {
      console.log("Disconnected from server");
    });

    socket.on("audio_ans", (data : any) => {
      const lastEmitted = timeRef.current;
      timeRef.current = getCurrentTime();

      if (timeRef.current != lastEmitted) {
        setTranscription(prev => [...prev, { text: data["text"], time: getCurrentTime() }]);
      }
      else {
        setTranscription(prev => {
          const newTranscription = [...prev];
          newTranscription[newTranscription.length - 1].text += ` ${data["text"]}`;
          return newTranscription;
        });
      }
    })

    socket.on("chat_response", (data : any) => {
      setFullText(prev => prev + data["message"]);
      fullTextRef.current += data["message"];
      if (!fullTextTimeRef.current) fullTextTimeRef.current = getCurrentTime();
    })

    socket.on("stream_end", (data : any) => {
      setWaitingForResponse(false);
      const temp = fullTextRef.current;
      const tempTime = fullTextTimeRef.current;
      setMessages(prev => [...prev, { type: "AI", content: temp, time: tempTime }]);

      setFullText("");
      fullTextRef.current = "";
      fullTextTimeRef.current = "";
    })

    socket.on("face_recognition_ans", (data : any) => {
      setEmotions(prev => [...prev, {time: getCurrentTime(), emotion: data["message"]}]);
    });

    return () => {
      socket.off("connect");
      socket.off("disconnect");
      socket.off("audio_ans");
      socket.off("chat_response");
      socket.off("stream_end");
      socket.off("face_recognition_ans");
    }

  }, []);

  useEffect(() => {
    if (!isRecording) return;

    const frameInterval = setInterval(async () => {
      
      if (!vidRef.current || !vidRef.current.srcObject) return;

      const canvas = canvasRef.current;
      if (!canvas) return;
      const context = canvas.getContext('2d');
      if (!context) return;

      canvas.width = vidRef.current.videoWidth;
      canvas.height = vidRef.current.videoHeight;

      context.drawImage(vidRef.current, 0, 0);
      canvas.toBlob(async (blob) => {
        const buf = await blob?.arrayBuffer();

        socket.emit("face_recognition", {
          "image_data": buf,
        });

      }, 'image/jpeg', 0.95);

    }, 30000);

    return () => {
      clearInterval(frameInterval);
    };
  }, [isRecording]);

  const startRecording = async () => {

    stream.current = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });

    audioCtx.current = new AudioContext({ sampleRate: 16000 });
    audioCtx.current.resume();

    vidRecorder.current = new MediaRecorder(stream.current);

    vidRef.current!.srcObject = stream.current;

    vidRecorder.current.ondataavailable = async (event) => {
      if (event.data && event.data.size > 0) {
        const buf = await event.data.arrayBuffer();
        socket.emit("video", {
          "video_data": buf,
        });
      }
    }
    vidRecorder.current.start(1000)

    input.current = audioCtx.current.createMediaStreamSource(stream.current);
    processor.current = audioCtx.current.createScriptProcessor(4096, 1, 1);
    
    processor.current.onaudioprocess = async (e) => {
      const data = e.inputBuffer.getChannelData(0);
      sendChunkToServer(data);
    };
    input.current?.connect(processor.current);
    processor.current?.connect(audioCtx.current.destination);
    setIsRecording(true);
    socket.emit("start")
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
    socket.emit("audio", {
      "audio_data": blob,
    });
  }

  function textMessageHandler(event: any) {
    if (waitingForResponse) return

    if (message.trim() === "") {
      return
    }

    setMessages([...messages, {type: "User", content: message, time: getCurrentTime()}]);
    socket.emit("chat_message", { message, title, transcription: transcription.map((obj) => {
      return `${obj.time} ${obj.text}`;
    }).join("\n"), history: messages.slice(-10) });
    setMessage("");
  }

  if (titleSet)
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", width: "100vw" }}>
        <canvas ref={canvasRef} style={{display: "none"}}></canvas>
        <div style={{ marginBottom: "16px" }}>
          <button onClick={async () => {
            if (!isRecording) startRecording();
            else stopRecording();
          }} style={{ backgroundColor: isRecording ? "red" : "green" }}>
            { isRecording ? "Stop" : "Start" }
          </button>
        </div>
        <video style={{ border: "1px solid black", }}
          ref={vidRef}
          muted
          autoPlay
          playsInline
          width="640"
          height="480"
        ></video>
        <EmotionWheel emotions={emotions} />
        <div style={{ marginTop: "16px", width: "90%", textAlign: "center", display: "flex", flexDirection: "row", justifyContent: "space-evenly" }}>

          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", width: "60%" }}>
            <p>Chatbox</p>
            <ChatBox messages={messages} temp={fullText} temptime={fullTextTimeRef.current} />
            <div style={{ marginTop: "16px", width: "100%" }}>
              <input onKeyDown={(e) => {
                if (e.key === "Enter") {
                  textMessageHandler(e);
                }
              }} style={{ height: "100%", width: "50%", marginRight: "8px" }} type="text" value={message} onChange={(e) => setMessage(e.target.value)} />
              <button onClick={textMessageHandler} disabled={waitingForResponse}>Send</button>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "left", width: "40%", margin: 0 }}>
            <p>Transcription</p>
            <TranscriptionBox messages={transcription} />
          </div>

        </div>
        <button onClick={() => {
          console.log(messages);
        }} style={{ marginTop: "16px" }}>debug</button>
      </div>
    )
  else return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100vh", width: "100vw" }}>
      <input style={{ marginBottom: "16px", padding: "8px", fontSize: "16px", width: "80%" }} type="text" value={title} onChange={(e) => setTitle(e.target.value)} />
      <button onClick={() => setTitleSet(true)}>Set Title</button>
    </div>
  )
}

export default App
