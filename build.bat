REM --onefile    : 将所有依赖打包成单个 .exe 文件（便于分发）
REM --windowed   : 不显示命令行窗口（适用于 GUI 程序，如果是控制台程序则不要加这个参数）

pyinstaller.exe --onefile --windowed http_server_gui.py

REM ========== 检查 PyInstaller 是否执行成功 ==========
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller 打包失败，请检查错误信息！
    pause  REM 暂停，防止窗口自动关闭
    exit /b %errorlevel%  REM 退出并返回错误码
)

copy .\dist\*.exe .
