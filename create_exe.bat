@echo off
chcp 65001 > nul
title NEO ANALYZER - BUILD EXE

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║     ◤◢◣◥                                                    ║
echo ║    ◢ RDNK ◣              NEO ANALYZER                       ║
echo ║    ◥████◤               BUILD SYSTEM v3.0                   ║
echo ║     ◣◥◢◤                                                    ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo.

echo [1/3] Проверка Python...
python --version
if errorlevel 1 (
    echo ❌ Python не установлен!
    pause
    exit /b 1
)
echo.

echo [2/3] Проверка файла neo_analyzer.py...
if not exist "neo_analyzer.py" (
    echo ❌ Файл neo_analyzer.py не найден!
    pause
    exit /b 1
)
echo ✅ Файл найден
echo.

echo [3/3] Сборка EXE (через Python)...
echo Это займет 1-2 минуты, подождите...
echo.

python -m PyInstaller --onefile --console --name "NeoAnalyzer" --clean --noconfirm neo_analyzer.py

if errorlevel 1 (
    echo.
    echo ❌ Ошибка сборки!
    echo.
    echo Попробуйте установить PyInstaller заново:
    echo pip uninstall pyinstaller -y
    echo pip install pyinstaller
    pause
    exit /b 1
)

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║                     ✅ ГОТОВО!                              ║
echo ║                                                              ║
echo ║     Файл создан: dist\NeoAnalyzer.exe                       ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

echo Открыть папку с программой?
echo.
choice /c YN /n /m "Нажмите Y для открытия папки, N для выхода: "

if errorlevel 2 goto :exit
if errorlevel 1 goto :open

:open
explorer dist
goto :exit

:exit
echo.
pause