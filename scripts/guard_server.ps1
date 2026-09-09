# -*- coding: utf-8 -*-
# 本地 Gradio 守护脚本：检测 7860 端口无服务时自动重启 serve.py（v2 权重）
# 由 Windows 计划任务每 5 分钟调用一次；日志写入 D:\ai\logs（符合"大文件/日志存 D 盘"偏好）
$ErrorActionPreference = 'SilentlyContinue'

$port = 7860
# 用 netstat 检测（Get-NetTCPConnection 在本机 CIM 查询可能异常，导致误判重复启动）
$listening = netstat -ano | Select-String ":$port\s+.*LISTENING"
if ($listening) {
    exit 0
}

$logDir = 'D:\ai\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$py     = 'C:\Users\48544\Doubao\chats\2026-09-02\new-chat\business-admin-answer-helper\.venv_train\Scripts\python.exe'
$script = 'C:\Users\48544\Doubao\chats\2026-09-02\new-chat\business-admin-answer-helper\scripts\serve.py'
$adapter = 'D:/ai/outputs/business-admin-answer-helper-3b-v2/adapter'

Start-Process -FilePath $py `
    -ArgumentList @($script, '--adapter', $adapter, '--port', '7860') `
    -WindowStyle Hidden `
    -RedirectStandardOutput "$logDir\serve.out.log" `
    -RedirectStandardError "$logDir\serve.err.log"

"$([DateTime]::Now)  serve.py was down -> restarted" | Out-File "$logDir\guard.log" -Append -Encoding UTF8
