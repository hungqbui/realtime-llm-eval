from llama_cpp import Llama

llm = Llama.from_pretrained(
    repo_id="hungqbui/medgemma-4b-it-Q4_K_M-GGUF",
    filename="*q4_k_m.gguf"
)

out = llm("What is the capital of France?", max_tokens=10, stop=["Q:", "\n"], echo=True)

print(out)