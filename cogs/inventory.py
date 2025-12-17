import discord
from discord import app_commands
from discord.ext import commands
from database import db
from settings import ITEMS_DB
# Импортируем всё из UI, чтобы вызывать менюшки
from utils.ui import InventoryPaginationView, InventoryLogic

class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    @app_commands.command(name="inventory", description="Открыть инвентарь")
    async def inventory_cmd(self, interaction: discord.Interaction):
        user = await db.find_user(interaction.user.id)
        if not user:
            return await interaction.response.send_message("❌ Профиль не найден.", ephemeral=True)

        inventory = user.get("inventory", {})
        actual_items = {k: v for k, v in inventory.items() if v > 0}

        if not actual_items:
            return await interaction.response.send_message("🎒 Ваш рюкзак пуст.", ephemeral=True)

        # Вызываем View, который теперь живет в utils/ui.py
        view = InventoryPaginationView(interaction, actual_items)
        await interaction.response.send_message("🎒 **Ваш Инвентарь:**", view=view, ephemeral=True)

    @app_commands.command(name="use", description="Использовать предмет (вручную)")
    @app_commands.describe(item_id="Предмет", target="Цель")
    @app_commands.autocomplete(item_id=item_autocomplete)
    async def use_cmd(self, interaction: discord.Interaction, item_id: str, target: discord.Member = None):
        # Вызываем логику из utils/ui.py
        await InventoryLogic.process_use(interaction, item_id, target)

async def setup(bot):
    await bot.add_cog(Inventory(bot))