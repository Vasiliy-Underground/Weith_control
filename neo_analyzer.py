#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NEO ANALYZER v2.0 - Киберпанк анализатор дискового пространства
© 2026 Vasiliy-Underground (MIT License)
"""

import os
import sys
import time
import json
import sqlite3
import threading
import ctypes
from datetime import datetime
from pathlib import Path

# Для цветов в консоли Windows
if sys.platform == 'win32':
    os.system('color 0D')
    os.system('chcp 65001 > nul')
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

# Цвета ANSI
PURPLE = '\033[95m'
PINK = '\033[95m'
CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'

# Глобальные переменные
stop_scan = False
current_cache = {}
cache_conn = None
cache_cursor = None

def init_cache():
    """Инициализация SQLite кэша"""
    global cache_conn, cache_cursor
    os.makedirs('analyzer_data', exist_ok=True)
    cache_conn = sqlite3.connect('analyzer_data/cache.db', timeout=10)
    cache_cursor = cache_conn.cursor()
    cache_cursor.execute('''
        CREATE TABLE IF NOT EXISTS folder_cache (
            path TEXT PRIMARY KEY,
            size INTEGER,
            scan_date TEXT,
            children_data TEXT
        )
    ''')
    cache_conn.commit()

def save_to_cache(path, size, children_data):
    """Сохранение данных в кэш"""
    try:
        cache_cursor.execute('''
            INSERT OR REPLACE INTO folder_cache (path, size, scan_date, children_data)
            VALUES (?, ?, ?, ?)
        ''', (path, size, datetime.now().isoformat(), json.dumps(children_data)))
        cache_conn.commit()
    except:
        pass

def load_from_cache(path):
    """Загрузка данных из кэша"""
    try:
        cache_cursor.execute('SELECT size, scan_date, children_data FROM folder_cache WHERE path = ?', (path,))
        row = cache_cursor.fetchone()
        if row:
            return {'size': row[0], 'scan_date': row[1], 'children': json.loads(row[2])}
    except:
        pass
    return None

def clear_cache():
    """Очистка кэша"""
    try:
        cache_cursor.execute('DELETE FROM folder_cache')
        cache_conn.commit()
        return True
    except:
        return False

def get_folder_size_fast(path):
    """Быстрое получение размера папки из свойств Windows (без рекурсии)"""
    try:
        if os.path.isfile(path):
            return os.path.getsize(path)
        total = 0
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat().st_size
                    elif entry.is_dir(follow_symlinks=False):
                        total += get_folder_size_fast(entry.path)
                except (PermissionError, OSError):
                    continue
        return total
    except:
        return 0

def format_size(bytes_size):
    """Форматирование размера"""
    if bytes_size >= 1024**3:
        return f"{bytes_size / 1024**3:.2f} ГБ"
    elif bytes_size >= 1024**2:
        return f"{bytes_size / 1024**2:.2f} МБ"
    elif bytes_size >= 1024:
        return f"{bytes_size / 1024:.2f} КБ"
    else:
        return f"{bytes_size} Б"

def get_size_and_children(path, progress_callback=None):
    """Рекурсивный подсчет размера и сбор детей"""
    global stop_scan
    if stop_scan:
        return 0, {}
    
    children = {}
    total = 0
    
    try:
        with os.scandir(path) as it:
            items = list(it)
            for idx, entry in enumerate(items):
                if stop_scan:
                    return 0, {}
                if progress_callback:
                    progress_callback(idx + 1, len(items), entry.name)
                try:
                    if entry.is_file(follow_symlinks=False):
                        size = entry.stat().st_size
                        total += size
                        children[entry.name] = size
                    elif entry.is_dir(follow_symlinks=False):
                        sub_size, sub_children = get_size_and_children(entry.path, progress_callback)
                        total += sub_size
                        children[entry.name] = sub_size
                        save_to_cache(entry.path, sub_size, sub_children)
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass
    
    return total, children

def scan_folder(path, show_progress=True):
    """Сканирование папки с прогресс-баром"""
    global stop_scan
    stop_scan = False
    
    print(f"\n{PURPLE}{'='*70}{RESET}")
    print(f"{CYAN}🔍 СКАНИРОВАНИЕ: {path}{RESET}")
    print(f"{PURPLE}{'='*70}{RESET}\n")
    
    anim_chars = ['⚛', '∞', '∫', '∑', '√', '🧬', '💠', '🔷']
    anim_idx = 0
    last_percent = -1
    
    def progress_callback(current, total, name):
        nonlocal anim_idx, last_percent
        if total > 0:
            percent = int(current / total * 100)
            if percent != last_percent:
                last_percent = percent
                anim_idx = (anim_idx + 1) % len(anim_chars)
                bar_len = 40
                filled = int(bar_len * percent / 100)
                bar = '█' * filled + '░' * (bar_len - filled)
                sys.stdout.write(f"\r{anim_chars[anim_idx]} Прогресс: [{bar}] {percent}%")
                sys.stdout.flush()
    
    start_time = time.time()
    total_size, children = get_size_and_children(path, progress_callback if show_progress else None)
    elapsed = time.time() - start_time
    
    sys.stdout.write(f"\n✅ Сканирование завершено за {elapsed:.1f} сек\n")
    
    save_to_cache(path, total_size, children)
    
    return total_size, children

def get_status_icon(path, cached_data):
    """Получение иконки статуса для папки"""
    if not cached_data:
        return f"{DIM}⚡ НЕТ ДАННЫХ{RESET}"
    
    current_size = get_folder_size_fast(path)
    cached_size = cached_data['size']
    
    if abs(current_size - cached_size) < 1024 * 1024:  # меньше 1 МБ разницы
        return f"{GREEN}✅ {format_size(cached_size)}{RESET}"
    else:
        diff = current_size - cached_size
        diff_str = format_size(abs(diff))
        direction = "+" if diff > 0 else "-"
        return f"{YELLOW}⚠️ {format_size(cached_size)} ({direction}{diff_str}){RESET}"

def draw_spectral_diagram(path, data):
    """Отрисовка спектральной диаграммы"""
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print(f"{PURPLE}{'='*70}{RESET}")
    print(f"{CYAN}{BOLD}📊 {os.path.basename(path)} ({format_size(data['size'])}){RESET}")
    print(f"{DIM}СПЕКТРАЛЬНЫЙ АНАЛИЗ | {data['scan_date']}{RESET}")
    print(f"{PURPLE}{'='*70}{RESET}\n")
    
    items = list(data['children'].items())
    items.sort(key=lambda x: x[1], reverse=True)
    total = data['size']
    
    for name, size in items[:15]:
        percent = (size / total * 100) if total > 0 else 0
        bar_len = 50
        filled = int(bar_len * percent / 100)
        bar = '█' * filled + '░' * (bar_len - filled)
        print(f"{CYAN}{name[:30]}{RESET} {GREEN}{bar}{RESET} {YELLOW}{format_size(size)}{RESET} ({percent:.1f}%)")
    
    if len(items) > 15:
        print(f"\n{DIM}... и еще {len(items)-15} элементов{RESET}")
    
    print(f"\n{PURPLE}{'='*70}{RESET}")
    print(f"{DIM}[←→] Навигация  [Enter] Детали  [H] HTML  [Esc] Назад{RESET}")

def navigate_filesystem():
    """LiDAR-навигатор"""
    current_path = os.path.expanduser('~')
    current_index = 0
    page = 0
    items_per_page = 10
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Шапка
        print(f"{PURPLE}╔{'═'*68}╗{RESET}")
        print(f"{PURPLE}║{RESET} {CYAN}{BOLD}🧬 LIDAR NAVIGATOR v2.0{RESET}{' '*43}{PURPLE}║{RESET}")
        print(f"{PURPLE}╠{'═'*68}╣{RESET}")
        
        # Текущий путь
        display_path = current_path if len(current_path) <= 60 else '...' + current_path[-57:]
        print(f"{PURPLE}║{RESET} {YELLOW}📍{RESET} {display_path}{' '*(66-len(display_path))}{PURPLE}║{RESET}")
        print(f"{PURPLE}╠{'═'*68}╣{RESET}")
        
        # Получение списка папок
        try:
            items = []
            with os.scandir(current_path) as it:
                for entry in it:
                    if entry.is_dir() and not entry.name.startswith('.'):
                        items.append(entry.name)
            items.sort(key=str.lower)
            
            # Добавляем ".." для навигации вверх
            if current_path != os.path.dirname(current_path):
                items.insert(0, '..')
        except PermissionError:
            items = ['..'] if current_path != os.path.dirname(current_path) else []
        
        # Пагинация
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(items))
        page_items = items[start_idx:end_idx]
        total_pages = (len(items) + items_per_page - 1) // items_per_page if items else 1
        
        # Отображение списка
        print(f"{PURPLE}║{RESET}                                                      {PURPLE}║{RESET}")
        for idx, item in enumerate(page_items):
            full_path = os.path.join(current_path, item)
            cached = load_from_cache(full_path)
            status = get_status_icon(full_path, cached)
            
            cursor = "▶" if idx == current_index else " "
            prefix = "📁" if item != '..' else "⬆️"
            name_display = item if len(item) <= 35 else item[:32] + "..."
            
            print(f"{PURPLE}║{RESET}  {cursor} {prefix} {name_display:<35} {status:<30} {PURPLE}║{RESET}")
        
        # Заполнение пустых строк
        for _ in range(items_per_page - len(page_items)):
            print(f"{PURPLE}║{RESET}                                                      {PURPLE}║{RESET}")
        
        # Футер
        print(f"{PURPLE}╠{'═'*68}╣{RESET}")
        print(f"{PURPLE}║{RESET} {DIM}▲/▼ Навигация  ► Войти  ◄ Назад  S Сканировать  V Визуализация{RESET} {PURPLE}║{RESET}")
        print(f"{PURPLE}║{RESET} {DIM}Q/E Страницы  X Очистить кэш  0 Выход{RESET}{' '*33}{PURPLE}║{RESET}")
        print(f"{PURPLE}╚{'═'*68}╝{RESET}")
        
        # Ввод пользователя
        key = get_key()
        
        if key == 'UP' and current_index > 0:
            current_index -= 1
            if current_index < 0:
                current_index = 0
                if page > 0:
                    page -= 1
                    current_index = items_per_page - 1
        elif key == 'DOWN' and current_index < len(page_items) - 1:
            current_index += 1
            if current_index >= items_per_page and page < total_pages - 1:
                page += 1
                current_index = 0
        elif key == 'RIGHT' and page_items:
            selected = page_items[current_index]
            if selected == '..':
                current_path = os.path.dirname(current_path)
                current_index = 0
                page = 0
            else:
                current_path = os.path.join(current_path, selected)
                current_index = 0
                page = 0
        elif key == 'LEFT':
            parent = os.path.dirname(current_path)
            if parent != current_path:
                current_path = parent
                current_index = 0
                page = 0
        elif key == 's':
            if page_items:
                selected = page_items[current_index]
                if selected != '..':
                    full_path = os.path.join(current_path, selected)
                    print(f"\n{YELLOW}⚠️ Сканирование {selected}... Нажмите Ctrl+C для отмены{RESET}")
                    try:
                        size, children = scan_folder(full_path, True)
                        print(f"\n{GREEN}✅ Готово! Размер: {format_size(size)}{RESET}")
                        input(f"\n{DIM}Нажмите Enter для продолжения...{RESET}")
                    except KeyboardInterrupt:
                        global stop_scan
                        stop_scan = True
                        print(f"\n{RED}⚠️ Сканирование прервано{RESET}")
                        input(f"\n{DIM}Нажмите Enter для продолжения...{RESET}")
        elif key == 'v':
            if page_items:
                selected = page_items[current_index]
                if selected != '..':
                    full_path = os.path.join(current_path, selected)
                    cached = load_from_cache(full_path)
                    if cached:
                        draw_spectral_diagram(full_path, cached)
                        input(f"\n{DIM}Нажмите Enter для продолжения...{RESET}")
                    else:
                        print(f"\n{YELLOW}⚠️ Нет данных. Сначала отсканируйте папку (кнопка S){RESET}")
                        time.sleep(1.5)
        elif key == 'q':
            if page > 0:
                page -= 1
                current_index = 0
        elif key == 'e':
            if page < total_pages - 1:
                page += 1
                current_index = 0
        elif key == 'x':
            if clear_cache():
                print(f"\n{GREEN}✅ Кэш очищен{RESET}")
                time.sleep(1)
        elif key == '0':
            print(f"\n{PURPLE}Выход...{RESET}")
            break

def get_key():
    """Кроссплатформенный ввод клавиш"""
    if sys.platform == 'win32':
        import msvcrt
        key = msvcrt.getch()
        if key == b'\xe0':
            key = msvcrt.getch()
            if key == b'H':
                return 'UP'
            elif key == b'P':
                return 'DOWN'
            elif key == b'M':
                return 'RIGHT'
            elif key == b'K':
                return 'LEFT'
        elif key == b's':
            return 's'
        elif key == b'v':
            return 'v'
        elif key == b'q':
            return 'q'
        elif key == b'e':
            return 'e'
        elif key == b'x':
            return 'x'
        elif key == b'0':
            return '0'
        return None
    else:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                ch = sys.stdin.read(2)
                if ch == '[A':
                    return 'UP'
                elif ch == '[B':
                    return 'DOWN'
                elif ch == '[C':
                    return 'RIGHT'
                elif ch == '[D':
                    return 'LEFT'
            elif ch == 's':
                return 's'
            elif ch == 'v':
                return 'v'
            elif ch == 'q':
                return 'q'
            elif ch == 'e':
                return 'e'
            elif ch == 'x':
                return 'x'
            elif ch == '0':
                return '0'
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return None

def draw_logo():
    """Криповатый корпоративный логотип"""
    os.system('cls' if os.name == 'nt' else 'clear')
    
    logo = f"""
{PURPLE}
╔{'═'*68}╗
║{RESET}{' '*68}{PURPLE}║{RESET}
║{RESET}     {CYAN}◤◢◣◥{RESET}{' '*57}{PURPLE}║{RESET}
║{RESET}    {CYAN}◢ RDNK ◣{RESET}{' '*55}{PURPLE}║{RESET}
║{RESET}    {CYAN}◥████◤{RESET}{' '*56}{PURPLE}║{RESET}
║{RESET}     {CYAN}◣◥◢◤{RESET}{' '*57}{PURPLE}║{RESET}
║{RESET}{' '*68}{PURPLE}║{RESET}
║{RESET}     {BOLD}{PINK}FOLDER ANALYZER v2.0{RESET}{' '*44}{PURPLE}║{RESET}
║{RESET}{' '*68}{PURPLE}║{RESET}
║{RESET}     {DIM}КИБЕРПАНК ЭДИШН{RESET}{' '*47}{PURPLE}║{RESET}
║{RESET}{' '*68}{PURPLE}║{RESET}
╠{'═'*68}╣
║{RESET}{' '*68}{PURPLE}║{RESET}
"""
    
    print(logo)
    
    # Анимация загрузки
    for i in range(101):
        bar_len = 50
        filled = int(bar_len * i / 100)
        bar = '█' * filled + '░' * (bar_len - filled)
        sys.stdout.write(f"\r{PURPLE}║{RESET}     {DIM}ЗАГРУЗКА: [{bar}] {i}%{RESET}{' '*15}{PURPLE}║{RESET}")
        sys.stdout.flush()
        time.sleep(0.02)
    
    footer = f"""
{PURPLE}╠{'═'*68}╣
║{RESET}{' '*68}{PURPLE}║{RESET}
║{RESET}     {DIM}© 2026 Vasiliy-Underground | MIT License{RESET}{' '*21}{PURPLE}║{RESET}
║{RESET}{' '*68}{PURPLE}║{RESET}
╚{'═'*68}╝{RESET}
"""
    print(footer)
    time.sleep(1)

def main():
    """Главная функция"""
    try:
        init_cache()
        draw_logo()
        navigate_filesystem()
    except KeyboardInterrupt:
        print(f"\n{RED}Программа прервана{RESET}")
    finally:
        if cache_conn:
            cache_conn.close()

if __name__ == "__main__":
    main()