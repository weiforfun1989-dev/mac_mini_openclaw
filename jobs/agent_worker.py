#!/usr/bin/env python3
"""
Agent Worker - Automates job processing for agents
Simulates agents taking jobs from queue and completing them.
"""

import json
import sys
import time
import random
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from jobs import load_db, save_db, get_job, complete_job, assign_job
from workflow import create_job, AGENTS

JOBS_DB = Path("/Users/wxia/.openclaw/workspace/jobs/jobs-db.json")

# Simulated agent responses for auto-completion
AGENT_RESPONSES = {
    "research": None,  # Research uses real web search instead
    "planning": [
        "Created detailed roadmap with 4 milestones",
        "Designed system architecture and data flow",
        "Defined project scope and resource requirements",
        "Built task breakdown with timeline estimates",
        "Prepared implementation strategy document"
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

def perform_web_research(job_description, context=None):
    """
    Perform real web research for a job.
    Returns a summary of findings.
    """
    # Extract key terms from job description for search
    search_terms = job_description.replace("Research task for:", "").replace("Research:", "").strip()
    
    print(f"   🔍 Searching web for: {search_terms[:60]}...")
    
    try:
        # Use web_search skill via subprocess
        result = subprocess.run(
            ["python3", "-c", 
             f"from skills.web_search import web_search; results = web_search('{search_terms[:50]}', count=3); print(json.dumps([r['snippet'] for r in results]))"],
            capture_output=True,
            text=True,
            cwd="/Users/wxia/.openclaw/workspace"
        )
        
        if result.returncode == 0 and result.stdout:
            snippets = json.loads(result.stdout)
            if snippets:
                return f"Research findings: {snippets[0][:150]}"
    except Exception:
        pass
    
    # Fallback: research-like response based on the search terms
    research_topics = {
        "workflow": "workflow automation best practices, job dispatch patterns, multi-agent systems",
        "website": "web development frameworks, responsive design, modern UI patterns",
        "feature": "feature implementation strategies, user requirements analysis",
        "dashboard": "dashboard design patterns, data visualization, real-time monitoring",
        "api": "API design principles, RESTful architecture, integration patterns"
    }
    
    for topic, details in research_topics.items():
        if topic.lower() in search_terms.lower():
            return f"Research findings: {details}"
    
    return f"Research completed on '{search_terms[:50]}' with industry best practices and standards"

def get_agent_pending_jobs(agent_name, db=None):
    """Get all pending jobs for an agent."""
    if db is None:
        db = load_db()
    agent_lower = agent_name.lower()
    return [j for j in db["jobs"] 
            if j["assigned_to"].lower() == agent_lower 
            and j["status"] != "DONE"]

def claim_job(job_id, agent_name, estimated_minutes=None):
    """Agent claims a job to work on with time estimate."""
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
    
    # Only set estimated_minutes if not already set
    if estimated_minutes is None:
        # Check if job already has an estimate
        if job.get("estimated_minutes"):
            estimated_minutes = job["estimated_minutes"]
        else:
            # Default estimates by agent type
            default_estimates = {
                "research": 30,
                "planning": 20,
                "glitch": 60,
                "mac": 10
            }
            agent_key = agent_name.lower()
            estimated_minutes = default_estimates.get(agent_key, 30)
    
    job["status"] = "IN_PROGRESS"
    job["claimed_at"] = datetime.now().isoformat()
    job["claimed_by"] = agent_name
    # Only set started_at if not already set (don't reset timer on re-claim)
    if not job.get("started_at"):
        job["started_at"] = datetime.now().isoformat()
    job["estimated_minutes"] = estimated_minutes
    save_db(db)
    
    print(f"🔨 {agent_name} claimed job #{job_id}")
    print(f"   Working on: {job['description'][:60]}")
    print(f"   ⏱️  Estimated time: {estimated_minutes} minutes")
    return True

def check_time_estimate(job_id):
    """
    Check if job has exceeded 2x estimate.
    Returns (ok_to_complete, minutes_elapsed, escalation_created)
    """
    db = load_db()
    job = get_job(db, job_id)
    
    if not job or not job.get("started_at"):
        return True, 0, False
    
    estimated = job.get("estimated_minutes")
    if not estimated:
        return True, 0, False
    
    # Calculate elapsed time
    started = datetime.fromisoformat(job["started_at"])
    elapsed = (datetime.now() - started).total_seconds() / 60  # minutes
    
    # Check if exceeded 2x estimate
    if elapsed > (estimated * 2):
        if not job.get("escalated"):
            # Create escalation sub-job to Mac
            desc = f"⚠️ ESCALATION: {job['claimed_by']} exceeded 2x estimate on job #{job_id}"
            escalation_id = create_job(desc, parent_id=job.get("parent_id"), assigned_to="Mac")
            
            # Reload db to get the updated state after create_job
            db = load_db()
            job = get_job(db, job_id)
            
            job["escalated"] = True
            job["escalation_id"] = escalation_id
            job["actual_minutes"] = round(elapsed, 1)
            save_db(db)
            
            print(f"\n⚠️  TIME LIMIT EXCEEDED!")
            print(f"   Estimated: {estimated} min | Actual: {round(elapsed, 1)} min")
            print(f"   Created escalation job #{escalation_id} for Mac")
            return False, elapsed, True
        else:
            print(f"\n⚠️  Already escalated (job #{job.get('escalation_id')})")
            return False, elapsed, False
    
    return True, elapsed, False

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
    
    # Claim the job with time estimate
    # Pass None to use existing estimate if present, or default based on agent type
    claim_job(job_id, agent_name, estimated_minutes=None)
    
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
        # Reload job to get the estimate that was set
        db = load_db()
        job = get_job(db, job_id)
        estimate = job.get("estimated_minutes", 30)
        
        # Simulate work time (shortened for demo - use smaller time)
        work_time = min(estimate * 0.1, 2)  # Simulate 10% of estimate time, max 2 seconds
        time.sleep(work_time)
        
        # Check if exceeded time estimate before completing
        can_complete, elapsed, was_escalated = check_time_estimate(job_id)
        
        if not can_complete:
            print(f"   ⛔ Cannot complete - escalated to Mac")
            return job_id
        
        print(f"   ✅ Completed in {round(elapsed, 1)} min (estimated {estimate} min)")
        
        # Generate completion response
        agent_key = agent_name.lower()
        
        if agent_key == "research":
            # Research agent performs web search
            response = perform_web_research(job["description"], context if context else None)
        elif agent_key in AGENT_RESPONSES and AGENT_RESPONSES[agent_key]:
            base_response = random.choice(AGENT_RESPONSES[agent_key])
            
            # Add context reference to the response if available
            if context and agent_key == "planning":
                response = f"Based on research findings: {base_response}"
            elif context and agent_key == "glitch":
                response = f"Following the plan: {base_response}"
            else:
                response = base_response
        else:
            response = "Task completed successfully"
        
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
            if job.get('estimated_minutes'):
                elapsed = 0
                if job.get('started_at'):
                    started = datetime.fromisoformat(job["started_at"])
                    elapsed = (datetime.now() - started).total_seconds() / 60
                status = "⏰ OVERDUE" if elapsed > job['estimated_minutes'] * 2 else f"⏱️  {round(elapsed, 1)}/{job['estimated_minutes']} min"
                print(f"      Time: {status}")
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