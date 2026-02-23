"""
Workflow Enforcement - Prevents Mac from implementing directly
This module enforces that Mac must dispatch to agents instead of implementing
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Track direct implementation attempts
ENFORCEMENT_LOG = Path("/Users/wxia/.openclaw/workspace/logs/workflow_violations.log")

def log_workflow_violation(action, reason):
    """Log when workflow is bypassed."""
    ENFORCEMENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(ENFORCEMENT_LOG, 'a') as f:
        f.write(f"[{datetime.now().isoformat()}] VIOLATION: {action} - {reason}\n")

def enforce_dispatch_required(agent_name, action_description):
    """
    Enforce that only agents can implement, not Mac.
    Raises exception if Mac tries to implement directly.
    """
    if agent_name.lower() == "mac":
        error_msg = f"""
╔══════════════════════════════════════════════════════════════════╗
║  WORKFLOW VIOLATION - Mac cannot implement directly!             ║
╠══════════════════════════════════════════════════════════════════╣
║  Attempted: {action_description[:50]:50} ║
╠══════════════════════════════════════════════════════════════════╣
║  Mac's role: Coordinator ONLY                                    ║
║  - Talk to user                                                  ║
║  - Dispatch to agents                                            ║
║  - Verify completed work                                         ║
╠══════════════════════════════════════════════════════════════════╣
║  REQUIRED ACTION:                                                ║
║  1. Create task: jobctl create "description" --from-user        ║
║  2. Confirm task: jobctl confirm <id> --dispatch                ║
║  3. Let agents do the work!                                      ║
╚══════════════════════════════════════════════════════════════════╝
"""
        log_workflow_violation(action_description, "Mac attempted direct implementation")
        raise PermissionError(error_msg)
    return True

def check_before_edit(file_path):
    """
    Check if Mac is about to edit a file.
    Warns/enforces workflow compliance.
    """
    # Get the caller's context
    import inspect
    frame = inspect.currentframe().f_back
    
    # Check if this is being called from agent_worker (allowed) or elsewhere (Mac)
    caller_file = frame.f_code.co_filename
    
    # Only allow edits from agent_worker.py (agents) or jobs.py (system)
    if 'agent_worker.py' not in caller_file and 'jobs.py' not in caller_file:
        if 'workflow_enforcement' not in caller_file:
            enforce_dispatch_required("Mac", f"Attempted to edit {file_path}")

class WorkflowEnforcer:
    """
    Context manager to enforce workflow during operations.
    Usage:
        with WorkflowEnforcer(agent="Mac", action="writing code"):
            # This will raise error if agent is Mac
            write_code()
    """
    def __init__(self, agent, action):
        self.agent = agent
        self.action = action
    
    def __enter__(self):
        enforce_dispatch_required(self.agent, self.action)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

# Self-reminder for Mac
MAC_REMINDER = """
╔════════════════════════════════════════════════════════════╗
║                    ⚠️  MAC REMINDER  ⚠️                     ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  YOU ARE MAC - COORDINATOR, NOT IMPLEMENTER               ║
║                                                            ║
║  Before you write code or edit files:                     ║
║                                                            ║
║  1. STOP ✋                                                ║
║  2. Create a task:                                        ║
║     jobctl create "Implement X" --from-user               ║
║                                                            ║
║  3. Confirm and dispatch:                                 ║
║     jobctl confirm <id> --dispatch                        ║
║                                                            ║
║  4. Let Sage/Atlas/Glitch do the work                     ║
║                                                            ║
║  DO NOT IMPLEMENT DIRECTLY!                               ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
"""

def print_mac_reminder():
    """Print reminder for Mac."""
    print(MAC_REMINDER)

if __name__ == "__main__":
    print_mac_reminder()
