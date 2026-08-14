# ============================================================
# build_portable.ps1 — 重新构建 DeepSeekExe 便携版
# 用法: powershell -ExecutionPolicy Bypass -File build_portable.ps1
# 产物: C:\Users\asus\Desktop\DeepSeekExe-portable\
# ============================================================
$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
$portable  = "C:\Users\asus\Desktop\DeepSeekExe-portable"
$nodeExe   = (Get-Command node -ErrorAction SilentlyContinue).Source

Write-Host "== 1/3 打包 exe ==" -ForegroundColor Cyan
python -m PyInstaller --onefile --windowed --name DeepSeekExe `
    --collect-all webview --collect-all pythonnet --collect-all clr_loader `
    --icon "$workspace\assets\deepseek.ico" `
    --add-data "$workspace\assets\deepseek.ico;assets" `
    --distpath "$workspace\dist" --workpath "$workspace\build" `
    --specpath "$workspace" "$workspace\DeepSeekExe.py"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller 打包失败" }

Write-Host "== 2/3 组装 runtime (node + dsh 引擎) ==" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path "$portable\runtime" | Out-Null

# node.exe
if (-not $nodeExe) { throw "未找到 node.exe, 请先安装 Node.js" }
Copy-Item $nodeExe "$portable\runtime\node.exe" -Force
Write-Host "  node.exe 已拷贝"

# dsh 引擎: 从 npx 缓存自动发现最新安装
$npxRoot = Join-Path $env:LOCALAPPDATA "npm-cache\_npx"
$dshSrc = Get-ChildItem $npxRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object { Test-Path (Join-Path $_.FullName "node_modules\@deepseek-ai\dsh\lib\bin.js") } |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $dshSrc) { throw "npx 缓存中未找到 @deepseek-ai/dsh, 请先安装 dsh" }
Write-Host "  dsh 引擎来源: $($dshSrc.FullName)"
robocopy $dshSrc.FullName "$portable\runtime\dsh" /E /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy 拷贝 dsh 失败" }

Write-Host "== 3/3 拷贝 exe 与配套文件 ==" -ForegroundColor Cyan
Copy-Item "$workspace\dist\DeepSeekExe.exe" "$portable\" -Force
Copy-Item "$workspace\build_portable.ps1" "$portable\build_portable.ps1" -Force
$size = [math]::Round((Get-ChildItem $portable -Recurse -File | Measure-Object Length -Sum).Sum/1MB, 1)
Write-Host "完成! 便携版: $portable (总大小 $size MB)" -ForegroundColor Green
Write-Host "把整个文件夹拷到目标电脑, 双击 DeepSeekExe.exe 即可运行"
