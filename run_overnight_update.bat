@echo off
REM ============================================================
REM DFS ServiceWatch - Overnight Database Update
REM ============================================================
REM This batch file runs the complete data update workflow.
REM Run this overnight or schedule it with Windows Task Scheduler.
REM
REM To schedule with Task Scheduler:
REM   1. Open Task Scheduler
REM   2. Create Basic Task
REM   3. Set trigger to "Daily" at your preferred time (e.g., 2:00 AM)
REM   4. Action: Start a program
REM   5. Program: cmd.exe
REM   6. Arguments: /c "C:\path\to\run_overnight_update.bat"
REM   7. Start in: C:\path\to\dfs_servdash
REM ============================================================

echo.
echo ============================================================
echo DFS ServiceWatch - Overnight Update Starting
echo ============================================================
echo Started at: %date% %time%
echo.

REM Change to script directory
cd /d "%~dp0"

REM Activate virtual environment if exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

REM Run the overnight update script
echo Running overnight_update.py...
python overnight_update.py

REM Capture exit code
set EXIT_CODE=%ERRORLEVEL%

echo.
echo ============================================================
echo Update completed with exit code: %EXIT_CODE%
echo Finished at: %date% %time%
echo ============================================================

REM Keep window open if there was an error
if %EXIT_CODE% NEQ 0 (
    echo.
    echo ERROR: Update failed! Check the logs folder for details.
    echo Press any key to close...
    pause > nul
)

exit /b %EXIT_CODE%
