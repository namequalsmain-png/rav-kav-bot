import discord
import os
import asyncio
from discord.ext import commands
from settings import BOT_TOKEN
from aiohttp import web
import threading
from utils.logger import log

# Настройка намерений
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Загружаем коги из папки cogs
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
                print(f"Loaded extension: {filename}")
        
        # Синхронизация слэш-команд (глобально может занять до часа, для теста используй sync(guild=...))
        # await self.tree.sync() 

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')


async def health_check(request):
    return web.Response(text="I am alive!")

async def run_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000) # Слушаем порт 8000
    await site.start()

async def main():
    await run_server() 

    bot = MyBot()
    async with bot:
        await bot.start(BOT_TOKEN)
    

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass