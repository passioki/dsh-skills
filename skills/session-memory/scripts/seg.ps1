<#
取【指定时间段】的完整对话（含正文，不止首行）。

用法:
  .\seg.ps1 -From '10-11 20:00' -To '10-12 15:00' -File D:\OAS-dev\_both.txt
  .\seg.ps1 -From '10-11 20:00' -To '10-12 15:00' -UserOnly   # 只要用户发言（正文）
  .\seg.ps1 -From '10-11 20:00' -To '10-12 15:00' -WithReply  # 用户 + 此后 1 条助手回复

★ 铁律: 禁止用"首行预览"当读过 —— 本脚本输出【完整正文】。
#>
param(
  [Parameter(Mandatory = $true)][string]$From,
  [Parameter(Mandatory = $true)][string]$To,
  [string]$File = 'D:\OAS-dev\_both.txt',
  [switch]$UserOnly,
  [switch]$WithReply,
  [int]$Max = 0            # 0 = 不限
)

if (-not (Test-Path $File)) { Write-Host "** 找不到 $File"; exit 1 }
$lines = Get-Content $File -Encoding UTF8

# 找起止
$hs = @()
for ($i = 0; $i -lt $lines.Count; $i++) {
  if ($lines[$i] -match '^======== (USER|ASST) \[([\d\-]+ [\d:]+)\] ========$') {
    $hs += [pscustomobject]@{ Idx = $i; Who = $matches[1]; Time = $matches[2] }
  }
}
$start = ($hs | Where-Object { $_.Time -ge $From } | Select-Object -First 1).Idx
$endItem = ($hs | Where-Object { $_.Time -ge $To } | Select-Object -First 1)
$end = if ($endItem) { $endItem.Idx } else { $lines.Count }

if ($null -eq $start) { Write-Host "** 该时间段没有对话"; exit 0 }

$count = 0
for ($i = $start; $i -lt $end; $i++) {
  if ($lines[$i] -match '^======== (USER|ASST) \[([\d\-]+ [\d:]+)\] ========$') {
    $who = $matches[1]
    if ($UserOnly -and $who -ne 'USER') {
      if (-not $WithReply) { continue }
      # WithReply: 只保留紧跟 USER 的那 1 条 ASST
      if ($who -eq 'ASST' -and ($i -gt 0) -and ($lines[$i-1] -match '^======== USER')) { } else { continue }
    }
    Write-Host ""
    Write-Host "======== $who [$($matches[2])] ========"
    $count++
    if ($Max -gt 0 -and $count -gt $Max) { break }
    continue
  }
  if ($lines[$i] -match '^======== ') { continue }
  if ($lines[$i].Trim()) { Write-Host $lines[$i] }
}
Write-Host ""
Write-Host "★ 本次输出块数: $count"
