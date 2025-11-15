#!/usr/bin/env python3
"""
Setup launchd (macOS preferred scheduler) for daily data refresh.
This is the recommended alternative to cron on macOS.
"""

import os
import sys
import subprocess
from pathlib import Path

def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent.absolute()

def create_plist():
    """Create the launchd plist file."""
    project_root = get_project_root()
    python_path = project_root / "venv" / "bin" / "python"
    script_path = project_root / "scripts" / "daily_refresh.py"
    log_path = project_root / "logs" / "daily_refresh.log"
    error_log_path = project_root / "logs" / "daily_refresh_error.log"
    
    # Ensure logs directory exists
    log_path.parent.mkdir(exist_ok=True)
    
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.smartinvest.dailyrefresh</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{script_path}</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>{project_root}</string>
    
    <key>StandardOutPath</key>
    <string>{log_path}</string>
    
    <key>StandardErrorPath</key>
    <string>{error_log_path}</string>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>6</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
"""
    
    # Path to user's LaunchAgents directory
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(exist_ok=True)
    
    plist_path = launch_agents_dir / "com.smartinvest.dailyrefresh.plist"
    
    return plist_path, plist_content

def main():
    print("\n" + "=" * 70)
    print("SmartInvest - launchd Setup (macOS Daily Scheduler)")
    print("=" * 70 + "\n")
    
    # Create plist
    print("1. Creating launchd plist file...")
    plist_path, plist_content = create_plist()
    
    with open(plist_path, 'w') as f:
        f.write(plist_content)
    
    print(f"   ✓ Created: {plist_path}\n")
    
    # Unload existing job if present
    print("2. Checking for existing job...")
    result = subprocess.run(
        ['launchctl', 'list'],
        capture_output=True,
        text=True
    )
    
    if 'com.smartinvest.dailyrefresh' in result.stdout:
        print("   Found existing job, unloading...")
        subprocess.run(['launchctl', 'unload', str(plist_path)], check=False)
        print("   ✓ Unloaded old job\n")
    else:
        print("   No existing job found\n")
    
    # Load the new job
    print("3. Loading launchd job...")
    result = subprocess.run(
        ['launchctl', 'load', str(plist_path)],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("   ✓ Job loaded successfully!\n")
    else:
        print(f"   ⚠️  Warning: {result.stderr}\n")
    
    # Verify
    print("4. Verifying installation...")
    result = subprocess.run(
        ['launchctl', 'list'],
        capture_output=True,
        text=True
    )
    
    if 'com.smartinvest.dailyrefresh' in result.stdout:
        print("   ✓ Job is active!\n")
    else:
        print("   ⚠️  Job may not be loaded properly\n")
    
    # Display summary
    print("=" * 70)
    print("SETUP COMPLETE!")
    print("=" * 70 + "\n")
    
    print("📅 Schedule: Daily at 6:00 AM")
    print(f"📝 Logs: {get_project_root()}/logs/daily_refresh.log")
    print(f"❌ Errors: {get_project_root()}/logs/daily_refresh_error.log\n")
    
    print("COMMANDS:")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    print("Test run now:")
    print(f"  launchctl start com.smartinvest.dailyrefresh\n")
    
    print("Check status:")
    print(f"  launchctl list | grep smartinvest\n")
    
    print("View logs:")
    print(f"  tail -f {get_project_root()}/logs/daily_refresh.log\n")
    
    print("Stop job:")
    print(f"  launchctl stop com.smartinvest.dailyrefresh\n")
    
    print("Unload completely:")
    print(f"  launchctl unload {plist_path}\n")
    
    print("Reload after changes:")
    print(f"  launchctl unload {plist_path}")
    print(f"  launchctl load {plist_path}\n")
    
    print("=" * 70)
    
    # Ask about removing cron job
    print("\n⚠️  IMPORTANT: You should remove the old cron job")
    print("Run: crontab -e")
    print("Then delete the line with 'daily_refresh.py'\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)

