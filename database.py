import motor.motor_asyncio
import time
from settings import MONGO_URL

class DatabaseManager:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
        # Используем одну базу данных, но разные коллекции
        self.db = self.client['Main_Database'] 
        self.users = self.db['users']
    async def find_user(self, user_id):
        return await self.users.find_one({"_id": user_id})

    async def create_user(self, user_id, username):
        new_user = {
            "_id": user_id,
            "username": username,
            "reg_date": time.time(),
            "xp": 0,
            "level": 0,
            "rank": "Новичок",
            "inventory": {},
            "rewards_claimed": [0]
        }
        try:
            await self.users.insert_one(new_user)
            return new_user
        except:
            return None # Пользователь уже существует

    async def update_user(self, user_id, data: dict):
        """Обновляет любые поля пользователя"""
        await self.users.update_one({"_id": user_id}, {"$set": data})

    async def add_item(self, user_id: int, item_id: str, amount: int):
        """Добавляет предмет (или отнимает, если amount < 0)"""
        await self.users.update_one(
            {"_id": user_id},
            {"$inc": {f"inventory.{item_id}": amount}},
            upsert=True
        )

# Создаем экземпляр, который будем импортировать в других файлах
db = DatabaseManager()