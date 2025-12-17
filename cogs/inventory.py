import discord
import random
import asyncio
from discord import app_commands, ui
from discord.ext import commands
from database import db
from settings import ITEMS_DB

# --- 1. МОДАЛКА ДЛЯ ИСПОЛЬЗОВАНИЯ ПРЕДМЕТА ЧЕРЕЗ КНОПКУ ---
class UseItemModal(ui.Modal):
    def __init__(self, item_id, item_name, needs_target):
        super().__init__(title=f"Использовать: {item_name}")
        self.item_id = item_id
        self.needs_target = needs_target

        if self.needs_target:
            self.target_input = ui.TextInput(
                label="Цель (Имя, Ник или ID)", 
                placeholder="Например: namequalsmain",
                required=True
            )
            self.add_item(self.target_input)
        else:
            self.confirm_input = ui.TextInput(
                label="Подтверждение",
                placeholder="Напишите 'да' для активации",
                required=False,
                default="да"
            )
            self.add_item(self.confirm_input)

    async def on_submit(self, interaction: discord.Interaction):
        # Чтобы не дублировать логику, мы вызываем метод use_logic из кога
        # Но для этого нам нужно найти мембера по введенному тексту
        target_member = None
        
        if self.needs_target:
            query = self.target_input.value.lower()
            # Пытаемся найти пользователя на сервере
            for m in interaction.guild.members:
                if (str(m.id) == query) or (m.name.lower() == query) or (m.display_name.lower() == query):
                    target_member = m
                    break
            
            if not target_member:
                return await interaction.response.send_message(f"❌ Не смог найти пользователя: {self.target_input.value}", ephemeral=True)

        # Вызываем логику использования (которая описана ниже в InventoryLogic)
        # Нам нужно получить доступ к экземпляру Inventory. 
        # Трюк: мы импортируем логику или просто дублируем вызов метода. 
        # Для простоты и надежности вызовем статический метод обработки.
        
        await InventoryLogic.process_use(interaction, self.item_id, target_member)


# --- 2. КНОПКА ПРЕДМЕТА ---
class InventoryItemButton(ui.Button):
    def __init__(self, item_id, amount, item_data):
        self.item_id = item_id
        
        # Формируем название кнопки: "🦶 Пинок (x5)"
        label = f"{item_data.get('name', item_id)} (x{amount})"
        emoji = item_data.get('emoji', '📦')
        
        super().__init__(label=label, emoji=emoji, style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        # Список предметов, требующих цель
        needs_target = self.item_id in ['kick', 'mute', 'rename', 'steal_xp', 'hook']
        
        item_name = ITEMS_DB.get(self.item_id, {}).get('name', self.item_id)
        await interaction.response.send_modal(UseItemModal(self.item_id, item_name, needs_target))


# --- 3. ПАГИНАЦИЯ (СТРАНИЦЫ) ---
class InventoryPaginationView(ui.View):
    def __init__(self, interaction, inventory_dict):
        super().__init__(timeout=180)
        self.interaction = interaction
        self.user_id = interaction.user.id
        # Превращаем словарь {"kick": 5} в список [("kick", 5), ...]
        self.items = list(inventory_dict.items())
        self.page = 0
        self.items_per_page = 20 # 4 ряда по 5 кнопок
        
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        
        # Срезаем список для текущей страницы
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        current_items = self.items[start:end]

        # Добавляем кнопки предметов
        for item_id, amount in current_items:
            item_data = ITEMS_DB.get(item_id, {})
            self.add_item(InventoryItemButton(item_id, amount, item_data))

        # Добавляем навигацию, если предметов много
        if len(self.items) > self.items_per_page:
            # Кнопка Назад
            prev_btn = ui.Button(label="◀️ Назад", style=discord.ButtonStyle.primary, disabled=(self.page == 0), row=4)
            prev_btn.callback = self.prev_callback
            self.add_item(prev_btn)

            # Счетчик страниц
            total_pages = (len(self.items) - 1) // self.items_per_page + 1
            counter_btn = ui.Button(label=f"Стр. {self.page + 1}/{total_pages}", style=discord.ButtonStyle.gray, disabled=True, row=4)
            self.add_item(counter_btn)

            # Кнопка Вперед
            next_btn = ui.Button(label="Вперед ▶️", style=discord.ButtonStyle.primary, disabled=(end >= len(self.items)), row=4)
            next_btn.callback = self.next_callback
            self.add_item(next_btn)

    async def prev_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: return
        self.page -= 1
        self.update_buttons()
        await interaction.response.edit_message(view=self)

    async def next_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id: return
        self.page += 1
        self.update_buttons()
        await interaction.response.edit_message(view=self)


# --- 4. ВСПОМОГАТЕЛЬНЫЙ КЛАСС ЛОГИКИ (ЧТОБЫ НЕ ДУБЛИРОВАТЬ КОД) ---
class InventoryLogic:
    @staticmethod
    async def process_use(interaction: discord.Interaction, item_id: str, target: discord.Member = None):
        """Вся магия использования предмета тут"""
        
        # 1. Проверки базы
        user_data = await db.find_user(interaction.user.id)
        current_amount = user_data.get("inventory", {}).get(item_id, 0)

        if current_amount <= 0:
            return await interaction.response.send_message(f"❌ Предмет закончился!", ephemeral=True)

        if target and target.bot:
            return await interaction.response.send_message("🤖 На роботов нельзя.", ephemeral=True)
        
        # Щит цели
        if target:
            target_data = await db.find_user(target.id)
            if target_data and target_data.get('inventory', {}).get('shield', 0) > 0:
                # Атака в щит
                await db.add_item(target.id, 'shield', -1)
                await db.add_item(interaction.user.id, item_id, -1)
                return await interaction.response.send_message(f"🛡️ **{target.display_name}** отразил атаку щитом!", ephemeral=False)

        msg = ""
        success = False

        try:
            # === HOOK ===
            if item_id == "hook":
                if not interaction.user.voice or not interaction.user.voice.channel:
                    return await interaction.response.send_message("❌ Зайдите в войс сами!", ephemeral=True)
                if not target or not target.voice:
                    return await interaction.response.send_message("❌ Цель не в войсе!", ephemeral=True)
                await target.move_to(interaction.user.voice.channel)
                msg = f"🪝 **{interaction.user.name}** притянул **{target.display_name}**!"
                success = True

            # === KICK ===
            elif item_id == "kick":
                if target and target.voice:
                    await target.move_to(None)
                    msg = f"🦶 **{interaction.user.name}** кикнул **{target.display_name}**!"
                    success = True
                else:
                    return await interaction.response.send_message("❌ Цель не в войсе.", ephemeral=True)

            # === MUTE ===
            elif item_id == "mute":
                if target and target.voice:
                    await target.edit(mute=True)
                    msg = f"🤐 **{interaction.user.name}** замутил **{target.display_name}**!"
                    success = True
                    asyncio.create_task(InventoryLogic.unmute_later(target)) # Фоновый размут
                else:
                    return await interaction.response.send_message("❌ Цель не в войсе.", ephemeral=True)

            # === RENAME ===
            elif item_id == "rename":
                if target:
                    await target.edit(nick="Лохматый")
                    msg = f"🤡 **{target.display_name}** переименован!"
                    success = True

            # === STEAL XP ===
            elif item_id == "steal_xp":
                if target:
                    if random.choice([True, False]):
                        target_xp = (await db.find_user(target.id)).get('xp', 0)
                        steal = min(target_xp, 500)
                        if steal > 0:
                            await db.update_user(target.id, {"xp": target_xp - steal})
                            await db.update_user(interaction.user.id, {"xp": user_data['xp'] + steal})
                            msg = f"🔪 **{interaction.user.name}** украл {steal} XP у **{target.display_name}**!"
                            success = True
                        else: return await interaction.response.send_message("У него нет XP.", ephemeral=True)
                    else:
                        fine = 300
                        await db.update_user(interaction.user.id, {"xp": max(0, user_data['xp'] - fine)})
                        msg = f"🚓 **{interaction.user.name}** пойман при краже! Штраф {fine} XP."
                        success = True

            # === XP BOOST ===
            elif item_id == "xp_boost":
                await db.update_user(interaction.user.id, {"xp": user_data['xp'] + 1000})
                msg = f"⚡ **{interaction.user.name}** получил +1000 XP!"
                success = True
            
            # === ПАССИВНЫЕ / КУПОНЫ ===
            elif item_id in ["shield", "ticket_tg", "ticket_nitro", "color_ticket"]:
                return await interaction.response.send_message(f"ℹ️ Предмет **{item_id}** работает пассивно или через админа.", ephemeral=True)

            else:
                 return await interaction.response.send_message("❓ Неизвестный предмет.", ephemeral=True)

        except discord.Forbidden:
             return await interaction.response.send_message("🚫 Нет прав (Move/Mute/Rename).", ephemeral=True)
        except Exception as e:
             return await interaction.response.send_message(f"⚠️ Ошибка: {e}", ephemeral=True)

        if success:
            await db.add_item(interaction.user.id, item_id, -1)
            # Отвечаем, проверяя, был ли уже ответ (defer и т.д.)
            if interaction.response.is_done():
                await interaction.followup.send(msg)
            else:
                await interaction.response.send_message(msg)

    @staticmethod
    async def unmute_later(member):
        await asyncio.sleep(300)
        try: await member.edit(mute=False)
        except: pass


# --- 5. КОГ INVENTORY ---
class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Старое автодополнение (нужно для команды /use, если кто-то хочет писать руками)
    async def item_autocomplete(self, interaction: discord.Interaction, current: str):
        user = await db.find_user(interaction.user.id)
        if not user: return []
        inv = user.get("inventory", {})
        choices = []
        for i_id, amt in inv.items():
            if amt > 0:
                data = ITEMS_DB.get(i_id)
                if not data: continue
                name = f"{data['emoji']} {data['name']} (x{amt})"
                if current.lower() in name.lower():
                    choices.append(app_commands.Choice(name=name, value=i_id))
        return choices[:25]

    @app_commands.command(name="inventory", description="Открыть инвентарь с кнопками")
    async def inventory_cmd(self, interaction: discord.Interaction):
        user = await db.find_user(interaction.user.id)
        if not user:
            return await interaction.response.send_message("❌ Профиль не найден.", ephemeral=True)

        inventory = user.get("inventory", {})
        # Фильтруем пустые
        actual_items = {k: v for k, v in inventory.items() if v > 0}

        if not actual_items:
            return await interaction.response.send_message("🎒 Ваш рюкзак пуст.", ephemeral=True)

        # Создаем View с кнопками
        view = InventoryPaginationView(interaction, actual_items)
        await interaction.response.send_message("🎒 **Ваш Инвентарь:**\n*Нажмите на предмет, чтобы использовать*", view=view, ephemeral=True)

    @app_commands.command(name="use", description="Использовать предмет (классический способ)")
    @app_commands.describe(item_id="Предмет", target="Цель")
    @app_commands.autocomplete(item_id=item_autocomplete)
    async def use_cmd(self, interaction: discord.Interaction, item_id: str, target: discord.Member = None):
        await InventoryLogic.process_use(interaction, item_id, target)

async def setup(bot):
    await bot.add_cog(Inventory(bot))