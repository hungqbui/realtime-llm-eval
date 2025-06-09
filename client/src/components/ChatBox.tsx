import { useEffect, useRef } from 'react'
import "./ChatBox.css"
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize';

function ChatBox(props : any) {

    const end = useRef<HTMLDivElement>(null);
    useEffect(() => {
        if (end.current) {
            // Find the chat container and scroll it directly
            const chatContainer = end.current.closest('.chat-container');
            if (chatContainer instanceof HTMLElement) {
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        }
    }, [props]);

    return (
        <div className="chat-container">
            {props.messages.map((msg : any, index : any) => (
              <div style={{ width: "80%", marginLeft: "40px", marginBottom: "20px" }} key={index}><div className={`message-header`} >{msg.type} {msg.time}</div><div className={msg.type == "User" ? "user" : "ai"} >
                    <ReactMarkdown rehypePlugins={[rehypeSanitize]} >{msg.content}</ReactMarkdown>
                </div></div>
            ))}
            { props.temp && <div style={{ width: "80%", marginLeft: "40px", marginBottom: "20px" }}><div className={`message-header`}>AI {props.temptime}</div><div className="ai" >
                <ReactMarkdown rehypePlugins={[rehypeSanitize]}>{props.temp}</ReactMarkdown>
                </div></div>}
            <div ref={end}></div>
        </div>
    )
}

export default ChatBox;