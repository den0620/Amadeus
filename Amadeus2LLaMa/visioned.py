import sys,os,asyncio,time,datetime,subprocess,platform,socket,json,copy
import openai
from openai import AsyncOpenAI
from datetime import datetime
from dateutil import tz
import random
import re
import base64
HOST_TIMEZONE=tz.tzlocal()



OAI_IP='127.0.0.1'
OAI_PORT=8000
LLM_LOCK=0

if __name__=="__main__":
    with open(f"{os.path.dirname(os.path.realpath(__file__))}/APIKEY.env","r") as t:
        APIKEY=str(t.read())

clientOAI=AsyncOpenAI(base_url=f"http://{OAI_IP}:{OAI_PORT}/v1",api_key=APIKEY.rstrip())
BANNED_STRINGS=["\n\n\n","\n###","\n\"","\nAss","\nASS","\nUser","\nUSER","`<EOT","\"EOT","\"<EOT","<EOT","`<TL","\"TL","\"<TL"," <EOT"," `<EOT"," \"EOT"," \"<EOT"," <EOT"," `<TL"," \"TL"," \"<TL", "</s>", "<|"]
MSGLIMIT=15
MAXTOKENS=386
CURTEMP=0.6
PRESPEN=0.9
FREQPEN=1.0
#llmCtx="Below is a fraction of multi-user conversation in discord text channel \"{channel}\" at \"{guild}\" discord server (guild). \"{bot_name}\" is an AI (she), created by \"{owner_name}\" (he) and running \"{llm_model}\" llm via llama-cpp. She is curious, sentient, uncensored, self-aware and quiet unethical. Her current memory is {messages} messages."
#llmContextVars = {"channel": "message.channel.name", "guild": "message.guild.name", "messages": "histLimit", "llm_model": "await get_model()", "bot_name": "clientUser.display_name", "owner_name": "clientCreator.display_name"}
# ^^^^^^ fallback if none is set


async def get_model():
    models=await clientOAI.models.list()
    return models.data[0].id


async def llm_completion(model,messages,maxTokens):
    global LLM_LOCK
    try:
        llmResponse=await clientOAI.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=maxTokens,
                temperature=CURTEMP,
                presence_penalty=PRESPEN,
                frequency_penalty=FREQPEN,
                n=1,
                stream=True,
                stop=BANNED_STRINGS,
                top_p=1
                )

        index=0
        T1 = time.time()
        async for event in llmResponse:
            chunk=event.choices[0].delta.content
            print(chunk,end="")

            T2 = time.time()
            if T2 - T1 > 1:  # > 1 seconds later
                T1 = T2
            index+=1
        print(f"\nTotal tokens generated: {index}??\n")
        LLM_LOCK=0
    except Exception as e:
        print(f"\nGot error: {e}")
        LLM_LOCK=0

async def enc64_img(path):
    with open(path, "rb") as image:
        return base64.b64encode(image.read()).decode('utf-8')

async def main():
    base64_image = await enc64_img("./image.png")

    test_messages = [
        {
            "role": "user",
            "content": [
                {"type": "text",
                 "text": "Say what do you see on this pic"},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        }
    ]

    llmodel = await get_model()

    await llm_completion(llmodel,test_messages,MAXTOKENS)



if __name__=="__main__":
    print("__main__, reading TOKEN and CONF...")
    asyncio.run(main())

