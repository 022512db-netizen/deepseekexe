# ============================================================
# build_exe.ps1 — 只编译 DeepSeekExe.exe
# 用法: powershell -ExecutionPolicy Bypass -File build_exe.ps1 [-Workspace <源码目录>]
# 产物: <Workspace>\dist\DeepSeekExe.exe
# ============================================================
param([string]$Workspace = "C:\Users\asus\Desktop\deepseek")
$ErrorActionPreference = "Continue"  # 脚本用显式 throw + $LASTEXITCODE 检查, 避免 native stderr 中断
$PSNativeCommandUseErrorActionPreference = $false  # python/git 的 stderr 信息不中断脚本

# 结束残留进程, 否则 dist\DeepSeekExe.exe 被占用会导致打包失败
Get-Process -Name DeepSeekExe -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "== 编译 DeepSeekExe.exe ==" -ForegroundColor Cyan
python -m PyInstaller --onefile --windowed --name DeepSeekExe `
    --collect-all webview --collect-all pythonnet --collect-all clr_loader `
    --icon "$Workspace\assets\deepseek.ico" `
    --add-data "$Workspace\assets\deepseek.ico;assets" `
    --add-data "$Workspace\assets\vision_skill;assets\vision_skill" `
    --add-data "$Workspace\assets\default_skills;assets\default_skills" `
    --distpath "$Workspace\dist" --workpath "$Workspace\build" `
    --specpath "$Workspace" "$Workspace\DeepSeekExe.py"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller 打包失败" }

Write-Host "完成: $Workspace\dist\DeepSeekExe.exe" -ForegroundColor Green
