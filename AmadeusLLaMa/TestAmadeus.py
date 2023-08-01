import sys,os
from llama_cpp import Llama

llm = Llama(model_path=f"./models/ggml-wizard-vicuna-30b-q4_0.bin",n_ctx=256,n_threads=4,n_batch=128)

prompt = str(input())
while not prompt=="exit":
    print(llm(f"User: {prompt}\nAssistant:",max_tokens=64,temperature=0.75,top_p=0.85,stop=["\nUser:","\nAssistant:","\n#"],frequency_penalty=0.05,repeat_penalty=1.3,echo=False)["choices"][0]["text"])
    prompt=str(input())

