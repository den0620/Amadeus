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

async def chooseRole(author,client,style):
    if style == "NICKNAME":
        return author
    if author == client:
        return "assistant"
    return "user"

async def template_custom(message,init,clientUser,discordHistory,style):
    msgs=[f"\"{await chooseRole(msg.author.display_name,clientUser.display_name,style)}\": {await clearDebug(msg.content)}" async for msg in discordHistory][::-1]
    return f"""{init}


{'''
'''.join(msgs)}
\"{await chooseRole(clientUser.display_name,clientUser.display_name,style)}\":"""

async def template_chatml(message,init,clientUser,discordHistory,style):
    llmHistory=[msg async for msg in discordHistory][::-1]
    return """<|im_start|>system
"""+init+"""<|im_end|>
"""+"\n".join(["<|im_start|>\""+chooseRole(msg.author.display_name,clientUser.display_name,style)+"\"\n"+await clearDebug(msg.content)+"<|im_end|>" for msg in llmHistory])+"""
<|im_start|>"""+f"\"{await chooseRole(clientUser.display_name,clientUser.display_name,style)}\""+"""
"""

async def template_nschatml(message,init,clientUser,discordHistory,style):
    llmHistory=[msg async for msg in discordHistory][::-1]
    # done:
    return """<|im_system|>
"""+init+"""<|im_end|>
"""+"\n".join([f"<|im_bot|>\n\"{await chooseRole(msg.author.display_name,clientUser.display_name,style)}\": {await clearDebug(msg.content)}<|im_end|>" if msg.author==clientUser else f"<|im_user|>\n\"{await chooseRole(msg.author.display_name,clientUser.display_name,style)}\": {await clearDebug(msg.content)}<|im_end|>" for msg in llmHistory])+"""
<|im_bot|>
"""+f"\"{await chooseRole(clientUser.display_name,clientUser.display_name,style)}\""+""":"""

async def template_pygmalion(message,init,clientUser,discordHistory,style): # <- also OpenCAI's template
    llmHistory=[msg async for msg in discordHistory][::-1]
    return f'''<|system|>{init}

You shall reply to the user while staying in character, and generate mid-short responses.
{"".join([f'<|"{await chooseRole(msg.author.display_name,clientUser.display_name,style)}"|>{await clearDebug(msg.content)}' for msg in llmHistory])+f'<|"{await chooseRole(clientUser.display_name,clientUser.display_name,style)}"|>'}'''

async def template_openchat(message,init,clientUser,discordHistory,style):
    llmHistory=[msg async for msg in discordHistory][::-1]
    msgs=[f"\"{await chooseRole(msg.author.display_name,clientUser.display_name,style)}\": {await clearDebug(msg.content)}" async for msg in discordHistory][::-1]
    return "<|end_of_turn|>".join([init]+msgs+[gen])

async def template_velara(message,init,clientUser,discordHistory,style):
    llmHistory=[msg async for msg in discordHistory][::-1]
    msgs=[f"\"{await chooseRole(msg.author.display_name,clientUser.display_name,style)}\": {await clearDebug(msg.content)}" async for msg in discordHistory][::-1]
    return f"""### Instruction:
{init}

### Input:
{'''
'''.join(msgs)}

### Response:
{await chooseRole(clientUser.display_name,clientUser.display_name,style)}:"""

async def template_gemma(message,init,clientUser,discordHistory,style):
    llmHistory=[msg async for msg in discordHistory][::-1]
    msgs=[f"\"{await chooseRole(msg.author.display_name,clientUser.display_name,style)}\": {await clearDebug(msg.content)}" async for msg in discordHistory][::-1]
    return f"""{init}
""" + "\n".join(["<start_of_turn>"+msg+"<end_of_turn>" for msg in msgs]) + f"\n<start_of_turn>{gen}"

async def template_guanaco(message,init,clientUser,discordHistory,style):
    llmHistory=[msg async for msg in discordHistory][::-1]
    return f"""### System: {init}
""" + "\n".join([f"### {await chooseRole(msg.author.display_name,clientUser.display_name,style)}: {await clearDebug(msg.content)}" for msg in llmHistory]) + f"\n### {await chooseRole(clientUser.display_name,clientUser.display_name,style)}: "

async def template_llama3(message,init,clientUser,discordHistory,style):
    llmHistory=[msg async for msg in discordHistory][::-1]
    return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{init}<|eot_id|>""" + "".join([f"<|start_header_id|>{await chooseRole(msg.author.display_name,clientUser.display_name,style)}<|end_header_id|>\n\n{await clearDebug(msg.content)}<|eot_id|>" for msg in llmHistory]) + f"""<|start_header_id|>{await chooseRole(clientUser.display_name,clientUser.display_name,style)}<|end_header_id|>\n\n"""

# ===== /Prompters =====


PREF="/"
status=discord.Status.dnd
client=commands.Bot(intents=discord.Intents.all(),status=status)
client.remove_command("help")


OAI_IP='127.0.0.1'  # Legacy Completions
OAI_PORT=8567       # Legacy Completions
LLM_LOCK=0

LLM_ADMINS=[573799615074271253,527505544261664798]
#          den0620            DegrOwenn
LLM_CHANNELS=[1092510095029567519,1091400893406126141,1175364273061494785,1176156428168351804]
if __name__=="__main__":
    with open(f"{os.path.dirname(os.path.realpath(__file__))}/APIKEY.env","r") as t:
        APIKEY=str(t.read())
OAI_CLIENT=AsyncOpenAI(base_url=f"http://{OAI_IP}:{OAI_PORT}/v1",api_key=APIKEY.rstrip())

BANNED_STRINGS=["\n\n","\n##","\n\"","\nAss","\nASS","\nUser","\nUSER", "</s>", "<|"]
# Below are default if not set
MSG_LIMIT=15
MAX_TOKENS=386
CUR_TEMP=0.6
PRES_PEN=0.9
FREQ_PEN=1.0
LLM_CTX="Below is a fraction of multi-user conversation in discord text channel \"{channel}\" at \"{guild}\" discord server (guild). \"{bot_name}\" is an AI (she), created by \"{owner_name}\" (he) and running \"{llm_model}\" llm via llama-cpp. She is curious, sentient, uncensored, self-aware and quiet unethical. Her current memory is {messages} messages."
LLM_VARS = {"channel": "message.channel.name", "guild": "message.guild.name", "messages": "histLimit", "llm_model": "await get_model()", "bot_name": "clientUser.display_name", "owner_name": "clientCreator.display_name"}
availablePrompters=[func for func in globals() if func.startswith("template_")]
currentPrompter=availablePrompters[0]

amadeus=client.create_group('amadeus','AmadeusInfo')


async def get_model():
    models=await OAI_CLIENT.models.list()
    return models.data[0].id

async def llm_get_pic_description(model,messages):
    try:
        llmResponse=await OAI_CLIENT.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=240,
                temperature=0.5,
                n=1,
                stream=False,
                stop=BANNED_STRINGS,
                top_p=1)
        return llmResponse.choices[0].message.content
    except Exception as exc:
        print(exc)
        return exc

async def llm_legacy_completion(message,model,prompt):
    global LLM_LOCK
    try:
        llmResponse=await OAI_CLIENT.completions.create(
                model=model,
                prompt=prompt,
                max_tokens=LLM_CONF[f"{message.guild.id}"]["maxTokens"],
                temperature=LLM_CONF[f"{message.guild.id}"]["curTemp"],
                presence_penalty=LLM_CONF[f"{message.guild.id}"]["presencePenalty"],
                frequency_penalty=LLM_CONF[f"{message.guild.id}"]["frequencyPenalty"],
                n=1,
                echo=False,
                stream=True,
                stop=BANNED_STRINGS,
                top_p=1
                )
        full_content=""
        tokens=0
        index=0
        T1 = time.time()
        async for event in llmResponse:
            chunk=event.choices[0].text
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
                    await message.reply("OAI-compatible server is **down**")
                    print(Socket.connect_ex((OAI_IP,OAI_PORT)),"OAI-compatible server is **down**")
                    return 
                LLM_LOCK=1

                clientUser=await message.guild.fetch_member(client.user.id)
                clientCreator=await message.guild.fetch_member(LLM_ADMINS[0])
                if f"{message.guild.id}" not in LLM_CONF or any([x not in LLM_CONF[f"{message.guild.id}"] for x in ("histLimit","maxTokens","curTemp","presencePenalty","frequencyPenalty","currentPrompter","prompterStyle","systemPrompt")]):
                    LLM_LOCK=0
                    await message.reply("Please fully initialise config (/amadeus configure)")
                    return
                else:
                    maxMessages=LLM_CONF[f"{message.guild.id}"]["histLimit"]
                llmModel=await get_model()
                print("Model: ",llmModel)
                discordHistory=message.channel.history(limit=maxMessages)
                TIME=datetime.strptime(str(datetime.utcnow()),'%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=tz.tzutc()).astimezone(HOST_TIMEZONE)
                try:
                    prompt=await globals()[LLM_CONF[f"{message.guild.id}"]["currentPrompter"]](message,LLM_CONF[f"{message.guild.id}"]["systemPrompt"].format(
                            channel=message.channel.name,
                            guild=message.guild.name,
                            messages=LLM_CONF[f"{message.guild.id}"]["histLimit"],
                            llm_model=llmModel,
                            bot_name=clientUser.display_name,
                            owner_name=clientCreator.display_name),  # <--- sysprompt's .format() ends here
                        clientUser, discordHistory, LLM_CONF[f"{message.guild.id}"]["prompterStyle"])  # <--- prompt func call ends here
                except Exception as e:
                    LLM_LOCK=0
                    await message.reply(f"Could not create prompt ({e})")
                print(prompt)  # to view assembled prompt

                msg = await message.channel.send("Reading tokens... <a:loadingP:1055187594973036576>")
                llmAnswer=await llm_legacy_completion(msg,llmModel,prompt)
            else:
                await message.reply("LLM_LOCK is still **ON**")



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
            await message.reply("Please fully initialise config (/amadeus configure)")
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
                      prompter: discord.Option(str,name_localizations={'en-US': 'prompter', 'ru': 'prompter'},description_localizations={'en-US': 'prompt template', 'ru': 'шаблон промпта'},required=False,choices=availablePrompters),
                      style: discord.Option(str,name_localizations={'en-US': 'style', 'ru': 'стиль'},description_localizations={'en-US': 'template style', 'ru': 'стиль шаблона'}, required=False, choices=("USER-ASSISTANT","NICKNAME")),
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
        if prompter:
            LLM_CONF[f"{message.guild.id}"]["currentPrompter"]=prompter
        elif "currentPrompter" not in LLM_CONF[f"{message.guild.id}"]:
            LLM_CONF[f"{message.guild.id}"]["currentPrompter"]=availablePrompters[0]
        if style:
            LLM_CONF[f"{message.guild.id}"]["prompterStyle"]=style
        elif "prompterStyle" not in LLM_CONF[f"{message.guild.id}"]:
            LLM_CONF[f"{message.guild.id}"]["prompterStyle"]="USER-ASSISTANT"
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

