#!/usr/bin/env python3
"""
Job Dispatch Workflow Manager
Handles job creation, sub-jobs, assignments, and status tracking.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

JOBS_DB = Path("/Users/wxia/.openclaw/workspace/jobs/jobs-db.json")

def load_db():
    """Load the jobs database."""
    if JOBS_DB.exists():
        with open(JOBS_DB) as f:
            return json.load(f)
    return {"version": "1.0", "jobs": [], "lastJobId": 0}

def save_db(db):
    """Save the jobs database."""
    with open(JOBS_DB, 'w') as f:
        json.dump(db, f, indent=2)

def create_job(description, parent_id=None, assigned_to="Mac"):
    """Create a new job or sub-job."""
    db = load_db()
    db["lastJobId"] += 1
    job_id = db["lastJobId"]
    
    job = {
        "id": job_id,
        "parent_id": parent_id,
        "description": description,
        "status": "TODO",
        "assigned_to": assigned_to,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "sub_jobs": [],
        "notes": ""
    }
    
    db["jobs"].append(job)
    
    # If this is a sub-job, add to parent's sub_jobs list
    if parent_id:
        parent = get_job(db, parent_id)
        if parent:
            parent["sub_jobs"].append(job_id)
            parent["status"] = "IN_PROGRESS"
    
    save_db(db)
    return job_id

def get_job(db, job_id):
    """Get a job by ID."""
    for job in db["jobs"]:
        if job["id"] == job_id:
            return job
    return None

def assign_job(job_id, agent):
    """Assign a job to an agent."""
    db = load_db()
    job = get_job(db, job_id)
    if not job:
        print(f"Job #{job_id} not found")
        return False
    
    job["assigned_to"] = agent
    job["status"] = "IN_PROGRESS"
    save_db(db)
    print(f"Job #{job_id} assigned to {agent}")
    return True

def complete_job(job_id, notes=""):
    """Mark a job as complete."""
    db = load_db()
    job = get_job(db, job_id)
    if not job:
        print(f"Job #{job_id} not found")
        return False
    
    job["status"] = "DONE"
    job["completed_at"] = datetime.now().isoformat()
    if notes:
        job["notes"] = notes
    
    save_db(db)
    
    # If this is a sub-job, check if parent should be marked complete
    if job["parent_id"]:
        check_parent_completion(db, job["parent_id"])
    
    print(f"Job #{job_id} marked as DONE")
    return True

def check_parent_completion(db, parent_id):
    """Check if all sub-jobs of a parent are done."""
    parent = get_job(db, parent_id)
    if not parent:
        return
    
    all_done = True
    for sub_id in parent["sub_jobs"]:
        sub = get_job(db, sub_id)
        if sub and sub["status"] != "DONE":
            all_done = False
            break
    
    if all_done and parent["sub_jobs"]:
        print(f"\n⚠️  All sub-jobs of #{parent_id} are complete. Ready to mark main job as DONE.")
        print(f"   Run: jobs complete {parent_id}")

def list_jobs(status=None, agent=None):
    """List all jobs with optional filters."""
    db = load_db()
    jobs = db["jobs"]
    
    if status:
        jobs = [j for j in jobs if j["status"] == status]
    if agent:
        jobs = [j for j in jobs if j["assigned_to"] == agent]
    
    if not jobs:
        print("No jobs found.")
        return
    
    print(f"\n{'ID':<6}{'Status':<12}{'Assigned':<12}{'Description'}")
    print("-" * 60)
    for job in jobs:
        sub_indicator = f" [{len(job['sub_jobs'])} sub]" if job["sub_jobs"] else ""
        parent_indicator = f" (sub of #{job['parent_id']})" if job["parent_id"] else ""
        desc = job["description"][:40] + "..." if len(job["description"]) > 40 else job["description"]
        print(f"#{job['id']:<5}{job['status']:<12}{job['assigned_to']:<12}{desc}{sub_indicator}{parent_indicator}")
    print()

def show_job(job_id):
    """Show detailed view of a job including sub-jobs."""
    db = load_db()
    job = get_job(db, job_id)
    if not job:
        print(f"Job #{job_id} not found")
        return
    
    print(f"\n{'='*50}")
    print(f"Job #{job_id}{' (Sub-job of #' + str(job['parent_id']) + ')' if job['parent_id'] else ' (Main Job)'}")
    print(f"{'='*50}")
    print(f"Description: {job['description']}")
    print(f"Status: {job['status']}")
    print(f"Assigned to: {job['assigned_to']}")
    print(f"Created: {job['created_at']}")
    if job["completed_at"]:
        print(f"Completed: {job['completed_at']}")
    if job["notes"]:
        print(f"Notes: {job['notes']}")
    
    if job["sub_jobs"]:
        print(f"\nSub-jobs:")
        for sub_id in job["sub_jobs"]:
            sub = get_job(db, sub_id)
            if sub:
                print(f"  #{sub_id}: [{sub['status']}] {sub['description'][:50]}")
    print()

def create_completion_subjob(parent_id, agent_name, summary):
    """Auto-create a completion sub-job when an agent finishes."""
    description = f"{agent_name} complete for #{parent_id}: {summary}"
    sub_id = create_job(description, parent_id=parent_id, assigned_to="Mac")
    print(f"Auto-created completion sub-job #{sub_id} → Mac")
    return sub_id

def get_pending_for_agent(agent):
    """Get all pending jobs for a specific agent."""
    db = load_db()
    return [j for j in db["jobs"] if j["assigned_to"] == agent and j["status"] != "DONE"]

def main():
    if len(sys.argv) < 2:
        print("Usage: jobs <command> [args]")
        print("\nCommands:")
        print("  create <description>          Create a new job")
        print("  sub <parent_id> <desc>        Create a sub-job")
        print("  assign <id> <agent>           Assign job to agent")
        print("  complete <id> [notes]         Mark job as complete")
        print("  list [status] [agent]         List jobs")
        print("  show <id>                     Show job details")
        print("  agent <name>                  Show agent's work queue view")
        print("  work <agent> [id] [--complete] Agent takes & works on job")
        print("  dispatch                      Mac auto-routes completed jobs")
        print("  pending <agent>               Show pending jobs for agent")
        print("  dashboard                     Launch web dashboard")
        print("  workflow <cmd> [args]         Workflow automation commands")
        print("\nAgents: Mac, Glitch, Research, Planning")
        print("\nAgent Worker:")
        print("  jobs work <agent>                   - Agent takes next job")
        print("  jobs work <agent> <id> --complete   - Complete specific job")
        print("  jobs dispatch                       - Mac routes completed work")
        print("\nWorkflow commands:")
        print("  jobs workflow dashboard                    - Show CLI dashboard")
        print("  jobs workflow dispatch <id> <agent>        - Dispatch to agent")
        print("  jobs workflow complete <agent> <id> <msg>  - Agent completes")
        print("  jobs workflow clarify <agent> <id> <msg>   - Agent needs help")
        print("  jobs workflow evaluate <sub_job_id>        - Mac evaluates")
        print("  jobs workflow route <main_id> <agent>      - Route to next")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "create":
        if len(sys.argv) < 3:
            print("Usage: jobs create <description>")
            sys.exit(1)
        desc = " ".join(sys.argv[2:])
        job_id = create_job(desc)
        print(f"Created job #{job_id}: {desc}")
    
    elif cmd == "sub":
        if len(sys.argv) < 4:
            print("Usage: jobs sub <parent_id> <description>")
            sys.exit(1)
        parent_id = int(sys.argv[2])
        desc = " ".join(sys.argv[3:])
        job_id = create_job(desc, parent_id=parent_id)
        print(f"Created sub-job #{job_id} under #{parent_id}: {desc}")
    
    elif cmd == "assign":
        if len(sys.argv) < 4:
            print("Usage: jobs assign <id> <agent>")
            sys.exit(1)
        job_id = int(sys.argv[2])
        agent = sys.argv[3]
        assign_job(job_id, agent)
    
    elif cmd == "complete":
        if len(sys.argv) < 3:
            print("Usage: jobs complete <id> [notes]")
            sys.exit(1)
        job_id = int(sys.argv[2])
        notes = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        complete_job(job_id, notes)
    
    elif cmd == "list":
        status = sys.argv[2] if len(sys.argv) > 2 else None
        agent = sys.argv[3] if len(sys.argv) > 3 else None
        list_jobs(status, agent)
    
    elif cmd == "show":
        if len(sys.argv) < 3:
            print("Usage: jobs show <id>")
            sys.exit(1)
        show_job(int(sys.argv[2]))
    
    elif cmd == "agent":
        # Check if it's a subcommand for agent_worker
        if len(sys.argv) >= 3 and sys.argv[2] in ["status", "work", "process"]:
            from agent_worker import main as worker_main
            sys.argv = ["agent_worker"] + sys.argv[2:]
            worker_main()
        else:
            # Show agent's work queue view
            if len(sys.argv) < 3:
                print("Usage: jobs agent <name>")
                print("\nShows the work queue from an agent's perspective:")
                print("  - Pending jobs assigned to them")
                print("  - Recently completed jobs")
                print("  - Stats about their workload")
                print("\nAgents: Mac, Glitch, Research, Planning")
                print("\nAgent subcommands:")
                print("  jobs agent status <name>      - Detailed agent status")
                print("  jobs agent work <name>        - Agent takes next job")
                print("  jobs agent process <name>     - Process all pending jobs")
                sys.exit(1)
            
            agent_name = sys.argv[2]
            db = load_db()
            
            # Find all jobs for this agent
            agent_jobs = [j for j in db["jobs"] if j["assigned_to"].lower() == agent_name.lower()]
            
            if not agent_jobs:
                print(f"\n📭 No jobs found for {agent_name}")
                sys.exit(0)
            
            pending = [j for j in agent_jobs if j["status"] != "DONE"]
            completed = [j for j in agent_jobs if j["status"] == "DONE"]
            
            print(f"\n{'='*60}")
            print(f"👤 {agent_name.upper()} AGENT VIEW")
            print(f"{'='*60}")
            
            print(f"\n📊 STATS")
            print(f"   Pending: {len(pending)}")
            print(f"   Completed: {len(completed)}")
            print(f"   Total: {len(agent_jobs)}")
            
            if pending:
                print(f"\n🔄 PENDING JOBS ({len(pending)})")
                for job in sorted(pending, key=lambda x: x["id"]):
                    parent_info = f" (sub of #{job['parent_id']})" if job["parent_id"] else ""
                    print(f"   #{job['id']}: {job['description'][:50]}{parent_info}")
            
            if completed:
                print(f"\n✅ COMPLETED JOBS ({len(completed)})")
                for job in sorted(completed, key=lambda x: x["id"], reverse=True)[:5]:
                    print(f"   #{job['id']}: {job['description'][:50]}")
                if len(completed) > 5:
                    print(f"   ... and {len(completed) - 5} more")
            
            print()
    
    elif cmd == "work":
        # Delegate to agent worker
        # sys.argv = ['jobs', 'work', 'Planning', '--complete']
        # Need to pass: ['agent_worker', 'work', 'Planning', '--complete']
        from agent_worker import main as worker_main
        original_argv = sys.argv.copy()
        sys.argv = ["agent_worker"] + original_argv[1:]
        worker_main()
    
    elif cmd == "dispatch":
        # Mac auto-dispatches completed jobs
        from agent_worker import main as worker_main
        sys.argv = ["agent_worker", "dispatch"]
        worker_main()
    
    elif cmd == "pending":
        if len(sys.argv) < 3:
            print("Usage: jobs pending <agent>")
            sys.exit(1)
        agent = sys.argv[2]
        jobs = get_pending_for_agent(agent)
        if jobs:
            print(f"\nPending jobs for {agent}:")
            for job in jobs:
                print(f"  #{job['id']}: {job['description'][:60]}")
        else:
            print(f"No pending jobs for {agent}")
    
    elif cmd == "dashboard":
        # Check if already running
        import urllib.request
        try:
            urllib.request.urlopen("http://localhost:8765/", timeout=1)
            print("🌐 Dashboard already running at http://localhost:8765")
            print("   Opening browser...")
            import webbrowser
            webbrowser.open("http://localhost:8765")
            return
        except:
            pass
        
        # Launch web dashboard
        import subprocess
        import threading
        import time
        import webbrowser
        
        dashboard_path = Path(__file__).parent / "dashboard_server.py"
        print("🌐 Starting dashboard server...")
        
        # Start server in background
        process = subprocess.Popen(
            ["python3", str(dashboard_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        time.sleep(1)
        
        # Check if it's running
        try:
            urllib.request.urlopen("http://localhost:8765/", timeout=2)
            print("   ✅ Server running at http://localhost:8765")
            print("   Opening browser...")
            webbrowser.open("http://localhost:8765")
            print("   Dashboard launched!")
        except Exception as e:
            print(f"   ❌ Failed to start server: {e}")
            process.terminate()
    
    elif cmd == "workflow":
        # Delegate to workflow module
        from workflow import main as workflow_main
        sys.argv = sys.argv[1:]  # Remove 'jobs' from args
        workflow_main()
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()