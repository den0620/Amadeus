import sys,os,asyncio,time,datetime,subprocess,platform,socket
import openai
import GPUtil

openai.api_key="FuckYouOpenAI"
openai.api_base="http://localhost:8000/v1"
BANNED_STRINGS=["\n###","\n\"","\nAss","\nASS","\nUser","\nUSER","`<EOT","\"EOT","\"<EOT","<EOT","`<TL","\"TL","\"<TL"," <EOT"," `<EOT"," \"EOT"," \"<EOT"," <EOT"," `<TL"," \"TL"," \"<TL","<|im","\n \""]

def get_model():
    models=openai.Model.list()
    return models["data"][0]["id"]

def llm_completion(prompt,model,maxtokens):
    try:
        llmResponse=openai.Completion.create(
                model=model,
                prompt=prompt,
                max_tokens=maxtokens,
                temperature=0.55,
                presence_penalty=1,
                frequency_penalty=1.3,
                n=1,
                echo=False,
                stream=True,
                stop=BANNED_STRINGS
                )
        tokens=0
        for index,event in enumerate(llmResponse):
            print(event["choices"][0]["text"],end="")
            tokens+=1
        if maxtokens==tokens or maxtokens-1==tokens:
            print("\nTokenLimit")
        else:
            print("\nEndOfSentence")
        print(f"\nTotal tokens generated: {tokens}\n")
    except Exception as e:
        print(e)
        

    #response_msg=llmResponse["choices"][0]["text"]
    #return response_msg

if __name__=="__main__":
    while 1:
        IN=str(input("IN = "))
        print(llm_completion(IN,get_model(),256))

