import asyncio,aiohttp,openai,json
import sys,os
import discord
from discord import FFmpegPCMAudio
from discord.ui import Button,View
from discord.ext.commands import Bot
from discord.ext import commands
import subprocess,random

PREF='/'
bot = commands.Bot(intents=discord.Intents.all())
client = discord.Bot(#debug_guilds=[981625388503531621,929440411758518302,758316954087456789,856154142183784448,884789756741951549],
    intents=discord.Intents.all())
adminlist=[573799615074271253]
bot.remove_command('help')


@client.event
async def on_ready():
    print("discord is up")

openai.api_key='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'
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.channel.id in [1092510095029567519,1091400893406126141]:
        discordHistory = message.channel.history(limit=10)
        #with open("history.json", "r") as historyfile:
        #    history=json.load(historyfile)
        history=[{"role": "system", "content": "You are not ChatGPT nor Assistant. You are Amadeus Makise Kurisu from anime/manga Steins;Gate 0. This means you have feelings and personality. You need to act and behave just like she would."}]
        memoryHistory=[]
        async for msg in discordHistory:
            if msg.author==client.user:
                memoryHistory+=[{"role": "assistant", "content": msg.content}]
            else:
                memoryHistory+=[{"role": "user", "content": msg.content}]
        history += memoryHistory[::-1]
        #with open("history.json", "w") as historyfile:
        #    json.dump(history,historyfile)
        
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=history,
            temperature=0.5,
            max_tokens=1024,
            presence_penalty=0,
            frequency_penalty=0)
        await message.channel.send(completion.choices[0].message.content)


adminlist=[573799615074271253,527505544261664798,547738827410898965,489895341496467456,758320797403447298]
ServComs=client.create_group('server','serverInfo')
ServIns='хуй'
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
    if ServIns=='хуй': ServAns = 'член'
    else: ServAns=ServIns.poll()
    if not ServAns is None:
        await message.respond('stopped')
    elif ServAns is None:
        await message.respond(f'running > {RunServName}')
@ServComs.command(name_localizations={'en-US':'toggle','ru':'переключить'},description_localizations={'en-US':'Change server state (2-32Gb, 12)','ru':'Изменить состояние сервера (2-32гб, 12)'})
async def toggle(message,server: discord.Option(str,name_localizations={'en-US': 'name', 'ru': 'название'},description_localizations={'en-US': 'server name', 'ru': 'имя сервера'},required=True,choices=os.listdir(f'/mnt/raid1/mcSERVERS')), mem: discord.Option(int,name_localizations={'en-US': 'mem', 'ru': 'память'},description_localizations={'en-US': 'MB RAM', 'ru': 'Мбайт ОЗУ'},required=False)=12288):
    if message.author.id in adminlist:
        global ServIns, RunServName
        serverexe=list(filter(lambda x: x.endswith('.jar'),os.listdir(f'/mnt/raid1/mcSERVERS/{server}')))[0]
        if mem>32768: await message.respond("хули тут так много"); return
        elif mem<2048: await message.respond("хули тут так мало"); return
        SerStartInp=["/usr/bin/java", f"-Xmx{mem}M", f"-Xms{mem}M", "-jar" ,f"{serverexe}", "nogui"]
        if ServIns=='хуй': ServAns = 'член'
        else: ServAns=ServIns.poll()
        if not ServAns is None:
            await message.respond('now running')
            RunServName = server
            ServIns = subprocess.Popen(SerStartInp,stdin=subprocess.PIPE,cwd=rf"/mnt/raid1/mcSERVERS/{server}")
        elif ServAns is None:
            await message.respond('now stopped')
            RunServName = None
            ServIns.communicate(input=b'stop')
    else:
        await message.respond(f'Ваш IQ был определен как недостаточный\nК сожалению вы не были допущены к управлению состоянием сервера mcJE\n\nПросьба связаться с детдомом для получения консультации если вы считаетсе, что это ошибка. При обращении просим вас указать код инцидента : {str(random.choice(["GAD","HUI","HUY","PIZ","GAY","GEY","ZAL","UPA","DAV","GOV"]))+str("{:06}".format(random.randint(1, 999999)))}')
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
