import os
import json
from dotenv import load_dotenv





GUILD_ID = 1173882167504408626
CHANNEL_ID = 1173888168546803744


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEM_PROMPT_PATH = os.path.join(BASE_DIR, 'data', 'ai_system_prompt.txt')


dotenv_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print("⚠️  ВНИМАНИЕ: Файл .env не найден! Бот не запустится.")



DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
BOT_TOKEN = os.getenv('BOT_TOKEN')
MONGO_URL = os.getenv('MONGO_URL')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
if BOT_TOKEN is None:
    raise ValueError("❌ ОШИБКА: BOT_TOKEN не найден в .env файле или файл не загрузился.")



# Загружаем его явно
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print("⚠️  ВНИМАНИЕ: Файл .env не найден! Бот не запустится.")

def load_json_file(filename, key_is_int=False):
    """
    filename: имя файла в папке data/ (например 'items.json')
    key_is_int: если True, превращает ключи словаря в числа (нужно для levels)
    """
    path = os.path.join(BASE_DIR, 'data', filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if key_is_int:
                return {int(k): v for k, v in data.items()}
            return data
    except FileNotFoundError:
        print(f"❌ ОШИБКА: Файл data/{filename} не найден!")
        return {}
    except json.JSONDecodeError:
        print(f"❌ ОШИБКА: Ошибка синтаксиса в data/{filename}")
        return {}

def load_txt_file(filename):
    path = os.path.join(BASE_DIR, 'data', filename)
    try:
        with open(path, 'r', encoding='utf-8') as file:
            system_prompt = file.read()
            return system_prompt
    except FileNotFoundError:
        print(f"❌ ОШИБКА: Файл data/{filename} не найден!")
        return {}
# --- Загружаем данные ---

SYSTEM_PROMPT = load_txt_file('ai_system_prompt.txt')
LEVELS = load_json_file('levels.json', key_is_int=True)
ITEMS_DB = load_json_file('items_data.json', key_is_int=False)
