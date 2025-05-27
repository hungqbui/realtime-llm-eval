from llama_cpp import Llama

llm = Llama.from_pretrained(
    repo_id="hungqbui/medgemma-4b-it-Q4_K_M-GGUF",
    filename="*q4_k_m.gguf",
    verbose=False,
    n_ctx=131072,
)

def llm_answer(question, history=None, context=None):

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
    )

    print("LLM output:", out)

    return out.get("choices")[0].get("message").get("content").strip() if out.choices else "No response from LLM."