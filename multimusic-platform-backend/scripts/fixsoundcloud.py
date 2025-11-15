#!/usr/bin/env python3
"""
Comprehensive fix for SoundCloud import issues
This script will identify and help fix the problem
"""
import sys
import os
from pathlib import Path

def check_working_directory():
    """Ensure we're in the right directory"""
    print("=" * 70)
    print("1. Checking working directory...")
    print("=" * 70)
    cwd = Path.cwd()
    print(f"Current directory: {cwd}")
    
    # Check if we're in the backend directory
    if not (cwd / "main.py").exists():
        print("❌ Not in backend directory!")
        print("\n💡 Solution:")
        print("   cd ~/Projects/mmp_be/multimusic-platform-backend")
        return False
    
    print("✅ In correct directory")
    return True


def check_file_exists():
    """Check if soundcloud.py exists"""
    print("\n" + "=" * 70)
    print("2. Checking if soundcloud.py exists...")
    print("=" * 70)
    
    path = Path("src/handlers/platforms/soundcloud.py")
    if not path.exists():
        print(f"❌ NOT FOUND: {path}")
        print("\n💡 Solution:")
        print(f"   cp soundcloud.py src/handlers/platforms/")
        return False
    
    print(f"✅ Found: {path}")
    print(f"   Size: {path.stat().st_size} bytes")
    return True


def check_dependencies():
    """Check if all dependencies are installed"""
    print("\n" + "=" * 70)
    print("3. Checking dependencies...")
    print("=" * 70)
    
    deps = {
        'httpx': 'httpx',
        'aws_lambda_powertools': 'aws-lambda-powertools',
        'cryptography': 'cryptography',
        'boto3': 'boto3',
    }
    
    missing = []
    for module, package in deps.items():
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} (install: pip install {package})")
            missing.append(package)
    
    if missing:
        print(f"\n💡 Solution:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    return True


def test_import_step_by_step():
    """Test imports step by step to find the issue"""
    print("\n" + "=" * 70)
    print("4. Testing imports step by step...")
    print("=" * 70)
    
    steps = [
        ("Standard library", "import json, os, secrets"),
        ("httpx", "import httpx"),
        ("aws-lambda-powertools", "from aws_lambda_powertools import Logger"),
        ("Base handler", "from src.handlers.platforms.base import BasePlatformHandler"),
        ("Response utils", "from src.utils.responses import success_response"),
        ("SoundCloud module", "from src.handlers.platforms import soundcloud"),
    ]
    
    for step_name, import_cmd in steps:
        try:
            exec(import_cmd)
            print(f"✅ {step_name}")
        except Exception as e:
            print(f"❌ {step_name}")
            print(f"   Error: {e}")
            print(f"\n   Import command: {import_cmd}")
            
            # Provide specific help
            if "soundcloud" in import_cmd:
                print("\n💡 This is the issue! Checking soundcloud.py...")
                check_soundcloud_file_content()
            
            return False
    
    return True


def check_soundcloud_file_content():
    """Check the actual content of soundcloud.py"""
    path = Path("src/handlers/platforms/soundcloud.py")
    if not path.exists():
        print("   File doesn't exist!")
        return
    
    content = path.read_text()
    
    # Check for common issues
    issues = []
    
    if "connect_handler" not in content:
        issues.append("Missing connect_handler function")
    
    if "callback_handler" not in content:
        issues.append("Missing callback_handler function")
    
    if "refresh_handler" not in content:
        issues.append("Missing refresh_handler function")
    
    if "@logger.inject_lambda_context" not in content:
        issues.append("Missing @logger.inject_lambda_context decorators")
    
    if "BasePlatformHandler" not in content:
        issues.append("Not using BasePlatformHandler")
    
    if issues:
        print("\n   Issues found in soundcloud.py:")
        for issue in issues:
            print(f"   - {issue}")
        print("\n   💡 Solution: Use the corrected soundcloud.py file provided")
    else:
        print("   File structure looks correct")
        print("   Trying to compile...")
        try:
            import py_compile
            py_compile.compile(str(path), doraise=True)
            print("   ✅ No syntax errors")
        except SyntaxError as e:
            print(f"   ❌ Syntax error on line {e.lineno}: {e.msg}")


def test_direct_import():
    """Try to import soundcloud directly and show the error"""
    print("\n" + "=" * 70)
    print("5. Direct import test...")
    print("=" * 70)
    
    try:
        from src.handlers.platforms import soundcloud
        print("✅ Import successful!")
        
        # Check handlers
        if hasattr(soundcloud, 'connect_handler'):
            print("✅ connect_handler found")
        else:
            print("❌ connect_handler NOT FOUND")
            
        if hasattr(soundcloud, 'callback_handler'):
            print("✅ callback_handler found")
        else:
            print("❌ callback_handler NOT FOUND")
            
        if hasattr(soundcloud, 'refresh_handler'):
            print("✅ refresh_handler found")
        else:
            print("❌ refresh_handler NOT FOUND")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed!")
        print(f"\nError type: {type(e).__name__}")
        print(f"Error message: {e}")
        
        import traceback
        print("\nFull traceback:")
        print("-" * 70)
        traceback.print_exc()
        print("-" * 70)
        
        # Provide specific help based on error
        error_str = str(e).lower()
        
        if "no module named" in error_str:
            print("\n💡 Missing module or file not found")
            print("   Check that soundcloud.py is in src/handlers/platforms/")
        
        elif "cannot import" in error_str:
            if "baseplatformhandler" in error_str:
                print("\n💡 Issue with BasePlatformHandler")
                print("   Check that src/handlers/platforms/base.py exists")
            else:
                print("\n💡 Import error in dependencies")
                print("   One of the imported modules has an issue")
        
        elif "circular import" in error_str:
            print("\n💡 Circular import detected")
            print("   Check imports in soundcloud.py")
        
        return False


def main():
    """Run all checks"""
    print("\n🔍 SoundCloud Import Diagnostic Tool")
    print("=" * 70)
    print()
    
    checks = [
        check_working_directory,
        check_file_exists,
        check_dependencies,
        test_import_step_by_step,
        test_direct_import,
    ]
    
    for check in checks:
        if not check():
            print("\n" + "=" * 70)
            print("❌ Found the issue! Fix it and run this script again.")
            print("=" * 70)
            sys.exit(1)
    
    print("\n" + "=" * 70)
    print("🎉 All checks passed!")
    print("=" * 70)
    print("\nYour SoundCloud integration should be working now.")
    print("Try starting your backend:")
    print("  python main.py")


if __name__ == "__main__":
    main()