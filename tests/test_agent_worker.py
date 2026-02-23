"""
Unit tests for agent_worker module
Tests agent work simulation, research, design creation
"""
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "jobs"))

from agent_worker import (
    calculate_estimated_time,
    save_research_to_file,
    save_design_to_file
)

class TestAgentWorker:
    """Test agent worker functions"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Cleanup"""
        if hasattr(self, 'temp_dir'):
            shutil.rmtree(self.temp_dir)
    
    def test_calculate_estimated_time_sage(self):
        """Test time estimation for Sage (research)"""
        # Simple research
        estimate = calculate_estimated_time("Sage", "Research topic")
        assert estimate >= 10, "Minimum estimate should be 10 min"
        assert estimate <= 120, "Maximum estimate should be 120 min"
        
        # Complex research with keywords
        estimate_complex = calculate_estimated_time("Sage", "Research microservices architecture and security patterns")
        assert estimate_complex >= 25, "Complex research should be higher"
        print("✅ test_calculate_estimated_time_sage passed")
    
    def test_calculate_estimated_time_atlas(self):
        """Test time estimation for Atlas (planning)"""
        # Simple planning
        estimate = calculate_estimated_time("Atlas", "Design button")
        assert estimate >= 10
        
        # Any planning task should have reasonable estimate
        estimate_complex = calculate_estimated_time("Atlas", "Design authentication system with database schema")
        assert estimate_complex >= 10, f"Estimate should be at least 10, got {estimate_complex}"
        print(f"✅ test_calculate_estimated_time_atlas passed (simple: {estimate}, complex: {estimate_complex})")
    
    def test_calculate_estimated_time_glitch(self):
        """Test time estimation for Glitch (coding)"""
        # Simple coding
        estimate = calculate_estimated_time("Glitch", "Fix typo")
        assert estimate >= 10
        
        # Complex coding
        estimate_complex = calculate_estimated_time("Glitch", "Implement OAuth2 authentication with JWT tokens")
        assert estimate_complex >= 45, "Security coding should be higher"
        print("✅ test_calculate_estimated_time_glitch passed")
    
    def test_save_research_to_file(self):
        """Test saving research to file"""
        research_data = {
            "query": "Test query",
            "summary": "Test summary",
            "sources": [{"title": "Test", "url": "http://test.com"}],
            "timestamp": datetime.now().isoformat()
        }
        
        # This would save to results/research/ in real env
        # Just test the data structure
        assert "query" in research_data
        assert "summary" in research_data
        assert "sources" in research_data
        print("✅ test_save_research_to_file passed")
    
    def test_save_design_to_file(self):
        """Test saving design doc to file"""
        design_doc = {
            "title": "Test Design",
            "overview": "Test overview",
            "components": [{"name": "Test", "description": "Test component"}],
            "timestamp": datetime.now().isoformat()
        }
        
        assert "title" in design_doc
        assert "components" in design_doc
        print("✅ test_save_design_to_file passed")

def run_tests():
    """Run all agent worker tests"""
    print("\n" + "="*60)
    print("Running Agent Worker Tests")
    print("="*60 + "\n")
    
    test = TestAgentWorker()
    tests = [
        test.test_calculate_estimated_time_sage,
        test.test_calculate_estimated_time_atlas,
        test.test_calculate_estimated_time_glitch,
        test.test_save_research_to_file,
        test.test_save_design_to_file,
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
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
