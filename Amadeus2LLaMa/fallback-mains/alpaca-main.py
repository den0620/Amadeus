import sys,os,asyncio,time,datetime,subprocess,platform,socket
from mcrcon import MCRcon
import discord
from discord.ext import commands
from discord.ext import tasks
import openai
import GPUtil


PREF="/"
#activity=discord.Activity(type=discord.ActivityType.listening,name="channels")
status=discord.Status.dnd
client=commands.Bot(intents=discord.Intents.all(),status=status)
client.remove_command("help")


LLM_ADMINS=[573799615074271253]
#          den0620            DegrOwenn          lexonixeo         Twi1ightM4ks        VolnyV             NeNazvali
LLM_USERS=[573799615074271253,527505544261664798,396961790778540032,579639623668727808,489895341496467456,547738827410898965,676476841707700235]
LLM_CHANNELS=[1092510095029567519]
LLM_LOCK=0
openai.api_key="FuckYouOpenAI"
openai.api_base="http://localhost:8000/v1"
BANNED_STRINGS=["\n###","\n\"","\nAss","\nASS","\nUser","\nUSER","`<EOT","\"EOT","\"<EOT","<EOT","`<TL","\"TL","\"<TL"," <EOT"," `<EOT"," \"EOT"," \"<EOT"," <EOT"," `<TL"," \"TL"," \"<TL","<|im","\n \""]


servadminlist=[573799615074271253,547738827410898965,527505544261664798,489895341496467456]
ServComs=client.create_group('server','serverInfo')
ServIns='хуй'

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
                temperature=0.55,
                presence_penalty=1,
                frequency_penalty=1.3,
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
            if index%16==0:
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
    status_changer.start()


@tasks.loop(seconds=3.0,reconnect=False)
async def status_changer():
    gpus = GPUtil.getGPUs()
    status=discord.Status.dnd
    ActivityName=f"{gpus[0].name}: {int(gpus[0].memoryUsed)}MiB/{int(gpus[0].memoryTotal)}MiB @ {int(gpus[0].temperature)}°C"
    await client.change_presence(status=status, activity=discord.Activity(type=discord.ActivityType.watching,name=ActivityName,emoji=None))

# LLAMA


@client.event
async def on_message(message):
    if message.author==client.user:
        return
    if message.channel.id in LLM_CHANNELS:
        if message.author.id in LLM_USERS:
            global LLM_LOCK
            Socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            if LLM_LOCK==0:
                if Socket.connect_ex(('127.0.0.1',8000))!=0:
                    await message.channel.send("Python module llama_cpp.server is **down**")
                    print(Socket.connect_ex(('127.0.0.1',8000)),"Python module llama_cpp.server is **down**")
                    return

                LLM_LOCK=1
                
                clientUser=await message.guild.fetch_member(client.user.id)
                clientCreator=await message.guild.fetch_member(LLM_ADMINS[0])

                def clearDebug(line):
                    return line.replace("`<EOT>`","").replace("`<TL>`","")
                def alpacanize(member,content):
                    if member==clientUser.display_name:
                        temp="Responce"
                    else:
                        temp="Instruction"
                    return f"### {temp}:\n{content}\n"

                #def process_author(author):
                #    return f"ASSISTANT \"{author.display_name}\"" if author.id == client.user.id else f"USER \"{author.display_name}\""

                discordLimit=1
                maxTokens=768
                llmModel=get_model()
                print("Model: ",llmModel)
                llmContext=f"Below is a fraction of discord text channel \"{message.channel.name}\" at \"{message.guild.name}\" discord server (guild). You are \"{clientUser.display_name}\", an AI (she), created by \"{clientCreator.display_name}\" (he) and running \"{llmModel}\" llm via llama-cpp. Your current memory is {discordLimit} messages.\n\n"
                discordHistory=message.channel.history(limit=discordLimit)
                #llmHistory=[f"{process_author(msg.author)}: {clearDebug(msg.content)}" async for msg in discordHistory][::-1]
                llmHistory=[alpacanize(msg.author.display_name,clearDebug(msg.content)) async for msg in discordHistory][::-1]
                prompt=llmContext"\n".join(llmHistory+[f"### Response:\n"])
                print(prompt)
                msg = await message.channel.send("Reading tokens... <a:loadingP:1055187594973036576>")
                llmAnswer=await llm_completion(msg,prompt,llmModel,maxTokens)
                #print(llmAnswer)
                #await message.channel.send(llmAnswer)
            else:
                await message.channel.send("LLM_LOCK is still **ON**")


# SERVER


@ServComs.command(name_localizations={'en-US':'list','ru':'список'},description_localizations={'en-US':'list available servers','ru':'list av servs'})
async def servlist(message):
    ServList={}
    MaxLen=len(sorted(os.listdir('/mnt/raid1/mcSERVERS'))[-1])
    for i in os.listdir('/mnt/raid1/mcSERVERS'):
        for j in os.listdir(f'/mnt/raid1/mcSERVERS/{i}'):
            if j.endswith('.jar'):
                ServList[i]=j
    for i in ServList:
        OutPut=[str(i+' '*(MaxLen-len(i))+' > '+ServList[i]) for i in ServList]
    await message.respond('```'+"\n".join(OutPut)+'```')
    
    
async def ConnectToVoiceChannel(message):
    try:
        VoiceChannel=message.author.voice.channel
        await VoiceChannel.connect()
        Voice=discord.utils.get(client.voice_clients,guild=message.guild)
        return('Directly')
    except:
        try:
            Voice=message.author.guild.get_member(client.user.id).voice.channel
            if Voice==VoiceChannel:
                Voice=discord.utils.get(client.voice_clients,guild=message.guild)
                Voice.stop()
                return('AlreadyIn')
            else:
                Voice=discord.utils.get(client.voice_clients,guild=message.guild)
                await Voice.disconnect()
                await VoiceChannel.connect()
            return('Moved')
        except:
            return('NotConnected')

@client.command(name="name",description="description")
async def join(message):
    ans = await ConnectToVoiceChannel(message)
    if ans == "NotConnected": await message.respond("EC 1")
    else: await message.respond("EC 0")
        
@ServComs.command(name_localizations={'en-US':'status','ru':'статус'},description_localizations={'en-US':'status','ru':'статус'})
async def status(message):
    if ServIns=='хуй' or ServIns.poll()!=None:
        await message.respond('stopped')
    elif ServIns.poll()==None:
        await message.respond(f'running > {RunServName}')

@ServComs.command(name_localizations={'en-US':'toggle','ru':'переключить'},description_localizations={'en-US':'Change server state (2-16Gb, 6)','ru':'Изменить состояние сервера (2-16гб, 6)'})
async def toggle(message,server: discord.Option(str,name_localizations={'en-US': 'name', 'ru': 'название'},description_localizations={'en-US': 'server name', 'ru': 'имя сервера'},required=True,choices=os.listdir(f'/mnt/raid1/mcSERVERS')), mem: discord.Option(int,name_localizations={'en-US': 'mem', 'ru': 'память'},description_localizations={'en-US': 'MB RAM', 'ru': 'Мбайт ОЗУ'},required=False)=6144):
    if message.author.id in servadminlist:
        global ServIns, RunServName
        serverexe=list(filter(lambda x: x.endswith('.jar'),os.listdir(f'/mnt/raid1/mcSERVERS/{server}')))[0]
        if mem>16384: await message.respond("хули тут так много"); return
        elif mem<2048: await message.respond("хули тут так мало"); return
        SerStartInp=["/usr/bin/java", f"-Xmx{mem}M", f"-Xms{mem}M", "-jar" ,f"{serverexe}", "nogui"]
        if ServIns=='хуй' or ServIns.poll()!=None:
            await message.respond('now running')
            RunServName = server
            ServIns = subprocess.Popen(SerStartInp,stdin=subprocess.PIPE,stdout=subprocess.PIPE,cwd=rf"/mnt/raid1/mcSERVERS/{server}")
        elif ServIns.poll()==None:
            await message.respond('already running')
    else:
        await message.respond(f'Ваш IQ был определен как недостаточный\nК сожалению вы не были допущены к управлению состоянием сервера mcJE\n\nПросьба связаться с детдомом для получения консультации если вы считаетсе, что это ошибка. При обращении просим вас указать код инцидента : {str(random.choice(["GAD","HUI","HUY","PIZ","GAY","GEY","ZAL","UPA","DAV","GOV"]))+str("{:06}".format(random.randint(1, 999999)))}')

# ======

@ServComs.command(name_localizations={'en-US':'send','ru':'отправить'},description_localizations={'en-US':'Send stdin to terminal','ru':'Отправить stdin в терминал'})
async def send(message,stdmess: discord.Option(str,name_localizations={'en-US': 'std', 'ru': 'строка'},description_localizations={'en-US': 'stdin input', 'ru': 'stdin ввод'},required=True)):
    if message.author.id in servadminlist:
        global ServIns, RunServName
        if ServIns=='хуй' or ServIns.poll()!=None:
            await message.respond('stopped')
        elif ServIns.poll()==None:
            with MCRcon('localhost','vladgad') as mcr:
                resp=mcr.command(stdmess)
                if not resp=="":
                    await message.respond(resp)
                else:
                    await message.respond("EC0")
    else:
        await message.respond(f'Ваш IQ был определен как недостаточный\nК сожалению вы не были допущены к управлению терминалом сервера mcJE\n\nПросьба связаться с детдомом для получения консультации если вы считаетсе, что это ошибка. При обращении просим вас указать код инцидента : {str(random.choice(["GAD","HUI","HUY","PIZ","GAY","GEY","ZAL","UPA","DAV","GOV"]))+str("{:06}".format(random.randint(1, 999999)))}')
@client.event
async def on_voice_state_update(member,before,after):
        if after.channel==None:
                try:
                        VoiceChannel=member.guild.voice_client.channel
                        Voice=discord.utils.get(client.voice_clients,guild=member.guild)
                        if Voice!=None:
                                if len(VoiceChannel.members)<=1:
                                        await Voice.disconnect()
                except:
                        None


if __name__=="__main__":
    print("__main__, reading TOKEN...")
    with open(f"{os.path.dirname(os.path.realpath(__file__))}/TOKEN.env","r") as t:
        TOKEN=str(t.read())
    print("Starting discord instance...")
    client.run(TOKEN)

