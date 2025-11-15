#!/usr/bin/env python3
"""
Debug script for SoundCloud integration
Run this to identify any issues with the setup
"""
import sys
import os
from pathlib import Path

def check_file_exists():
    """Check if soundcloud.py exists in the correct location"""
    print("=" * 70)
    print("1. Checking if soundcloud.py exists...")
    print("=" * 70)
    
    expected_path = Path("src/handlers/platforms/soundcloud.py")
    
    if expected_path.exists():
        print(f"✅ Found: {expected_path}")
        print(f"   Size: {expected_path.stat().st_size} bytes")
        return True
    else:
        print(f"❌ NOT FOUND: {expected_path}")
        print("\n💡 Solution:")
        print(f"   Copy soundcloud.py to: {expected_path.absolute()}")
        return False


def check_imports():
    """Try to import the soundcloud handlers"""
    print("\n" + "=" * 70)
    print("2. Testing imports...")
    print("=" * 70)
    
    try:
        print("Attempting: from src.handlers.platforms import soundcloud")
        from src.handlers.platforms import soundcloud
        print("✅ Module imported successfully")
        
        # Check for required functions
        required_functions = ['connect_handler', 'callback_handler', 'refresh_handler']
        missing = []
        
        for func_name in required_functions:
            if hasattr(soundcloud, func_name):
                print(f"✅ Found: soundcloud.{func_name}")
            else:
                print(f"❌ Missing: soundcloud.{func_name}")
                missing.append(func_name)
        
        if missing:
            print(f"\n⚠️  Missing functions: {', '.join(missing)}")
            return False
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {str(e)}")
        print("\n💡 Possible causes:")
        print("   1. soundcloud.py not in src/handlers/platforms/")
        print("   2. Syntax error in soundcloud.py")
        print("   3. Missing dependencies")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False


def check_init_file():
    """Check if __init__.py has soundcloud imports"""
    print("\n" + "=" * 70)
    print("3. Checking __init__.py...")
    print("=" * 70)
    
    init_path = Path("src/handlers/platforms/__init__.py")
    
    if not init_path.exists():
        print(f"❌ NOT FOUND: {init_path}")
        return False
    
    print(f"✅ Found: {init_path}")
    
    content = init_path.read_text()
    
    required_lines = [
        "from src.handlers.platforms.soundcloud import connect_handler as soundcloud_connect_handler",
        "from src.handlers.platforms.soundcloud import callback_handler as soundcloud_callback_handler",
        "from src.handlers.platforms.soundcloud import refresh_handler as soundcloud_refresh_handler"
    ]
    
    all_found = True
    for line in required_lines:
        if line in content:
            print(f"✅ Found import: {line.split('import')[1].strip()}")
        else:
            print(f"❌ Missing import: {line.split('import')[1].strip()}")
            all_found = False
    
    # Check __all__
    if "'soundcloud_connect_handler'" in content:
        print("✅ Found in __all__: soundcloud_connect_handler")
    else:
        print("❌ Missing from __all__: soundcloud_connect_handler")
        all_found = False
    
    return all_found


def check_env_variables():
    """Check if required environment variables are set"""
    print("\n" + "=" * 70)
    print("4. Checking environment variables...")
    print("=" * 70)
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = {
        'SOUNDCLOUD_CLIENT_ID': os.getenv('SOUNDCLOUD_CLIENT_ID'),
        'SOUNDCLOUD_CLIENT_SECRET': os.getenv('SOUNDCLOUD_CLIENT_SECRET'),
        'SOUNDCLOUD_REDIRECT_URI': os.getenv('SOUNDCLOUD_REDIRECT_URI'),
        'FRONTEND_URL': os.getenv('FRONTEND_URL')
    }
    
    all_set = True
    for var_name, var_value in required_vars.items():
        if var_value:
            display_value = f"{var_value[:15]}..." if len(var_value) > 15 else var_value
            if 'SECRET' in var_name:
                display_value = "***" + var_value[-4:] if len(var_value) > 4 else "***"
            print(f"✅ {var_name}: {display_value}")
        else:
            print(f"❌ {var_name}: NOT SET")
            all_set = False
    
    return all_set


def check_main_routes():
    """Check if main.py has soundcloud routes"""
    print("\n" + "=" * 70)
    print("5. Checking main.py routes...")
    print("=" * 70)
    
    main_path = Path("main.py")
    
    if not main_path.exists():
        print(f"❌ NOT FOUND: {main_path}")
        return False
    
    content = main_path.read_text()
    
    required_imports = [
        "soundcloud_connect_handler",
        "soundcloud_callback_handler",
        "soundcloud_refresh_handler"
    ]
    
    required_routes = [
        "@app.post(\"/platforms/soundcloud/connect\")",
        "@app.get(\"/platforms/soundcloud/callback\")",
        "@app.post(\"/platforms/soundcloud/refresh\")"
    ]
    
    import_found = all(imp in content for imp in required_imports)
    routes_found = all(route in content for route in required_routes)
    
    if import_found:
        print("✅ SoundCloud handlers imported in main.py")
    else:
        print("❌ SoundCloud handlers NOT imported in main.py")
        print("   Add to imports: soundcloud_connect_handler, soundcloud_callback_handler, soundcloud_refresh_handler")
    
    if routes_found:
        print("✅ All SoundCloud routes defined in main.py")
    else:
        print("❌ Some SoundCloud routes missing in main.py")
        for route in required_routes:
            if route in content:
                print(f"   ✅ {route}")
            else:
                print(f"   ❌ {route}")
    
    return import_found and routes_found


def test_handler_call():
    """Try to call a handler function"""
    print("\n" + "=" * 70)
    print("6. Testing handler execution...")
    print("=" * 70)
    
    try:
        from src.handlers.platforms import soundcloud_connect_handler
        
        # Create mock event
        mock_event = {
            'httpMethod': 'POST',
            'path': '/platforms/soundcloud/connect',
            'headers': {
                'Authorization': 'Bearer test_token_12345'
            },
            'queryStringParameters': {},
            'body': '{}'
        }
        
        # Mock context
        class MockContext:
            function_name = "test"
            aws_request_id = "test-123"
        
        print("Calling soundcloud_connect_handler with mock data...")
        result = soundcloud_connect_handler(mock_event, MockContext())
        
        print(f"✅ Handler executed successfully")
        print(f"   Status Code: {result.get('statusCode')}")
        
        if result.get('statusCode') == 401:
            print("   ⚠️  Got 401 (expected - invalid token)")
            print("   This is normal - handler is working!")
            return True
        
        return True
        
    except Exception as e:
        print(f"❌ Handler execution failed: {str(e)}")
        print(f"\n💡 Error details:")
        import traceback
        print(traceback.format_exc())
        return False


def main():
    """Run all checks"""
    print("\n🔍 SoundCloud Integration Debug Script")
    print("=" * 70)
    print()
    
    checks = [
        ("File exists", check_file_exists),
        ("Imports work", check_imports),
        ("__init__.py correct", check_init_file),
        ("Environment variables", check_env_variables),
        ("main.py routes", check_main_routes),
        ("Handler execution", test_handler_call)
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"\n❌ Check failed with error: {str(e)}")
            results.append((check_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {check_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nPassed: {passed}/{total} checks")
    
    if passed == total:
        print("\n🎉 All checks passed! SoundCloud integration should be working.")
        print("\n💡 If you're still having issues, check:")
        print("   1. Backend server is running (python main.py)")
        print("   2. DynamoDB Local is running")
        print("   3. Frontend is making requests to correct URL")
    else:
        print("\n⚠️  Some checks failed. Review the output above to fix issues.")
        print("\n📋 Common fixes:")
        print("   1. Copy soundcloud.py to src/handlers/platforms/")
        print("   2. Update __init__.py with soundcloud imports")
        print("   3. Add SOUNDCLOUD_* variables to .env")
        print("   4. Update main.py with soundcloud routes")
        print("   5. Restart the backend server")


if __name__ == "__main__":
    main()
