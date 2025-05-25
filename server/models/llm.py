from llama_cpp import Llama

llm = Llama.from_pretrained(
    repo_id="hungqbui/medgemma-4b-it-Q4_K_M-GGUF",
    filename="*q4_k_m.gguf"
)

def llm_answer(question, history=None, context=None):

    prompt = "".join([f"{i.type}: {i.content}\n" for i in history]) if history else ""

    prompt += f"User: {question}\nAI:"

    

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
            {"role": "user", "content": prompt},
        ],
        response_format={
            "type": "json_object",
        },
    )

    print("LLM output:", out)

    return out