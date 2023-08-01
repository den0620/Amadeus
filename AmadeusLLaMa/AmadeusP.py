import asyncio,sys,os,discord,random,datetime
from llama_cpp import Llama
from discord.ext import commands

PREF="/"
bot=commands.Bot(intents=discord.Intents.all())
activity=discord.Activity(type=discord.ActivityType.listening,name="хентай")
status=discord.Status.dnd
client = discord.Bot(activity=activity,status=status,intents=discord.Intents.all())

gptadminlist=[573799615074271253,527505544261664798,547738827410898965,489895341496467456,579890116361977889]
creator=573799615074271253
gptchannels=[1092510095029567519,1091400893406126141]
bot.remove_command("help")
llmlock=False

model="ggml-wizard-vicuna-30b-q4_0.bin"
llm = Llama(model_path=f"{os.path.dirname(os.path.realpath(__file__))}/models/{model}",n_ctx=1024,n_gpu_layers=0,seed=0,n_threads=2,n_batch=256)

@client.event
async def on_ready():
    print("discord is up")
    
def convertUTC(UTC):
    date,time=map(str,UTC.split(" "));time=time[:time.find(".")]
    return date,time

@client.event
async def on_message(message):
    if message.author==client.user:
        return
    if message.channel.id in [1092510095029567519,1091400893406126141]:
        if message.author.id in gptadminlist:
            clientUser=await message.guild.fetch_member(client.user.id)
            clientCreator=await message.guild.fetch_member(creator)
            llmcontext=f"This is fraction of discord text channel \"{message.channel.name}\". You are {clientUser.display_name}, an AI (she) created by \"{clientCreator.display_name}\" (he). There you talk to other users. Answer as short as possible.\n\n...\n"
            discordHistory=message.channel.history(limit=9)
            #[{msg.created_at.strftime("%H:%M %d/%m/%Y")}]
            prohis=[f'User "{msg.author.display_name}": {msg.content}' async for msg in discordHistory][::-1]
            history=[]
            for line in prohis:
                if not line.endswith((".","?","!")): history+=[line+"."]
                else: history+=[line]
            prompt=llmcontext+"\n".join(history+[f'User "{clientUser.display_name}":'])
            
            print(prompt)
            llmanswer=llm(prompt, max_tokens=192, temperature=0.75, top_p=0.85, stop=["\n[0","\n[1","\n[2","\nHuman:","\n###","\nAssistant:","\nUser"], frequency_penalty=0.05, repeat_penalty=1.3, echo=False)["choices"][0]["text"]
            await message.channel.send(llmanswer)


with open('TOKEN.env', 'r') as t:
    TOKEN = str(t.read())
client.run(TOKEN)
