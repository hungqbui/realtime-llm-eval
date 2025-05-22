from llama_cpp import Llama

llm = Llama.from_pretrained(
    repo_id="mtgv/MobileVLM_V2-3B",
)

out = llm("What is the capital of France?", max_tokens=10, stop=["Q:", "\n"], echo=True)

print(out)