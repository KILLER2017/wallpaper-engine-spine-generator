@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM 优先使用带完整 Tcl/Tk 的系统 Python 3.12；若路径不同请改下面这一行。
set "PY=D:\Program Files\Python312\python.exe"
if not exist "%PY%" set "PY=python"

"%PY%" gui.py
if errorlevel 1 (
  echo.
  echo 程序异常退出，请把上方报错反馈。
  pause
)
