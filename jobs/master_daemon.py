#!/usr/bin/env python3
"""
Master Auto-Run Daemon - Runs the entire job dispatch system automatically
Combines agent pollers, Mac coordinator, and compaction service
"""

import json
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jobs import load_db
from agent_poller import start_agent_pollers
from coordinator import run_coordinator
from compact_service import compact_database

# Global control flag
running = True

def print_status():
    """Print current system status."""
    db = load_db()
    total = len(db['jobs'])
    done = len([j for j in db['jobs'] if j['status'] == 'DONE'])
    in_prog = len([j for j in db['jobs'] if j['status'] == 'IN_PROGRESS'])
    todo = len([j for j in db['jobs'] if j['status'] == 'TODO'])
    
    print(f"\n{'='*60}")
    print(f"📊 SYSTEM STATUS - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    print(f"Progress: {done}/{total} ({round(done/total*100)}%)")
    print(f"Active: {in_prog} | Queued: {todo}")
    
    # Agent status
    for agent in ['Mac', 'Glitch', 'Sage', 'Atlas']:
        jobs = [j for j in db['jobs'] if j['assigned_to'] == agent]
        in_p = len([j for j in jobs if j['status'] == 'IN_PROGRESS'])
        todo_a = len([j for j in jobs if j['status'] == 'TODO'])
        status = '🔴' if in_p > 0 else '🟢' if todo_a == 0 else '⏳'
        print(f"  {agent:8} {status} Active:{in_p} Queue:{todo_a}")

def master_daemon():
    """Master control daemon that runs all services."""
    print("="*60)
    print("🚀 MASTER AUTO-RUN DAEMON STARTED")
    print("="*60)
    print("\nThis daemon automatically:")
    print("  • Polls agents for work every 5 seconds")
    print("  • Coordinates Mac dispatch every 10 seconds")
    print("  • Compacts database every 24 hours")
    print("  • Shows status every 60 seconds")
    print("\nPress Ctrl+C to stop\n")
    
    # Start agent pollers in background thread
    poller_thread = threading.Thread(target=start_agent_pollers, daemon=True)
    poller_thread.start()
    print("✅ Agent pollers started")
    
    # Start coordinator in background thread
    coordinator_thread = threading.Thread(target=run_coordinator, daemon=True)
    coordinator_thread.start()
    print("✅ Mac coordinator started")
    
    last_status = 0
    last_compact = 0
    COMPACT_INTERVAL = 24 * 3600  # 24 hours
    STATUS_INTERVAL = 60  # 60 seconds
    
    try:
        while running:
            now = time.time()
            
            # Print status periodically
            if now - last_status > STATUS_INTERVAL:
                print_status()
                last_status = now
            
            # Compact database periodically
            if now - last_compact > COMPACT_INTERVAL:
                print("\n🗜️ Running database compaction...")
                compact_database()
                last_compact = now
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n👋 Master daemon stopped")

def run_once():
    """Run one complete cycle of all services."""
    print("="*60)
    print("🚀 MASTER AUTO-RUN - SINGLE CYCLE")
    print("="*60)
    
    print("\n1️⃣ Running agent poll cycle...")
    from agent_poller import run_single_poll_cycle
    run_single_poll_cycle()
    
    print("\n2️⃣ Running Mac coordinator...")
    from coordinator import coordinator_cycle
    coordinator_cycle()
    
    print_status()
    
    print("\n✅ Cycle complete")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        master_daemon()
    else:
        run_once()
