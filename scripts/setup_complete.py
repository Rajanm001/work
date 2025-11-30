"""
Setup script for quick project initialization
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and print status"""
    print(f"\n{'='*60}")
    print(f"⚙️  {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ {description} - FAILED")
            if result.stderr:
                print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run complete setup"""
    
    print("\n" + "="*60)
    print("🚀 Clinical Supply Chain AI - Complete Setup")
    print("="*60 + "\n")
    
    steps = [
        ("python database\\setup\\create_database.py", "Creating database"),
        ("python database\\setup\\create_tables_actual.py", "Creating tables"),
        ("python database\\setup\\load_actual_data.py", "Loading CSV data"),
    ]
    
    success_count = 0
    
    for cmd, desc in steps:
        if run_command(cmd, desc):
            success_count += 1
    
    print("\n" + "="*60)
    print(f"📊 Setup Complete: {success_count}/{len(steps)} steps successful")
    print("="*60)
    
    if success_count == len(steps):
        print("\n✅ All setup steps completed successfully!")
        print("\n📌 Next Steps:")
        print("  1. Start API server: python api\\main.py")
        print("  2. Open dashboard: http://localhost:8000/dashboard")
        print("  3. Run monitoring: python agents\\supply_watchdog\\run_monitoring_simple.py")
        print("  4. Test chat: python agents\\scenario_strategist\\chat_interface_simple.py")
    else:
        print("\n⚠️  Some steps failed. Please check errors above.")
    
    return success_count == len(steps)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
