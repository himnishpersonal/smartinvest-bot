#!/usr/bin/env python3
"""
Run test suite for SmartInvest Bot
"""
import pytest
import sys


def run_tests():
    """Run all tests"""
    print("Running SmartInvest Bot test suite...\n")
    
    # Run pytest with verbose output
    args = [
        'tests/',
        '-v',  # Verbose
        '--tb=short',  # Short traceback format
        '--color=yes',  # Colored output
        '-x',  # Stop on first failure
    ]
    
    exit_code = pytest.main(args)
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(run_tests())
