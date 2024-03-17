import discord.ui
from discord.ext import commands

import config.config as config

import config.secret_values as secret_values
from config.secret_values import TOKEN, GUILD

import core.kdr_db as db

# intents & bot instance
intents = discord.Intents.all()
client = commands.Bot(command_prefix="!", intents=intents)

""" Run """


def run():
    client.run(TOKEN)


""" On Ready """


@client.event
async def on_ready():
    print(f'{client} is ready and syncing commands.')
    await client.load_extension('core.kdr_core')
    await client.load_extension('core.kdr_admin')
    await client.load_extension('core.kdr_util')
    await client.load_extension('core.kdr_shop')
    await client.load_extension('core.kdr_fun')

    # clear all commands
    if config.CLEAR_COMMANDS:
        print(f'CLEAR_COMMANDS config flag is true. Clearing Commands.')
        client.tree.clear_commands()
        if config.CLEAR_COMMANDS_GLOBAL:
            print(f'CLEAR_COMMANDS_GLOBAL config flag is true. Clearing Global Tree.')
            await client.tree.sync()
            return
        print(f'CLEAR_COMMANDS_GLOBAL config flag is false. Clearing Guild Tree.')
        await client.tree.sync()
        return

    # try syncing commands
    try:
        synced = await client.tree.sync()
        if not synced:
            print(f'{client} command sync failed.')
        print(f'{client} Bot is ready. ')
    except Exception as e:
        print(f"Error Syncing Commands {e}")
