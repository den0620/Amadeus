import sys,os,asyncio,time,datetime
import discord
import openai
from discord.ext import commands


PREF="/"
activity=discord.Activity(type=discord.ActivityType.listening,name="channels")
status=discord.Status.dnd
client=commands.Bot(intents=discord.Intents.all(),activity=activity,status=status)

LLM_ADMINS=[573799615074271253]
#          den0620            DegrOwenn          lexonixeo         Twi1ightM4ks        VolnyV             NeNazvali
LLM_USERS=[573799615074271253,527505544261664798,396961790778540032,579639623668727808,489895341496467456,547738827410898965]
LLM_CHANNELS=[1092510095029567519]
LLM_LOCK=0

client.remove_command("help")


openai.api_key="FuckYouOpenAI"
openai.api_base="http://192.168.1.82:8000/v1"
BANNED_STRINGS=["\n###","\n\"","\nAss","\nASS","\nUser","\nUSER","`<EOT","\"EOT","\"<EOT","<EOT","`<TL","\"TL","\"<TL","<EOS","`<EOS","\"EOS","\"<EOS","<EOS"]

def get_model():
    models=openai.Model.list()
    return models["data"][0]["id"]


async def llm_completion(message,prompt,model,maxtokens):
    global LLM_LOCK
    try:
        llmResponse=openai.Completion.create(
                model=model,
                prompt=prompt,
                max_tokens=maxtokens,
                temperature=0.6,
                presence_penalty=1,
                frequency_penalty=1.5,
                n=1,
                echo=False,
                stream=True,
                stop=BANNED_STRINGS
                )
        full_content=""
        old_content=""
        tokens=0
        for index,event in enumerate(llmResponse):
            print(event["choices"][0]["text"],end="")
            full_content+=event["choices"][0]["text"]
            tokens+=1
            if index%8==0:
                try:
                    message=await message.edit(full_content[len(old_content):])
                except:
                    old_content=message.content
                    message=await message.channel.send(full_content[len(old_content):])
        if maxtokens==tokens or maxtokens-1==tokens:
            message=await message.edit(full_content[len(old_content):]+" `<TL>`")
        else:
            message=await message.edit(full_content[len(old_content):]+" `<EOT>`")
        print(f"\nTotal tokens generated: {tokens}\n")
        LLM_LOCK=0
    except Exception as e:
        print(e)
        await message.edit(f"```{e}```")
        LLM_LOCK=0
        

    #response_msg=llmResponse["choices"][0]["text"]
    #return response_msg


@client.event
async def on_ready():
    phrase="PyCord Is Up"
    print("\n".join(["/"+"-"*(len(phrase))+"\\","|"+f"{phrase}"+"|","\\"+"-"*(len(phrase))+"/"]))

@client.event
async def on_message(message):
    if message.author==client.user:
        return
    if message.channel.id in LLM_CHANNELS:
        if message.author.id in LLM_USERS:
            global LLM_LOCK
            if LLM_LOCK==0:
                LLM_LOCK=1
                clientUser=await message.guild.fetch_member(client.user.id)
                clientCreator=await message.guild.fetch_member(LLM_ADMINS[0])
                discordLimit=15
                maxTokens=386
                llmModel=get_model()
                print("Model: ",llmModel)
                llmContext=f"This is fraction of discord text channel \"{message.channel.name}\" at \"{message.guild.name}\" discord server (guild). \"{clientUser.display_name}\" is an AI (she), created by \"{clientCreator.display_name}\" (he) and running \"{llmModel}\" llm via llama-cpp. Her current memory is {discordLimit} messages.\n\n"
                discordHistory=message.channel.history(limit=discordLimit)
                llmHistory=[f"\"{msg.author.display_name}\": {msg.content}" async for msg in discordHistory][::-1]
                prompt=llmContext+"\n".join(llmHistory+[f"\"{clientUser.display_name}\":"])
                print(prompt)
                msg = await message.channel.send("Reading tokens... <a:loadingP:1055187594973036576>")
                llmAnswer=await llm_completion(msg,prompt,llmModel,maxTokens)
                #print(llmAnswer)
                #await message.channel.send(llmAnswer)


if __name__=="__main__":
    print("__main__, reading TOKEN...")
    with open(f"{os.path.dirname(os.path.realpath(__file__))}/TOKEN.env","r") as t:
        TOKEN=str(t.read())
    print("Starting discord instance...")
    client.run(TOKEN)

