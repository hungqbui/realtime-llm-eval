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

def llm_answer(question, history=None, context=None):

    prompt = [{
        "role": "system" if h.get("type") == "AI" else "user",
        "content": h.get("content") 
    } for h in history] if history else []

    prompt.append({
        "role": "user",
        "content": question
    })

    messages=[
            {
                "role": "system",
                "content": "You are a helpful medical assistant for doctors by answering questions in the context of a conversation between the doctor with their patient based on the context of the given transcription.",
            },
            {
                "role": "user",
                "content": f"This is the conversation up-to this point: {context}" if context else "No transcription has been made.",
            },
            {
                "role": "system",
                "content": "Thank you for the context. I am now aware of the details of the conversation and ready to answer any questions.",
            },
            *prompt
        ]

    out = llm.create_chat_completion(
        messages=messages,
        stream=True
    )

    return out
        
