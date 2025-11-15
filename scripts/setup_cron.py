"""
Setup automatic daily refresh via cron job.
Creates a cron job that runs daily_refresh.py every day at 6 AM ET.
"""

import sys
import os
from pathlib import Path
import subprocess
import platform

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_project_root():
    """Get absolute path to project root."""
    return Path(__file__).parent.parent.resolve()


def get_python_path():
    """Get path to Python interpreter in venv."""
    project_root = get_project_root()
    
    if platform.system() == "Windows":
        python_path = project_root / "venv" / "Scripts" / "python.exe"
    else:
        python_path = project_root / "venv" / "bin" / "python"
    
    if not python_path.exists():
        # Fallback to system python
        python_path = sys.executable
    
    return str(python_path)


def create_cron_job():
    """
    Create cron job for daily refresh.
    Runs daily at 6:00 AM ET (before market opens at 9:30 AM).
    """
    project_root = get_project_root()
    python_path = get_python_path()
    script_path = project_root / "scripts" / "daily_refresh.py"
    log_path = project_root / "logs" / "daily_refresh.log"
    
    # Create logs directory
    log_path.parent.mkdir(exist_ok=True)
    
    # Cron job command
    # Run at 6 AM ET every day, redirect output to log
    cron_command = (
        f"0 6 * * * "
        f"cd {project_root} && "
        f"{python_path} {script_path} >> {log_path} 2>&1"
    )
    
    logger.info("Creating cron job for daily refresh...")
    logger.info(f"Project root: {project_root}")
    logger.info(f"Python: {python_path}")
    logger.info(f"Script: {script_path}")
    logger.info(f"Log: {log_path}")
    
    if platform.system() == "Windows":
        logger.warning("❌ Cron is not available on Windows")
        logger.info("Use Task Scheduler instead:")
        logger.info(f"  1. Open Task Scheduler")
        logger.info(f"  2. Create Basic Task")
        logger.info(f"  3. Trigger: Daily at 6:00 AM")
        logger.info(f"  4. Action: Start a program")
        logger.info(f"  5. Program: {python_path}")
        logger.info(f"  6. Arguments: {script_path}")
        logger.info(f"  7. Start in: {project_root}")
        return False
    
    # Check if cron job already exists
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True
        )
        
        existing_crontab = result.stdout
        
        if "daily_refresh.py" in existing_crontab:
            logger.info("✅ Cron job already exists")
            logger.info("Current crontab:")
            print(existing_crontab)
            
            response = input("\nReplace existing cron job? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                logger.info("❌ Cancelled by user")
                return False
            
            # Remove old daily_refresh lines
            lines = [line for line in existing_crontab.split('\n') 
                    if 'daily_refresh.py' not in line and line.strip()]
            new_crontab = '\n'.join(lines) + '\n'
        else:
            new_crontab = existing_crontab
        
    except subprocess.CalledProcessError:
        # No existing crontab
        new_crontab = ""
    
    # Add new cron job
    new_crontab += f"\n# SmartInvest daily data refresh (6 AM ET)\n"
    new_crontab += f"{cron_command}\n"
    
    # Install new crontab
    try:
        process = subprocess.Popen(
            ["crontab", "-"],
            stdin=subprocess.PIPE,
            text=True
        )
        process.communicate(input=new_crontab)
        
        if process.returncode == 0:
            logger.info("✅ Cron job created successfully!")
            logger.info("\nCron schedule:")
            logger.info(f"  • Daily at 6:00 AM ET")
            logger.info(f"  • Logs: {log_path}")
            return True
        else:
            logger.error("❌ Failed to create cron job")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error creating cron job: {e}")
        return False


def create_systemd_service():
    """
    Alternative: Create systemd service + timer (Linux).
    More robust than cron for production systems.
    """
    project_root = get_project_root()
    python_path = get_python_path()
    script_path = project_root / "scripts" / "daily_refresh.py"
    
    service_content = f"""[Unit]
Description=SmartInvest Daily Data Refresh
After=network.target

[Service]
Type=oneshot
User={os.getenv('USER', 'root')}
WorkingDirectory={project_root}
ExecStart={python_path} {script_path}
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
    
    timer_content = """[Unit]
Description=Run SmartInvest refresh daily at 6 AM
Requires=smartinvest-refresh.service

[Timer]
OnCalendar=*-*-* 06:00:00
Persistent=true

[Install]
WantedBy=timers.target
"""
    
    service_path = Path("/etc/systemd/system/smartinvest-refresh.service")
    timer_path = Path("/etc/systemd/system/smartinvest-refresh.timer")
    
    logger.info("\n" + "="*60)
    logger.info("SYSTEMD SERVICE SETUP (Alternative to cron)")
    logger.info("="*60)
    
    print("\nSystemd is more robust than cron for production.")
    print("To use systemd instead:")
    print(f"\n1. Create service file: {service_path}")
    print(f"   Content:")
    print(service_content)
    print(f"\n2. Create timer file: {timer_path}")
    print(f"   Content:")
    print(timer_content)
    print("\n3. Enable and start:")
    print("   sudo systemctl daemon-reload")
    print("   sudo systemctl enable smartinvest-refresh.timer")
    print("   sudo systemctl start smartinvest-refresh.timer")
    print("\n4. Check status:")
    print("   sudo systemctl status smartinvest-refresh.timer")
    print("   sudo systemctl list-timers")


def view_logs():
    """View recent refresh logs."""
    project_root = get_project_root()
    log_path = project_root / "logs" / "daily_refresh.log"
    
    if log_path.exists():
        logger.info(f"\n📄 Recent logs from {log_path}:")
        logger.info("="*60)
        
        with open(log_path, 'r') as f:
            lines = f.readlines()
            # Show last 50 lines
            for line in lines[-50:]:
                print(line.rstrip())
    else:
        logger.info(f"No logs found at {log_path}")


def main():
    """Main execution."""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║         AUTOMATIC DAILY REFRESH SETUP - SmartInvest        ║
    ╚════════════════════════════════════════════════════════════╝
    
    This script will set up automatic daily data refresh using:
    • CRON (macOS/Linux) - Runs daily_refresh.py at 6 AM ET
    • Task Scheduler (Windows) - Manual setup required
    • Systemd (Linux alternative) - More robust for production
    
    Schedule:
    • 6:00 AM ET - Data refresh starts
    • 6:15 AM ET - Refresh completes (est.)
    • 9:30 AM ET - Market opens with fresh data
    
    """)
    
    print("Options:")
    print("  1. Setup cron job (recommended for macOS/Linux)")
    print("  2. View systemd instructions (Linux production)")
    print("  3. View recent logs")
    print("  4. Exit")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == "1":
        create_cron_job()
    elif choice == "2":
        create_systemd_service()
    elif choice == "3":
        view_logs()
    else:
        logger.info("❌ Cancelled")


if __name__ == "__main__":
    main()

