#!/usr/bin/env python3
"""
Agent Worker - Automates job processing for agents
Simulates agents taking jobs from queue and completing them.
"""

import json
import sys
import time
import random
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from jobs import load_db, save_db, get_job, complete_job, assign_job
from workflow import create_job, AGENTS

JOBS_DB = Path("/Users/wxia/.openclaw/workspace/jobs/jobs-db.json")

# Simulated agent responses for auto-completion
AGENT_RESPONSES = {
    "research": [
        "Analyzed 10 sources and identified key trends",
        "Found 5 relevant case studies with implementation details",
        "Researched competitor strategies and best practices",
        "Gathered market data and user feedback summary",
        "Completed technical feasibility analysis"
    ],
    "planning": [
        "Created detailed roadmap with 4 milestones",
        "Designed system architecture and data flow",
        "Defined project scope and resource requirements",
        "Built task breakdown with timeline estimates",
        "Prepared implementation strategy document"
    ],
    "glitch": [
        "Implemented core functionality with tests",
        "Built frontend components and API integration",
        "Refactored code and optimized performance",
        "Fixed bugs and added error handling",
        "Deployed to staging environment"
    ],
    "mac": [
        "Reviewed and approved deliverables",
        "Coordinated next phase with team",
        "Validated requirements are met",
        "Updated project documentation"
    ]
}

def get_agent_pending_jobs(agent_name, db=None):
    """Get all pending jobs for an agent."""
    if db is None:
        db = load_db()
    agent_lower = agent_name.lower()
    return [j for j in db["jobs"] 
            if j["assigned_to"].lower() == agent_lower 
            and j["status"] != "DONE"]

def claim_job(job_id, agent_name):
    """Agent claims a job to work on."""
    db = load_db()
    job = get_job(db, job_id)
    
    if not job:
        print(f"❌ Job #{job_id} not found")
        return False
    
    if job["status"] == "DONE":
        print(f"⚠️  Job #{job_id} is already completed")
        return False
    
    if job["assigned_to"].lower() != agent_name.lower():
        print(f"⚠️  Job #{job_id} is assigned to {job['assigned_to']}, not {agent_name}")
        return False
    
    job["status"] = "IN_PROGRESS"
    job["claimed_at"] = datetime.now().isoformat()
    job["claimed_by"] = agent_name
    save_db(db)
    
    print(f"🔨 {agent_name} claimed job #{job_id}")
    print(f"   Working on: {job['description'][:60]}")
    return True

def simulate_agent_work(agent_name, job_id=None, auto_complete=False):
    """
    Simulate an agent taking a job from their queue.
    If job_id is None, takes the oldest pending job.
    Includes context from previous agent work on the same main task.
    """
    db = load_db()
    pending = get_agent_pending_jobs(agent_name, db)
    
    if not pending:
        print(f"📭 {agent_name} has no pending jobs")
        return None
    
    # Get the job to work on
    if job_id:
        job = get_job(db, job_id)
        if not job or job["assigned_to"].lower() != agent_name.lower():
            print(f"❌ Job #{job_id} not found or not assigned to {agent_name}")
            return None
    else:
        # Take oldest pending job
        job = sorted(pending, key=lambda x: x["id"])[0]
        job_id = job["id"]
    
    # Claim the job
    claim_job(job_id, agent_name)
    
    # Gather context from previous agent work on the same main task
    context = []
    if job.get("parent_id"):
        parent_id = job["parent_id"]
        # Find all completed sibling sub-jobs
        sibling_jobs = [j for j in db["jobs"] 
                       if j.get("parent_id") == parent_id 
                       and j["id"] != job_id
                       and j["status"] == "DONE"]
        
        # Look for Research completions (useful for Planning)
        agent_lower = agent_name.lower()
        if agent_lower == "planning":
            research_completions = [j for j in sibling_jobs 
                                   if "research complete" in j["description"].lower()]
            if research_completions:
                context.append("📚 Previous Research Results:")
                for rj in research_completions:
                    # Extract the summary part after the colon
                    desc = rj["description"]
                    if ":" in desc:
                        summary = desc.split(":", 1)[1].strip()
                        context.append(f"   • {summary[:80]}")
        
        # Look for Planning completions (useful for Glitch)
        elif agent_lower == "glitch":
            planning_completions = [j for j in sibling_jobs 
                                   if "planning complete" in j["description"].lower()]
            if planning_completions:
                context.append("📋 Previous Planning Results:")
                for pj in planning_completions:
                    desc = pj["description"]
                    if ":" in desc:
                        summary = desc.split(":", 1)[1].strip()
                        context.append(f"   • {summary[:80]}")
    
    if context:
        print("   📖 Context from previous work:")
        for line in context:
            print(f"   {line}")
    
    print(f"   ⏳ Processing...")
    
    if auto_complete:
        # Simulate work time
        time.sleep(0.5)
        
        # Generate completion response with context awareness
        agent_key = agent_name.lower()
        if agent_key in AGENT_RESPONSES:
            base_response = random.choice(AGENT_RESPONSES[agent_key])
        else:
            base_response = "Task completed successfully"
        
        # Add context reference to the response if available
        if context and agent_key == "planning":
            response = f"Based on research findings: {base_response}"
        elif context and agent_key == "glitch":
            response = f"Following the plan: {base_response}"
        else:
            response = base_response
        
        # Complete the job and create sub-job to Mac
        from workflow import agent_complete_and_notify
        agent_complete_and_notify(agent_name, job_id, response)
        
        print(f"   ✅ Completed! Created sub-job for Mac to review.")
    else:
        print(f"   📝 Run with --complete to finish: jobs agent work {agent_name} {job_id} --complete")
    
    return job_id

def process_agent_queue(agent_name, auto=False):
    """Process all pending jobs in agent's queue."""
    db = load_db()
    pending = get_agent_pending_jobs(agent_name, db)
    
    if not pending:
        print(f"📭 {agent_name} has no pending jobs")
        return 0
    
    print(f"\n🔍 {agent_name} checking queue...")
    print(f"   Found {len(pending)} pending job(s)")
    
    processed = 0
    for job in sorted(pending, key=lambda x: x["id"]):
        print(f"\n📋 Processing job #{job['id']}: {job['description'][:50]}")
        
        if auto:
            simulate_agent_work(agent_name, job["id"], auto_complete=True)
            processed += 1
            time.sleep(0.3)  # Brief pause between jobs
        else:
            print(f"   Run: jobs agent work {agent_name} {job['id']} --complete")
    
    if auto:
        print(f"\n✅ {agent_name} processed {processed} job(s)")
    else:
        print(f"\n💡 Run with --auto to complete all: jobs agent process {agent_name} --auto")
    
    return processed

def show_agent_status(agent_name):
    """Show detailed status of what an agent is working on."""
    db = load_db()
    agent_jobs = [j for j in db["jobs"] 
                  if j["assigned_to"].lower() == agent_name.lower()]
    
    if not agent_jobs:
        print(f"\n📭 {agent_name} has no jobs")
        return
    
    pending = [j for j in agent_jobs if j["status"] != "DONE"]
    in_progress = [j for j in agent_jobs if j["status"] == "IN_PROGRESS"]
    completed = [j for j in agent_jobs if j["status"] == "DONE"]
    
    print(f"\n{'='*60}")
    print(f"🤖 {agent_name.upper()} AGENT STATUS")
    print(f"{'='*60}")
    
    print(f"\n📊 QUEUE SUMMARY")
    print(f"   🔄 Currently working: {len(in_progress)}")
    print(f"   ⏳ Pending: {len(pending) - len(in_progress)}")
    print(f"   ✅ Completed: {len(completed)}")
    print(f"   📊 Total assigned: {len(agent_jobs)}")
    
    if in_progress:
        print(f"\n🔨 IN PROGRESS")
        for job in in_progress:
            print(f"   #{job['id']}: {job['description'][:55]}")
            if job.get('claimed_at'):
                print(f"      Claimed: {job['claimed_at'][:19]}")
    
    if pending and len(pending) > len(in_progress):
        print(f"\n⏳ PENDING QUEUE ({len(pending) - len(in_progress)})")
        for job in sorted(pending, key=lambda x: x["id"]):
            if job["status"] != "IN_PROGRESS":
                print(f"   #{job['id']}: {job['description'][:55]}")

def auto_dispatch_from_mac():
    """
    Mac reviews completion sub-jobs and auto-routes to next agent.
    This simulates Mac's coordination role.
    """
    db = load_db()
    
    # Find sub-jobs assigned to Mac that need evaluation
    mac_jobs = [j for j in db["jobs"] 
                if j["assigned_to"].lower() == "mac" 
                and j["status"] != "DONE"]
    
    if not mac_jobs:
        print("📭 Mac has no jobs to evaluate")
        return
    
    print(f"\n🧠 Mac evaluating {len(mac_jobs)} job(s)...")
    
    for job in mac_jobs:
        desc_lower = job["description"].lower()
        parent_id = job.get("parent_id")
        
        print(f"\n📋 Evaluating job #{job['id']}: {job['description'][:50]}")
        
        # Mark as evaluated
        job["status"] = "DONE"
        job["notes"] = "Auto-evaluated and routed"
        save_db(db)  # Save immediately after marking done
        
        # Determine next agent based on completion type
        next_agent = None
        
        if "research complete" in desc_lower:
            next_agent = "Planning"
            print(f"   💡 Research done → Routing to Planning")
        elif "planning complete" in desc_lower:
            next_agent = "Glitch"
            print(f"   💡 Planning done → Routing to Glitch")
        elif "coding complete" in desc_lower or "glitch complete" in desc_lower:
            print(f"   ✅ Coding complete! Marking main job done.")
            # Could mark main job as complete here
        elif "clarification" in desc_lower or "⚠️" in job["description"]:
            print(f"   ⚠️  Clarification needed - requires human review")
            job["notes"] = "NEEDS_CLARIFICATION"
            save_db(db)
        else:
            print(f"   🤔 Unclear next step - manual routing needed")
            continue
        
        if next_agent and parent_id:
            # Create sub-job for next agent
            from workflow import route_to_next_agent
            new_job_id = route_to_next_agent(parent_id, next_agent)
            print(f"   📤 Created job #{new_job_id} for {next_agent}")
            # Reload db to get updated state
            db = load_db()
    
    print(f"\n✅ Mac evaluation complete")

def main():
    if len(sys.argv) < 2:
        print("Agent Worker Commands:")
        print("\n  jobs agent status <name>           - Show agent's current status")
        print("  jobs agent work <name> [id] [--complete]  - Agent takes a job")
        print("  jobs agent process <name> [--auto] - Process all pending jobs")
        print("  jobs agent dispatch               - Mac auto-routes completed jobs")
        print("\nAgents: Mac, Glitch, Research, Planning")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "status":
        if len(sys.argv) < 3:
            print("Usage: jobs agent status <agent_name>")
            sys.exit(1)
        show_agent_status(sys.argv[2])
    
    elif cmd == "work":
        if len(sys.argv) < 3:
            print("Usage: jobs agent work <agent_name> [job_id] [--complete]")
            sys.exit(1)
        agent = sys.argv[2]
        job_id = None
        auto_complete = False
        
        for arg in sys.argv[3:]:
            if arg == "--complete":
                auto_complete = True
            elif arg.isdigit():
                job_id = int(arg)
        
        simulate_agent_work(agent, job_id, auto_complete)
    
    elif cmd == "process":
        if len(sys.argv) < 3:
            print("Usage: jobs agent process <agent_name> [--auto]")
            sys.exit(1)
        agent = sys.argv[2]
        auto = "--auto" in sys.argv
        process_agent_queue(agent, auto)
    
    elif cmd == "dispatch":
        auto_dispatch_from_mac()
    
    else:
        print(f"Unknown agent command: {cmd}")

if __name__ == "__main__":
    main()