import os

def get_size(path):
    """Рекурсивно считает размер папки или файла в ГБ"""
    if os.path.isfile(path):
        return os.path.getsize(path)
    
    total = 0
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isfile(item_path):
                total += os.path.getsize(item_path)
            else:
                total += get_size(item_path)
    except (PermissionError, OSError):
        pass  # пропускаем папки, куда нет доступа
    return total

def format_size(bytes_size):
    """Переводит байты в читаемый вид (ГБ, МБ, КБ)"""
    if bytes_size >= 1024**3:
        return f"{bytes_size / 1024**3:.2f} ГБ"
    elif bytes_size >= 1024**2:
        return f"{bytes_size / 1024**2:.2f} МБ"
    elif bytes_size >= 1024:
        return f"{bytes_size / 1024:.2f} КБ"
    else:
        return f"{bytes_size} Б"

def analyze_folder():
    """Основная функция анализа папки"""
    path = input("Введите путь к папке для анализа: ").strip()
    
    # Убираем кавычки, если пользователь их поставил
    path = path.strip('"').strip("'")
    
    if not os.path.exists(path):
        print(f"❌ Путь не существует: {path}")
        return
    
    if not os.path.isdir(path):
        print("❌ Это не папка")
        return
    
    print(f"\n🔍 Анализируем: {path}")
    print("⏳ Это может занять время, особенно на больших дисках...\n")
    
    items = []
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            size = get_size(item_path)
            items.append((item, size, item_path))
    except PermissionError:
        print("⚠️ Нет доступа к некоторым папкам (системные)")
    
    # Сортируем по размеру (от больших к маленьким)
    items.sort(key=lambda x: x[1], reverse=True)
    
    # Выводим результат
    print("=" * 70)
    print(f"{'№':<4} {'Размер':<12} {'Имя':<50}")
    print("=" * 70)
    
    total_size = 0
    for i, (name, size, item_path) in enumerate(items[:50], 1):  # топ-50
        size_str = format_size(size)
        # Обрезаем длинные имена
        name_display = name if len(name) < 47 else name[:44] + "..."
        print(f"{i:<4} {size_str:<12} {name_display}")
        total_size += size
    
    print("=" * 70)
    print(f"\n📊 Всего проанализировано: {len(items)} элементов")
    print(f"💾 Суммарный размер (топ-50): {format_size(total_size)}")
    
    # Дополнительная информация
    if len(items) > 50:
        print(f"⚠️ Показаны только 50 самых больших элементов из {len(items)}")
    
    print("\n💡 Совет: Ищите большие папки вроде 'Downloads', 'Documents', 'Desktop'")
    print("   Также проверьте корзину и временные файлы (Win + R → %temp%)")

if __name__ == "__main__":
    analyze_folder()