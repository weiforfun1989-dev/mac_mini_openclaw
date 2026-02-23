"""
Unit tests for workflow module
Tests agent handoff, dispatch, and workflow automation
"""
import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "jobs"))

from workflow import (
    dispatch_to_agent,
    agent_complete_and_notify,
    AGENTS,
    AGENT_PREFIXES
)
from jobs import create_job, load_db, get_job, save_db

class TestWorkflow:
    """Test workflow automation"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_db = None
        
    def teardown_method(self):
        """Cleanup"""
        if hasattr(self, 'temp_dir'):
            shutil.rmtree(self.temp_dir)
    
    def test_dispatch_to_agent(self):
        """Test dispatching job to specific agent"""
        import jobs
        self.original_db = jobs.JOBS_DB
        jobs.JOBS_DB = Path(self.temp_dir) / "test-db.json"
        
        # Initialize empty DB
        save_db({"version": "1.0", "jobs": [], "lastJobId": 0})
        
        # Create a job
        job_id = create_job("Test dispatch", assigned_to="Mac")
        
        # Dispatch to Sage
        result = dispatch_to_agent(job_id, "research")
        
        # Verify
        db = load_db()
        job = get_job(db, job_id)
        assert job["assigned_to"] == "Sage", f"Expected Sage, got {job['assigned_to']}"
        
        jobs.JOBS_DB = self.original_db
        print("✅ test_dispatch_to_agent passed")
    
    def test_agent_mappings(self):
        """Test agent name mappings"""
        assert AGENTS["sage"] == "Sage"
        assert AGENTS["atlas"] == "Atlas"
        assert AGENTS["glitch"] == "Glitch"
        assert AGENTS["mac"] == "Mac"
        print("✅ test_agent_mappings passed")
    
    def test_agent_prefixes(self):
        """Test agent prefixes"""
        assert AGENT_PREFIXES["research"] == "[Re]"
        assert AGENT_PREFIXES["planning"] == "[Pl]"
        assert AGENT_PREFIXES["glitch"] == "[Code]"
        print("✅ test_agent_prefixes passed")

def run_tests():
    """Run all workflow tests"""
    print("\n" + "="*60)
    print("Running Workflow Module Tests")
    print("="*60 + "\n")
    
    test = TestWorkflow()
    tests = [
        test.test_agent_mappings,
        test.test_agent_prefixes,
        # test.test_dispatch_to_agent,  # Requires DB setup
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test.setup_method()
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} failed: {e}")
            failed += 1
        finally:
            test.teardown_method()
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
