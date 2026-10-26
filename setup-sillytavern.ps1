$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

$root = Join-Path ([Environment]::GetFolderPath('Desktop')) 'SillyTavern-release'
$st   = Join-Path $root 'SillyTavern-release'
$nodeDir = Join-Path $st 'node'
$log  = Join-Path $root 'setup.log'

function Say([string]$m) {
    $line = '[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $m
    try { Add-Content -LiteralPath $log -Value $line -Encoding utf8 -ErrorAction SilentlyContinue } catch {}
    Write-Output $line
}

Say '=== setup start ==='
Say "root    : $root"
Say "app dir : $st"
if (-not (Test-Path -LiteralPath $st)) {
    Say 'ABORT: app dir not found'
    return
}

# ---------- 1. portable Node (includes npm) ----------
$nodeExe = Join-Path $nodeDir 'node.exe'
$npmCmd  = Join-Path $nodeDir 'npm.cmd'

if (Test-Path -LiteralPath $npmCmd) {
    Say 'node already installed, skip download'
} else {
    Say 'querying nodejs.org for latest LTS ...'
    $ver = $null
    try {
        $idx  = Invoke-RestMethod -Uri 'https://nodejs.org/dist/index.json' -TimeoutSec 45
        $cand = $idx | Where-Object { $_.lts } | Select-Object -First 1
        if ($cand) { $ver = $cand.version }
        Say "latest LTS = $ver"
    } catch {
        Say "index fetch failed: $($_.Exception.Message)"
    }
    if (-not $ver) { $ver = 'v24.22.0'; Say "fallback version = $ver" }

    $zip = Join-Path $env:TEMP ("node-$ver-win-x64.zip")
    $url = "https://nodejs.org/dist/$ver/node-$ver-win-x64.zip"
    Say "downloading $url"
    try {
        Invoke-WebRequest -Uri $url -OutFile $zip -TimeoutSec 900
        Say ("downloaded " + [math]::Round((Get-Item -LiteralPath $zip).Length / 1MB, 1) + " MB")
        $tmp = Join-Path $env:TEMP 'node-extract'
        if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force }
        Expand-Archive -LiteralPath $zip -DestinationPath $tmp -Force
        $inner = Get-ChildItem -LiteralPath $tmp -Directory | Select-Object -First 1
        Say "extracted to $($inner.FullName)"
        if (Test-Path -LiteralPath $nodeDir) { Remove-Item -LiteralPath $nodeDir -Recurse -Force }
        Move-Item -LiteralPath $inner.FullName -Destination $nodeDir -Force
        Say "node placed at $nodeDir"
        Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue
    } catch {
        Say "NODE DOWNLOAD FAILED: $($_.Exception.Message)"
    }
}

Say "node.exe : $(Test-Path -LiteralPath $nodeExe)"
Say "npm.cmd  : $(Test-Path -LiteralPath $npmCmd)"
if (Test-Path -LiteralPath $nodeExe) { Say ("node -v  : " + (& $nodeExe -v 2>&1)) }
if (Test-Path -LiteralPath $npmCmd)  { Say ("npm  -v  : " + (& $npmCmd -v 2>&1)) }

# ---------- 2. npm install ----------
$express = Join-Path $st 'node_modules\express\package.json'
if (Test-Path -LiteralPath $express) {
    Say 'dependencies already installed, skip npm install'
} elseif (Test-Path -LiteralPath $npmCmd) {
    $env:PATH = "$nodeDir;$env:PATH"
    Say 'npm install starting (this takes a few minutes) ...'
    Push-Location -LiteralPath $st
    & $npmCmd install --no-save --no-audit --no-fund --loglevel=error --no-progress --omit=dev --ignore-scripts 2>&1 | ForEach-Object { $_ }
    $code = $LASTEXITCODE
    Pop-Location
    Say "npm install exit code = $code"
} else {
    Say 'SKIP npm install (no npm)'
}
Say "express present : $(Test-Path -LiteralPath $express)"

# ---------- 3. launcher .bat (ASCII body, name built from code points) ----------
$batName = ([char]0x542F) + ([char]0x52A8) + ([char]0x9152) + ([char]0x9986) + '.bat'
$batPath = Join-Path $st $batName
$bat = @'
@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PATH=%~dp0node;%PATH%"
set NODE_ENV=production
if not exist "node_modules\express\package.json" (
  echo Installing dependencies for the first run, please wait...
  call npm install --no-save --no-audit --no-fund --loglevel=error --no-progress --omit=dev --ignore-scripts
)
node server.js %*
pause
'@
try {
    Set-Content -LiteralPath $batPath -Value $bat -Encoding ASCII -ErrorAction Stop
    Say "launcher written: $batPath"
} catch { Say "launcher write failed: $($_.Exception.Message)" }

Say '=== setup done ==='
