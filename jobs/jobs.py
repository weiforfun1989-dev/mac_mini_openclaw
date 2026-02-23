#!/usr/bin/env python3
"""
Job Dispatch Workflow Manager
Handles job creation, sub-jobs, assignments, and status tracking.
"""

import json
import os
import sys
import fcntl
from datetime import datetime
from pathlib import Path

JOBS_DB = Path("/Users/wxia/.openclaw/workspace/jobs/jobs-db.json")

def load_db():
    """Load the jobs database with file locking."""
    if JOBS_DB.exists():
        with open(JOBS_DB, 'r') as f:
            # Acquire shared lock for reading
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                return json.load(f)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    return {"version": "1.0", "jobs": [], "lastJobId": 0}

def save_db(db):
    """Save the jobs database with file locking."""
    with open(JOBS_DB, 'w') as f:
        # Acquire exclusive lock for writing
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            json.dump(db, f, indent=2)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

def create_job(description, parent_id=None, assigned_to="Mac", priority="medium", from_user=False):
    """Create a new job or sub-job with atomic ID generation."""
    db = load_db()
    
    # Atomic ID generation - reload DB to get latest ID
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
        "notes": "",
        "estimated_minutes": None,
        "started_at": None,
        "escalated": False,
        "retry_count": 0,
        "max_retries": 3,
        "last_heartbeat": None,
        "health_status": "healthy",
        "priority": priority,
        "dispatched_by": None,
        "research_result": None,
        "design_doc": None,
        "needs_confirmation": from_user,  # Jobs from user need Mac confirmation
        "confirmed": False
    }
    
    db["jobs"].append(job)
    
    # If this is a sub-job, add to parent's sub_jobs list atomically
    if parent_id:
        db = load_db()  # Reload to get latest state
        parent = get_job(db, parent_id)
        if parent:
            parent["sub_jobs"].append(job_id)
            parent["status"] = "IN_PROGRESS"
            save_db(db)
    
    save_db(db)
    
    # If from user, create Mac confirmation sub-job
    if from_user:
        confirm_id = create_job(
            f"📝 CONFIRMATION NEEDED: Please review and confirm job #{job_id}",
            parent_id=job_id,
            assigned_to="Mac",
            priority="high"
        )
        print(f"   📋 Confirmation job #{confirm_id} created for Mac")
    
    return job_id

def get_job(db, job_id):
    """Get a job by ID."""
    for job in db["jobs"]:
        if job["id"] == job_id:
            return job
    return None

def assign_job(job_id, agent, dispatched_by="Mac"):
    """Assign a job to an agent."""
    db = load_db()
    job = get_job(db, job_id)
    if not job:
        print(f"Job #{job_id} not found")
        return False
    
    job["assigned_to"] = agent
    job["dispatched_by"] = dispatched_by
    # Status stays TODO - only becomes IN_PROGRESS when agent claims it
    save_db(db)
    print(f"Job #{job_id} assigned to {agent}")
    return True

def complete_job(job_id, notes=""):
    """Mark a job as complete with atomic check."""
    db = load_db()
    job = get_job(db, job_id)
    if not job:
        print(f"Job #{job_id} not found")
        return False
    
    # Atomic check: don't re-complete already done jobs
    if job["status"] == "DONE":
        return True
    
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
    """Get all pending jobs for a specific agent, sorted by priority.
    For Mac, escalation jobs get highest priority."""
    db = load_db()
    
    if agent == "Mac":
        # Mac has two queues: Escalations first, then regular completions
        mac_jobs = [j for j in db["jobs"] 
                    if j["assigned_to"] == agent 
                    and j["status"] != "DONE"]
        
        # Separate escalation jobs from regular completions
        escalations = [j for j in mac_jobs 
                       if "escalation" in j.get("description", "").lower() 
                       or "exceeded" in j.get("description", "").lower()
                       or "⚠️" in j.get("description", "")]
        regular = [j for j in mac_jobs if j not in escalations]
        
        # Sort escalations by creation time (oldest first)
        escalations.sort(key=lambda x: x["created_at"])
        regular.sort(key=lambda x: x["created_at"])
        
        # Return escalations first, then regular
        return escalations + regular
    else:
        # Other agents: sort by priority
        pending = [j for j in db["jobs"] 
                   if j["assigned_to"] == agent and j["status"] != "DONE"]
        
        # Priority order: high > medium > low
        priority_order = {"high": 3, "medium": 2, "low": 1}
        
        # Sort by priority (descending), then by creation time (ascending)
        pending.sort(key=lambda j: (-priority_order.get(j.get("priority", "medium"), 2), j["created_at"]))
        
        return pending

def main():
    if len(sys.argv) < 2:
        print("Usage: jobs <command> [args]")
        print("\nCommands:")
        print("  create <description> [--priority high|medium|low]  Create a new job")
        print("  sub <parent_id> <desc> [--priority p]  Create a sub-job")
        print("  assign <id> <agent>           Assign job to agent")
        print("  complete <id> [notes]         Mark job as complete")
        print("  list [status] [agent]         List jobs")
        print("  show <id>                     Show job details")
        print("  research <job_id>             View research results")
        print("  design <job_id>               View design document")
        print("  agent <name>                  Show agent's work queue view")
        print("  work <agent> [id] [--complete] Agent takes & works on job")
        print("  dispatch                      Mac auto-routes completed jobs")
        print("  pending <agent>               Show pending jobs for agent")
        print("  dashboard                     Launch web dashboard")
        print("  health [agent]                Run health check on agent(s)")
        print("  parallel <agent> [--complete]  Process jobs in parallel")
        print("  retry <job_id>                Retry a failed/stuck job")
        print("  notify <message> [level]       Send notification (info/warning/error/urgent)")
        print("  auto [--daemon]               Auto-trigger agents and check for deadlocks")
        print("  coordinator [--daemon]        Mac aggressively pushes all agents to closure")
        print("  poll [--daemon]               Agents actively query for work when idle")
        print("  confirm <job_id>              Confirm a job for dispatch (after Mac review)")
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
        # Parse arguments for priority and from-user flag
        priority = "medium"
        from_user = False
        desc_parts = []
        
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--priority" and i + 1 < len(sys.argv):
                priority = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--from-user":
                from_user = True
                i += 1
            else:
                desc_parts.append(sys.argv[i])
                i += 1
        
        if not desc_parts:
            print("Usage: jobs create <description> [--priority high|medium|low] [--from-user]")
            sys.exit(1)
        
        desc = " ".join(desc_parts)
        job_id = create_job(desc, priority=priority, from_user=from_user)
        if from_user:
            print(f"Created job #{job_id} [{priority}] [NEEDS CONFIRMATION]: {desc}")
            print(f"   Mac will review before dispatching to agents")
        else:
            print(f"Created job #{job_id} [{priority}]: {desc}")

    elif cmd == "confirm":
        # Confirm a job that needs user approval
        if len(sys.argv) < 3:
            print("Usage: jobs confirm <job_id>")
            print("\nConfirms a job that was created from user request.")
            print("Mac can then dispatch it to appropriate agents.")
            sys.exit(1)
        
        job_id = int(sys.argv[2])
        db = load_db()
        job = get_job(db, job_id)
        
        if not job:
            print(f"Job #{job_id} not found")
            sys.exit(1)
        
        if not job.get("needs_confirmation"):
            print(f"Job #{job_id} doesn't need confirmation")
            sys.exit(0)
        
        if job.get("confirmed"):
            print(f"Job #{job_id} already confirmed")
            sys.exit(0)
        
        job["confirmed"] = True
        job["confirmed_at"] = datetime.now().isoformat()
        job["notes"] = "Confirmed by user, ready for dispatch"
        save_db(db)
        
        print(f"✅ Job #{job_id} confirmed!")
        print(f"   Description: {job['description'][:60]}")
        print(f"   Mac can now dispatch to appropriate agents")
        print(f"   Run: jobs dispatch  # to start workflow")
    
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

    elif cmd == "research":
        # View research results for a job
        if len(sys.argv) < 3:
            print("Usage: jobs research <job_id>")
            print("\nShows research results including sources and summary")
            sys.exit(1)
        job_id = int(sys.argv[2])
        db = load_db()
        job = get_job(db, job_id)
        if not job:
            print(f"Job #{job_id} not found")
            sys.exit(1)
        
        if not job.get("research_result"):
            print(f"No research results for job #{job_id}")
            sys.exit(0)
        
        rr = job["research_result"]
        print(f"\n📚 RESEARCH RESULTS FOR JOB #{job_id}")
        print("=" * 60)
        print(f"Query: {rr.get('query', 'N/A')}")
        print(f"Timestamp: {rr.get('timestamp', 'N/A')}")
        if rr.get("summary"):
            print(f"\nSummary:\n{rr['summary']}")
        if rr.get("sources"):
            print(f"\nSources ({len(rr['sources'])}):")
            for i, src in enumerate(rr["sources"][:5], 1):
                print(f"  {i}. {src.get('title', 'N/A')}")
                print(f"     {src.get('url', 'N/A')}")
        
    elif cmd == "design":
        # View design document for a job
        if len(sys.argv) < 3:
            print("Usage: jobs design <job_id>")
            print("\nShows design document with architecture and components")
            sys.exit(1)
        job_id = int(sys.argv[2])
        db = load_db()
        job = get_job(db, job_id)
        if not job:
            print(f"Job #{job_id} not found")
            sys.exit(1)
        
        if not job.get("design_doc"):
            print(f"No design document for job #{job_id}")
            sys.exit(0)
        
        dd = job["design_doc"]
        print(f"\n📋 DESIGN DOCUMENT FOR JOB #{job_id}")
        print("=" * 60)
        print(f"Title: {dd.get('title', 'N/A')}")
        print(f"Timestamp: {dd.get('timestamp', 'N/A')}")
        print(f"\nOverview:\n{dd.get('overview', 'N/A')}")
        print(f"\nArchitecture: {dd.get('architecture', 'N/A')}")
        print(f"Tech Stack: {dd.get('tech_stack', 'N/A')}")
        print(f"Estimated Effort: {dd.get('estimated_effort', 'N/A')}")
        
        if dd.get("components"):
            print(f"\nComponents:")
            for comp in dd["components"]:
                print(f"  • {comp['name']}: {comp['description']}")
        
        if dd.get("research_context"):
            print(f"\nResearch Context: {dd['research_context'][:100]}...")
    
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
            in_progress = [j for j in agent_jobs if j["status"] == "IN_PROGRESS"]
            
            print(f"\n{'='*60}")
            print(f"👤 {agent_name.upper()} AGENT VIEW")
            print(f"{'='*60}")
            
            print(f"\n📊 STATS")
            print(f"   🔄 In Progress: {len(in_progress)}")
            print(f"   ⏳ Pending: {len(pending) - len(in_progress)}")
            print(f"   ✅ Completed: {len(completed)}")
            print(f"   📊 Total: {len(agent_jobs)}")
            
            if in_progress:
                print(f"\n🔨 IN PROGRESS ({len(in_progress)})")
                for job in in_progress:
                    parent_info = f" (sub of #{job['parent_id']})" if job["parent_id"] else ""
                    print(f"   #{job['id']}: {job['description'][:50]}{parent_info}")
            
            if pending and len(pending) > len(in_progress):
                print(f"\n⏳ PENDING QUEUE ({len(pending) - len(in_progress)})")
                for job in sorted(pending, key=lambda x: x["id"]):
                    if job["status"] != "IN_PROGRESS":
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
    
    elif cmd == "health":
        # Run health check on all agents or specific agent
        from agent_worker import main as worker_main
        sys.argv = ["agent_worker", "health"] + (sys.argv[2:] if len(sys.argv) > 2 else [])
        worker_main()
    
    elif cmd == "parallel":
        # Process jobs in parallel
        if len(sys.argv) < 3:
            print("Usage: jobs parallel <agent_name> [--complete]")
            sys.exit(1)
        from agent_worker import main as worker_main
        sys.argv = ["agent_worker", "parallel"] + sys.argv[2:]
        worker_main()
    
    elif cmd == "retry":
        # Retry a failed job
        if len(sys.argv) < 3:
            print("Usage: jobs retry <job_id>")
            sys.exit(1)
        from agent_worker import main as worker_main
        sys.argv = ["agent_worker", "retry"] + sys.argv[2:]
        worker_main()
    
    elif cmd == "notify":
        # Send notification
        if len(sys.argv) < 3:
            print("Usage: jobs notify <message> [level]")
            print("Levels: info, warning, error, urgent")
            sys.exit(1)
        from agent_worker import main as worker_main
        sys.argv = ["agent_worker", "notify"] + sys.argv[2:]
        worker_main()
    
    elif cmd == "auto":
        # Auto-worker daemon or single check
        from auto_worker import run_auto_worker, run_single_check
        if len(sys.argv) > 2 and sys.argv[2] == "--daemon":
            run_auto_worker()
        else:
            run_single_check()
    
    elif cmd == "coordinator":
        # Mac auto-coordinator - aggressive workflow pusher
        from coordinator import run_coordinator, run_single_push
        if len(sys.argv) > 2 and sys.argv[2] == "--daemon":
            run_coordinator()
        else:
            run_single_push()
    
    elif cmd == "poll":
        # Agent auto-poller - agents actively query for work
        from agent_poller import start_agent_pollers, run_single_poll_cycle
        if len(sys.argv) > 2 and sys.argv[2] == "--daemon":
            start_agent_pollers()
        else:
            run_single_poll_cycle()
    
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