<#
.SYNOPSIS
    DFS ServiceWatch - Overnight Database Update Runner
.DESCRIPTION
    Runs the complete data update workflow.
    Designed for manual execution or Windows Task Scheduler.
.NOTES
    To schedule with Task Scheduler:
    Program: powershell.exe
    Arguments: -ExecutionPolicy Bypass -File "C:\path\to\run_overnight_update.ps1"
    Start in: C:\path\to\dfs_servdash
#>

# Set error preference to stop on errors
$ErrorActionPreference = "Stop"

# Get the script's directory and move there
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "DFS ServiceWatch - Overnight Update Starting" -ForegroundColor Cyan
Write-Host "============================================================"
Write-Host "Started at: $(Get-Date)"
Write-Host "Working Dir: $ScriptDir`n"

# 1. Activate Virtual Environment if it exists
$VenvPath = Join-Path $ScriptDir ".venv\Scripts\Activate.ps1"
if (Test-Path $VenvPath) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    . $VenvPath
} else {
    Write-Host "No virtual environment found at .venv, using system python..." -ForegroundColor DarkGray
}

# 2. Run the Python Orchestration Script
Write-Host "Running overnight_update.py..." -ForegroundColor Green
try {
    # Using Start-Process to ensure we catch exit codes correctly
    $Process = Start-Process -FilePath "python" -ArgumentList "overnight_update.py" -PassThru -NoNewWindow -Wait
    $ExitCode = $Process.ExitCode
}
catch {
    Write-Error "Failed to launch python process: $_"
    $ExitCode = 1
}

Write-Host "`n============================================================" -ForegroundColor Cyan
if ($ExitCode -eq 0) {
    Write-Host "Update completed SUCCESSFULLY" -ForegroundColor Green
} else {
    Write-Host "Update FAILED with exit code: $ExitCode" -ForegroundColor Red
}
Write-Host "Finished at: $(Get-Date)"
Write-Host "============================================================"

# 3. Check for errors and pause if run manually (not in scheduled task)
if ($ExitCode -ne 0) {
    Write-Host "`nERROR: Update failed! Check the logs folder for details." -ForegroundColor Red
    
    # Only pause if running interactively
    if ($Host.Name -eq 'ConsoleHost') {
        Read-Host "Press Enter to exit..."
    }
    exit $ExitCode
}

exit 0
