from llama_cpp import Llama

llm = Llama.from_pretrained(
    repo_id="hungqbui/medgemma-4b-it-Q4_K_M-GGUF",
    filename="*q4_k_m.gguf"
)

out = llm.create_chat_completion(
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant that outputs in JSON.",
        },
        {"role": "user", "content": "Who won the world series in 2020"},
    ],
    response_format={
        "type": "json_object",
    },
)
print(out)