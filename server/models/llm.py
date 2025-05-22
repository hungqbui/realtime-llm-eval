from llama_cpp import Llama

llm = Llama.from_pretrained(
    repo_id="ZiangWu/MobileVLM_V2-1.7B-GGUF",
    filename="*q8_k.gguf"
)

out = llm("What is the capital of France?", max_tokens=10, stop=["Q:", "\n"], echo=True)

print(out)