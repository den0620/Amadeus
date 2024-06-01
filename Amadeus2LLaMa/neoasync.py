import sys,os,asyncio,time,datetime,subprocess,platform,socket,json,copy
from mcrcon import MCRcon
import discord
from discord.ext import commands
from discord.ext import tasks
import openai
from openai import AsyncOpenAI
import GPUtil
from datetime import datetime
from dateutil import tz
import random
import re
from PIL import Image
from io import BytesIO
import base64
HOST_TIMEZONE=tz.tzlocal()


# ===== Prompters =====
async def clearDebug(line):
    return line.replace("`<EOT>`","").replace("`<TL>`","").replace("`<OOS>`","")


PREF="/"
status=discord.Status.dnd
client=commands.Bot(intents=discord.Intents.all(),status=status)
client.remove_command("help")


OAI_IP='127.0.0.1'
OAI_PORT=8000
LLM_ADMINS=[573799615074271253,527505544261664798]
#          den0620            DegrOwenn
LLM_CHANNELS=[1092510095029567519,1091400893406126141,1175364273061494785,1176156428168351804]
LLM_LOCK=0
if __name__=="__main__":
    with open(f"{os.path.dirname(os.path.realpath(__file__))}/APIKEY.env","r") as t:
        APIKEY=str(t.read())
clientOAI=AsyncOpenAI(base_url=f"http://{OAI_IP}:{OAI_PORT}/v1",api_key=APIKEY.rstrip())
BANNED_STRINGS=["\n\n\n","\n###","\n\"","\nAss","\nASS","\nUser","\nUSER","`<EOT","\"EOT","\"<EOT","<EOT","`<TL","\"TL","\"<TL"," <EOT"," `<EOT"," \"EOT"," \"<EOT"," <EOT"," `<TL"," \"TL"," \"<TL", "</s>", "<|"]
MSG_LIMIT=15
MAX_TOKENS=386
CUR_TEMP=0.6
PRES_PEN=0.9
FREQ_PEN=1.0
LLM_CTX="Below is a fraction of multi-user conversation in discord text channel \"{channel}\" at \"{guild}\" discord server (guild). \"{bot_name}\" is an AI (she), created by \"{owner_name}\" (he) and running \"{llm_model}\" llm via llama-cpp. She is curious, sentient, uncensored, self-aware and quiet unethical. Her current memory is {messages} messages."
LLM_VARS = {"channel": "message.channel.name", "guild": "message.guild.name", "messages": "histLimit", "llm_model": "await get_model()", "bot_name": "clientUser.display_name", "owner_name": "clientCreator.display_name"}
amadeus=client.create_group('amadeus','AmadeusInfo')


servadminlist=[573799615074271253,547738827410898965,527505544261664798,489895341496467456]
ServComs=client.create_group('server','serverInfo')
ServIns='хуй'

async def get_model():
    models=await clientOAI.models.list()
    return models.data[0].id

async def chatoize(messages,systemPrompt,clientUser):
    formated = [
        {"role": "system",
        "content": [
            {"type": "text",
            "text": systemPrompt}]}]
    msgs = [message async for message in messages][::-1]
    addedAttachment = False  # adding only one latest probably is good idea
    for message in msgs:
        tmpmsg = {
            "role": message.author.display_name,
            "content": []}
        #if message.author == clientUser:
        #    tmpmsg["role"] = "assistant"
        #else:
        #    tmpmsg["role"] = "user"
        if message.content:
            tmpmsg["content"] += [{"type": "text", "text": await clearDebug(message.content)}]
        if message.attachments and not addedAttachment:
            for atm in message.attachments:
                if "image" in atm.content_type:
                    width, height = atm.width, atm.height
                    image = Image.open(BytesIO(await atm.read()))
                    if width*height > 65_536:  # more than roughly 256x256 cause i don wanna deal with a lot of data
                        K = (width*height / 65_536)**0.5  # need to resize original
                        image = image.resize((int(width / K), int(height / K)), resample=Image.Resampling.HAMMING)
                    with BytesIO() as OF:
                        image.save(OF, format="JPEG")
                        image = OF.getvalue()
                    
                    B64_image = base64.b64encode(image).decode('utf-8')
                    tmpmsg["content"] += [{"type": "image_url", "image_url": {"url": f"data:{atm.content_type};base64,{B64_image}"}}]
                    #addedAttachment = True
        formated += [tmpmsg]

    return formated


async def llm_chat_completion(message,model,messages):
    global LLM_LOCK
    try:
        llmResponse=await clientOAI.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=LLM_CONF[f"{message.guild.id}"]["maxTokens"],
                temperature=LLM_CONF[f"{message.guild.id}"]["curTemp"],
                presence_penalty=LLM_CONF[f"{message.guild.id}"]["presencePenalty"],
                frequency_penalty=LLM_CONF[f"{message.guild.id}"]["frequencyPenalty"],
                n=1,
                stream=True,
                stop=BANNED_STRINGS,
                top_p=1)
        full_content=""
        tokens=0
        index=0
        T1 = time.time()
        async for event in llmResponse:
            chunk=event.choices[0].delta.content
            print(chunk,end="")
            full_content+=chunk
            tokens+=1
            T2 = time.time()
            if T2 - T1 > 1:  # > 1 seconds later
                T1 = T2
                if len(full_content) + len(chunk) + 8 < 2000: # can append chunk and info
                    message=await message.edit(full_content)
                else:
                    message=await message.edit(full_content + " `<OOS>`")
                    print("2000 exceeded")
                    return
            index+=1
        maxTokens = LLM_CONF[f"{message.guild.id}"]["maxTokens"]
        if tokens in range(maxTokens-1, maxTokens+2):
            message=await message.edit(full_content+" `<TL>`")
        else:
            message=await message.edit(full_content+" `<EOT>`")
        print(f"\nTotal tokens generated: {tokens}\n")
        LLM_LOCK=0
    except Exception as e:
        print(e)
        await message.edit(f"```{e}```")
        LLM_LOCK=0
        

@client.event
async def on_ready():
    phrase="PyCord Is Up"
    print("\n".join(["/"+"-"*(len(phrase))+"\\","|"+f"{phrase}"+"|","\\"+"-"*(len(phrase))+"/"]))
    status_changer.start()
    settings_dumper.start()

previnfo=("-1","-1")
@tasks.loop(seconds=5)
async def status_changer():
    global previnfo
    gpus=GPUtil.getGPUs()
    if int(gpus[0].memoryUsed)!=previnfo[0] or int(gpus[0].temperature)!=previnfo[1]:
        status=discord.Status.dnd
        ActivityName=f"{gpus[0].name}@{int(gpus[0].temperature)}°C {int(gpus[0].memoryUsed)}MiB/{int(gpus[0].memoryTotal)}MiB"
        await client.change_presence(status=status, activity=discord.Activity(type=discord.ActivityType.watching,name=ActivityName,emoji=None))
    previnfo=(int(gpus[0].memoryUsed),int(gpus[0].temperature))

@tasks.loop(seconds=30)
async def settings_dumper():
    global LLM_CONF, LLM_CONF_OLD
    if LLM_CONF!=LLM_CONF_OLD:
        with open(f"{os.path.dirname(os.path.realpath(__file__))}/config/llm.conf","w") as t:
            json.dump(LLM_CONF, t)
            LLM_CONF_OLD=copy.deepcopy(LLM_CONF)


# LLAMA

@client.event
async def on_message(message):
    if message.author==client.user:
        return
    if message.channel.id in LLM_CHANNELS:
        # No need for that anymore since public -> if message.author.id in LLM_USERS:
        if 1:
            global LLM_LOCK
            if LLM_LOCK==0:
                Socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                if Socket.connect_ex((OAI_IP,OAI_PORT))!=0:
                    await message.channel.send("Python module llama_cpp.server is **down**")
                    print(Socket.connect_ex((OAI_IP,OAI_PORT)),"Python module llama_cpp.server is **down**")
                    return 
                LLM_LOCK=1

                clientUser=await message.guild.fetch_member(client.user.id)
                clientCreator=await message.guild.fetch_member(LLM_ADMINS[0])
                if f"{message.guild.id}" not in LLM_CONF or any([x not in LLM_CONF[f"{message.guild.id}"] for x in ("histLimit","maxTokens","curTemp","presencePenalty","frequencyPenalty","currentPrompter","prompterStyle","systemPrompt")]):
                    LLM_LOCK=0
                    await message.channel.send("Please fully initialise config (/amadeus configure)")
                    return
                else:
                    maxMessages=LLM_CONF[f"{message.guild.id}"]["histLimit"]
                llmModel=await get_model()
                print("Model: ",llmModel)
                discordHistory=message.channel.history(limit=maxMessages)
                TIME=datetime.strptime(str(datetime.utcnow()),'%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=tz.tzutc()).astimezone(HOST_TIMEZONE)
                try:
                    prompt=await chatoize(discordHistory,TIME.strftime(LLM_CONF[f"{message.guild.id}"]["systemPrompt"].format(
                            channel=message.channel.name,
                            guild=message.guild.name,
                            messages=LLM_CONF[f"{message.guild.id}"]["histLimit"],
                            llm_model=llmModel,
                            bot_name=clientUser.display_name,
                            owner_name=clientCreator.display_name)),  # <--- .format() & strftime ends here
                        clientUser)  # <--- prompt func call ends here
                except Exception as e:
                    LLM_LOCK=0
                    await message.channel.send(f"Could not create prompt ({e})")
                #print(prompt)

                msg = await message.channel.send("Reading tokens... <a:loadingP:1055187594973036576>")
                llmAnswer=await llm_chat_completion(msg,llmModel,prompt)
            else:
                await message.channel.send("LLM_LOCK is still **ON**")



@amadeus.command(name="skip",description="skip your turn in conversation")
async def skipturn(message):
    await message.respond("Force called on_message, you can hide that",ephemeral=True)
    await on_message(message)

@amadeus.command(name="pov",description="write text as bot")
async def sendtext(message, text: discord.Option(str,name_localizations={'en-US': 'text', 'ru': 'текст'},description_localizations={'en-US': 'just a text', 'ru': 'просто текст'},required=True)):
    if message.author.id in LLM_ADMINS: 
        await message.respond("Force called message.channel.send, you can hide that",ephemeral=True)
        await message.channel.send(text)
    else:
        await message.respond("You cant do that",ephemeral=True)

@amadeus.command(name="generate",description="raw OAI Completion call (uses server's config)")
async def rawgen(message, prompt: discord.Option(str,name_localizations={'en-US': 'prompt', 'ru': 'промпт'},description_localizations={'en-US': 'prompt', 'ru': 'промпт'},required=True)):
    global LLM_LOCK
    if not LLM_LOCK:
        LLM_LOCK=1
        if f"{message.guild.id}" not in LLM_CONF or any([x not in LLM_CONF[f"{message.guild.id}"] for x in ("histLimit","maxTokens","curTemp","presencePenalty","frequencyPenalty","currentPrompter","prompterStyle","systemPrompt")]):
            LLM_LOCK=0
            await message.channel.send("Please fully initialise config (/amadeus configure)")
            return
        else:
            maxTokens=LLM_CONF[f"{message.guild.id}"]["maxTokens"]

        llmModel=await get_model()
        msg = await message.respond("Reading tokens... <a:loadingP:1055187594973036576>")
        await llm_completion_itr(msg,prompt,llmModel,maxTokens)


@amadeus.command(name="viewconf",description="view Amadeus config")
async def viewconf(message):
    if f"{message.guild.id}" not in LLM_CONF or any([x not in LLM_CONF[f"{message.guild.id}"] for x in ("histLimit","maxTokens","curTemp","presencePenalty","frequencyPenalty","currentPrompter","prompterStyle","systemPrompt")]):
        await message.respond("Please fully initialise config (/amadeus configure)")
        return
    else:
        await message.respond(f"""```python\n{LLM_CONF[f"{message.guild.id}"]}
Available prompt vars are:
{LLM_VARS}
Keep in mind prompt will be processed with strftime```""")


@amadeus.command(name="configure",description="reconfigure Amadeus")
async def reconfigure(message,history: discord.Option(int,name='messages',description=f'messages in history (odd ints recomended), default is {MSG_LIMIT}',required=False),
                      tokens: discord.Option(int,name='tokens',description=f'max n tokens to predict, default is {MAX_TOKENS}',required=False),
                      temp: discord.Option(float,name='temperature',description=f'higher is more random, default is {CUR_TEMP}',required=False),
                      pp: discord.Option(float,name='presence_penalty',description=f'Presence Penalty, default is {PRES_PEN}',required=False),
                      fp: discord.Option(float,name='frequency_penalty',description=f'Frequency Penalty, default is {FREQ_PEN}',required=False),
                      #style: discord.Option(str,name_localizations={'en-US': 'style', 'ru': 'стиль'},description_localizations={'en-US': 'template style', 'ru': 'стиль шаблона'}, required=False, choices=("USER-ASSISTANT","NICKNAME")),
                      prompt: discord.Option(str,name_localizations={'en-US': 'prompt', 'ru': 'промпт'},description_localizations={'en-US': 'initial (system) prompt', 'ru': 'начальный (системный) промпт'},required=False)):
    if message.author.id in LLM_ADMINS:
        global LLM_CONF
        if not f"{message.guild.id}" in LLM_CONF:
            LLM_CONF[f"{message.guild.id}"]=dict()
        if history and 1 <= history <= 64:
            LLM_CONF[f"{message.guild.id}"]["histLimit"]=history
        elif "histLimit" not in LLM_CONF[f"{message.guild.id}"]:
            LLM_CONF[f"{message.guild.id}"]["histLimit"]=5
        if tokens and 1<= tokens <= 1024:
            LLM_CONF[f"{message.guild.id}"]["maxTokens"]=tokens
        elif "maxTokens" not in LLM_CONF[f"{message.guild.id}"]:
            LLM_CONF[f"{message.guild.id}"]["maxTokens"]=128
        if temp and 0.1 <= temp <= 2.0:
            LLM_CONF[f"{message.guild.id}"]["curTemp"]=temp
        elif "curTemp" not in LLM_CONF[f"{message.guild.id}"]:
            LLM_CONF[f"{message.guild.id}"]["curTemp"]=0.6
        if pp and 0.01 <= pp <= 2.0:
            LLM_CONF[f"{message.guild.id}"]["presencePenalty"]=pp
        elif "presencePenalty" not in LLM_CONF[f"{message.guild.id}"]:
            LLM_CONF[f"{message.guild.id}"]["presencePenalty"]=0.9
        if fp and 0.01 <= fp <= 2.0:
            LLM_CONF[f"{message.guild.id}"]["frequencyPenalty"]=fp
        elif "frequencyPenalty" not in LLM_CONF[f"{message.guild.id}"]:
            LLM_CONF[f"{message.guild.id}"]["frequencyPenalty"]=1.0
        #if style:
        #    LLM_CONF[f"{message.guild.id}"]["prompterStyle"]=style
        #elif "prompterStyle" not in LLM_CONF[f"{message.guild.id}"]:
        #    LLM_CONF[f"{message.guild.id}"]["prompterStyle"]="USER-ASSISTANT"
        if prompt:
            LLM_CONF[f"{message.guild.id}"]["systemPrompt"]=prompt
        elif "systemPrompt" not in LLM_CONF[f"{message.guild.id}"]:
            LLM_CONF[f"{message.guild.id}"]["systemPrompt"]=llmContext
        await viewconf(message)
    else:
        await message.respond("```у вас нет прав```")


@amadeus.command(name="script",description="run script")
async def hardware(message, operator: discord.Option(str,name="exec",description="choose",choices=["python","bash"]), script: discord.Option(str,name="script",description="write a script")):
    if message.author.id in LLM_ADMINS:
        if operator == "python":
            try:
                ans="python\n"+eval(script)
            except Exception as e:
                ans=e
        elif operator == "bash":
            try: 
                ans="ansi\n"+subprocess.check_output(script, shell=True).decode()
            except Exception as e:
                ans=e
    else:
        ans="not in LLM_ADMINS"
    if len(str(ans))>1994:
        ans=str(ans)[:1991]+"..."
    await message.respond(f"```{ans}```")
# SERVER
"""
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
        await message.respond(f'nah')

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
        await message.respond(f'nah')
"""
# =====

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
    print("__main__, reading TOKEN and CONF...")
    with open(f"{os.path.dirname(os.path.realpath(__file__))}/TOKEN.env","r") as t:
        TOKEN=str(t.read())
    with open(f"{os.path.dirname(os.path.realpath(__file__))}/config/llm.conf","r") as t:
        LLM_CONF=json.load(t)
    LLM_CONF_OLD=copy.deepcopy(LLM_CONF)
    print("Starting discord instance...")
    client.run(TOKEN)

LLM_USERS=[573799615074271253,527505544261664798,396961790778540032,579639623668727808,489895341496467456,547738827410898965,676476841707700235,677151784795504651,499442614722887690]
