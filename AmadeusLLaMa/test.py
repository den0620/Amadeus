import sys,os
from llama_cpp import Llama

model="ggml-llama1-65b-instruct-q3_K_M.bin"

seed=int(input("seed="))

llm=Llama(model_path=f"{os.path.dirname(os.path.realpath(__file__))}/models/{model}",n_ctx=1024,n_gpu_layers=0,seed=seed,n_threads=4,n_batch=256)

prompt="### Human:\nНарисуй человека символами ASCII.\n### Assistant:\n"

llmanswer=llm(prompt, max_tokens=192, temperature=0.75, top_p=0.85, stop=["\n[0","\n[1","\n[2","\nHuman:","\n###","\nAssistant:","\nUser","\nuser"], frequency_penalty=0.05, repeat_penalty=1.3, echo=True)["choices"][0]["text"]

print(llmanswer)

