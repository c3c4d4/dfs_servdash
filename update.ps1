<#
.SYNOPSIS
    DFS ServiceWatch - Daily Update
.DESCRIPTION
    Performs an incremental update of the database.
    
    1. Reads 'oldest.txt' to fetch only recent Chamados.
    2. Checks 'o2c.csv' for any NEW orders to unpack (skips existing).
    3. Enriches only new items with Warranty/RTM info.
    
    This is safe to run multiple times a day.
#>

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "Checking for existing state files..." -ForegroundColor Cyan

# Verify we have the state file from the overnight run
if (-not (Test-Path "oldest.txt")) {
    Write-Host "WARNING: 'oldest.txt' not found." -ForegroundColor Yellow
    Write-Host "This looks like a fresh run. It might take longer to fetch history." -ForegroundColor Yellow
} else {
    $Date = Get-Content "oldest.txt"
    Write-Host "Found last state. Incremental update will start from: $Date" -ForegroundColor Green
}

# Run the orchestration script
# It automatically handles the logic of "skip existing, process new"
Write-Host "`nStarting Incremental Update..." -ForegroundColor Cyan
./run_overnight_update.ps1
