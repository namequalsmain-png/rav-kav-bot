from PIL import Image, ImageDraw, ImageFont, ImageOps
from utils.logger import log
import requests
import io
import asyncio
import os
import traceback


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')


async def generate_image_in_thread(func, *args, **kwargs):
    """Универсальная обертка для запуска Pillow в отдельном потоке"""
    return await asyncio.to_thread(func, *args, **kwargs)

class Generator:

    @staticmethod
    def make_circle(img):
        """маска аватарки/картинка/чего угодно"""
        mask = Image.new('L', img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + img.size, fill=255)
        output = ImageOps.fit(img, mask.size, centering=(0.5, 0.5))
        output.putalpha(mask)
        return output
    



    @staticmethod
    def get_progressbar(current_xp: int, max_xp: int, bar_empty: str, bar_full: str):
            bar_empty_path = os.path.join(ASSETS_DIR, 'images', bar_empty)
            try:
                base = Image.open(bar_empty_path).convert("RGBA").copy()
            except Exception as e:
                log(f'Ошибка в создани в получении ассета {bar_empty}\n{e}', level='ERROR')
                print(traceback.format_exc())
                return 

            if max_xp == 0: max_xp = 1
            percent = current_xp / max_xp
            if percent > 1: percent = 1
            if percent <= 0: return base 

            full_width, height = base.size
            fill_width = int(full_width * percent)
            if fill_width < 1: fill_width = 1

            bar_full_path = os.path.join(ASSETS_DIR, 'images', bar_full)
            try:
                full_gradient = Image.open(bar_full_path).convert("RGBA")
                cropped_gradient = full_gradient.crop((0, 0, fill_width, height))
                base.paste(cropped_gradient, (0, 0), mask=cropped_gradient)
            except Exception as e:
                log(f'Ошибка в создани в получении ассета {bar_full}\n{e}', level='ERROR')
                print(traceback.format_exc())
                return
            return base
    
    @staticmethod
    def get_font(name, size):
        """Безопасная загрузка шрифта. Если нет файла, берет стандартный."""
        path = os.path.join(ASSETS_DIR, 'fonts', name)
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            log(f"Шрифт {name} не найден по пути {path}. Использую стандартный.", level='WARN')
            return ImageFont.load_default()

    @staticmethod
    def create_roadmap(username, avatar_url, current_xp, need_xp, level, page, all_levels):
        # Убедись, что пути к assets/ правильные
        
        try:
            # --- ОТЛАДКА ---
            log(f"Начало генерации Roadmap для {username}...", level='DEBUG')

            W, H = 900, 1300
            
            # 1. ФОН
            bg_path = os.path.join(ASSETS_DIR, 'images', 'roadmap_bg.png')
            try:
                bg = Image.open(bg_path).convert("RGBA").resize((W, H))
            except FileNotFoundError:
                log(f"Фон не найден: {bg_path}", level="WARN")
                bg = Image.new('RGB', (W, H), color='#2b2d31') # Темно-серый фон

            draw = ImageDraw.Draw(bg)

            # 2. ШРИФТЫ (Убедись, что они есть в assets/fonts/ или используй стандартные)
            font_head = Generator.get_font("Gilroy-ExtraBold.ttf", 48)
            font_sub = Generator.get_font("Gilroy-Bold.ttf", 32)
            font_lvl = Generator.get_font("Gilroy-ExtraBold.ttf", 38)

            # 3. АВАТАРКА (Скачивание)
            if avatar_url:
                try:
                    response = requests.get(avatar_url, timeout=2) # Таймаут 2 сек
                    if response.status_code == 200:
                        avatar_bytes = io.BytesIO(response.content)
                        avatar = Image.open(avatar_bytes).convert("RGBA").resize((130, 130))
                        
                        # Круглая маска
                        mask = Image.new('L', avatar.size, 0)
                        ImageDraw.Draw(mask).ellipse((0, 0) + avatar.size, fill=255)
                        avatar_circle = ImageOps.fit(avatar, mask.size, centering=(0.5, 0.5))
                        avatar_circle.putalpha(mask)
                        
                        bg.paste(avatar_circle, (40, 25), avatar_circle)
                except Exception as e:
                    log(f"Ошибка загрузки аватара: {e}", level='ERROR')

            # 4. ТЕКСТ
            draw.text((190, 40), str(username), font=font_head, fill="white")
            draw.text((190, 100), f"XP: {current_xp} / {need_xp}", font=font_sub, fill="#00ff7f")
            draw.text((720, 50), f"PAGE {page}", font=font_head, fill="#aaaaaa")

            # 5. СПИСОК УРОВНЕЙ (Логика отрисовки)
            start_lvl = (page - 1) * 10
            start_y = 250
            step_y = 95
            line_x = 105

            text_left_margin = line_x + 50
            for i in range(11):
                lvl_num = start_lvl + i  
                y = start_y + (i * step_y)
                
                # Цвет кружка
                if lvl_num < level:
                    color = "#00ff7f" # Зеленый (получено)
                elif lvl_num == level:
                    color = "#ffd700" # Желтый (текущий)
                else:
                    color = "#444444" # Серый (закрыто)

                # Рисуем кружок
                r = 30
                draw.ellipse((line_x-r, y-r, line_x+r, y+r), fill=color)
                
                # Номер уровня
                w_text = draw.textlength(str(lvl_num), font=font_lvl)
                draw.text((line_x - w_text/2, y - 20), str(lvl_num), font=font_lvl, fill="black")

                # Текст награды
                lvl_data = all_levels.get(lvl_num) # all_levels здесь будет словарем int: dict
                if lvl_data:
                    desc = lvl_data.get('desc', 'Награда')
                    draw.text((line_x + 50, y - 15), desc, font=font_sub, fill="white")
                else:
                    if lvl_num == 0:
                        draw.text((text_left_margin, y - 15), "НАЧАЛО", font=font_sub, fill="white")
                    else:
                        draw.text((line_x + 50, y - 15), f"Уровень {lvl_num}", font=font_sub, fill="#777777")

            # --- СОХРАНЕНИЕ ---
            output_buffer = io.BytesIO()
            bg.save(output_buffer, format="PNG")
            output_buffer.seek(0)
            
            log("Генерация завершена успешно.", level='SUCCESS')
            return output_buffer

        except Exception as e:
            log(f"❌ КРИТИЧЕСКАЯ ОШИБКА В ГЕНЕРАТОРЕ:\n{e}", level='ERROR')
            print(traceback.format_exc()) # Выведет полный текст ошибки
            return None # Вернем None, чтобы бот знал об ошибке
        


    @staticmethod
    def create_bp_card(username, level, current_xp, max_xp, avatar_url):
        """Генерирует боевого пропуска для пользователя"""
        bg_path = os.path.join(ASSETS_DIR, 'images', 'battlepass_background.png')
        try:
            log(f'Загружен ассет {bg_path}', level="DEBUG")
            background = Image.open(bg_path).convert("RGBA")
        except Exception as e:
            log(f"Ассет {bg_path} не загружен, произошка ошибка:\n{e}", level="ERROR")
            print(traceback.format_exc())
            return
        draw = ImageDraw.Draw(background)

        # 2. Шрифты
        font_name = Generator.get_font("Gilroy-ExtraBold.ttf", 48)
        font_info = Generator.get_font("Gilroy-Light.ttf", 28)
        font_xp = Generator.get_font("Gilroy-Bold.ttf", 32)
        
        draw.text((250, 40), str(username), font=font_name, fill="white")
        draw.text((250, 100), f"LEVEL {level} | SEASON 1", font=font_info, fill="#aaaaaa")

        # 4. Прогресс бар
        bar_img = Generator.get_progressbar(current_xp, max_xp, 'bar_empty.png', 'bar_full.png')
        background.paste(bar_img, (50, 160), bar_img)

        # Текст XP
        text = f"{current_xp} / {max_xp} XP"
        draw.text((321, 171), text, font=font_xp, fill="#003300") # Тень
        draw.text((320, 170), text, font=font_xp, fill="#FFFFFF") # Белый

        # 5. Аватарка
        if avatar_url:
            try:
                response = requests.get(avatar_url, timeout=5)
                avatar_bytes = io.BytesIO(response.content)
                avatar = Image.open(avatar_bytes).convert("RGBA")
                avatar = avatar.resize((100, 100))
                
                # Делаем круг
                avatar_circle = Generator.make_circle(avatar)
                background.paste(avatar_circle, (30, 30), avatar_circle)
                log(f'Аватарка пользователя {username} получена', level='DEBUG')
            except Exception as e:
                log(f'Ошибка загрузки аватарки пользователя {username}\n{e}', level='DEBUG')
                print(traceback.format_exc())
                return None

        output_buffer = io.BytesIO()
        background.save(output_buffer, format="PNG")
        output_buffer.seek(0)
        

        return output_buffer

        
        
        
    