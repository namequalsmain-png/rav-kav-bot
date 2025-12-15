import discord
from discord import app_commands
from discord.ext import commands
from database import db
from settings import ITEMS_DB

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- УМНОЕ АВТОДОПОЛНЕНИЕ ---
    async def item_autocomplete(self, interaction: discord.Interaction, current: str):
        """Показывает только те предметы, которые есть у пользователя > 0"""
        
        # 1. Загружаем профиль пользователя из БД
        user = await db.find_user(interaction.user.id)
        
        # Если профиля нет или инвентаря нет — список пуст
        if not user:
            return []

        inventory = user.get("inventory", {})
        choices = []

        # 2. Пробегаем по инвентарю пользователя
        for item_id, amount in inventory.items():
            # Показываем, только если предмета больше 0
            if amount > 0:
                # Получаем данные о предмете из конфига (чтобы взять эмодзи и имя)
                item_data = ITEMS_DB.get(item_id)
                
                # Если вдруг у юзера есть предмет, которого нет в конфиге (старый), пропускаем
                if not item_data: 
                    continue

                # Формируем красивое название: "🦶 Пинок под зад (x2)"
                display_name = f"{item_data['emoji']} {item_data['name']} (x{amount})"
                
                # 3. Фильтр: если пользователь что-то начал писать, ищем совпадение
                if current.lower() in display_name.lower():
                    choices.append(app_commands.Choice(name=display_name, value=item_id))
        
        # Дискорд позволяет вернуть максимум 25 вариантов
        return choices[:25]

    # --- КОМАНДА: ИНВЕНТАРЬ ---
    @app_commands.command(name="inventory", description="Посмотреть свой рюкзак")
    async def show_inventory(self, interaction: discord.Interaction):
        user = await db.find_user(interaction.user.id)
        if not user:
            return await interaction.response.send_message("❌ Ваш профиль не найден.", ephemeral=True)

        inventory = user.get("inventory", {})
        actual_items = {k: v for k, v in inventory.items() if v > 0}

        if not actual_items:
            return await interaction.response.send_message("🎒 Ваш рюкзак пуст.", ephemeral=True)

        text = f"🎒 **Рюкзак {interaction.user.name}:**\n\n"
        for item_id, amount in actual_items.items():
            info = ITEMS_DB.get(item_id, {"name": item_id, "emoji": "❓", "desc": "Неизвестный предмет"})
            text += f"{info['emoji']} **{info['name']}** — {amount} шт.\n└ *{info['desc']}*\n"

        await interaction.response.send_message(text, ephemeral=True)

    # --- КОМАНДА: ИСПОЛЬЗОВАТЬ ПРЕДМЕТ ---
    @app_commands.command(name="use", description="Использовать предмет на пользователе")
    @app_commands.describe(item_id="Выберите предмет из вашего рюкзака", target="На ком использовать?")
    @app_commands.autocomplete(item_id=item_autocomplete) # Подключаем нашу умную функцию
    async def use_item(self, interaction: discord.Interaction, item_id: str, target: discord.Member):
        
        # 1. Проверки базы данных
        user_data = await db.find_user(interaction.user.id)
        if not user_data:
            return await interaction.response.send_message("❌ Профиль не найден.", ephemeral=True)
            
        current_amount = user_data.get("inventory", {}).get(item_id, 0)

        if current_amount <= 0:
            return await interaction.response.send_message(f"❌ У вас нет предмета **{ITEMS_DB.get(item_id, {}).get('name', item_id)}**!", ephemeral=True)

        # 2. Проверки цели
        if target.bot:
            return await interaction.response.send_message("🤖 На роботов это не действует.", ephemeral=True)
        if target.guild_permissions.administrator:
            return await interaction.response.send_message("🛡️ У цели божественный щит (Админ).", ephemeral=True)

        # 3. Логика эффектов
        msg = ""
        success = False

        try:
            if item_id == "kick":
                if target.voice:
                    await target.move_to(None) 
                    msg = f"🦶 **{interaction.user.name}** дал пинка **{target.display_name}**!"
                    success = True
                else:
                    return await interaction.response.send_message("❌ Цель не в голосовом канале.", ephemeral=True)

            elif item_id == "mute":
                if target.voice:
                    await target.edit(mute=True)
                    msg = f"🤐 **{interaction.user.name}** заклеил рот **{target.display_name}** скотчем!"
                    success = True
                else:
                    return await interaction.response.send_message("❌ Цель не в голосовом канале.", ephemeral=True)

            elif item_id == "rename":
                old_name = target.display_name
                await target.edit(nick="Лохматый") 
                msg = f"🏷️ **{old_name}** теперь известен как **Лохматый**!"
                success = True

            elif item_id == "xp_boost":
                msg = f"⚡ **{interaction.user.name}** выпил энергетик! (Визуальный эффект)"
                success = True
            
            elif item_id == "shield":
                 msg = f"🛡️ **{interaction.user.name}** активировал щит!"
                 success = True

            else:
                return await interaction.response.send_message("❓ Этот предмет пока нельзя использовать.", ephemeral=True)

        except discord.Forbidden:
            return await interaction.response.send_message("🚫 У бота нет прав (Manage Nicknames / Move Members / Mute Members).", ephemeral=True)
        except Exception as e:
            return await interaction.response.send_message(f"⚠️ Ошибка: {e}", ephemeral=True)

        # 4. Списание предмета
        if success:
            await db.add_item(interaction.user.id, item_id, -1)
            await interaction.response.send_message(msg)

async def setup(bot):
    await bot.add_cog(Inventory(bot))