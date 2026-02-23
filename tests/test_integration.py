"""
Integration tests for job dispatch workflow
Tests full workflow: User → Mac → Sage → Atlas → Glitch → Done
"""
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "jobs"))

from jobs import (
    create_job, complete_job, load_db, get_job, save_db,
    assign_job, JOBS_DB
)
from workflow import dispatch_to_agent

class TestWorkflowIntegration:
    """Integration tests for complete workflow"""
    
    def setup_method(self):
        """Setup isolated test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_db = JOBS_DB
        
        # Patch JOBS_DB
        import jobs
        jobs.JOBS_DB = Path(self.temp_dir) / "test-jobs-db.json"
        
        # Initialize empty DB
        save_db({"version": "1.0", "jobs": [], "lastJobId": 0})
    
    def teardown_method(self):
        """Restore original DB"""
        import jobs
        jobs.JOBS_DB = self.original_db
        if hasattr(self, 'temp_dir'):
            shutil.rmtree(self.temp_dir)
    
    def test_simple_workflow(self):
        """Test simple workflow: User → Mac → Done"""
        # User creates task
        job_id = create_job("Simple task", assigned_to="Mac", from_user=True)
        
        db = load_db()
        job = get_job(db, job_id)
        
        # Job might be IN_PROGRESS if confirmation sub-job was created
        assert job["status"] in ["TODO", "IN_PROGRESS"]
        assert job["needs_confirmation"] == True
        assert job["assigned_to"] == "Mac"
        
        # Mac confirms
        job["confirmed"] = True
        job["confirmed_at"] = datetime.now().isoformat()
        save_db(db)
        
        # Mac dispatches and completes
        complete_job(job_id, "Task completed")
        
        db = load_db()
        job = get_job(db, job_id)
        assert job["status"] == "DONE"
        
        print("✅ test_simple_workflow passed")
    
    def test_sub_job_creation(self):
        """Test creating sub-jobs under main job"""
        # Create main job
        main_id = create_job("Main task", assigned_to="Mac")
        
        # Create sub-jobs
        sub1 = create_job("Sub-task 1", parent_id=main_id, assigned_to="Sage")
        sub2 = create_job("Sub-task 2", parent_id=main_id, assigned_to="Atlas")
        
        db = load_db()
        main = get_job(db, main_id)
        
        # Verify sub-jobs linked
        assert sub1 in main["sub_jobs"]
        assert sub2 in main["sub_jobs"]
        
        # Verify parent set
        sub1_job = get_job(db, sub1)
        assert sub1_job["parent_id"] == main_id
        
        print("✅ test_sub_job_creation passed")
    
    def test_dispatch_workflow(self):
        """Test dispatch to agent workflow"""
        # Create job
        job_id = create_job("Research task", assigned_to="Mac")
        
        # Dispatch to Sage
        result = dispatch_to_agent(job_id, "research")
        assert result == True
        
        # Verify assignment
        db = load_db()
        job = get_job(db, job_id)
        assert job["assigned_to"] == "Sage"
        
        print("✅ test_dispatch_workflow passed")
    
    def test_job_hierarchy_completion(self):
        """Test completing jobs in hierarchy"""
        # Create main job
        main_id = create_job("Main task", assigned_to="Mac")
        
        # Create and complete sub-job
        sub_id = create_job("Sub-task", parent_id=main_id, assigned_to="Glitch")
        complete_job(sub_id, "Sub-task done")
        
        # Complete main
        complete_job(main_id, "All sub-tasks complete")
        
        db = load_db()
        main = get_job(db, main_id)
        sub = get_job(db, sub_id)
        
        assert main["status"] == "DONE"
        assert sub["status"] == "DONE"
        
        print("✅ test_job_hierarchy_completion passed")

def run_tests():
    """Run all integration tests"""
    print("\n" + "="*60)
    print("Running Workflow Integration Tests")
    print("="*60 + "\n")
    
    test = TestWorkflowIntegration()
    tests = [
        test.test_simple_workflow,
        test.test_sub_job_creation,
        test.test_dispatch_workflow,
        test.test_job_hierarchy_completion,
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
            import traceback
            traceback.print_exc()
            failed += 1
        finally:
            test.teardown_method()
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0

if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
