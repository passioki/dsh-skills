# =============================================================================
# seg.ps1 -- print a WHOLE time-slice of the conversation (full body, not preview)
#
# WHY THIS FILE IS ASCII-ONLY:
#   Windows PowerShell 5.1 decodes a .ps1 WITHOUT a UTF-8 BOM as ANSI/GBK.
#   A non-ASCII string literal or comment would then be mis-decoded and can
#   break parsing. Since this is a *generic* skill (it must run on any machine,
#   after any editor), we keep this script pure ASCII on purpose.
#   Chinese documentation lives in SKILL.md / README.md instead.
#
# Usage (no hard-coded paths):
#   .\seg.ps1 -From '10-11 20:00' -To '10-12 15:00'
#   .\seg.ps1 -From '10-11 20:00' -To '10-12 15:00' -File <other _both.txt>
#   .\seg.ps1 -From ... -To ... -UserOnly     # only user turns
#   .\seg.ps1 -From ... -To ... -UserOnly -WithReply  # user turns + their reply
#
# INPUT RESOLUTION (never guesses):
#   1) -File <path>                       (explicit)
#   2) ./session-memory.config.json  ->   "input"
#   3) ./_both.txt                        (current directory)
#   none of them exists  ->  loud error, exit 1
#
# extract.py writes _both.txt NEXT TO the session jsonl by default.
# =============================================================================
param(
  [Parameter(Mandatory = $true)][string]$From,
  [Parameter(Mandatory = $true)][string]$To,
  [string]$File = '',
  [switch]$UserOnly,
  [switch]$WithReply,
  [int]$Max = 0            # 0 = unlimited
)

# ---------- resolve input file ----------
if (-not $File) {
  $cfg = Join-Path (Get-Location).Path 'session-memory.config.json'
  if (Test-Path $cfg) {
    try {
      $j = Get-Content $cfg -Raw -Encoding UTF8 | ConvertFrom-Json
      if ($j.input) { $File = [string]$j.input }
    } catch { }
  }
}
if (-not $File) { $File = Join-Path (Get-Location).Path '_both.txt' }

if (-not (Test-Path $File)) {
  Write-Host "** conversation dump not found: $File"
  Write-Host "   Run extract.py first (it writes _both.txt next to the session jsonl),"
  Write-Host "   then pass -File <path>, or set \"input\" in session-memory.config.json."
  Write-Host "   This script never guesses a path."
  exit 1
}
$lines = Get-Content $File -Encoding UTF8

# ---------- locate the time window ----------
$hs = @()
for ($i = 0; $i -lt $lines.Count; $i++) {
  if ($lines[$i] -match '^======== (USER|ASST) \[([\d\-]+ [\d:]+)\] ========$') {
    $hs += [pscustomobject]@{ Idx = $i; Who = $matches[1]; Time = $matches[2] }
  }
}
$start = ($hs | Where-Object { $_.Time -ge $From } | Select-Object -First 1).Idx
$endItem = ($hs | Where-Object { $_.Time -ge $To } | Select-Object -First 1)
$end = if ($endItem) { $endItem.Idx } else { $lines.Count }

if ($null -eq $start) { Write-Host "** no conversation in that window"; exit 0 }

$count = 0
$skip = $false   # when a block is filtered out, skip its BODY as well
                 # (old version only skipped the header line, so an assistant
                 #  body leaked into the previous user block)
$prevWho = ''    # who owned the PREVIOUS header (any header, kept or not)
                 # used by -WithReply: keep an ASST block only when it directly
                 # follows a USER block. Checking "$lines[$i-1]" was wrong --
                 # the user's own body sits between the two headers, so the
                 # reply was ALWAYS dropped (old bug).
for ($i = $start; $i -lt $end; $i++) {
  if ($lines[$i] -match '^======== (USER|ASST) \[([\d\-]+ [\d:]+)\] ========$') {
    $who = $matches[1]
    $keepThis = $true
    if ($UserOnly -and $who -ne 'USER') {
      $keepThis = $WithReply -and $who -eq 'ASST' -and $prevWho -eq 'USER'
    }
    $prevWho = $who
    if (-not $keepThis) { $skip = $true; continue }
    $skip = $false
    Write-Host ""
    Write-Host "======== $who [$($matches[2])] ========"
    $count++
    if ($Max -gt 0 -and $count -gt $Max) { break }
    continue
  }
  if ($skip) { continue }
  if ($lines[$i] -match '^======== ') { continue }
  if ($lines[$i].Trim()) { Write-Host $lines[$i] }
}
Write-Host ""
Write-Host "** blocks printed: $count"
