#!/usr/bin/env python3
"""
Agent Auto-Poller - Agents actively query for work when idle
Each agent runs independently, checking their queue every N seconds
"""

import json
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jobs import load_db, get_job, save_db
from agent_worker import simulate_agent_work, get_agent_pending_jobs

# Configuration
POLL_INTERVAL = 5  # seconds between queue checks
AGENTS = ["Research", "Planning", "Glitch"]  # Work agents (Mac handles coordination)

# Track agent states
agent_threads = {}
agent_busy = {}
thread_lock = threading.Lock()

def is_agent_at_capacity(agent_name):
    """Check if agent is at max concurrent job limit."""
    db = load_db()
    agent_jobs = [j for j in db["jobs"] 
                  if j["assigned_to"].lower() == agent_name.lower()]
    in_progress = len([j for j in agent_jobs if j["status"] == "IN_PROGRESS"])
    return in_progress >= MAX_CONCURRENT_PER_AGENT

def agent_poll_loop(agent_name):
    """Continuous polling loop for an agent."""
    print(f"🤖 {agent_name} auto-poller started")
    
    while True:
        try:
            # Check if already at capacity
            if is_agent_at_capacity(agent_name):
                time.sleep(POLL_INTERVAL)
                continue
            
            # Check for pending work
            db = load_db()
            pending = get_agent_pending_jobs(agent_name, db)
            
            if pending:
                # Get next job
                next_job = pending[0]
                job_id = next_job["id"]
                
                print(f"\n🔔 {agent_name} found work: Job #{job_id}")
                print(f"   {next_job['description'][:60]}")
                
                # Do the work
                simulate_agent_work(agent_name, job_id, auto_complete=True)
                
                print(f"✅ {agent_name} completed job #{job_id}")
                
                # Brief pause before checking for more work
                time.sleep(1)
            else:
                # No work, sleep and poll again
                time.sleep(POLL_INTERVAL)
                
        except Exception as e:
            print(f"⚠️  {agent_name} error: {e}")
            time.sleep(POLL_INTERVAL)

def start_agent_pollers():
    """Start polling threads for all agents."""
    print("="*60)
    print("🤖 AGENT AUTO-POLLERS STARTED")
    print("="*60)
    print(f"Poll interval: {POLL_INTERVAL} seconds")
    print(f"Max concurrent per agent: {MAX_CONCURRENT_PER_AGENT}")
    print(f"Agents: {', '.join(AGENTS)}")
    print("\nPress Ctrl+C to stop\n")
    
    # Start a thread for each agent
    threads = []
    for agent in AGENTS:
        t = threading.Thread(target=agent_poll_loop, args=(agent,), daemon=True)
        t.start()
        threads.append(t)
        print(f"  ✅ {agent} poller started")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 Agent auto-pollers stopped")

def run_single_poll_cycle():
    """Run one poll cycle for all agents (for manual triggering)."""
    print("="*60)
    print("🤖 SINGLE POLL CYCLE")
    print("="*60)
    
    for agent in AGENTS:
        if is_agent_at_capacity(agent):
            print(f"\n{agent}: At capacity, skipping")
            continue
        
        db = load_db()
        pending = get_agent_pending_jobs(agent, db)
        
        if pending:
            job = pending[0]
            print(f"\n{agent}: Processing job #{job['id']}")
            simulate_agent_work(agent, job["id"], auto_complete=True)
        else:
            print(f"\n{agent}: No pending work")
    
    print("\n✅ Poll cycle complete")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        start_agent_pollers()
    else:
        run_single_poll_cycle()
