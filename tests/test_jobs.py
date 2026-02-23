"""Tests for job dispatch system."""
import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add jobs directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "jobs"))

import jobs
from jobs import create_job, get_job, assign_job, complete_job, load_db, save_db

class TestJobSystem:
    """Test suite for job management."""
    
    def setup_method(self):
        """Setup test environment."""
        # Create temp directory for test DB
        self.temp_dir = tempfile.mkdtemp()
        self.original_db = jobs.JOBS_DB
        jobs.JOBS_DB = Path(self.temp_dir) / "test-jobs-db.json"
        
        # Initialize empty DB
        save_db({"version": "1.0", "jobs": [], "lastJobId": 0})
    
    def teardown_method(self):
        """Cleanup test environment."""
        shutil.rmtree(self.temp_dir)
        jobs.JOBS_DB = self.original_db
    
    def test_create_main_job(self):
        """Test creating a main job."""
        job_id = create_job("Test main job", assigned_to="Mac")
        
        db = load_db()
        job = get_job(db, job_id)
        
        assert job is not None
        assert job["description"] == "Test main job"
        assert job["assigned_to"] == "Mac"
        assert job["status"] == "TODO"
        assert job["parent_id"] is None
        assert job["estimated_minutes"] is not None
        print("✅ test_create_main_job passed")
    
    def test_create_sub_job(self):
        """Test creating a sub-job."""
        main_id = create_job("Main job", assigned_to="Mac")
        sub_id = create_job("Sub job", parent_id=main_id, assigned_to="Sage")
        
        db = load_db()
        main = get_job(db, main_id)
        sub = get_job(db, sub_id)
        
        assert sub["parent_id"] == main_id, f"Expected parent_id {main_id}, got {sub['parent_id']}"
        assert sub_id in main["sub_jobs"], f"Expected sub_id {sub_id} in sub_jobs {main['sub_jobs']}"
        assert "/" in sub.get("display_id", ""), f"Expected '/' in display_id, got {sub.get('display_id')}"
        print("✅ test_create_sub_job passed")
    
    def test_assign_job(self):
        """Test assigning job to agent."""
        job_id = create_job("Test job", assigned_to="Mac")
        assign_job(job_id, "Glitch")
        
        db = load_db()
        job = get_job(db, job_id)
        
        assert job["assigned_to"] == "Glitch"
        print("✅ test_assign_job passed")
    
    def test_complete_job(self):
        """Test completing a job."""
        job_id = create_job("Test job", assigned_to="Glitch")
        complete_job(job_id, "Completed successfully")
        
        db = load_db()
        job = get_job(db, job_id)
        
        assert job["status"] == "DONE"
        assert job["completed_at"] is not None
        assert "Completed successfully" in job["notes"]
        print("✅ test_complete_job passed")
    
    def test_time_estimation(self):
        """Test time estimation based on complexity."""
        simple = create_job("Simple task", assigned_to="Sage")
        complex_job = create_job("Research microservices architecture security", assigned_to="Sage")
        
        db = load_db()
        simple_job = get_job(db, simple)
        complex_job_obj = get_job(db, complex_job)
        
        # Complex job should have higher estimate
        assert complex_job_obj["estimated_minutes"] >= simple_job["estimated_minutes"]
        print("✅ test_time_estimation passed")
    
    def test_job_hierarchy(self):
        """Test job hierarchy with multiple sub-jobs."""
        main_id = create_job("Main task", assigned_to="Mac")
        
        sub1 = create_job("Research", parent_id=main_id, assigned_to="Sage")
        sub2 = create_job("Design", parent_id=main_id, assigned_to="Atlas")
        sub3 = create_job("Code", parent_id=main_id, assigned_to="Glitch")
        
        db = load_db()
        main = get_job(db, main_id)
        
        assert len(main["sub_jobs"]) == 3
        assert main["status"] == "IN_PROGRESS"
        
        # Check display IDs
        for sub_id in [sub1, sub2, sub3]:
            sub = get_job(db, sub_id)
            assert sub["display_id"].startswith(f"{main_id}/")
        
        print("✅ test_job_hierarchy passed")


def run_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("Running Job Dispatch System Tests")
    print("="*60 + "\n")
    
    test = TestJobSystem()
    
    tests = [
        test.test_create_main_job,
        test.test_create_sub_job,
        test.test_assign_job,
        test.test_complete_job,
        test.test_time_estimation,
        test.test_job_hierarchy,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        test.setup_method()
        try:
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
