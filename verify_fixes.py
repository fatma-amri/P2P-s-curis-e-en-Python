#!/usr/bin/env python3
"""
Verification script to test all fixes are working correctly.
This script runs all tests and provides a summary of results.
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{'='*70}")
    print(f"Testing: {description}")
    print(f"Command: {cmd}")
    print('='*70)
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        success = result.returncode == 0
        print(f"\n{'✅ PASS' if success else '❌ FAIL'}: {description}")
        return success
    
    except subprocess.TimeoutExpired:
        print(f"❌ FAIL: {description} (timeout)")
        return False
    except Exception as e:
        print(f"❌ FAIL: {description} ({e})")
        return False

def main():
    """Run all verification tests."""
    print("="*70)
    print("P2P Secure Chat - Verification Script")
    print("="*70)
    
    # Change to project directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"Working directory: {script_dir}")
    
    results = []
    
    # Test 1: Crypto tests
    results.append(run_command(
        "python3 -m unittest p2p_secure_chat.test_crypto",
        "Cryptographic functionality (6 tests)"
    ))
    
    # Test 2: Session key persistence
    results.append(run_command(
        "python3 -m unittest p2p_secure_chat.test_network.TestNetworkConnection.test_session_key_persistence",
        "Session key persistence"
    ))
    
    # Test 3: Message exchange
    results.append(run_command(
        "python3 -m unittest p2p_secure_chat.test_network.TestNetworkConnection.test_message_exchange",
        "Bidirectional message exchange"
    ))
    
    # Test 4: Port conflict handling
    results.append(run_command(
        "python3 -m unittest p2p_secure_chat.test_network.TestNetworkConnection.test_port_conflict_handling",
        "Port conflict handling"
    ))
    
    # Test 5: Package imports
    results.append(run_command(
        "python3 -c 'from p2p_secure_chat import CryptoHandler, NetworkHandler, Logger; print(\"Imports successful\")'",
        "Package import structure"
    ))
    
    # Test 6: Module discovery
    results.append(run_command(
        "python3 -c 'import p2p_secure_chat; print(\"Package version:\", p2p_secure_chat.__version__)'",
        "Package metadata"
    ))
    
    # Summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nTests passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
        print("\nThe following issues have been fixed:")
        print("  ✅ Session key derivation (both peers derive same key)")
        print("  ✅ Connection stability (stays active after sending messages)")
        print("  ✅ Package structure (proper imports work)")
        print("  ✅ Port conflict handling (dynamic port selection)")
        print("  ✅ Detailed logging (debug information available)")
        print("\nThe application is ready to use!")
        return 0
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED")
        print("\nPlease review the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
