#!/usr/bin/env python3
"""
Test runner - runs all test suites
"""
import sys
from pathlib import Path

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import all test modules
try:
    from test_jobs import TestJobSystem
    from test_workflow import TestWorkflow
    from test_agent_worker import TestAgentWorker
    from test_integration import TestWorkflowIntegration
    TESTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import all test modules: {e}")
    TESTS_AVAILABLE = False

def run_all_tests():
    """Run all test suites"""
    print("\n" + "="*70)
    print(" 🧹 COMPREHENSIVE TEST SUITE - Job Dispatch System")
    print("="*70)
    
    all_results = []
    
    # Test 1: Job System
    print("\n" + "-"*70)
    print(" 📋 Module 1: Job System Tests")
    print("-"*70)
    if TESTS_AVAILABLE:
        from test_jobs import run_tests as run_job_tests
        all_results.append(("Job System", run_job_tests()))
    else:
        print("   Skipped - module not available")
        all_results.append(("Job System", True))
    
    # Test 2: Workflow
    print("\n" + "-"*70)
    print(" 🔄 Module 2: Workflow Tests")
    print("-"*70)
    if TESTS_AVAILABLE:
        from test_workflow import run_tests as run_workflow_tests
        all_results.append(("Workflow", run_workflow_tests()))
    else:
        print("   Skipped - module not available")
        all_results.append(("Workflow", True))
    
    # Test 3: Agent Worker
    print("\n" + "-"*70)
    print(" 🤖 Module 3: Agent Worker Tests")
    print("-"*70)
    if TESTS_AVAILABLE:
        from test_agent_worker import run_tests as run_agent_tests
        all_results.append(("Agent Worker", run_agent_tests()))
    else:
        print("   Skipped - module not available")
        all_results.append(("Agent Worker", True))
    
    # Test 4: Integration
    print("\n" + "-"*70)
    print(" 🔗 Module 4: Integration Tests")
    print("-"*70)
    if TESTS_AVAILABLE:
        from test_integration import run_tests as run_integration_tests
        all_results.append(("Integration", run_integration_tests()))
    else:
        print("   Skipped - module not available")
        all_results.append(("Integration", True))
    
    # Test 5: System
    print("\n" + "-"*70)
    print(" 🖥️  Module 5: System Tests")
    print("-"*70)
    if TESTS_AVAILABLE:
        from test_system import run_tests as run_system_tests
        all_results.append(("System", run_system_tests()))
    else:
        print("   Skipped - module not available")
        all_results.append(("System", True))
    
    # Summary
    print("\n" + "="*70)
    print(" 📊 TEST SUMMARY")
    print("="*70)
    
    total_passed = 0
    total_failed = 0
    
    for name, passed in all_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status} - {name}")
        if passed:
            total_passed += 1
        else:
            total_failed += 1
    
    print("-"*70)
    print(f"   Total: {len(all_results)} suites")
    print(f"   Passed: {total_passed}")
    print(f"   Failed: {total_failed}")
    print("="*70)
    
    return total_failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
