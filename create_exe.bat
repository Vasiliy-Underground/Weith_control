@echo off
echo ====================================
echo   Создание EXE файла
echo ====================================
echo.

REM Проверка установки PyInstaller
pip show pyinstaller > nul 2>&1
if errorlevel 1 (
    echo Установка PyInstaller...
    pip install pyinstaller
)

echo Создание EXE файла...
pyinstaller --onefile --console --clean --name "FolderAnalyzer" folder_analyzer.py

if exist "dist\FolderAnalyzer.exe" (
    echo.
    echo ====================================
    echo   ГОТОВО!
    echo ====================================
    echo Файл создан: dist\FolderAnalyzer.exe
    echo.
    echo Запустите программу:
    echo dist\FolderAnalyzer.exe
) else (
    echo.
    echo ОШИБКА: Не удалось создать EXE файл
)

pause