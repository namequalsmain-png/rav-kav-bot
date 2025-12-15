import discord
from database import db
from settings import ITEMS_DB, LEVELS
from utils.generator import Generator, generate_image_in_thread
from discord import ui




class RoadmapPagination(discord.ui.View):
    def __init__(self, user, page, user_data):
        super().__init__(timeout=60)
        self.user = user
        self.page = page
        self.user_data = user_data
        self.update_buttons()

    def update_buttons(self):
        self.children[0].disabled = (self.page <= 1)
        self.children[1].disabled = (self.page >= 3) # Макс страниц

    async def update_image(self, interaction):
        # Генерируем новую картинку
        need_xp = LEVELS.get(self.user_data['level'] + 1, {}).get('exp_need', 99999)
        
        buffer = await generate_image_in_thread(
            Generator.create_roadmap,
            self.user.name,
            self.user.display_avatar.url,
            self.user_data['xp'],
            need_xp,
            self.user_data['level'],
            self.page,
            LEVELS
        )
        file = discord.File(fp=buffer, filename="roadmap.png")
        await interaction.response.edit_message(attachments=[file], view=self)

    @discord.ui.button(label="◀️ Назад", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.user.id: return
        self.page -= 1
        self.update_buttons()
        await self.update_image(interaction)

    @discord.ui.button(label="Вперед ▶️", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.user.id: return
        self.page += 1
        self.update_buttons()
        await self.update_image(interaction)


class BattlepassView(ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id

    # Кнопка: Инвентарь
    @ui.button(label="Рюкзак", style=discord.ButtonStyle.primary, emoji="🎒")
    async def inventory_btn(self, interaction: discord.Interaction, button: ui.Button):
        # Проверка, что нажал владелец
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Это не твой профиль!", ephemeral=True)

        user = await db.find_user(self.user_id)
        inventory = user.get("inventory", {})
        actual_items = {k: v for k, v in inventory.items() if v > 0}

        if not actual_items:
            return await interaction.response.send_message("🎒 Ваш рюкзак пуст.", ephemeral=True)

        text = f"🎒 **Рюкзак {interaction.user.name}:**\n\n"
        for item_key, amount in actual_items.items():
            info = ITEMS_DB.get(item_key, {"name": item_key, "emoji": "❓"})
            text += f"{info['emoji']} **{info['name']}** (x{amount})\n"
        
        await interaction.response.send_message(text, ephemeral=True)

    # Кнопка: Забрать награду
    @ui.button(label="Забрать награду", style=discord.ButtonStyle.success, emoji="🎁")
    async def claim_btn(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Руки прочь, это не твое!", ephemeral=True)
            
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        # ЛОГИКА ВЫДАЧИ НАГРАД
        user = await db.find_user(self.user_id)
        current_lvl = user.get('level', 0)
        # rewards_claimed может не быть в старых профилях, создаем список
        claimed_list = user.get('rewards_claimed', [0]) 
        
        rewards_text = []
        newly_claimed = []

        # Проверяем все уровни от 1 до текущего
        for lvl in range(1, current_lvl + 1):
            if lvl not in claimed_list:
                lvl_data = LEVELS.get(lvl)
                if not lvl_data: continue

                # Выдача
                reward_type = lvl_data.get('type')
                desc = lvl_data.get('desc', 'Награда')

                if reward_type == 'item':
                    item_id = lvl_data['id']
                    amount = lvl_data.get('amount', 1)
                    await db.add_item(self.user_id, item_id, amount)
                    rewards_text.append(f"🎒 Предмет: **{desc}** (x{amount})")
                
                elif reward_type == 'role':
                    role_id = lvl_data['id']
                    role = interaction.guild.get_role(role_id)
                    if role:
                        try:
                            await interaction.user.add_roles(role)
                            rewards_text.append(f"🎭 Роль: **{role.name}**")
                        except discord.Forbidden:
                            rewards_text.append(f"⚠️ Не смог выдать роль {role.name} (нет прав)")
                    else:
                        rewards_text.append(f"⚠️ Роль ID {role_id} удалена с сервера")

                elif reward_type == 'none':
                    rewards_text.append(f"🎉 Особая награда: **{desc}** (Пиши админу)")

                newly_claimed.append(lvl)

        # Сохраняем в БД
        if newly_claimed:
            # Обновляем список полученных
            updated_list = claimed_list + newly_claimed
            await db.update_user(self.user_id, {"rewards_claimed": updated_list})
            
            msg = "✅ **Вы получили награды:**\n" + "\n".join(rewards_text)
            await interaction.followup.send(msg)
        else:
            await interaction.followup.send("🤷‍♂️ Вы уже забрали все доступные награды для своего уровня!")
    @ui.button(label="Карта наград", style=discord.ButtonStyle.secondary, emoji="🗺️")
    async def roadmap_btn(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Это не твой профиль!", ephemeral=True)

        # 1. Говорим "Думаю..." (Ephemeral = видит только нажавший)
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        # 2. Получаем данные
        user = await db.find_user(self.user_id)
        if not user:
            return await interaction.followup.send("Профиль не найден.")

        lvl = user.get('level', 0)
        if lvl == 0: lvl = 1
        
        # Определяем страницу
        page = 1
        if lvl > 10: page = 2
        if lvl > 20: page = 3
        
        need_xp = LEVELS.get(lvl + 1, {}).get('exp_need', 99999)

        # 3. Генерируем картинку
        buffer = await generate_image_in_thread(
            Generator.create_roadmap,
            interaction.user.name,
            interaction.user.display_avatar.url,
            user['xp'],
            need_xp,
            lvl,
            page,
            LEVELS
        )

        if buffer:
            file = discord.File(fp=buffer, filename="roadmap.png")
            # Подключаем класс RoadmapPagination (он теперь определен выше)
            view = RoadmapPagination(interaction.user, page, user)
            await interaction.followup.send(file=file, view=view, ephemeral=True)
        else:
            await interaction.followup.send("Ошибка генерации карты.")
