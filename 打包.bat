@echo off
chcp 65001 >nul
echo ============================================
echo   操作系统处理机调度模拟 - 一键打包工具
echo ============================================
echo.

cd /d "%~dp0"

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

:: 安装依赖（仅必需的）
echo [1/3] 安装依赖...
pip install matplotlib ttkbootstrap pyinstaller -q
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)
echo       依赖安装完成 ✓
echo.

:: 打包（排除无用模块减小体积）
echo [2/3] 正在打包（首次约1-3分钟）...
pyinstaller --noconfirm --onefile --windowed ^
    --name "操作系统处理机调度模拟" ^
    --hidden-import unittest ^
    --exclude-module openpyxl ^
    --exclude-module numpy.random.tests ^
    --exclude-module numpy.tests ^
    --exclude-module matplotlib.tests ^
    --exclude-module pytest ^
    --exclude-module _pytest ^
    --exclude-module email ^
    --exclude-module xmlrpc ^
    --exclude-module pydoc ^
    --exclude-module doctest ^
    --exclude-module lib2to3 ^
    --exclude-module tkinter.test ^
    --exclude-module turtle ^
    --exclude-module turtledemo ^
    --strip ^
    main.py

if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)
echo       打包完成 ✓
echo.

:: 整理输出
echo [3/3] 整理输出...
if not exist "输出" mkdir "输出"
copy /y "dist\操作系统处理机调度模拟.exe" "输出\" >nul
copy /y "README.md" "输出\" >nul

:: 显示文件大小
for %%A in ("输出\操作系统处理机调度模拟.exe") do (
    set "size=%%~zA"
    set /a "sizeMB=%%~zA / 1048576"
)
echo       文件大小: 约 %sizeMB% MB

:: 清理临时文件
rd /s /q build >nul 2>&1
rd /s /q dist >nul 2>&1
del /q *.spec >nul 2>&1

echo.
echo ============================================
echo   打包成功！
echo   文件位置: %cd%\输出\操作系统处理机调度模拟.exe
echo ============================================
echo.

explorer "输出"
pause
