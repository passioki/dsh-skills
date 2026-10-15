<#
================================================================
 DSH 技能仓库 —— 一键安装 / 同步到本机
================================================================
把 <本仓库>\skills\<技能名>\ 安装到 DSH 的扫描根（$DSH_HOME\skills\）：

  默认 = Junction（目录联接）
      ⇒ 以后只要 git pull，技能立刻是最新（不用再跑本脚本）
      ⇒ 不需要管理员权限

  -Copy = 复制
      ⇒ 只在 DSH 目录里放文件副本，不建联接
      ⇒ 每次 git pull 之后要再跑一次本脚本

用法（☆ 在仓库根目录执行）：
  .\install.ps1                      # 安装 / 换成 junction 模式
  .\install.ps1 -Copy                # 安装 / 更新成复制模式
  .\install.ps1 -WhatIf              # 只看会做什么，不动任何文件
  .\install.ps1 -DshHome 'X:\.dsh'   # 手工指定 DSH 配置根

★ 安全约定（重要）
  · 目标已存在且是【真目录】⇒ 先【改名备份】为 <名字>.bak-<时间戳>
    —— 绝不静默删除；备份不会自动清理，确认没问题后你自己删
  · 目标已存在且是【联接 / 符号链接】⇒ 用 rmdir 只删链接本体
    （※ 不用 Remove-Item -Recurse：旧版 PowerShell 会连带删掉
       链接【指向的真实内容】—— 这是个真实的坑）
  · 建联接失败 ⇒ 自动把备份改回原名（回滚）
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$DshHome,
    [switch]$Copy
)

$ErrorActionPreference = 'Stop'
function Info($m) { Write-Host $m }
function Warn($m) { Write-Host $m -ForegroundColor Yellow }

# ---------- 1. 定位 DSH 配置根 ----------
if (-not $DshHome) {
    if ($env:DSH_HOME) { $DshHome = $env:DSH_HOME }
    else { $DshHome = Join-Path $env:USERPROFILE '.dsh' }
}
$DshHome    = [System.IO.Path]::GetFullPath($DshHome)
$skillsRoot = Join-Path $DshHome 'skills'
$repoSkills = Join-Path $PSScriptRoot 'skills'
$mode       = if ($Copy) { '复制（-Copy）' } else { 'Junction 联接（git pull 即同步）' }

Info "DSH 配置根   : $DshHome"
Info "技能扫描目录 : $skillsRoot"
Info "仓库技能来源 : $repoSkills"
Info "模式         : $mode"
Info ''

if (-not (Test-Path -LiteralPath $repoSkills)) {
    throw "找不到 $repoSkills —— ☆ 请在仓库根目录运行本脚本"
}
if (-not (Test-Path -LiteralPath $skillsRoot)) {
    if ($PSCmdlet.ShouldProcess($skillsRoot, '创建技能扫描目录')) {
        New-Item -ItemType Directory -Path $skillsRoot -Force | Out-Null
    }
}

function Test-IsLink($p) {
    $i = Get-Item -LiteralPath $p -Force
    return [bool]($i.Attributes -band [IO.FileAttributes]::ReparsePoint)
}

$done = @()
foreach ($src in Get-ChildItem -LiteralPath $repoSkills -Directory) {
    $name = $src.Name
    $dst  = Join-Path $skillsRoot $name
    Info "── $name"

    $backup = $null
    if (Test-Path -LiteralPath $dst) {
        if (Test-IsLink $dst) {
            if ($PSCmdlet.ShouldProcess($dst, '移除旧联接（只删链接本体）')) {
                cmd /c rmdir "$dst" | Out-Null
                Info '   旧联接已移除'
            }
        } else {
            $backup = "$dst.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
            if ($PSCmdlet.ShouldProcess($dst, "改名备份为 $backup")) {
                Rename-Item -LiteralPath $dst -NewName (Split-Path $backup -Leaf)
                Warn "   目标已存在（真目录）⇒ 已改名备份: $backup"
            }
        }
    }

    try {
        if ($Copy) {
            if ($PSCmdlet.ShouldProcess($dst, '复制技能文件')) {
                Copy-Item -LiteralPath $src.FullName -Destination $dst -Recurse -Force
                Info '   已复制'
            }
        } else {
            if ($PSCmdlet.ShouldProcess($dst, "新建联接 -> $($src.FullName)")) {
                New-Item -ItemType Junction -Path $dst -Target $src.FullName | Out-Null
                Info '   已新建联接'
            }
        }
        $done += $name
    } catch {
        if ($backup -and (Test-Path -LiteralPath $backup) -and -not (Test-Path -LiteralPath $dst)) {
            Rename-Item -LiteralPath $backup -NewName $name
            Warn '   ★ 安装失败 ⇒ 已把备份改回原名（回滚完成）'
        }
        throw
    }
}

Info ''
Info ("完成: " + ($done -join ', '))
if ($Copy) {
    Info '★ 每次 git pull 之后，需要再跑一次本脚本以刷新文件'
} else {
    Info '★ 以后 git pull 之后【不用】再跑本脚本（联接已生效）'
}

if ($done -and -not $WhatIfPreference) {
    Info ''
    Info '自检（应列出 SKILL.md）：'
    foreach ($n in $done) {
        $f = Join-Path $skillsRoot "$n\SKILL.md"
        $tag = if (Test-Path -LiteralPath $f) { 'OK  ' } else { '★缺失' }
        Info ("   {0} {1}" -f $tag, $f)
    }
}
