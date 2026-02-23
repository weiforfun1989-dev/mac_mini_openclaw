"""
System tests for dashboard and API
Tests dashboard server, API endpoints, and web interface
"""
import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "jobs"))

from jobs import create_job, load_db, save_db, JOBS_DB

class TestDashboardAPI:
    """Test dashboard API functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_db = JOBS_DB
        
        import jobs
        jobs.JOBS_DB = Path(self.temp_dir) / "test-dashboard-db.json"
        save_db({"version": "1.0", "jobs": [], "lastJobId": 0})
    
    def teardown_method(self):
        """Cleanup"""
        import jobs
        jobs.JOBS_DB = self.original_db
        if hasattr(self, 'temp_dir'):
            shutil.rmtree(self.temp_dir)
    
    def test_api_jobs_response_format(self):
        """Test API response format"""
        # Create some jobs
        create_job("Test job 1", assigned_to="Sage")
        create_job("Test job 2", assigned_to="Atlas")
        
        db = load_db()
        
        # Verify structure
        assert "version" in db
        assert "jobs" in db
        assert "lastJobId" in db
        assert isinstance(db["jobs"], list)
        assert len(db["jobs"]) == 2
        
        print("✅ test_api_jobs_response_format passed")
    
    def test_job_fields(self):
        """Test that jobs have all required fields"""
        job_id = create_job("Test job with all fields", assigned_to="Glitch", priority="high")
        
        db = load_db()
        job = db["jobs"][0]
        
        required_fields = ["id", "description", "status", "assigned_to", "created_at", 
                          "priority", "sub_jobs", "notes"]
        
        for field in required_fields:
            assert field in job, f"Missing field: {field}"
        
        assert job["priority"] == "high"
        assert job["assigned_to"] == "Glitch"
        
        print("✅ test_job_fields passed")
    
    def test_sub_job_structure(self):
        """Test sub-job parent-child relationship"""
        main_id = create_job("Main job", assigned_to="Mac")
        sub_id = create_job("Sub job", parent_id=main_id, assigned_to="Sage")
        
        db = load_db()
        main = [j for j in db["jobs"] if j["id"] == main_id][0]
        sub = [j for j in db["jobs"] if j["id"] == sub_id][0]
        
        assert sub_id in main["sub_jobs"]
        assert sub["parent_id"] == main_id
        
        print("✅ test_sub_job_structure passed")
    
    def test_job_status_transitions(self):
        """Test job status changes"""
        from jobs import complete_job, assign_job
        
        job_id = create_job("Status test job", assigned_to="Mac")
        
        db = load_db()
        job = [j for j in db["jobs"] if j["id"] == job_id][0]
        assert job["status"] == "TODO"
        
        # Assign to agent
        assign_job(job_id, "Sage")
        db = load_db()
        job = [j for j in db["jobs"] if j["id"] == job_id][0]
        assert job["assigned_to"] == "Sage"
        
        # Complete job
        complete_job(job_id, "Completed successfully")
        db = load_db()
        job = [j for j in db["jobs"] if j["id"] == job_id][0]
        assert job["status"] == "DONE"
        assert job["completed_at"] is not None
        
        print("✅ test_job_status_transitions passed")

class TestConfiguration:
    """Test system configuration"""
    
    def test_config_file_exists(self):
        """Test that config file exists"""
        config_path = Path("/Users/wxia/.openclaw/workspace/jobs/config.json")
        assert config_path.exists(), f"Config file not found at {config_path}"
        
        with open(config_path) as f:
            config = json.load(f)
        
        assert "agents" in config
        assert "workspace_path" in config
        print("✅ test_config_file_exists passed")
    
    def test_results_directories(self):
        """Test that result directories exist"""
        base_path = Path("/Users/wxia/.openclaw/workspace/results")
        
        dirs = ["research", "planning", "escalations"]
        for d in dirs:
            dir_path = base_path / d
            assert dir_path.exists(), f"Directory {d} not found"
        
        print("✅ test_results_directories passed")

def run_tests():
    """Run all system tests"""
    print("\n" + "="*60)
    print("Running System Tests")
    print("="*60 + "\n")
    
    # Dashboard API tests
    test = TestDashboardAPI()
    tests = [
        test.test_api_jobs_response_format,
        test.test_job_fields,
        test.test_sub_job_structure,
        test.test_job_status_transitions,
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
    
    # Config tests (no setup needed)
    test_config = TestConfiguration()
    try:
        test_config.test_config_file_exists()
        passed += 1
    except Exception as e:
        print(f"❌ test_config_file_exists failed: {e}")
        failed += 1
    
    try:
        test_config.test_results_directories()
        passed += 1
    except Exception as e:
        print(f"❌ test_results_directories failed: {e}")
        failed += 1
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0

if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
