#!/usr/bin/env python3
"""
Mac Auto-Coordinator - Aggressive workflow pusher
Continuously monitors and pushes all agents to complete jobs
"""

import json
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jobs import load_db, save_db, get_job
from agent_worker import (
    simulate_agent_work, process_parallel_jobs, 
    auto_dispatch_from_mac, get_agent_pending_jobs
)

# Configuration
CHECK_INTERVAL = 5  # seconds - frequent checks
MAX_WORKERS = 1  # Only 1 task in progress per agent at a time
AGENTS = ["Research", "Planning", "Glitch"]  # Work agents (not Mac)

# Thread tracking
active_threads = {}
thread_lock = threading.Lock()

def is_agent_busy(agent_name):
    """Check if agent is currently at max capacity."""
    db = load_db()
    agent_jobs = [j for j in db["jobs"] 
                  if j["assigned_to"].lower() == agent_name.lower()]
    in_progress = len([j for j in agent_jobs if j["status"] == "IN_PROGRESS"])
    return in_progress >= MAX_WORKERS

def get_agent_capacity(agent_name):
    """Get available slots for an agent."""
    db = load_db()
    agent_jobs = [j for j in db["jobs"] 
                  if j["assigned_to"].lower() == agent_name.lower()]
    in_progress = len([j for j in agent_jobs if j["status"] == "IN_PROGRESS"])
    return max(0, MAX_WORKERS - in_progress)

def push_agent_work(agent_name):
    """Force an agent to process their pending jobs."""
    with thread_lock:
        if active_threads.get(agent_name, False):
            return  # Already have a thread for this agent
        active_threads[agent_name] = True
    
    try:
        capacity = get_agent_capacity(agent_name)
        if capacity == 0:
            return
        
        db = load_db()
        pending = get_agent_pending_jobs(agent_name, db)
        
        if not pending:
            return
        
        jobs_to_process = pending[:capacity]
        
        print(f"\n🔥 PUSHING {agent_name}: {len(jobs_to_process)} job(s)")
        
        if len(jobs_to_process) == 1:
            simulate_agent_work(agent_name, jobs_to_process[0]["id"], auto_complete=True)
        else:
            process_parallel_jobs(agent_name, 
                                job_ids=[j["id"] for j in jobs_to_process], 
                                auto_complete=True)
        
        print(f"✅ {agent_name} batch complete")
        
    finally:
        with thread_lock:
            active_threads[agent_name] = False

def push_mac_dispatch():
    """Force Mac to dispatch all queued completions."""
    db = load_db()
    
    # Count Mac's TODO jobs (completion sub-jobs)
    mac_todo = [j for j in db["jobs"] 
                if j["assigned_to"].lower() == "mac" 
                and j["status"] == "TODO"]
    
    if len(mac_todo) >= 2:  # Dispatch when 2+ jobs queued
        print(f"\n🧠 PUSHING Mac: Dispatching {len(mac_todo)} completions")
        auto_dispatch_from_mac()
        return True
    return False

def fix_stuck_jobs():
    """Auto-fix jobs stuck in IN_PROGRESS with completed_at set."""
    db = load_db()
    fixed = 0
    
    for job in db["jobs"]:
        if job["status"] == "IN_PROGRESS" and job.get("completed_at"):
            job["status"] = "DONE"
            fixed += 1
    
    if fixed > 0:
        save_db(db)
        print(f"\n🔧 Fixed {fixed} stuck jobs")
    
    return fixed

def coordinator_cycle():
    """One complete coordination cycle."""
    print(f"\n{'='*60}")
    print(f"🎯 COORDINATOR CYCLE - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    # Step 1: Fix any stuck jobs
    fix_stuck_jobs()
    
    # Step 2: Push Mac to dispatch
    mac_dispatched = push_mac_dispatch()
    
    # Step 3: Push all work agents in parallel threads
    threads = []
    for agent in AGENTS:
        capacity = get_agent_capacity(agent)
        if capacity > 0:
            db = load_db()
            pending = get_agent_pending_jobs(agent, db)
            if pending:
                t = threading.Thread(target=push_agent_work, args=(agent,))
                threads.append(t)
                t.start()
                time.sleep(0.3)  # Stagger starts
    
    # Wait for all agents
    for t in threads:
        t.join(timeout=60)  # 60 second timeout per cycle
    
    # Print status
    db = load_db()
    total = len(db["jobs"])
    done = len([j for j in db["jobs"] if j["status"] == "DONE"])
    in_prog = len([j for j in db["jobs"] if j["status"] == "IN_PROGRESS"])
    todo = len([j for j in db["jobs"] if j["status"] == "TODO"])
    
    print(f"\n📊 Status: {done}/{total} done ({round(done/total*100)}%) | " +
          f"In Progress: {in_prog} | TODO: {todo}")
    
    return done, total

def run_coordinator():
    """Main coordinator loop - runs until all jobs done."""
    print("="*60)
    print("🚀 MAC AUTO-COORDINATOR STARTED")
    print("="*60)
    print(f"Check interval: {CHECK_INTERVAL}s")
    print(f"Max workers per agent: {MAX_WORKERS}")
    print("\nPress Ctrl+C to stop\n")
    
    cycle = 0
    
    try:
        while True:
            cycle += 1
            done, total = coordinator_cycle()
            
            # Check if complete
            if done == total:
                print(f"\n{'='*60}")
                print(f"🎉 ALL JOBS COMPLETE! {done}/{total}")
                print(f"{'='*60}")
                break
            
            # Check if stuck (no progress for many cycles)
            if cycle > 100:
                print(f"\n⚠️  Coordinator running long - checking for issues")
                cycle = 0
            
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n👋 Coordinator stopped")

def run_single_push():
    """Run one aggressive push cycle."""
    print("="*60)
    print("🚀 SINGLE COORDINATOR PUSH")
    print("="*60)
    
    coordinator_cycle()
    
    print("\n✅ Push complete")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        run_coordinator()
    else:
        run_single_push()
