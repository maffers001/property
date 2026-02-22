# Run property pipeline for a month. Usage: .\scripts\run_month.ps1 OCT2025
param([Parameter(Mandatory=$true)][string]$Month)
Set-Location $PSScriptRoot\..
$py = Get-Command python -ErrorAction SilentlyContinue; if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }; if (-not $py) { Write-Error "Python not found" }
& $py.Source -m property_pipeline run_month $Month
