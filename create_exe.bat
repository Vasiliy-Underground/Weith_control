@echo off
chcp 65001 > nul
title NEO ANALYZER - BUILD EXE

echo.
echo.
echo ██████╗░██████╗░███╗░░██╗██╗░░██╗  ░█████╗░░█████╗░░░░
echo ██╔══██╗██╔══██╗████╗░██║██║░██╔╝  ██╔══██╗██╔══██╗░░░
echo ██████╔╝██║░░██║██╔██╗██║█████═╝░  ██║░░╚═╝██║░░██║░░░
echo ██╔══██╗██║░░██║██║╚████║██╔═██╗░  ██║░░██╗██║░░██║░░░
echo ██║░░██║██████╔╝██║░╚███║██║░╚██╗  ╚█████╔╝╚█████╔╝██╗
echo ╚═╝░░╚═╝╚═════╝░╚═╝░░╚══╝╚═╝░░╚═╝  ░╚════╝░░╚════╝░╚═╝
echo.
echo ===============================================
echo     NEO ANALYZER - BUILD SYSTEM v3.0
echo ===============================================
echo.
echo.

echo [1/4] Проверка Python...
python --version > nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не установлен!
    echo Скачайте с https://python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python найден
echo.

echo [2/4] Проверка файла neo_analyzer_v3.py...
if not exist "neo_analyzer_v3.py" (
    if exist "neo_analyzer.py" (
        echo [OK] Найден neo_analyzer.py, переименовываю...
        rename neo_analyzer.py neo_analyzer_v3.py
    ) else (
        echo [ОШИБКА] Файл neo_analyzer_v3.py не найден!
        pause
        exit /b 1
    )
)
echo [OK] Файл найден
echo.

echo [3/4] Установка PyInstaller (если нужно)...
pip show pyinstaller > nul 2>&1
if errorlevel 1 (
    echo Установка PyInstaller...
    pip install pyinstaller
)
echo [OK] PyInstaller готов
echo.

echo [4/4] Сборка EXE (1-2 минуты)...
echo.
python -m PyInstaller --onefile --console --name "NeoAnalyzer" --clean --noconfirm neo_analyzer_v3.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Сборка не удалась!
    pause
    exit /b 1
)

echo.
echo ===============================================
echo                ГОТОВО!
echo ===============================================
echo.
echo Файл создан: dist\NeoAnalyzer.exe
echo.
echo Размер: примерно 8-12 МБ
echo.
echo ===============================================
echo.

:open
explorer dist

:exit
pause
