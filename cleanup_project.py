"""
Project cleanup script for SmartInvest bot.
Removes obsolete files and organizes documentation.
"""

import os
import shutil
from pathlib import Path

# Get project root
PROJECT_ROOT = Path(__file__).parent

def create_directories():
    """Create necessary directories."""
    dirs_to_create = [
        PROJECT_ROOT / "archive" / "old_scripts",
        PROJECT_ROOT / "archive" / "old_docs",
        PROJECT_ROOT / "archive" / "tests",
        PROJECT_ROOT / "logs",
    ]
    
    for dir_path in dirs_to_create:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {dir_path.relative_to(PROJECT_ROOT)}/")


def move_to_archive(file_path, archive_subdir="old_scripts"):
    """Move file to archive."""
    if not file_path.exists():
        print(f"⚠️  Not found: {file_path.name}")
        return
    
    archive_path = PROJECT_ROOT / "archive" / archive_subdir / file_path.name
    shutil.move(str(file_path), str(archive_path))
    print(f"📦 Archived: {file_path.name} → archive/{archive_subdir}/")


def delete_file(file_path):
    """Delete a file."""
    if not file_path.exists():
        print(f"⚠️  Not found: {file_path.name}")
        return
    
    file_path.unlink()
    print(f"🗑️  Deleted: {file_path.name}")


def reorganize_docs():
    """Reorganize documentation."""
    # Keep these docs in root
    keep_in_root = [
        'README.md',
        'CLEANUP_PLAN.md',
    ]
    
    # Move these to docs/
    move_to_docs = [
        'TECHNICAL_DOCUMENTATION.md',
        'AUTOMATION_GUIDE.md',
        'EXPANSION_PLAN.md',
        'PHASE_1_2_COMPLETE.md',
        'QUICK_START_AUTOMATION.md',
        'TRADING_BOT_INTEGRATION.md',
    ]
    
    # Ensure docs/ directory exists
    docs_dir = PROJECT_ROOT / "docs"
    docs_dir.mkdir(exist_ok=True)
    
    # Move docs
    for doc in move_to_docs:
        src = PROJECT_ROOT / doc
        if src.exists():
            dst = docs_dir / doc
            shutil.move(str(src), str(dst))
            print(f"📚 Moved: {doc} → docs/")


def main():
    """Execute cleanup."""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║         PROJECT CLEANUP - SmartInvest Bot                  ║
    ╚════════════════════════════════════════════════════════════╝
    
    This script will:
    1. Create archive/ and logs/ directories
    2. Move old files to archive/
    3. Delete obsolete files
    4. Reorganize documentation
    
    ⚠️  SAFETY: Nothing critical will be deleted!
    Database and venv are never touched.
    
    """)
    
    response = input("Proceed with cleanup? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Cleanup cancelled")
        return
    
    print("\n" + "="*60)
    print("STEP 1: Creating directories")
    print("="*60)
    create_directories()
    
    print("\n" + "="*60)
    print("STEP 2: Archiving test files")
    print("="*60)
    
    # Move tests to archive
    tests_dir = PROJECT_ROOT / "tests"
    if tests_dir.exists():
        archive_tests = PROJECT_ROOT / "archive" / "tests"
        for item in tests_dir.iterdir():
            if item.name != '__pycache__':
                shutil.move(str(item), str(archive_tests / item.name))
        print(f"📦 Archived: tests/ → archive/tests/")
    
    print("\n" + "="*60)
    print("STEP 3: Archiving old scripts")
    print("="*60)
    
    # Archive old root-level loaders
    old_loaders = [
        'load_incremental.py',
        'load_real_stocks.py',
        'load_sp100.py',
        'load_test_data.py',
    ]
    for loader in old_loaders:
        move_to_archive(PROJECT_ROOT / loader, "old_scripts")
    
    # Archive old test/demo files
    old_files = [
        'test_alphavantage.py',
        'verify_setup.py',
        'run_tests.py',
        'demo_pipeline.py',
    ]
    for file in old_files:
        move_to_archive(PROJECT_ROOT / file, "old_scripts")
    
    # Archive obsolete scripts in scripts/
    scripts_dir = PROJECT_ROOT / "scripts"
    old_scripts = [
        'load_sp500.py',  # Use load_full_sp500.py instead
        'train_model.py',  # Use train_model_v2.py instead
        'load_full_data.py',  # Redundant
        'test_pipeline.py',  # Obsolete
        'test_automation.py',  # Obsolete test
    ]
    for script in old_scripts:
        script_path = scripts_dir / script
        if script_path.exists():
            move_to_archive(script_path, "old_scripts")
    
    print("\n" + "="*60)
    print("STEP 4: Deleting obsolete documentation")
    print("="*60)
    
    # Delete redundant docs
    obsolete_docs = [
        'ANSWER_REAL_DATA.md',
        'REAL_TIME_DATA_SOLUTION.md',
        'LOAD_DATA_NOW.md',
        'SETUP_CHECKLIST.md',
        'START_BOT.md',
        'START_HERE.md',
    ]
    for doc in obsolete_docs:
        delete_file(PROJECT_ROOT / doc)
    
    # Delete old docs/ folder
    docs_dir = PROJECT_ROOT / "docs"
    if docs_dir.exists():
        archive_docs = PROJECT_ROOT / "archive" / "old_docs"
        for item in docs_dir.iterdir():
            if item.is_file():
                shutil.move(str(item), str(archive_docs / item.name))
        docs_dir.rmdir()
        print(f"📦 Archived: docs/ → archive/old_docs/")
    
    print("\n" + "="*60)
    print("STEP 5: Reorganizing documentation")
    print("="*60)
    
    reorganize_docs()
    
    print("\n" + "="*60)
    print("CLEANUP COMPLETE!")
    print("="*60)
    
    print("""
    ✅ Cleanup successful!
    
    What was done:
    ✅ Created archive/ and logs/ directories
    ✅ Moved old files to archive/ (safe keeping)
    ✅ Deleted obsolete documentation
    ✅ Reorganized remaining docs to docs/
    
    Your project is now clean and organized!
    
    Check CLEANUP_PLAN.md for details.
    
    Next steps:
    1. Load all 500 stocks: python scripts/load_full_sp500.py
    2. Setup automation: python scripts/setup_cron.py
    3. Start your bot: python bot_with_real_data.py
    
    """)


if __name__ == "__main__":
    main()

