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
    "research": "Sage",  # Changed from "Research"
    "sage": "Sage",
    "planning": "Atlas",  # Changed from "Planning"
    "atlas": "Atlas",
    "mac": "Mac"
}

AGENT_PREFIXES = {
    "research": "[Re]",
    "planning": "[Pl]",
    "glitch": "[Code]",
    "mac": "[Mac]"
}

AGENT_DISPLAY_NAMES = {
    "research": "Sage",
    "planning": "Atlas",
    "glitch": "Glitch",
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
    Agent completes work and workflow continues automatically.
    Instead of creating notification sub-jobs, we auto-route to next agent.
    Only creates Mac sub-job if clarification is needed.
    """
    agent_name = AGENTS.get(agent_key.lower(), agent_key)
    db = load_db()
    job = get_job(db, job_id)

    if not job:
        print(f"❌ Job #{job_id} not found")
        return False

    # Atomic check: don't re-complete already done jobs
    if job["status"] == "DONE":
        print(f"⚠️  Job #{job_id} already completed")
        return job.get("parent_id")

    # Mark original job as complete
    notes = "Needs clarification: " + summary if needs_clarification else summary
    complete_job(job_id, notes)

    # Reload DB after completion
    db = load_db()

    # Find the main job (root parent)
    main_job_id = job_id
    while True:
        j = get_job(db, main_job_id)
        if not j or not j.get("parent_id"):
            break
        main_job_id = j["parent_id"]

    agent_key_lower = agent_key.lower()
    display_name = AGENT_DISPLAY_NAMES.get(agent_key_lower, agent_name)
    prefix = AGENT_PREFIXES.get(agent_key_lower, "")

    # If needs clarification, create Mac sub-job
    if needs_clarification:
        desc = f"⚠️ {prefix} {display_name} needs clarification on #{main_job_id}: {summary}"
        sub_id = create_job(desc, parent_id=main_job_id, assigned_to="Mac")
        print(f"\n🔄 Workflow paused:")
        print(f"   • {display_name} needs clarification")
        print(f"   • Created sub-job #{sub_id} for Mac review")
        return sub_id

    # Auto-route to next agent based on who just completed
    print(f"\n🔄 {display_name} completed job #{job_id}")

    if agent_key_lower in ["research", "sage"]:
        # Auto-route to Atlas for planning - create sub-job
        print(f"   Auto-routing to Atlas for planning...")
        desc = f"[Pl] Design: Based on research from job #{job_id}"
        sub_id = create_job(desc, parent_id=main_job_id, assigned_to="Atlas")
        print(f"   Created planning sub-job #{sub_id}")
        return sub_id
    elif agent_key_lower in ["planning", "atlas"]:
        # Auto-route to Glitch for coding - create sub-job
        print(f"   Auto-routing to Glitch for implementation...")
        desc = f"[Code] Implement: Based on design from job #{job_id}"
        sub_id = create_job(desc, parent_id=main_job_id, assigned_to="Glitch")
        print(f"   Created implementation sub-job #{sub_id}")
        return sub_id
    elif agent_key_lower == "glitch":
        # All done - workflow complete
        print(f"   ✅ All work complete!")
        print(f"   Mac can mark main job #{main_job_id} as DONE")
        return main_job_id

    return main_job_id

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

AGENT_PREFIXES = {
    "research": "[Re]",
    "planning": "[Pl]",
    "glitch": "[Code]",
    "mac": "[Mac]"
}

def route_to_next_agent(main_job_id, next_agent_key):
    """Route a main job to the next agent in the workflow."""
    agent_name = AGENTS.get(next_agent_key.lower(), next_agent_key)
    db = load_db()
    main_job = get_job(db, main_job_id)

    if not main_job:
        print(f"❌ Job #{main_job_id} not found")
        return False

    # Check if job needs confirmation from user
    if main_job.get("needs_confirmation") and not main_job.get("confirmed"):
        print(f"⚠️  Job #{main_job_id} needs confirmation before dispatching")
        print(f"   Description: {main_job['description'][:60]}")
        print(f"   Run: jobs confirm {main_job_id}")
        return False

    # Create sub-job for the next agent with detailed description
    prefix = AGENT_PREFIXES.get(next_agent_key.lower(), "")
    display_name = AGENT_DISPLAY_NAMES.get(next_agent_key.lower(), agent_name)

    # Create detailed description based on agent type
    main_desc = main_job['description'][:40]
    if next_agent_key.lower() == "research":
        desc = f"{prefix} Research: '{main_desc}' - Search web sources, analyze findings, document results with URLs"
    elif next_agent_key.lower() == "planning":
        desc = f"{prefix} Design: '{main_desc}' - Create architecture, define components, write implementation plan"
    elif next_agent_key.lower() == "glitch":
        desc = f"{prefix} Implement: '{main_desc}' - Write code, add tests, commit to GitHub"
    else:
        desc = f"{prefix} {display_name} task for: {main_desc}"

    sub_id = create_job(desc, parent_id=main_job_id, assigned_to=agent_name)

    print(f"📤 Created sub-job #{sub_id} for {display_name}")
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