import discord
from discord.ext import commands
from database import db
from utils.logger import log

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Срабатывает, когда кто-то заходит на сервер"""
        
        # 1. Игнорируем ботов (им не нужна статистика)
        if member.bot:
            return

        # 2. Пытаемся создать пользователя
        # Метод create_user в database.py сам проверит, есть ли юзер, 
        # и если есть — ничего не сломает (вернет None).
        new_user = await db.create_user(member.id, member.name)

        if new_user:
            log(f"👋 Новый участник {member.name} ({member.id}) добавлен в БД!", level="SUCCESS")
        else:
            log(f"👋 Участник {member.name} вернулся (уже есть в БД).", level="INFO")

    @commands.Cog.listener()
    async def on_ready(self):
        """Срабатывает при запуске бота"""
        log(f"Бот запущен как {self.bot.user}", level="INFO")

async def setup(bot):
    await bot.add_cog(Events(bot))