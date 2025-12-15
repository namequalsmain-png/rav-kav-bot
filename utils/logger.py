import datetime
from settings import DEBUG

def log(message, level="INFO"):
    """
    Умный принт.
    level: "INFO", "DEBUG", "ERROR", "WARN"
    """
    
    # 1. Ошибки выводим ВСЕГДА, независимо от настроек
    if level == "ERROR":
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"❌ [{timestamp}] [ERROR] {message}")
        return

    # 2. Если режим DEBUG выключен — ничего не делаем для обычных сообщений
    if not DEBUG:
        return

    # 3. Если DEBUG=True, красиво выводим сообщение
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    icons = {
        "INFO": "ℹ️",
        "DEBUG": "🐛",
        "WARN": "⚠️",
        "SUCCESS": "✅"
    }
    icon = icons.get(level, "📝")
    
    print(f"{icon} [{timestamp}] [{level}] {message}")