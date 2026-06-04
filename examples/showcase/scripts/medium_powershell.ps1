# Medium PowerShell script — Fibonacci sequence + process snapshot

# ── Fibonacci ────────────────────────────────────────────────────────────────
function Get-Fibonacci {
    param([int]$Count = 12)
    $seq = @(0, 1)
    for ($i = 2; $i -lt $Count; $i++) {
        $seq += $seq[-1] + $seq[-2]
    }
    return $seq[0..($Count - 1)]
}

$fib = Get-Fibonacci -Count 12
Write-Output "=== PowerShell: Fibonacci (first 12) ==="
Write-Output ($fib -join "  ")
Write-Output "Sum : $(($fib | Measure-Object -Sum).Sum)"
Write-Output "Max : $(($fib | Measure-Object -Maximum).Maximum)"

# ── Top processes ────────────────────────────────────────────────────────────
Write-Output ""
Write-Output "=== Top 5 Processes by Memory ==="
Get-Process |
  Sort-Object WorkingSet -Descending |
  Select-Object -First 5 |
  ForEach-Object {
    $mb = [math]::Round($_.WorkingSet / 1MB, 1)
    Write-Output ("  {0,-25} {1,7} MB" -f $_.Name, $mb)
  }
