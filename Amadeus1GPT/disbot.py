import asyncio,aiohttp,openai

from gpt_index import SimpleDirectoryReader,GPTListIndex, GPTSimpleVectorIndex,LLMPredictor, PromptHelper
from langchain import OpenAI
import sys,os

with open("OPENAI.env","r") as openaitokenfile:
    openaitoken=str(openaitokenfile.read())

os.environ["OPENAI_API_KEY"]=openaitoken

def createVectorIndex(path):
    max_input=4096
    tokens=256
    max_chunk_overlap=20
    chunk_size = 600
    prompt_helper=PromptHelper(max_input,tokens,max_chunk_overlap,chunk_size_limit=chunk_size)

    #define LLM
    llmPredictor = LLMPredictor(llm=OpenAI(temperature=0, model_name="gpt-3.5-turbo",max_tokens=tokens))

    #load data
    docs = SimpleDirectoryReader(path).load_data()

    #create vector index
    vectorIndex = GPTSimpleVectorIndex(documents=docs,llm_predictor=llmPredictor,prompt_helper=prompt_helper)
    vectorIndex.save_to_disk("vectorIndex.json")
    return vectorIndex

print("running vectorIndex")
vectorIndex = createVectorIndex("learning")
print("done")

#def answerMe(vectorIndex):
#    vIndex = GPTSimpleVectorIndex.load_from_disk(vectorIndex)
#    while 1:
#        prompt = input("Please ask: ")
#        response = vIndex.query(prompt,response_mode="compact")
#        print(f"Response: {response}\n")

#answerMe("vectorIndex.json")

# ===================== PYCORD AREA ============================

import discord
from discord import FFmpegPCMAudio
from discord.ui import Button,View
from discord.ext.commands import Bot
from discord.ext import commands

PREF='/'
bot = commands.Bot(intents=discord.Intents.all())
client = discord.Bot(#debug_guilds=[981625388503531621,929440411758518302,758316954087456789,856154142183784448,884789756741951549],
    intents=discord.Intents.all())
adminlist=[573799615074271253]
bot.remove_command('help')


@client.event
async def on_ready():
    global vIndex
    print("discord is up")
    vectorIndex="vectorIndex.json"
    vIndex = GPTSimpleVectorIndex.load_from_disk(vectorIndex)

@client.command(name="ask",description="че за хуйня")
async def ask(message,option: discord.Option(str,name="ввод",required=True)):
    prompt = option
    msg = await message.respond("...")
    response = vIndex.query(prompt, response_mode="compact")
    await msg.edit_original_response(content=str(response))

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.channel.id == 1090219975622541402:
        prompt = message.content
        response =  vIndex.query(prompt, response_mode="compact")
        if response == None or str(response) == "Empty Response":
            response = "..."
        await message.reply(content=str(response))

with open('TOKEN.env', 'r') as t:
    TOKEN = str(t.read())
client.run(TOKEN)
