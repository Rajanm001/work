"""
Validate project setup and configuration
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import os
from agents.config import config


def check_environment():
    """Check environment variables"""
    print("\n🔍 Checking Environment Configuration...")
    
    issues = []
    
    # Check database config
    if not config.db_password:
        issues.append("❌ DB_PASSWORD not set in .env")
    else:
        print("✅ Database password configured")
    
    # Check API keys
    if not config.openai_api_key and not config.anthropic_api_key:
        issues.append("⚠️  No API keys configured (optional for basic features)")
    else:
        print("✅ API key configured")
    
    return issues


def check_directories():
    """Check required directories exist"""
    print("\n🔍 Checking Project Structure...")
    
    required_dirs = [
        "database/data",
        "database/setup",
        "agents/supply_watchdog",
        "agents/scenario_strategist",
        "tools",
        "api",
        "web",
        "docs",
        "logs",
        "tests"
    ]
    
    issues = []
    project_root = Path(__file__).parent.parent
    
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists():
            print(f"✅ {dir_path}")
        else:
            issues.append(f"❌ Missing directory: {dir_path}")
    
    return issues


def check_files():
    """Check required files exist"""
    print("\n🔍 Checking Required Files...")
    
    required_files = [
        "README.md",
        "QUICKSTART.md",
        "requirements.txt",
        ".env",
        "agents/config.py",
        "tools/sql_tools.py",
        "api/main.py",
        "web/index.html",
        "agents/supply_watchdog/run_monitoring_simple.py",
        "agents/scenario_strategist/chat_interface_simple.py"
    ]
    
    issues = []
    project_root = Path(__file__).parent.parent
    
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            issues.append(f"❌ Missing file: {file_path}")
    
    return issues


def check_data_files():
    """Check CSV data files"""
    print("\n🔍 Checking Data Files...")
    
    data_dir = Path(__file__).parent.parent / "database" / "data"
    
    if not data_dir.exists():
        return [f"❌ Data directory not found: {data_dir}"]
    
    csv_files = list(data_dir.glob("*.csv"))
    
    if len(csv_files) == 0:
        return ["❌ No CSV files found in database/data/"]
    
    print(f"✅ Found {len(csv_files)} CSV files")
    return []


def main():
    """Run all validation checks"""
    
    print("\n" + "="*60)
    print("🔬 Clinical Supply Chain AI - Project Validation")
    print("="*60)
    
    all_issues = []
    
    # Run all checks
    all_issues.extend(check_environment())
    all_issues.extend(check_directories())
    all_issues.extend(check_files())
    all_issues.extend(check_data_files())
    
    # Summary
    print("\n" + "="*60)
    print("📊 Validation Summary")
    print("="*60)
    
    if len(all_issues) == 0:
        print("\n✅ All validation checks passed!")
        print("\n🎉 Project is ready for deployment!")
        return True
    else:
        print(f"\n⚠️  Found {len(all_issues)} issues:\n")
        for issue in all_issues:
            print(f"  {issue}")
        print("\n❌ Please resolve issues before deployment.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
