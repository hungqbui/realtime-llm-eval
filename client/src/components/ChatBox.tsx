import { useEffect, useRef } from 'react'
import "./ChatBox.css"
import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize';

function ChatBox(props : any) {

    const end = useRef<HTMLDivElement>(null);
    useEffect(() => {
        end.current?.scrollIntoView({ behavior: "smooth" });
    }, [props]);

    return (
        <div className="chat-container">
            {props.messages.map((msg : any, index : any) => (
              <div style={{ width: "80%" }} key={index}><div style={{ fontWeight: "bold", width: "80%", display: "flex" }}>{msg.type}</div><span style={{ textAlign: "left" }}>
                    <ReactMarkdown rehypePlugins={[rehypeSanitize]}>{msg.content}</ReactMarkdown>
                </span></div>
            ))}
            { props.temp && <div style={{ width: "80%" }}><div style={{ fontWeight: "bold", width: "80%", display: "flex" }}>AI</div><span style={{ textAlign: "left" }}>
                <ReactMarkdown rehypePlugins={[rehypeSanitize]}>{props.temp}</ReactMarkdown>
                </span></div>}
            <div ref={end}></div>
        </div>
    )
}

export default ChatBox;