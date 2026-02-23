"""Configuration loader for job dispatch system."""
import json
from pathlib import Path

# Base paths
BASE_DIR = Path("/Users/wxia/.openclaw/workspace")
JOBS_DIR = BASE_DIR / "jobs"
CONFIG_PATH = JOBS_DIR / "config.json"

def load_config():
    """Load configuration from config.json."""
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return get_default_config()

def get_default_config():
    """Return default configuration."""
    return {
        "workspace_path": str(BASE_DIR),
        "jobs_db_path": str(JOBS_DIR / "jobs-db.json"),
        "archive_path": str(JOBS_DIR / "archive"),
        "results_path": str(BASE_DIR / "results"),
        "dashboard_port": 8765,
        "poll_interval": 5,
        "max_concurrent_per_agent": 1,
        "escalation_multiplier": 2.0,
        "max_retries": 3,
        "stuck_job_timeout_minutes": 30,
        "compact_days": 7,
        "agents": {
            "sage": {"name": "Sage", "base_estimate_minutes": 25},
            "atlas": {"name": "Atlas", "base_estimate_minutes": 35},
            "glitch": {"name": "Glitch", "base_estimate_minutes": 45},
            "mac": {"name": "Mac", "base_estimate_minutes": 10}
        }
    }

# Load config once at module level
CONFIG = load_config()

# Export commonly used values
WORKSPACE_PATH = Path(CONFIG["workspace_path"])
JOBS_DB_PATH = Path(CONFIG["jobs_db_path"])
ARCHIVE_PATH = Path(CONFIG["archive_path"])
RESULTS_PATH = Path(CONFIG["results_path"])
DASHBOARD_PORT = CONFIG["dashboard_port"]
POLL_INTERVAL = CONFIG["poll_interval"]
MAX_CONCURRENT = CONFIG["max_concurrent_per_agent"]
MAX_RETRIES = CONFIG["max_retries"]

# Agent configs
AGENT_CONFIGS = CONFIG.get("agents", {})
