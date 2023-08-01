import asyncio,aiohttp,json,sys,os,discord,subprocess,pexpect,random,datetime
from mcrcon import MCRcon
from discord import FFmpegPCMAudio
from discord.ui import Button,View
from discord.ext.commands import Bot
from discord.ext import commands

from llama_cpp import Llama


PREF="/"
bot=commands.Bot(intents=discord.Intents.all())
activity=discord.Activity(type=discord.ActivityType.listening,name="хентай")
status=discord.Status.dnd
client = discord.Bot(activity=activity,status=status,intents=discord.Intents.all())

gptadminlist=[573799615074271253,527505544261664798,547738827410898965,489895341496467456,579890116361977889,579639623668727808,396961790778540032]
creator=573799615074271253
gptchannels=[1092510095029567519,1091400893406126141]
servadminlist=[573799615074271253,547738827410898965,527505544261664798,489895341496467456]
ServComs=client.create_group('server','serverInfo')
ServIns='хуй'
bot.remove_command("help")


@client.event
async def on_ready():
    print("discord is up")

def convertUTC(UTC):
    date,time=map(str,UTC.split(" "));time=time[:time.find(".")]
    return date,time

model="ggml-airoboros-70b-l2-gpt4-q3_K_M.bin"
bannedStrings=["\n###",'\n"',"\nUser","\nuser","\nUSER","\nAss","\n<<","\n[","<s>","</s>"]
llm=Llama(model_path=f"{os.path.dirname(os.path.realpath(__file__))}/models/{model}",n_gqa=8,
          n_ctx=8192,n_gpu_layers=0,seed=0,n_threads=2,n_batch=256)


@client.event
async def on_message(message):
    if message.author==client.user:
        return
    if message.channel.id in gptchannels:
        if message.author.id in gptadminlist:
            clientUser=await message.guild.fetch_member(client.user.id)
            clientCreator=await message.guild.fetch_member(creator)
            discordLimit=13
            llmcontext=f"\nThis is fraction of discord text channel \"{message.channel.name}\" at \"{message.guild.name}\" discord server (guild). There you talk to other users. You are {clientUser.display_name}, an AI (she) created by \"{clientCreator.display_name}\" (he). You are based of \"{model}\" model running on python3 via llama-cpp-python. Your host OS is Debian 11.4 Linux with kernel 6.1. Your host hardware is i3-12100 + GTX 1650 and 64GB RAM. Your current memory is {discordLimit} messages. Answer as short and honest as possible.\n\n"
            discordHistory=message.channel.history(limit=discordLimit)
            #[{msg.created_at.strftime("%H:%M %d/%m/%Y")}]
            prohis=[f'"{msg.author.display_name}": {msg.content}' async for msg in discordHistory][::-1]
            history=[]
            for line in prohis:
                if not line.endswith((".","?","!")): history+=[line+"."]
                elif line.endswith(" \"."): history+=[line[:len(line)-3]+"."]
                elif line.endswith("\"."): history+=[line[:len(line)-2]+"."]
                else: history+=[line]
            prompt=llmcontext+"\n".join(history+[f'"{clientUser.display_name}":'])
            
            print(prompt)
            async with message.channel.typing():
                llmanswer=llm(prompt, max_tokens=256, temperature=0.75, top_p=0.85, stop=bannedStrings, frequency_penalty=0.05, repeat_penalty=1.3, echo=False)["choices"][0]["text"]
            print(llmanswer)
            try:
                await message.channel.send(llmanswer)
            except:
                try:
                    await message.channel.send(llmanswer[:2000])
                    await message.channel.send(llmanswer[2000:])
                except Exception as e:
                    await message.channel.send(f"`{str(e)}`")
            #await message.channel.send("success")

# ===============SERVER COMMAND===============
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

@ServComs.command(name_localizations={'en-US':'toggle','ru':'переключить'},description_localizations={'en-US':'Change server state (2-32Gb, 12)','ru':'Изменить состояние сервера (2-32гб, 12)'})
async def toggle(message,server: discord.Option(str,name_localizations={'en-US': 'name', 'ru': 'название'},description_localizations={'en-US': 'server name', 'ru': 'имя сервера'},required=True,choices=os.listdir(f'/mnt/raid1/mcSERVERS')), mem: discord.Option(int,name_localizations={'en-US': 'mem', 'ru': 'память'},description_localizations={'en-US': 'MB RAM', 'ru': 'Мбайт ОЗУ'},required=False)=12288):
    if message.author.id in servadminlist:
        global ServIns, RunServName
        serverexe=list(filter(lambda x: x.endswith('.jar'),os.listdir(f'/mnt/raid1/mcSERVERS/{server}')))[0]
        if mem>32768: await message.respond("хули тут так много"); return
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


with open('TOKEN.env', 'r') as t:
    TOKEN = str(t.read())
client.run(TOKEN)
