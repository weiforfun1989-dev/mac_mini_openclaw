#!/usr/bin/env python3
"""
Workflow Automation for Job Dispatch
Handles agent handoffs, auto-completion sub-jobs, and status tracking.
"""

import json
import sys
from pathlib import Path

# Import jobs module
sys.path.insert(0, str(Path(__file__).parent))
from jobs import (
    load_db, save_db, get_job, create_job, complete_job, 
    assign_job, get_pending_for_agent, check_parent_completion
)

AGENTS = {
    "glitch": "Glitch",
    "research": "Research", 
    "sage": "Research",  # alias
    "planning": "Planning",
    "atlas": "Planning",  # alias
    "mac": "Mac"
}

def dispatch_to_agent(job_id, agent_key):
    """Dispatch a job to a specific agent."""
    agent_name = AGENTS.get(agent_key.lower(), agent_key)
    db = load_db()
    job = get_job(db, job_id)
    
    if not job:
        print(f"❌ Job #{job_id} not found")
        return False
    
    assign_job(job_id, agent_name)
    print(f"📤 Dispatched job #{job_id} to {agent_name}")
    print(f"   Task: {job['description'][:60]}...")
    return True

def agent_complete_and_notify(agent_key, job_id, summary, needs_clarification=False):
    """
    Agent completes work and auto-creates a sub-job back to Mac.
    This implements the workflow rule: agents always report back to Mac.
    """
    agent_name = AGENTS.get(agent_key.lower(), agent_key)
    db = load_db()
    job = get_job(db, job_id)
    
    if not job:
        print(f"❌ Job #{job_id} not found")
        return False
    
    # Mark original job as complete
    notes = "Needs clarification: " + summary if needs_clarification else summary
    complete_job(job_id, notes)
    
    # Find the main job (root parent)
    main_job_id = job_id
    while True:
        j = get_job(db, main_job_id)
        if not j or not j.get("parent_id"):
            break
        main_job_id = j["parent_id"]
    
    # Create completion sub-job to Mac
    if needs_clarification:
        desc = f"⚠️ {agent_name} needs clarification on #{main_job_id}: {summary}"
    else:
        desc = f"✅ {agent_name} complete for #{main_job_id}: {summary}"
    
    sub_id = create_job(desc, parent_id=main_job_id, assigned_to="Mac")
    
    print(f"\n🔄 Workflow handoff complete:")
    print(f"   • {agent_name} finished job #{job_id}")
    print(f"   • Auto-created sub-job #{sub_id} for Mac")
    print(f"   • Mac will decide next steps")
    
    return sub_id

def mac_evaluate_and_route(sub_job_id):
    """
    Mac evaluates a completion sub-job and routes to next agent or completes.
    This is called when Mac receives a completion sub-job.
    """
    db = load_db()
    sub_job = get_job(db, sub_job_id)
    
    if not sub_job:
        print(f"❌ Sub-job #{sub_job_id} not found")
        return False
    
    if sub_job["assigned_to"] != "Mac":
        print(f"⚠️  Job #{sub_job_id} is not assigned to Mac")
        return False
    
    desc = sub_job["description"].lower()
    parent_id = sub_job["parent_id"]
    
    print(f"\n📋 Mac evaluating sub-job #{sub_job_id}:")
    print(f"   {sub_job['description'][:70]}...")
    
    # Check if clarification is needed
    if "clarification" in desc or "⚠️" in sub_job["description"]:
        print(f"\n⚠️  CLARIFICATION NEEDED from user")
        print(f"   Job #{parent_id} needs user input before proceeding")
        return "CLARIFICATION_NEEDED"
    
    # Check if research is complete → route to planning or coding
    if "research complete" in desc:
        print(f"\n💡 Research done. Next step: Planning or Coding?")
        print(f"   Option 1: jobs workflow route {parent_id} planning")
        print(f"   Option 2: jobs workflow route {parent_id} coding")
        return "NEEDS_ROUTING"
    
    # Check if planning is complete → route to coding
    if "planning complete" in desc:
        print(f"\n💡 Planning done. Next step: Coding")
        print(f"   Run: jobs workflow route {parent_id} coding")
        return "NEEDS_ROUTING"
    
    # Check if coding is complete
    if "coding complete" in desc:
        print(f"\n✅ Coding complete!")
        print(f"   All work done for job #{parent_id}")
        print(f"   Run: jobs complete {parent_id}")
        return "READY_TO_COMPLETE"
    
    print(f"\n🤔 Unclear next step. Manual review needed.")
    return "UNCLEAR"

def route_to_next_agent(main_job_id, next_agent_key):
    """Route a main job to the next agent in the workflow."""
    agent_name = AGENTS.get(next_agent_key.lower(), next_agent_key)
    db = load_db()
    main_job = get_job(db, main_job_id)
    
    if not main_job:
        print(f"❌ Job #{main_job_id} not found")
        return False
    
    # Create sub-job for the next agent
    desc = f"{agent_name} task for: {main_job['description'][:50]}"
    sub_id = create_job(desc, parent_id=main_job_id, assigned_to=agent_name)
    
    print(f"📤 Created sub-job #{sub_id} for {agent_name}")
    print(f"   Part of main job #{main_job_id}")
    
    return sub_id

def show_dashboard():
    """Show workflow dashboard with all active jobs."""
    db = load_db()
    jobs = db["jobs"]
    
    # Get main jobs (no parent)
    main_jobs = [j for j in jobs if j["parent_id"] is None]
    
    if not main_jobs:
        print("\n📊 No active jobs.")
        return
    
    print("\n" + "="*70)
    print("📊 JOB DISPATCH DASHBOARD")
    print("="*70)
    
    for main in main_jobs:
        # Calculate progress
        sub_count = len(main["sub_jobs"])
        if sub_count > 0:
            done_count = sum(1 for sid in main["sub_jobs"] 
                           if get_job(db, sid) and get_job(db, sid)["status"] == "DONE")
            progress = f"[{done_count}/{sub_count}]"
        else:
            progress = "[0/0]"
        
        status_icon = "✅" if main["status"] == "DONE" else "🔄" if main["status"] == "IN_PROGRESS" else "⏳"
        
        print(f"\n{status_icon} Job #{main['id']}: {main['description'][:50]}")
        print(f"   Status: {main['status']} | Progress: {progress}")
        
        if main["sub_jobs"]:
            print(f"   Sub-jobs:")
            for sub_id in main["sub_jobs"]:
                sub = get_job(db, sub_id)
                if sub:
                    icon = "✅" if sub["status"] == "DONE" else "🔄"
                    print(f"     {icon} #{sub_id} [{sub['assigned_to']}] {sub['description'][:40]}")
    
    print("\n" + "="*70)

def main():
    if len(sys.argv) < 2:
        print("Workflow Automation Commands:")
        print("\n  jobs workflow dispatch <job_id> <agent>   - Dispatch job to agent")
        print("  jobs workflow complete <agent> <job_id> <summary>  - Agent completes job")
        print("  jobs workflow clarify <agent> <job_id> <question>  - Agent needs clarification")
        print("  jobs workflow evaluate <sub_job_id>       - Mac evaluates completion")
        print("  jobs workflow route <main_job_id> <agent> - Route to next agent")
        print("  jobs workflow dashboard                   - Show dashboard view")
        sys.exit(1)
    
    # Handle both direct calls and calls from jobs.py
    # Direct: python workflow.py dashboard
    # From jobs: jobs workflow dashboard -> sys.argv = ["workflow", "dashboard", ...]
    if sys.argv[0] == "workflow" or sys.argv[0].endswith("workflow.py"):
        # Called directly or from jobs.py with shifted args
        offset = 1
    else:
        # Called as: python workflow.py workflow dashboard
        offset = 2
    
    cmd = sys.argv[offset] if len(sys.argv) > offset else sys.argv[1]
    
    if cmd == "dashboard":
        show_dashboard()
    
    elif cmd == "dispatch":
        if len(sys.argv) < offset + 3:
            print("Usage: jobs workflow dispatch <job_id> <agent>")
            sys.exit(1)
        dispatch_to_agent(int(sys.argv[offset + 1]), sys.argv[offset + 2])
    
    elif cmd == "complete":
        if len(sys.argv) < offset + 4:
            print("Usage: jobs workflow complete <agent> <job_id> <summary>")
            sys.exit(1)
        summary = " ".join(sys.argv[offset + 3:])
        agent_complete_and_notify(sys.argv[offset + 1], int(sys.argv[offset + 2]), summary)
    
    elif cmd == "clarify":
        if len(sys.argv) < offset + 4:
            print("Usage: jobs workflow clarify <agent> <job_id> <question>")
            sys.exit(1)
        question = " ".join(sys.argv[offset + 3:])
        agent_complete_and_notify(sys.argv[offset + 1], int(sys.argv[offset + 2]), question, needs_clarification=True)
    
    elif cmd == "evaluate":
        if len(sys.argv) < offset + 2:
            print("Usage: jobs workflow evaluate <sub_job_id>")
            sys.exit(1)
        mac_evaluate_and_route(int(sys.argv[offset + 1]))
    
    elif cmd == "route":
        if len(sys.argv) < offset + 3:
            print("Usage: jobs workflow route <main_job_id> <agent>")
            sys.exit(1)
        route_to_next_agent(int(sys.argv[offset + 1]), sys.argv[offset + 2])
    
    else:
        print(f"Unknown workflow command: {cmd}")

if __name__ == "__main__":
    main()