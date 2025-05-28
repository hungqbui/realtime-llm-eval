from llama_cpp import Llama
from concurrent.futures import ProcessPoolExecutor

try:
    llm = Llama.from_pretrained(
        repo_id="hungqbui/medgemma-4b-it-Q4_K_M-GGUF",
        filename="*q4_k_m.gguf",
        verbose=False,
        n_ctx=131072,
    )
except Exception as e:
    print(f"Error loading LLM model: {e}")
    llm = None

async def llm_answer(question, socket, sid, history=None, context=None):

    prompt = "".join([f"{i.get('type')}: {i.get('content')}\n" for i in history]) if history else ""

    prompt += f"User: {question}\nAI:"

    print(context)

    out = llm.create_chat_completion(
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that answers questions of a conversation base on the context of the transcription.",
            },
            {
                "role": "user",
                "content": f"This is the conversation: {context}" if context else "No context provided.",
            },
            {
                "role": "system",
                "content": "Thank you for the context. I am now aware of the details of the conversation and ready to answer any questions.",
            },
            {"role": "user", "content": prompt},
        ],
        stream=True
    )

    for chunk in out:
        if "choices" not in chunk or not chunk["choices"]:
            continue
        if "delta" not in chunk["choices"][0] or "content" not in chunk["choices"][0]["delta"]:
            continue
        
        await socket.emit("chat_response", {"message": chunk["choices"][0]["delta"]["content"]}, to=sid)

        print(chunk["choices"][0]["delta"]["content"], end="", flush=True)


    await socket.emit("stream_end", {}, to=sid)
