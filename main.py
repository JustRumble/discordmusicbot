import discord
from discord.ext import commands
import os
import json
import wavelink

"""JustRumble"""

bot = commands.Bot(command_prefix="!", help_command=None, intents=discord.Intents.all())
CONFIG = json.load(open("config.json"))


async def load_cogs():
    for file in os.listdir("./cogs"):
        if file.endswith(".py"):
            await bot.load_extension(f"cogs.{file[:-3]}")

async def reload_cogs():
    for file in os.listdir("./cogs"):
        if file.endswith(".py"):
            await bot.reload_extension(f"cogs.{file[:-3]}")
@bot.event
async def setup_hook():
    
    nodes = [   
        wavelink.Node(
            uri=CONFIG["node_main"]["lavalink_node_uri"],
            password=CONFIG["node_main"]["lavalink_node_pwd"],
            inactive_player_timeout=20
        ),
    ]
    await wavelink.Pool.connect(nodes=nodes, client=bot)
    await load_cogs()


@bot.event
async def on_ready():
    print("Listo")


@bot.command(name="sync")
async def sync_cmd(ctx: commands.Context):
    if await bot.is_owner(ctx.author):
        synced = await bot.tree.sync()
        await ctx.send(len(synced))
        await ctx.message.delete()

@bot.command(name="reloadcogs")
async def reloadcogs(ctx: commands.Context):
    if await bot.is_owner(ctx.author):
        await reload_cogs()
        await ctx.send("Listo")

bot.run(CONFIG["bot_token"])
