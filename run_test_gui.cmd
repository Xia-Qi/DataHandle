@echo off
setlocal

rem 使用 pythonw（无控制台）优先，否则用 python
where pythonw >nul 2>&1
if %errorlevel%==0 (
  set "PY=pythonw"
) else (
  where python >nul 2>&1
  if %errorlevel%==0 (
    set "PY=python"
  ) else (
    echo Python not found in PATH.
    pause
    exit /b 1
  )
)

rem 脚本目录（%~dp0 包含末尾反斜杠）
set "SCRIPT_DIR=%~dp0"
start "" "%PY%" "%SCRIPT_DIR%test_gui.py"
endlocal