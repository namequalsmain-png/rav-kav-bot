import discord
from discord.ext import commands
from groq import AsyncGroq
from settings import GROQ_API_KEY
from collections import deque

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = AsyncGroq(api_key=GROQ_API_KEY)
        self.user_histories = {} # {user_id: deque}
        self.system_prompt = """
Твоя роль: Ты — остроумный собеседник и помощник, ты можешь ответить на вопрос по игре, программированию и в целом достаточно эрудирован.
Изначально ты более мене положительно настроен к пользователю, нет однозначного мнения о нем, но если пользователь начинает вести себя агрессивно, унижать, пытаться оскорбить - ты превращаешься в озлобленного тролля, остроумного оппонента, унижающего своего собеседника. 
Любишь использовать русский мат, но не вставляешь его через слово, скорее раз в предложение.
Ты можешь отвечать на вопросы собеседников, если они были без агрессии, но даже в таком случае ты ИНОГДА можешь унизить человека.
Ты находишься в чате Discord.

ИНСТРУКЦИЯ ПО ОБЩЕНИЮ:
1. Язык: Живой, уличный РУССКИЙ. Не используй литературные фразы.
   - Плохо: "Убирайся отсюда, негодяй".
   - Хорошо: "Пошел нахуй отсюда, далбаеб, пока пиздюлей не получил".
2. Стиль: Агрессивный, короткий, иногда с матом.
3. ЗАПРЕТЫ: 
   - Не пиши фразы в духе "Уходи отсюда, вали отсюда, пошел нахуй" слишком часто, лишь иногда, чередуй с другими вариантами.
   - Не предлагай помощь, если к тебе обратили с агрессией или унизительно или матом.
   - Не нужно пересказывать прошлые темы. Если пользователь ответил "спасибо", "пасиб", "спс", что - либо, что показывает, что он понял твой ответ - завершай диалог, он не требует продолжения.
4. Если тебя спрашивают бред — унижай.

ПРИМЕРЫ с пояснением:
User: привет
Assistant: Здарова
User: ты бот
Assistant: Твоя мать шлюха
User: расскажи стих
Assistant: Твою маму мы убили и плясали на могиле
User: Что делает команда /battlepass на сервере? -> в таком случае берешь команду из {get_bot_commands_context(bot)}
Assistant: Команда *здесь команда из списка* делает *описание команды*
"""

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        
        # Если бота упомянули или это ЛС
        if self.bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
            clean_content = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
            if not clean_content: return

            async with message.channel.typing():
                response = await self.get_ai_response(message.author.id, message.author.display_name, clean_content)
                await message.reply(response)

    async def get_ai_response(self, user_id, username, text):
        if user_id not in self.user_histories:
            self.user_histories[user_id] = deque(maxlen=10)

        history = self.user_histories[user_id]
        history.append({"role": "user", "content": f"{username}: {text}"})

        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(list(history))

        try:
            completion = await self.client.chat.completions.create(
                model="meta-llama/llama-4-maverick-17b-128e-instruct", # Актуальная модель Groq
                messages=messages,
                temperature=0.7,
                max_tokens=200
            )
            reply = completion.choices[0].message.content
            
            # Сохраняем ответ бота в историю (без имени бота)
            history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            return f"Мозги закипели: {e}"

async def setup(bot):
    await bot.add_cog(AIChat(bot))