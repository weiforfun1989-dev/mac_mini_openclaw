#!/usr/bin/env python3
"""
Auto-Worker Daemon - Automatically triggers agents to work on jobs
Runs continuously in background, checking for pending work every N seconds.
"""

import json
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jobs import load_db, get_job, save_db
from agent_worker import simulate_agent_work, process_parallel_jobs

# Configuration
CHECK_INTERVAL = 10  # seconds between checks
MAX_CONCURRENT_PER_AGENT = 1  # Only 1 task at a time per agent
AGENTS = ["Mac", "Glitch", "Research", "Planning"]

# Track which agents are currently working (to prevent duplicate triggers)
working_agents = {}
agent_lock = threading.Lock()

def get_agent_workload(agent_name):
    """Get current workload stats for an agent."""
    db = load_db()
    agent_jobs = [j for j in db["jobs"] if j["assigned_to"].lower() == agent_name.lower()]
    
    in_progress = [j for j in agent_jobs if j["status"] == "IN_PROGRESS"]
    pending = [j for j in agent_jobs if j["status"] == "TODO"]
    
    return {
        "in_progress": len(in_progress),
        "pending": len(pending),
        "jobs": pending[:MAX_CONCURRENT_PER_AGENT]  # next jobs to process
    }

def check_deadlocks():
    """
    Check for potential deadlocks:
    1. Jobs stuck in IN_PROGRESS for too long (no heartbeat)
    2. Circular dependencies (not applicable yet without DAG)
    3. All agents idle but work remaining (coordination failure)
    """
    db = load_db()
    deadlocks = []
    
    # Check 1: Jobs stuck in progress > 30 min without completion
    for job in db["jobs"]:
        if job["status"] == "IN_PROGRESS":
            started = job.get("started_at")
            if started:
                started_time = datetime.fromisoformat(started)
                elapsed = (datetime.now() - started_time).total_seconds() / 60
                
                # If in progress > 30 min, likely stuck
                if elapsed > 30:
                    deadlocks.append({
                        "type": "stuck_job",
                        "job_id": job["id"],
                        "agent": job["assigned_to"],
                        "elapsed_minutes": round(elapsed, 1)
                    })
    
    # Check 2: All agents idle but TODO jobs exist
    all_agents_idle = True
    for agent in AGENTS:
        workload = get_agent_workload(agent)
        if workload["in_progress"] > 0:
            all_agents_idle = False
            break
    
    total_todo = len([j for j in db["jobs"] if j["status"] == "TODO"])
    
    if all_agents_idle and total_todo > 0:
        deadlocks.append({
            "type": "coordination_failure",
            "message": f"All agents idle but {total_todo} TODO jobs exist"
        })
    
    return deadlocks

def auto_trigger_agent(agent_name):
    """Automatically trigger an agent to work on pending jobs."""
    with agent_lock:
        if working_agents.get(agent_name, False):
            return  # Already working
        working_agents[agent_name] = True
    
    try:
        workload = get_agent_workload(agent_name)
        
        if workload["pending"] == 0:
            return
        
        # Skip if already at max concurrent
        if workload["in_progress"] >= MAX_CONCURRENT_PER_AGENT:
            return
        
        print(f"\n🤖 Auto-triggering {agent_name}")
        print(f"   Pending: {workload['pending']}, In Progress: {workload['in_progress']}")
        
        # Process up to available slots
        available_slots = MAX_CONCURRENT_PER_AGENT - workload["in_progress"]
        jobs_to_process = workload["jobs"][:available_slots]
        
        if len(jobs_to_process) == 1:
            # Single job - use sequential processing
            job = jobs_to_process[0]
            print(f"   Processing job #{job['id']}")
            simulate_agent_work(agent_name, job["id"], auto_complete=True)
        elif len(jobs_to_process) > 1:
            # Multiple jobs - use parallel processing
            print(f"   Processing {len(jobs_to_process)} jobs in parallel")
            process_parallel_jobs(agent_name, 
                                job_ids=[j["id"] for j in jobs_to_process], 
                                auto_complete=True)
        
    finally:
        with agent_lock:
            working_agents[agent_name] = False

def auto_dispatch_mac():
    """Auto-trigger Mac to dispatch completed jobs."""
    db = load_db()
    
    # Find completion sub-jobs assigned to Mac
    mac_jobs = [j for j in db["jobs"] 
                if j["assigned_to"].lower() == "mac" 
                and j["status"] == "TODO"
                and ("complete" in j["description"].lower() or 
                     "escalation" in j["description"].lower() or
                     "notification" in j["description"].lower())]
    
    if len(mac_jobs) >= 3:  # Dispatch when 3+ jobs queued
        print(f"\n🧠 Auto-dispatching Mac ({len(mac_jobs)} jobs to evaluate)")
        from agent_worker import auto_dispatch_from_mac
        auto_dispatch_from_mac()

def run_auto_worker():
    """Main loop for auto-worker daemon."""
    print("="*60)
    print("🤖 AUTO-WORKER DAEMON STARTED")
    print("="*60)
    print(f"Check interval: {CHECK_INTERVAL} seconds")
    print(f"Max concurrent per agent: {MAX_CONCURRENT_PER_AGENT}")
    print(f"Agents: {', '.join(AGENTS)}")
    print("\nPress Ctrl+C to stop\n")
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            print(f"\n--- Check #{iteration} at {datetime.now().strftime('%H:%M:%S')} ---")
            
            # Check for deadlocks first
            deadlocks = check_deadlocks()
            if deadlocks:
                print("\n⚠️  DEADLOCKS DETECTED:")
                for d in deadlocks:
                    if d["type"] == "stuck_job":
                        print(f"   Stuck job #{d['job_id']} ({d['agent']}) - {d['elapsed_minutes']} min")
                    elif d["type"] == "coordination_failure":
                        print(f"   {d['message']}")
            
            # Auto-dispatch Mac if needed
            auto_dispatch_mac()
            
            # Auto-trigger each agent
            for agent in AGENTS:
                if agent.lower() != "mac":  # Mac is triggered separately
                    workload = get_agent_workload(agent)
                    if workload["pending"] > 0 and workload["in_progress"] < MAX_CONCURRENT_PER_AGENT:
                        # Run in thread so agents work in parallel
                        t = threading.Thread(target=auto_trigger_agent, args=(agent,))
                        t.start()
                        time.sleep(0.5)  # Brief stagger
            
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n👋 Auto-worker stopped")

def run_single_check():
    """Run one check cycle (for manual triggering)."""
    print("\n" + "="*60)
    print("🤖 SINGLE AUTO-WORKER CHECK")
    print("="*60)
    
    # Check deadlocks
    deadlocks = check_deadlocks()
    if deadlocks:
        print("\n⚠️  DEADLOCKS DETECTED:")
        for d in deadlocks:
            if d["type"] == "stuck_job":
                print(f"   Stuck job #{d['job_id']} ({d['agent']}) - {d['elapsed_minutes']} min")
            elif d["type"] == "coordination_failure":
                print(f"   {d['message']}")
    else:
        print("\n✅ No deadlocks detected")
    
    # Dispatch Mac
    auto_dispatch_mac()
    
    # Trigger agents
    for agent in AGENTS:
        if agent.lower() != "mac":
            workload = get_agent_workload(agent)
            if workload["pending"] > 0:
                print(f"\n{agent}: {workload['pending']} pending, {workload['in_progress']} in progress")
                if workload["in_progress"] < MAX_CONCURRENT_PER_AGENT:
                    auto_trigger_agent(agent)
                else:
                    print(f"   At max capacity, skipping")
    
    print("\n✅ Check complete")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        run_auto_worker()
    elif len(sys.argv) > 1 and sys.argv[1] == "--check":
        run_single_check()
    else:
        print("Auto-Worker Commands:")
        print("\n  jobs auto --daemon    - Run continuous auto-worker")
        print("  jobs auto --check     - Run single check cycle")
        print("\nConfiguration:")
        print(f"  Check interval: {CHECK_INTERVAL}s")
        print(f"  Max concurrent: {MAX_CONCURRENT_PER_AGENT}")
