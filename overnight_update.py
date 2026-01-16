"""
DFS ServiceWatch - Overnight Database Update Script
====================================================
This script runs the complete data update workflow overnight.
It processes all data from 2023 onwards with retry logic and detailed logging.

Workflow:
1. Convert o2c.xlsx to o2c.csv (if xlsx exists)
2. Unpack serial numbers (o2c.csv -> o2c_unpacked.csv)
3. Enrich with warranty info (GARANTIA column)
4. Enrich with RTM/Bluetooth info (RTM column)
5. Update chamados from helpdesk API

Run this script overnight with:
    python overnight_update.py

Or use the batch file:
    run_overnight_update.bat
"""

import os
import sys
import time
import subprocess
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
MAX_RETRIES = 3
RETRY_DELAY = 60  # seconds between retries
LOG_DIR = "logs"
BACKUP_RETENTION_DAYS = 7  # Delete backups older than this
SCRIPT_DIR = Path(__file__).parent.absolute()

# Scripts to run in order
SCRIPTS = [
    {
        "name": "Convert XLSX to CSV",
        "script": "convert_xlsx_to_csv.py",
        "required": False,  # Skip if o2c.xlsx doesn't exist
        "condition": lambda: os.path.exists(SCRIPT_DIR / "o2c.xlsx"),
    },
    {
        "name": "Unpack Serial Numbers",
        "script": "unpack_by_serial.py",
        "required": True,
        "condition": lambda: os.path.exists(SCRIPT_DIR / "o2c.csv"),
    },
    {
        "name": "Warranty Check",
        "script": "warranty_check.py",
        "required": True,
        "condition": lambda: os.path.exists(SCRIPT_DIR / "o2c_unpacked.csv"),
    },
    {
        "name": "RTM/Bluetooth Check",
        "script": "rtm_check.py",
        "required": True,
        "condition": lambda: os.path.exists(SCRIPT_DIR / "o2c_unpacked.csv"),
    },
    {
        "name": "Update Chamados",
        "script": "update_chamados.py",
        "required": True,
        "condition": lambda: True,  # Always run
    },
]


class Logger:
    """Simple logger that writes to both console and file."""

    def __init__(self, log_file):
        self.log_file = log_file
        self.terminal = sys.stdout

    def write(self, message):
        self.terminal.write(message)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(message)

    def flush(self):
        self.terminal.flush()


def create_backup(files_to_backup):
    """Create backups of important files before update."""
    backup_dir = SCRIPT_DIR / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=True)

    backed_up = []
    for file_name in files_to_backup:
        src = SCRIPT_DIR / file_name
        if src.exists():
            dst = backup_dir / file_name
            shutil.copy2(src, dst)
            backed_up.append(file_name)

    return backup_dir, backed_up


def rotate_backups():
    """Delete backup directories older than BACKUP_RETENTION_DAYS."""
    backup_root = SCRIPT_DIR / "backups"
    if not backup_root.exists():
        return 0

    deleted_count = 0
    cutoff_date = datetime.now() - timedelta(days=BACKUP_RETENTION_DAYS)

    for backup_dir in backup_root.iterdir():
        if not backup_dir.is_dir():
            continue
        # Parse directory name (format: YYYYMMDD_HHMMSS)
        try:
            dir_date = datetime.strptime(backup_dir.name, "%Y%m%d_%H%M%S")
            if dir_date < cutoff_date:
                shutil.rmtree(backup_dir)
                deleted_count += 1
                print(f"  Deleted old backup: {backup_dir.name}")
        except ValueError:
            # Skip directories that don't match the expected format
            continue

    return deleted_count


def run_script(script_info, log_file):
    """Run a single script with retry logic."""
    script_name = script_info["name"]
    script_path = SCRIPT_DIR / script_info["script"]

    # Check condition
    if not script_info["condition"]():
        print(f"\n{'=' * 60}")
        print(f"SKIPPING: {script_name}")
        print(f"Reason: Precondition not met (missing input file)")
        print(f"{'=' * 60}")
        return True, "skipped"

    # Check if script exists
    if not script_path.exists():
        print(f"\n{'=' * 60}")
        print(f"ERROR: Script not found: {script_path}")
        print(f"{'=' * 60}")
        return False, "script_not_found"

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n{'=' * 60}")
        print(f"RUNNING: {script_name} (Attempt {attempt}/{MAX_RETRIES})")
        print(f"Script: {script_path}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 60}\n")

        try:
            # Run the script
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(SCRIPT_DIR),
                capture_output=False,  # Let output flow to our logger
                timeout=7200,  # 2 hour timeout per script
            )

            if result.returncode == 0:
                print(f"\n{'=' * 60}")
                print(f"SUCCESS: {script_name} completed successfully!")
                print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'=' * 60}")
                return True, "success"
            else:
                print(f"\n{'=' * 60}")
                print(f"FAILED: {script_name} returned exit code {result.returncode}")
                print(f"{'=' * 60}")

        except subprocess.TimeoutExpired:
            print(f"\n{'=' * 60}")
            print(f"TIMEOUT: {script_name} exceeded 2 hour timeout")
            print(f"{'=' * 60}")

        except Exception as e:
            print(f"\n{'=' * 60}")
            print(f"ERROR: {script_name} raised exception: {e}")
            print(f"{'=' * 60}")

        # Retry logic
        if attempt < MAX_RETRIES:
            print(f"\nRetrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)

    # All retries exhausted
    print(f"\n{'=' * 60}")
    print(f"FAILED: {script_name} failed after {MAX_RETRIES} attempts")
    print(f"{'=' * 60}")
    return False, "failed"


def main():
    """Main orchestration function."""
    start_time = datetime.now()

    # Create log directory
    log_dir = SCRIPT_DIR / LOG_DIR
    log_dir.mkdir(exist_ok=True)

    # Create log file
    log_filename = f"update_{start_time.strftime('%Y%m%d_%H%M%S')}.log"
    log_file = log_dir / log_filename

    # Set up logging to file and console
    logger = Logger(str(log_file))
    sys.stdout = logger

    print("=" * 70)
    print("DFS ServiceWatch - Overnight Database Update")
    print("=" * 70)
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Log file: {log_file}")
    print(f"Working directory: {SCRIPT_DIR}")
    print("=" * 70)

    # Create backups of important files
    print("\n--- Creating Backups ---")
    files_to_backup = [
        "chamados.csv",
        "chamados_fechados.csv",
        "o2c_unpacked.csv",
        "oldest.txt",
        "garantia_cache.csv",
        "rtm_cache.csv",
    ]
    backup_dir, backed_up = create_backup(files_to_backup)
    print(f"Backup directory: {backup_dir}")
    print(f"Files backed up: {', '.join(backed_up) if backed_up else 'None'}")

    # Rotate old backups
    print(f"\n--- Rotating Backups (keeping {BACKUP_RETENTION_DAYS} days) ---")
    deleted = rotate_backups()
    print(f"Deleted {deleted} old backup(s)")

    # Track results
    results = {}

    # Run each script
    for script_info in SCRIPTS:
        success, status = run_script(script_info, log_file)
        results[script_info["name"]] = {
            "success": success,
            "status": status,
        }

        # If a required script fails, we continue but log the failure
        if not success and script_info["required"]:
            print(f"\nWARNING: Required script '{script_info['name']}' failed!")
            print("Continuing with remaining scripts...")

    # Summary
    end_time = datetime.now()
    duration = end_time - start_time

    print("\n" + "=" * 70)
    print("UPDATE SUMMARY")
    print("=" * 70)
    print(f"Started:  {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Finished: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: {duration}")
    print()
    print("Results:")
    print("-" * 40)

    all_success = True
    for name, result in results.items():
        status_icon = {
            "success": "[OK]",
            "skipped": "[SKIP]",
            "failed": "[FAIL]",
            "script_not_found": "[ERR]",
        }.get(result["status"], "[?]")

        print(f"  {status_icon} {name}")
        if result["status"] == "failed":
            all_success = False

    print("-" * 40)

    if all_success:
        print("\nALL UPDATES COMPLETED SUCCESSFULLY!")
    else:
        print("\nSOME UPDATES FAILED - Check the log for details.")
        print(f"Log file: {log_file}")

    print("=" * 70)

    # Restore stdout
    sys.stdout = logger.terminal

    return 0 if all_success else 1


if __name__ == "__main__":
    sys.exit(main())
