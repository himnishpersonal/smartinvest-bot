#!/usr/bin/env python3
"""
Setup weekly model retraining cron job.
Trains model every Sunday at 2 AM with the week's accumulated data.
"""

import subprocess
import sys
from pathlib import Path

def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent.absolute()

def setup_weekly_cron():
    """Add weekly model training to crontab."""
    project_root = get_project_root()
    python_path = project_root / "venv" / "bin" / "python"
    script_path = project_root / "scripts" / "train_model_v2.py"
    log_path = project_root / "logs" / "weekly_training.log"
    
    # Ensure logs directory exists
    log_path.parent.mkdir(exist_ok=True)
    
    # Cron entry for Sunday 2 AM
    cron_entry = f"0 2 * * 0 cd {project_root} && {python_path} {script_path} >> {log_path} 2>&1"
    
    print("\n" + "=" * 70)
    print("SmartInvest - Weekly Model Training Setup")
    print("=" * 70 + "\n")
    
    print("This will add a cron job to retrain your ML model:")
    print(f"  📅 Schedule: Every Sunday at 2:00 AM")
    print(f"  🔧 Script: {script_path}")
    print(f"  📝 Logs: {log_path}")
    print()
    
    # Get current crontab
    result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
    current_crontab = result.stdout if result.returncode == 0 else ""
    
    # Check if already exists
    if 'train_model_v2.py' in current_crontab:
        print("⚠️  Weekly training cron job already exists!")
        print("\nCurrent entry:")
        for line in current_crontab.split('\n'):
            if 'train_model_v2.py' in line:
                print(f"  {line}")
        print()
        
        response = input("Replace with new schedule? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Cancelled.")
            return
        
        # Remove old entry
        current_crontab = '\n'.join([
            line for line in current_crontab.split('\n')
            if 'train_model_v2.py' not in line
        ])
    
    # Add new entry
    new_crontab = current_crontab.strip() + '\n' + cron_entry + '\n'
    
    # Write to crontab
    process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
    process.communicate(input=new_crontab)
    
    if process.returncode == 0:
        print("✅ Weekly training cron job added successfully!\n")
        print("=" * 70)
        print("SCHEDULE SUMMARY")
        print("=" * 70 + "\n")
        print("DAILY (6:00 PM):")
        print("  • Refresh stock prices")
        print("  • Refresh news & sentiment")
        print("  • Fast execution (~15-20 min)")
        print()
        print("WEEKLY (Sunday 2:00 AM):")
        print("  • Retrain ML model with week's data")
        print("  • Model automatically picked up by bot")
        print("  • Takes ~5-30 minutes")
        print()
        print("=" * 70)
        print("VERIFY CRON JOBS")
        print("=" * 70 + "\n")
        print("View all cron jobs:")
        print("  crontab -l")
        print()
        print("Check training logs (after Sunday 2 AM):")
        print(f"  tail -f {log_path}")
        print()
        print("=" * 70)
        print()
    else:
        print("❌ Failed to add cron job")
        sys.exit(1)

def main():
    """Main function."""
    try:
        setup_weekly_cron()
        
        print("NEXT STEPS:")
        print("━" * 70)
        print()
        print("1. ✅ Weekly training is now scheduled")
        print()
        print("2. 🧪 Test training manually (optional):")
        print("   python scripts/train_model_v2.py")
        print()
        print("3. 📅 First auto-run: Next Sunday at 2:00 AM")
        print()
        print("4. 📊 Bot will automatically use new model")
        print("   (No restart needed - loads on next recommendation)")
        print()
        print("━" * 70)
        print()
        print("✅ Setup complete!")
        print()
        
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

