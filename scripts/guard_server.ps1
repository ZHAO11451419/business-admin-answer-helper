# 本地 Gradio 守护脚本（可移植版）：检测端口无服务时自动重启 serve.py
# 用法：由计划任务 / 手动每 N 分钟调用一次。
#   验证配置（不启动服务）：powershell -File scripts\guard_server.ps1 -CheckOnly
#
# 配置优先级（从高到低）：
#   1. guard_config.ps1（仓库根，本机专属，已被 .gitignore 排除，勿提交）
#   2. 环境变量：BAH_ADAPTER / BAH_LOG_DIR / BAH_PYTHON / BAH_PORT
#   3. 脚本内默认值（不依赖任何作者本机路径）
param([switch]$CheckOnly)

$ErrorActionPreference = 'SilentlyContinue'

# --- 仓库根：脚本位于 <仓库>/scripts/ 下，上级即仓库根 ---
$repo = Split-Path -Parent $PSScriptRoot

# --- 本机配置（可选，勿提交）---
$configPath = Join-Path $repo 'guard_config.ps1'
if (Test-Path $configPath) {
    . $configPath
}

# --- 解析配置：环境变量 > 本机配置 > 默认值 ---
$adapter = $env:BAH_ADAPTER
if (-not $adapter) { $adapter = $BAH_Adapter }
if (-not $adapter) { $adapter = 'zhaoweichang/business-admin-answer-helper' }

$logDir = $env:BAH_LOG_DIR
if (-not $logDir) { $logDir = $BAH_LogDir }
if (-not $logDir) { $logDir = Join-Path $repo 'logs' }

$python = $env:BAH_PYTHON
if (-not $python) { $python = $BAH_Python }

$port = $env:BAH_PORT
if (-not $port) { $port = $BAH_Port }
if (-not $port) { $port = 7860 }

# --- Python 自动探测：仓库 venv > 系统 python ---
if (-not $python) {
    $candidates = @(
        (Join-Path $repo '.venv_train\Scripts\python.exe'),
        (Join-Path $repo '.venv\Scripts\python.exe'),
        (Join-Path $repo 'venv\Scripts\python.exe')
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $python = $c; break }
    }
}
if (-not $python) {
    $sysPy = Get-Command python -ErrorAction SilentlyContinue
    if ($sysPy) { $python = $sysPy.Source }
}

$scriptPath = Join-Path $repo 'scripts\serve.py'

if ($CheckOnly) {
    $configMsg = '(未配置，使用默认值)'
    if (Test-Path $configPath) { $configMsg = $configPath }
    Write-Host "repo    = $repo"
    Write-Host "adapter = $adapter"
    Write-Host "logDir  = $logDir"
    Write-Host "python  = $python"
    Write-Host "port    = $port"
    Write-Host "script  = $scriptPath"
    Write-Host "config  = $configMsg"
    if (-not $python) { Write-Host "警告：未找到 python，守护无法启动服务" }
    exit 0
}

if (-not $python) {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    "$([DateTime]::Now)  guard: 找不到 python，跳过本轮" | Out-File (Join-Path $logDir 'guard.log') -Append -Encoding UTF8
    exit 1
}

# 用 netstat 检测（Get-NetTCPConnection 在部分 Windows 上 CIM 查询异常）
$listening = netstat -ano | Select-String ":$port\s+.*LISTENING"
if ($listening) {
    exit 0
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

Start-Process -FilePath $python `
    -ArgumentList @($scriptPath, '--adapter', $adapter, '--port', "$port") `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDir 'serve.out.log') `
    -RedirectStandardError (Join-Path $logDir 'serve.err.log')

"$([DateTime]::Now)  serve.py was down -> restarted (adapter=$adapter)" |
    Out-File (Join-Path $logDir 'guard.log') -Append -Encoding UTF8
