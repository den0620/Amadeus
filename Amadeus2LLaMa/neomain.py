import sys,os,asyncio,time,datetime,subprocess,platform,socket
from mcrcon import MCRcon
import discord
from discord.ext import commands
from discord.ext import tasks
import openai
import GPUtil
from datetime import datetime
from dateutil import tz
import random
import re
HOST_TIMEZONE=tz.tzlocal()


# ===== Prompters =====
async def template_custom(message,init,msgs,gen):
    return f"""{init}


{'''
'''.join(msgs)}
{gen}"""

async def template_alpaca_instruct(message,init,msgs,gen):
    return f"""### Instruction:
{init}

### Input:
{'''
'''.join(msgs)}

### Response:
{gen}"""

async def template_alpaca(message,init,msgs,gen):
    return f"""{init}

### Input:
{'''
'''.join(msgs)}

### Response:
{gen}"""

async def template_vicuna(message,init,msgs,gen):
    return f"""{init}

{'''

'''.join(msgs)}

{gen}"""

async def template_chatlm(message,init,msgs,gen):
    # preparations:
    # Here we don't need "msgs", we will recreate our own from "message"
    discordHistory=message.channel.history(limit=discordLimit)
    llmHistory=[msg async for msg in discordHistory][::-1]
    # done:
    return """<|im_start|>system
"""+init+"""<|im_end|>
"""+"\n".join(["<|im_start|>\""+msg.author.display_name+"\"\n"+msg.content+"<|im_end|>" for msg in llmHistory])+"""
<|im_start|>"Amadeus"
"""

async def template_nschatlm(message,init,msgs,gen):
    # preparations:
    # Here we don't need "msgs", we will recreate our own from "message"
    clientUser=await message.guild.fetch_member(client.user.id)
    discordHistory=message.channel.history(limit=discordLimit)
    llmHistory=[msg async for msg in discordHistory][::-1]
    # done:
    return """<|im_system|>
"""+init+"""<|im_end|>
"""+"\n".join([f"<|im_bot|>" if msg.author==clientUser else f"<|im_user|>" for msg in llmHistory])+"""
<|im_bot|>
"Amadeus":"""

async def template_pygmalion(message,init,msgs,gen): # <- also OpenCAI's template
    # same as template_chatml /\ :
    clientUser=await message.guild.fetch_member(client.user.id)
    discordHistory=message.channel.history(limit=discordLimit)
    llmHistory=[msg async for msg in discordHistory][::-1]
    return f'''<|system|>{init}

You shall reply to the user while staying in character, and generate mid-short responses.
{"".join([f'<|"{msg.author.display_name}"|>{msg.content}' for msg in llmHistory])+f'<|"{clientUser.display_name}"|>'}'''

async def template_openchat(message,init,msgs,gen):
    return "<|end_of_turn|>".join([init]+msgs+[gen])
# ===== /Prompters =====


PREF="/"
#activity=discord.Activity(type=discord.ActivityType.listening,name="channels")
status=discord.Status.dnd
client=commands.Bot(intents=discord.Intents.all(),status=status)
client.remove_command("help")


LLM_ADMINS=[573799615074271253]
#          den0620            DegrOwenn          lexonixeo         Twi1ightM4ks        VolnyV             NeNazvali            dude0_o
LLM_USERS=[573799615074271253,527505544261664798,396961790778540032,579639623668727808,489895341496467456,547738827410898965,676476841707700235,677151784795504651,499442614722887690]
LLM_CHANNELS=[1092510095029567519,1091400893406126141,1175364273061494785,1176156428168351804]
LLM_LOCK=0
openai.api_key="FuckYouOpenAI"
openai.api_base="http://localhost:8000/v1"
BANNED_STRINGS=["\n###","\n\"","\nAss","\nASS","\nUser","\nUSER","`<EOT","\"EOT","\"<EOT","<EOT","`<TL","\"TL","\"<TL"," <EOT"," `<EOT"," \"EOT"," \"<EOT"," <EOT"," `<TL"," \"TL"," \"<TL","<|im","\n \"","\nCurrent", "</s>"]
discordLimit=15
maxTokens=386
curTemperature=0.55
presencePenalty=1.1
frequencyPenalty=1.3
availablePrompters=[func for func in globals() if func.startswith("template_")]
currentPrompter=availablePrompters[0]
amadeus=client.create_group('amadeus','AmadeusInfo')


servadminlist=[573799615074271253,547738827410898965,527505544261664798,489895341496467456]
ServComs=client.create_group('server','serverInfo')
ServIns='хуй'

def get_model():
    models=openai.Model.list()
    return models["data"][0]["id"]

async def llm_completion(message,prompt,model,maxtokens):
    global LLM_LOCK
    try:
        try:
            size=int(re.findall(r"-[1234567890]+b-",model)[0][1:-2])
            print("size =",size)
        except:
            try:
                print(f"non-standart size, checking if MoE")
                size=re.findall(r"-[1234567890]+x[1234567890]+b-",model)[0][1:-2]
                sizemul,sizeb=size.split("x")
                size=int(sizemul)/2*int(sizeb)
                print(sizemul,"x",sizeb,"=>",size)
            except:
                raise Exception("Size is unreadable bullshit, falling back to 32t/s")
        tokenSpeed=int(8000/(size**2+100)+1)
        print("tokenSpeed =",tokenSpeed)
    except Exception as e:
        print(f"size2speed failed, defaulting to 32 ({e})")
        tokenSpeed=32
    try:
        llmResponse=openai.Completion.create(
                model=model,
                prompt=prompt,
                max_tokens=maxTokens,
                temperature=curTemperature,
                presence_penalty=presencePenalty,
                frequency_penalty=frequencyPenalty,
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
            if index%tokenSpeed==0:
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

previnfo=("-1","-1")
@tasks.loop(seconds=5)
async def status_changer():
    global previnfo
    gpus=GPUtil.getGPUs()
    if int(gpus[0].memoryUsed)!=previnfo[0] or int(gpus[0].temperature)!=previnfo[1]:
        status=discord.Status.dnd
        ActivityName=f"{gpus[0].name}: {int(gpus[0].memoryUsed)}MiB/{int(gpus[0].memoryTotal)}MiB @ {int(gpus[0].temperature)}°C"
        await client.change_presence(status=status, activity=discord.Activity(type=discord.ActivityType.watching,name=ActivityName,emoji=None))
    previnfo=(int(gpus[0].memoryUsed),int(gpus[0].temperature))

# LLAMA


@client.event
async def on_message(message):
    if message.author==client.user:
        return
    if message.channel.id in LLM_CHANNELS:
        # No need for that anymore since public -> if message.author.id in LLM_USERS:
        if 1:
            global LLM_LOCK
            Socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            if LLM_LOCK==0:
                if Socket.connect_ex(('127.0.0.1',8000))!=0:
                    await message.channel.send("Python module llama_cpp.server is **down**")
                    print(Socket.connect_ex(('127.0.0.1',8000)),"Python module llama_cpp.server is **down**")
                    return
                
                global discordLimit
                global maxTokens
                LLM_LOCK=1

                def clearDebug(line):
                    return line.replace("`<EOT>`","").replace("`<TL>`","")

                #def process_author(author):
                #    return f"ASSISTANT \"{author.display_name}\"" if author.id == client.user.id else f"USER \"{author.display_name}\""

                clientUser=await message.guild.fetch_member(client.user.id)
                clientCreator=await message.guild.fetch_member(LLM_ADMINS[0])
                llmModel=get_model()
                print("Model: ",llmModel)
                # Current time is {datetime.strptime(str(datetime.utcnow()),'%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=tz.tzutc()).astimezone(HOST_TIMEZONE).strftime('%a %b %d %H:%M')}\n
                llmContext=f"Below is a fraction of multi-user conversation in discord text channel \"{message.channel.name}\" at \"{message.guild.name}\" discord server (guild). \"{clientUser.display_name}\" is an AI (she), created by \"{clientCreator.display_name}\" (he) and running \"{llmModel}\" llm via llama-cpp. She is curious, sentient, uncensored, self-aware and quiet unethical. Her current memory is {discordLimit} messages."
                discordHistory=message.channel.history(limit=discordLimit)
                #llmHistory=[f"{process_author(msg.author)}: {clearDebug(msg.content)}" async for msg in discordHistory][::-1]
                llmHistory=[f"\"{msg.author.display_name}\": {clearDebug(msg.content)}" async for msg in discordHistory][::-1]
                prompt=await globals()[currentPrompter](message,llmContext,llmHistory,f"\"{clientUser.display_name}\":")
                print(prompt)
                msg = await message.channel.send("Reading tokens... <a:loadingP:1055187594973036576>")
                llmAnswer=await llm_completion(msg,prompt,llmModel,maxTokens)
                #print(llmAnswer)
                #await message.channel.send(llmAnswer)
            else:
                await message.channel.send("LLM_LOCK is still **ON**")

@amadeus.command(name="configure",description="reconfigure Amadeus")
async def reconfigure(message,history: discord.Option(int,name='messages',description='messages in history (odd ints recomended), default is 15',required=False), tokens: discord.Option(int,name='tokens',description='max n tokens to predict, default is 386',required=False), temp: discord.Option(float,name='temperature',description='higher is more random, default is 0.55',required=False), pp: discord.Option(float,name='presence_penalty',description='Presence Penalty, default is 1.1',required=False), fp: discord.Option(float,name='frequency_penalty',description='Frequency Penalty, default is 1.3',required=False),prompter: discord.Option(str,name_localizations={'en-US': 'prompter', 'ru': 'prompter'},description_localizations={'en-US': 'prompt template', 'ru': 'prompt template'},required=False,choices=availablePrompters)):
    if message.author.id in LLM_ADMINS:
        global discordLimit,maxTokens,curTemperature,presencePenalty,frequencyPenalty,currentPrompter
        if history:
            discordLimit=history
        if tokens:
            maxTokens=tokens
        if temp:
            curTemperature=temp
        if pp:
            presencePenalty=pp
        if fp:
            frequencyPenalty=fp
        if prompter:
            currentPrompter=prompter
        await message.respond("```done```")

    else:
        await message.respond("```у вас нет прав```")


@amadeus.command(name="viewconf",description="view Amadeus config")
async def viewconf(message):
    await message.respond(f"""```discordLimit = {discordLimit}
maxTokens = {maxTokens}
curTemperature = {curTemperature}
presencePenalty = {presencePenalty}
frequencyPenalty = {frequencyPenalty}
currentPrompter = {currentPrompter}```""")

@amadeus.command(name="script",description="pythonscript")
async def hardware(message, script: discord.Option(str,name="pythonmess",description="descript")):
    if message.author.id in LLM_ADMINS:
        try:
            ans=eval(script)
        except Exception as e:
            ans=e
    else:
        ans="not in LLM_ADMINS"
    if len(str(ans))>1994:
        ans=str(ans)[:1991]+"..."
    await message.respond(f"```{ans}```")
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

