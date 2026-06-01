#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NEO ANALYZER v3.0 - Киберпанк анализатор дискового пространства
© 2026 (MIT License)
"""

import os
import sys
import time
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# ============= НАСТРОЙКИ =============
WINDOW_WIDTH = 100
PROGRESS_UPDATE_INTERVAL = 0.3  # секунды
TOP_FILES_COUNT = 7

# Цвета ANSI
PURPLE = '\033[95m'
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
cache_conn = None
cache_cursor = None

# ============= КЭШ =============
def init_cache():
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
    try:
        cache_cursor.execute('''
            INSERT OR REPLACE INTO folder_cache (path, size, scan_date, children_data)
            VALUES (?, ?, ?, ?)
        ''', (path, size, datetime.now().isoformat(), json.dumps(children_data)))
        cache_conn.commit()
    except:
        pass

def load_from_cache(path):
    try:
        cache_cursor.execute('SELECT size, scan_date, children_data FROM folder_cache WHERE path = ?', (path,))
        row = cache_cursor.fetchone()
        if row:
            return {'size': row[0], 'scan_date': row[1], 'children': json.loads(row[2])}
    except:
        pass
    return None

def clear_cache():
    try:
        cache_cursor.execute('DELETE FROM folder_cache')
        cache_conn.commit()
        return True
    except:
        return False

# ============= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =============
def format_size(bytes_size):
    if bytes_size >= 1024**3:
        return f"{bytes_size / 1024**3:.1f} ГБ"
    elif bytes_size >= 1024**2:
        return f"{bytes_size / 1024**2:.1f} МБ"
    elif bytes_size >= 1024:
        return f"{bytes_size / 1024:.1f} КБ"
    return f"{bytes_size} Б"

def get_all_drives():
    """Получение всех дисков в Windows"""
    drives = []
    if sys.platform == 'win32':
        import string
        from ctypes import windll
        drives_bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if drives_bitmask & 1:
                drives.append(f"{letter}:\\")
            drives_bitmask >>= 1
    else:
        drives = ['/']
    return drives

def get_size_and_children_fast(path, progress_callback=None):
    """Быстрый рекурсивный подсчет с остановкой"""
    global stop_scan
    if stop_scan:
        return 0, {}
    
    children = {}
    total = 0
    
    try:
        with os.scandir(path) as it:
            items = list(it)
            total_items = len(items)
            for idx, entry in enumerate(items):
                if stop_scan:
                    return 0, {}
                
                if progress_callback:
                    progress_callback(idx + 1, total_items, entry.name)
                
                try:
                    if entry.is_file(follow_symlinks=False):
                        size = entry.stat().st_size
                        total += size
                        children[entry.name] = size
                    elif entry.is_dir(follow_symlinks=False):
                        sub_size, _ = get_size_and_children_fast(entry.path, progress_callback)
                        total += sub_size
                        children[entry.name] = sub_size
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass
    
    return total, children

def collect_all_files(path):
    """Собрать все файлы с размерами для ТОПа"""
    all_files = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                if stop_scan:
                    return []
                try:
                    if entry.is_file(follow_symlinks=False):
                        all_files.append((entry.path, entry.stat().st_size))
                    elif entry.is_dir(follow_symlinks=False):
                        all_files.extend(collect_all_files(entry.path))
                except (PermissionError, OSError):
                    continue
    except:
        pass
    return all_files

# ============= СКАНИРОВАНИЕ С ЭКРАНОМ =============
def scan_folder_fullscreen(path):
    """Сканирование на весь экран с анимацией"""
    global stop_scan
    stop_scan = False
    
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Рамка сканирования
    print(f"{PURPLE}{'='*WINDOW_WIDTH}{RESET}")
    print(f"{CYAN}{BOLD}🔍 СКАНИРОВАНИЕ: {path}{RESET}")
    print(f"{PURPLE}{'='*WINDOW_WIDTH}{RESET}\n")
    
    anim_chars = ['⚛', '∞', '∫', '∑', '√', '🧬', '💠', '🔷']
    anim_idx = 0
    last_percent = -1
    last_update_time = 0
    
    def progress_callback(current, total, name):
        nonlocal anim_idx, last_percent, last_update_time
        now = time.time()
        if total > 0 and (now - last_update_time >= PROGRESS_UPDATE_INTERVAL or current == total):
            last_update_time = now
            percent = int(current / total * 100)
            if percent != last_percent:
                last_percent = percent
                anim_idx = (anim_idx + 1) % len(anim_chars)
                
                bar_len = 50
                filled = int(bar_len * percent / 100)
                bar = '█' * filled + '░' * (bar_len - filled)
                
                sys.stdout.write(f"\r{anim_chars[anim_idx]} Прогресс: [{bar}] {percent}%")
                sys.stdout.flush()
    
    start_time = time.time()
    total_size, children = get_size_and_children_fast(path, progress_callback)
    elapsed = time.time() - start_time
    
    print(f"\n\n✅ Сканирование завершено за {elapsed:.1f} сек")
    print(f"📊 Общий размер: {format_size(total_size)}")
    
    save_to_cache(path, total_size, children)
    
    print(f"\n{DIM}Нажмите Enter для возврата...{RESET}")
    input()
    
    return total_size, children

# ============= ТОП-7 ФАЙЛОВ =============
def show_top_files(path, page=0):
    """Показать топ файлов с гистограммой и навигацией"""
    global stop_scan
    stop_scan = False
    
    cached = load_from_cache(path)
    if not cached:
        return
    
    all_files = []
    print(f"\n{DIM}Сбор информации о файлах...{RESET}")
    
    def progress_cb(current, total, name):
        if total > 0 and current % max(1, total//20) == 0:
            sys.stdout.write(f"\r📁 Сканирование файлов: {current}/{total}")
            sys.stdout.flush()
    
    # Собираем все файлы рекурсивно
    all_files = collect_all_files(path)
    
    # Сортируем по размеру
    all_files.sort(key=lambda x: x[1], reverse=True)
    top_files = all_files[:TOP_FILES_COUNT * 3]  # запас для страниц
    
    total_pages = (len(top_files) + TOP_FILES_COUNT - 1) // TOP_FILES_COUNT
    page = max(0, min(page, total_pages - 1)) if total_pages > 0 else 0
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        
        start = page * TOP_FILES_COUNT
        end = min(start + TOP_FILES_COUNT, len(top_files))
        page_files = top_files[start:end]
        
        print(f"{PURPLE}{'='*WINDOW_WIDTH}{RESET}")
        print(f"{CYAN}{BOLD}📁 {os.path.basename(path)} ({format_size(cached['size'])}) - ТОП-{TOP_FILES_COUNT} САМЫХ БОЛЬШИХ ФАЙЛОВ{RESET}")
        print(f"{DIM}Страница {page+1}/{max(1, total_pages)}{RESET}")
        print(f"{PURPLE}{'='*WINDOW_WIDTH}{RESET}\n")
        
        for idx, (filepath, size) in enumerate(page_files, 1):
            filename = os.path.basename(filepath)
            rel_path = os.path.relpath(filepath, path)
            rel_dir = os.path.dirname(rel_path)
            if rel_dir == '.':
                rel_dir = ''
            
            percent = (size / cached['size'] * 100) if cached['size'] > 0 else 0
            bar_len = 40
            filled = int(bar_len * percent / 100)
            bar = '█' * filled + '░' * (bar_len - filled)
            
            # Форматирование с выравниванием
            name_display = filename[:30] + "..." if len(filename) > 30 else filename.ljust(30)
            size_display = format_size(size).rjust(8)
            
            print(f"{YELLOW}{idx}.{RESET} {name_display} {bar} {size_display}")
            if rel_dir:
                print(f"   {DIM}📂 {rel_dir}{RESET}")
            print()
        
        # Заполнение пустых строк
        for _ in range(TOP_FILES_COUNT - len(page_files)):
            print()
        
        print(f"{PURPLE}{'='*WINDOW_WIDTH}{RESET}")
        print(f"{DIM}[Q/E] Страницы    [H] HTML экспорт    [Esc] Назад{RESET}")
        
        key = get_key()
        if key == 'q':
            if page > 0:
                page -= 1
        elif key == 'e':
            if page < total_pages - 1:
                page += 1
        elif key == 'h':
            export_to_html(path, top_files, cached['size'])
            print(f"\n{GREEN}✅ HTML экспорт создан в папке analyzer_data/exports/{RESET}")
            print(f"{DIM}Нажмите Enter для продолжения...{RESET}")
            input()
        elif key == 'escape':
            break

def export_to_html(path, top_files, total_size):
    """Экспорт топа файлов в HTML"""
    os.makedirs('analyzer_data/exports', exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"analyzer_data/exports/export_{timestamp}.html"
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Анализ диска - {os.path.basename(path)}</title>
    <style>
        body {{ background: #0a0a0a; color: #0f0; font-family: 'Courier New', monospace; margin: 20px; }}
        h1 {{ color: #f0f; border-bottom: 2px solid #f0f; }}
        .path {{ color: #ff0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #333; padding: 8px; text-align: left; }}
        th {{ background: #1a1a1a; color: #0ff; }}
        tr:nth-child(even) {{ background: #111; }}
        .size {{ text-align: right; }}
        .bar {{ background: #1a1a1a; border-radius: 3px; overflow: hidden; }}
        .bar-fill {{ background: #0f0; height: 20px; }}
        .footer {{ margin-top: 30px; font-size: 0.8em; color: #666; }}
    </style>
</head>
<body>
    <h1>🔍 Анализ дискового пространства</h1>
    <p><strong>Папка:</strong> <span class="path">{path}</span></p>
    <p><strong>Общий размер:</strong> {format_size(total_size)}</p>
    <p><strong>Всего файлов в топе:</strong> {len(top_files)}</p>
    <table>
        <tr><th>#</th><th>Файл</th><th>Путь</th><th>Размер</th><th>Доля</th></tr>
"""
    
    for idx, (filepath, size) in enumerate(top_files[:50], 1):
        filename = os.path.basename(filepath)
        rel_path = os.path.relpath(filepath, path)
        rel_dir = os.path.dirname(rel_path)
        percent = (size / total_size * 100) if total_size > 0 else 0
        html_content += f"""
        <tr>
            <td>{idx}</td>
            <td>{filename}</td>
            <td><span class="path">{rel_dir if rel_dir != '.' else ''}</span></td>
            <td class="size">{format_size(size)}</td>
            <td>
                <div class="bar">
                    <div class="bar-fill" style="width: {percent}%;"></div>
                </div>
                {percent:.1f}%
            </td>
        </tr>"""
    
    html_content += f"""
    </table>
    <div class="footer">
        Экспорт создан: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br>
        Neo Analyzer v3.0
    </div>
</body>
</html>
"""
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

# ============= НАВИГАТОР =============
def get_directory_items(path):
    """Получение списка элементов в директории (папки + файлы)"""
    items = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        items.append((entry.name, 'dir', entry.path))
                    elif entry.is_file(follow_symlinks=False):
                        items.append((entry.name, 'file', entry.path))
                except (PermissionError, OSError):
                    continue
    except PermissionError:
        pass
    
    # Сортируем: сначала папки, потом файлы, внутри по имени
    dirs = [x for x in items if x[1] == 'dir']
    files = [x for x in items if x[1] == 'file']
    dirs.sort(key=lambda x: x[0].lower())
    files.sort(key=lambda x: x[0].lower())
    
    return dirs + files

def render_navigator(current_path, items, selected_idx, page, items_per_page, total_pages, drives_mode=False):
    """Отрисовка навигатора"""
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Логотип
    logo = f"""
{PURPLE}╭━━━┳━━━┳━╮╱╭┳╮╭━╮
┃╭━╮┣╮╭╮┃┃╰╮┃┃┃┃╭╯
┃╰━╯┃┃┃┃┃╭╮╰╯┃╰╯╯
┃╭╮╭╯┃┃┃┃┃╰╮┃┃╭╮┃
┃┃┃╰┳╯╰╯┃┃╱┃┃┃┃┃╰╮
╰╯╰━┻━━━┻╯╱╰━┻╯╰━╯{RESET}

{PURPLE}██████╗░██████╗░███╗░░██╗██╗░░██╗  ░█████╗░░█████╗░░░░
██╔══██╗██╔══██╗████╗░██║██║░██╔╝  ██╔══██╗██╔══██╗░░░
██████╔╝██║░░██║██╔██╗██║█████═╝░  ██║░░╚═╝██║░░██║░░░
██╔══██╗██║░░██║██║╚████║██╔═██╗░  ██║░░██╗██║░░██║░░░
██║░░██║██████╔╝██║░╚███║██║░╚██╗  ╚█████╔╝╚█████╔╝██╗
╚═╝░░╚═╝╚═════╝░╚═╝░░╚══╝╚═╝░░╚═╝  ░╚════╝░░╚════╝░╚═╝{RESET}
"""
    print(logo)
    
    print(f"{PURPLE}{'='*WINDOW_WIDTH}{RESET}")
    path_display = current_path if len(current_path) <= WINDOW_WIDTH-10 else '...' + current_path[-(WINDOW_WIDTH-13):]
    print(f"{CYAN}📍 {path_display}{RESET}")
    print(f"{PURPLE}{'='*WINDOW_WIDTH}{RESET}")
    
    # Пагинация
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(items))
    page_items = items[start_idx:end_idx]
    
    for i, (name, item_type, full_path) in enumerate(page_items):
        cursor = "▶" if i == selected_idx else " "
        icon = "📁" if item_type == 'dir' else "📄"
        
        # Получение размера из кэша
        cached = load_from_cache(full_path) if item_type == 'dir' else None
        if cached:
            size_str = f"{GREEN}{format_size(cached['size'])} ✓{RESET}"
        else:
            size_str = f"{RED}[НЕТ ДАННЫХ]{RESET}"
        
        name_display = name if len(name) <= 45 else name[:42] + "..."
        print(f"{PURPLE}{cursor}{RESET} {icon} {name_display:<45} {size_str}")
    
    # Заполнение пустых строк
    for _ in range(items_per_page - len(page_items)):
        print()
    
    print(f"{PURPLE}{'='*WINDOW_WIDTH}{RESET}")
    print(f"{DIM}▲/▼ выбор  ► вход  ◄ назад  S сканировать  V топ-7  X очистить кэш  0 выход{RESET}")
    print(f"{DIM}Страница {page+1}/{max(1, total_pages)} (Q/E){RESET}")
    print(f"{PURPLE}{'='*WINDOW_WIDTH}{RESET}")

def navigate_filesystem():
    """Основной навигатор"""
    current_path = None
    items = []
    current_idx = 0
    page = 0
    items_per_page = 15
    
    # Начинаем с дисков
    drives = get_all_drives()
    current_path = "drives"
    
    while True:
        if current_path == "drives":
            items = [(drive, 'dir', drive) for drive in drives]
            render_navigator("ДИСКИ", items, current_idx, page, items_per_page, (len(items)+items_per_page-1)//items_per_page, drives_mode=True)
        else:
            items = get_directory_items(current_path)
            
            # Добавляем ".." для навигации вверх, если не в корне диска
            parent = os.path.dirname(current_path)
            if parent and parent != current_path and len(current_path) > 3:
                items.insert(0, ('..', 'dir', parent))
            
            # Сортируем отсканированные папки вверх
            def sort_key(x):
                name, item_type, full_path = x
                if name == '..':
                    return (0, '', 0)
                cached = load_from_cache(full_path) if item_type == 'dir' else None
                if cached:
                    return (1, -cached['size'], name.lower())  # отсканированные вверх, большие сверху
                else:
                    return (2, 0, name.lower())
            
            items.sort(key=sort_key)
            
            total_pages = (len(items) + items_per_page - 1) // items_per_page if items else 1
            render_navigator(current_path, items, current_idx, page, items_per_page, total_pages)
        
        key = get_key()
        
        if key == 'UP':
            if current_idx > 0:
                current_idx -= 1
                if current_idx < 0:
                    current_idx = 0
                    if page > 0:
                        page -= 1
                        current_idx = items_per_page - 1
        elif key == 'DOWN':
            if current_idx < min(items_per_page, len(items)) - 1:
                current_idx += 1
                if current_idx >= items_per_page and page < (len(items)+items_per_page-1)//items_per_page - 1:
                    page += 1
                    current_idx = 0
        elif key == 'RIGHT':
            if items:
                selected = items[current_idx + page*items_per_page] if page*items_per_page + current_idx < len(items) else None
                if selected:
                    name, item_type, full_path = selected
                    if name == '..':
                        if current_path == "drives":
                            pass
                        else:
                            current_path = full_path
                            current_idx = 0
                            page = 0
                    else:
                        if current_path == "drives":
                            current_path = full_path
                        else:
                            current_path = full_path
                        current_idx = 0
                        page = 0
        elif key == 'LEFT':
            if current_path == "drives":
                pass
            else:
                parent = os.path.dirname(current_path)
                if parent and parent != current_path:
                    if len(parent) == 2 and parent[1] == ':':
                        current_path = "drives"
                    else:
                        current_path = parent
                    current_idx = 0
                    page = 0
        elif key == 's':
            if current_path != "drives" and items:
                selected = items[current_idx + page*items_per_page] if page*items_per_page + current_idx < len(items) else None
                if selected and selected[0] != '..':
                    scan_folder_fullscreen(selected[2])
        elif key == 'v':
            if current_path != "drives" and items:
                selected = items[current_idx + page*items_per_page] if page*items_per_page + current_idx < len(items) else None
                if selected and selected[0] != '..':
                    cached = load_from_cache(selected[2])
                    if cached:
                        show_top_files(selected[2])
                    else:
                        print(f"\n{RED}⚠️ Нет данных. Сначала отсканируйте папку (кнопка S){RESET}")
                        time.sleep(1.5)
        elif key == 'x':
            if clear_cache():
                print(f"\n{GREEN}✅ Кэш очищен{RESET}")
                time.sleep(1)
        elif key == 'q':
            if page > 0:
                page -= 1
                current_idx = 0
        elif key == 'e':
            total_pages = (len(items) + items_per_page - 1) // items_per_page if items else 1
            if page < total_pages - 1:
                page += 1
                current_idx = 0
        elif key == '0':
            break

# ============= ВВОД КЛАВИШ =============
def get_key():
    """Кроссплатформенный ввод одной клавиши"""
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
        elif key == b'x':
            return 'x'
        elif key == b'q':
            return 'q'
        elif key == b'e':
            return 'e'
        elif key == b'0':
            return '0'
        elif key == b'h':
            return 'h'
        elif key == b'\x1b':
            return 'escape'
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
                else:
                    return 'escape'
            elif ch == 's':
                return 's'
            elif ch == 'v':
                return 'v'
            elif ch == 'x':
                return 'x'
            elif ch == 'q':
                return 'q'
            elif ch == 'e':
                return 'e'
            elif ch == 'h':
                return 'h'
            elif ch == '0':
                return '0'
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return None

# ============= MAIN =============
def main():
    try:
        init_cache()
        navigate_filesystem()
    except KeyboardInterrupt:
        print(f"\n{RED}Программа прервана{RESET}")
    finally:
        if cache_conn:
            cache_conn.close()

if __name__ == "__main__":
    main()