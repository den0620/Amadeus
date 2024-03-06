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

async def template_chatml(message,init,msgs,gen):
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

async def template_nschatml(message,init,msgs,gen):
    # preparations:
    # Here we don't need "msgs", we will recreate our own from "message"
    clientUser=await message.guild.fetch_member(client.user.id)
    discordHistory=message.channel.history(limit=discordLimit)
    llmHistory=[msg async for msg in discordHistory][::-1]
    # done:
    return """<|im_system|>
"""+init+"""<|im_end|>
"""+"\n".join([f"<|im_bot|>\n\"{msg.author.display_name}\": {msg.content}<|im_end|>" if msg.author==clientUser else f"<|im_user|>\n\"{msg.author.display_name}\": {msg.content}<|im_end|>" for msg in llmHistory])+"""
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

async def template_velara(message,init,msgs,gen):
    return f"""### Instruction:
{init}

### Input:
{'''
'''.join(msgs)}

### Response:
{gen}"""

# ===== /Prompters =====
