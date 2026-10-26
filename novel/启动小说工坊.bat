@echo off
title 小说工坊
cd /d "%~dp0"

powershell -NoProfile -Command "try{$c=New-Object Net.Sockets.TcpClient;$c.Connect('127.0.0.1',8323);$c.Close();exit 0}catch{exit 1}"
if %errorlevel%==0 (
  echo 小说工坊已经在运行，正在打开浏览器...
  start "" "http://127.0.0.1:8323/"
  timeout /t 2 >nul
  exit /b 0
)

echo 正在启动小说工坊...
start "" "C:\Users\ZhuanZ(无密码)1\.dsh\dsh-runtimes\dsh-next-primary-runtime\dependencies\python\pythonw.exe" "%~dp0server.py"
timeout /t 5 >nul
start "" "http://127.0.0.1:8323/"
exit /b 0