import discord
import random
import asyncio
from discord import app_commands
from discord.ext import commands
from database import db
from settings import ITEMS_DB

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- УМНОЕ АВТОДОПОЛНЕНИЕ ---
    async def item_autocomplete(self, interaction: discord.Interaction, current: str):
        user = await db.find_user(interaction.user.id)
        if not user: return []
        
        inventory = user.get("inventory", {})
        choices = []
        for item_id, amount in inventory.items():
            if amount > 0:
                item_data = ITEMS_DB.get(item_id)
                if not item_data: continue
                display = f"{item_data['emoji']} {item_data['name']} (x{amount})"
                if current.lower() in display.lower():
                    choices.append(app_commands.Choice(name=display, value=item_id))
        return choices[:25]

    # --- КОМАНДА USE ---
    @app_commands.command(name="use", description="Использовать предмет")
    @app_commands.describe(item_id="Предмет", target="Цель (если нужно)")
    @app_commands.autocomplete(item_id=item_autocomplete)
    async def use_item(self, interaction: discord.Interaction, item_id: str, target: discord.Member = None):
        
        # 1. Проверка наличия предмета
        user_data = await db.find_user(interaction.user.id)
        if not user_data:
             return await interaction.response.send_message(f"❌ Профиль не найден.", ephemeral=True)

        current_amount = user_data.get("inventory", {}).get(item_id, 0)

        if current_amount <= 0:
            return await interaction.response.send_message(f"❌ У вас нет предмета **{ITEMS_DB.get(item_id, {}).get('name', item_id)}**!", ephemeral=True)

        # 2. Проверка цели
        # Добавили 'hook' в список предметов, требующих цель
        needs_target = item_id in ['kick', 'mute', 'rename', 'steal_xp', 'hook']
        
        if needs_target and not target:
             return await interaction.response.send_message(f"❌ Для использования **{item_id}** нужно выбрать цель!", ephemeral=True)
        
        if target and target.bot:
             return await interaction.response.send_message("🤖 Роботы слишком тяжелые для магии.", ephemeral=True)
        
        if target and target.guild_permissions.administrator:
             return await interaction.response.send_message("🛡️ Админа трогать нельзя.", ephemeral=True)

        # --- ЛОГИКА ЩИТА (HOOK тоже проверяет щит) ---
        if target and item_id in ['kick', 'mute', 'rename', 'steal_xp', 'hook']:
            target_data = await db.find_user(target.id)
            if not target_data:
                 # Если у цели нет профиля, считаем что щита нет
                 pass
            else:
                target_inv = target_data.get('inventory', {})
                # Если у цели есть Щит (количество > 0)
                if target_inv.get('shield', 0) > 0:
                    # Списываем щит у жертвы
                    await db.add_item(target.id, 'shield', -1)
                    # Списываем предмет у атакующего (потрачено!)
                    await db.add_item(interaction.user.id, item_id, -1)
                    
                    return await interaction.response.send_message(
                        f"🛡️ **{target.display_name}** активировал авто-щит! Крюк отскочил.", 
                        ephemeral=False
                    )

        msg = ""
        success = False

        try:
            # === HOOK (КРЮК) ===
            if item_id == "hook":
                # Проверка: атакующий должен быть в канале
                if not interaction.user.voice or not interaction.user.voice.channel:
                    return await interaction.response.send_message("❌ Вы сами не в голосовом канале! Куда тянуть?", ephemeral=True)
                
                # Проверка: жертва должна быть в канале
                if not target.voice:
                    return await interaction.response.send_message("❌ Цель не в голосовом канале.", ephemeral=True)

                # Проверка: не сидят ли они уже вместе
                if interaction.user.voice.channel == target.voice.channel:
                    return await interaction.response.send_message("❌ Вы и так в одной комнате.", ephemeral=True)

                # Тянем!
                destination_channel = interaction.user.voice.channel
                await target.move_to(destination_channel)
                msg = f"🪝 **{interaction.user.name}** притянул **{target.display_name}** в свой канал!"
                success = True

            # === KICK ===
            elif item_id == "kick":
                if target.voice:
                    await target.move_to(None)
                    msg = f"🦶 **{interaction.user.name}** выкинул **{target.display_name}** из войса!"
                    success = True
                else:
                    return await interaction.response.send_message("❌ Цель не в войсе.", ephemeral=True)

            # === MUTE ===
            elif item_id == "mute":
                if target.voice:
                    await target.edit(mute=True)
                    msg = f"🤐 **{interaction.user.name}** замутил **{target.display_name}**!"
                    success = True
                    await asyncio.sleep(300) # 5 минут
                    try: await target.edit(mute=False)
                    except: pass
                else:
                    return await interaction.response.send_message("❌ Цель не в войсе.", ephemeral=True)

            # === RENAME ===
            elif item_id == "rename":
                await target.edit(nick="Лохматый")
                msg = f"🤡 **{target.display_name}** теперь Лохматый!"
                success = True

            # === STEAL XP ===
            elif item_id == "steal_xp":
                steal_amount = 500
                chance = random.choice([True, False])
                
                if chance:
                    target_data = await db.find_user(target.id)
                    target_xp = target_data.get('xp', 0)
                    actual_steal = min(target_xp, steal_amount)
                    
                    if actual_steal > 0:
                        await db.update_user(target.id, {"xp": target_xp - actual_steal})
                        await db.update_user(interaction.user.id, {"xp": user_data['xp'] + actual_steal})
                        msg = f"🔪 **{interaction.user.name}** гопнул **{target.display_name}** на {actual_steal} XP!"
                        success = True
                    else:
                        return await interaction.response.send_message("У бедолаги нет XP.", ephemeral=True)
                else:
                    fine = 300
                    new_xp = max(0, user_data['xp'] - fine)
                    await db.update_user(interaction.user.id, {"xp": new_xp})
                    msg = f"🚓 **{interaction.user.name}** пытался украсть XP, но его поймали! Штраф {fine} XP."
                    success = True

            # === XP BOOST ===
            elif item_id == "xp_boost":
                # Простое начисление XP
                await db.update_user(interaction.user.id, {"xp": user_data['xp'] + 1000})
                msg = f"⚡ **{interaction.user.name}** выпил энергетик (+1000 XP)!"
                success = True

            # === КУПОНЫ И ЩИТЫ ===
            elif item_id in ["ticket_tg", "ticket_nitro", "color_ticket"]:
                msg = f"🎫 **{interaction.user.name}** активировал купон! Админ уведомлен."
                success = True

            elif item_id == "shield":
                return await interaction.response.send_message("🛡️ Щит работает автоматически (пассивно).", ephemeral=True)
            
            else:
                return await interaction.response.send_message("❓ Неизвестный предмет.", ephemeral=True)

        except discord.Forbidden:
             return await interaction.response.send_message("🚫 У бота нет прав перемещать участников (Move Members).", ephemeral=True)
        except Exception as e:
             return await interaction.response.send_message(f"⚠️ Ошибка: {e}", ephemeral=True)

        # 4. Списание
        if success:
            await db.add_item(interaction.user.id, item_id, -1)
            await interaction.response.send_message(msg)

async def setup(bot):
    await bot.add_cog(Inventory(bot))