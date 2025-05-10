@echo off
REM 设置控制台代码页为UTF-8，以便更好地显示中文和特殊字符
CHCP 65001 > nul

echo ==================================================
echo     Xice_Aitoolbox 启动脚本
echo ==================================================
echo.

REM 获取批处理文件所在的目录
set "SCRIPT_DIR=%~dp0"
REM 切换到脚本所在目录，确保所有相对路径正确
cd /d "%SCRIPT_DIR%"

echo 当前工作目录: %CD%
echo.

REM 检查 Python 是否安装
echo 正在检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo 错误：未检测到 Python。
    echo 请确保 Python 已安装并正确添加到系统的 PATH 环境变量中。
    echo 你可以从 https://www.python.org/downloads/ 下载 Python。
    echo.
    pause
    exit /b 1
)
python --version 2>&1 | findstr /R /C:"Python [3]\.[7-9]\." /C:"Python 3\.\(1[0-9]\|[2-9][0-9]\)\." >nul
if errorlevel 1 (
    echo.
    echo 警告：检测到的 Python 版本可能不是 3.7 或更高版本。
    echo 建议使用 Python 3.7+ 以获得最佳兼容性。
    python --version
    echo.
) else (
    echo Python 环境检查通过.
    python --version
    echo.
)


REM 检查 Node.js 是否安装 (可选，Python脚本内部也会检查)
echo 正在检查 Node.js 环境...
node --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo 警告：未检测到 Node.js。
    echo Xice_Aitoolbox 的核心拦截服务需要 Node.js。
    echo Python 脚本将尝试启动 Node.js 服务，如果 Node.js 未安装，则会失败。
    echo 你可以从 https://nodejs.org/ 下载 Node.js。
    echo.
) else (
    echo Node.js 环境检查通过.
    node --version
    echo.
)

REM 检查 node_modules 目录是否存在
IF NOT EXIST "node_modules" (
    echo.
    echo 警告: "node_modules" 目录不存在。
    echo 这可能意味着 Node.js 依赖项尚未安装。
    echo 你可能需要在项目根目录下手动运行 "npm install" 命令。
    echo Python 脚本在启动时也会进行检查。
    echo.
)

echo 准备启动 Xice_Aitoolbox 主程序 (main.py)...
echo.
REM 使用 start 命令可以在新窗口中运行 Python，但这可能使日志分散
REM start "Xice_Aitoolbox" cmd /c "python main.py & pause"
python main.py

echo.
echo ==================================================
echo Xice_Aitoolbox 主程序已结束。
echo ==================================================
echo.
pause