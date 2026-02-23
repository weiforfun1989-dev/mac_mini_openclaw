#!/usr/bin/env python3
"""
System Compaction Service - Mac triggers periodic cleanup across all agents
Runs compaction to archive completed jobs and optimize the database
"""

import json
import sys
import time
import shutil
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jobs import load_db, save_db, JOBS_DB

# Configuration
COMPACT_INTERVAL_HOURS = 24  # Run compaction every 24 hours
ARCHIVE_DAYS = 7  # Archive jobs older than 7 days
MAX_JOBS_KEEP = 1000  # Keep max 1000 recent jobs

def get_job_age_days(job):
    """Get age of job in days."""
    if job.get("completed_at"):
        completed = datetime.fromisoformat(job["completed_at"])
        return (datetime.now() - completed).days
    return 0

def compact_database():
    """
    Compact the jobs database by archiving old completed jobs.
    Returns statistics about the compaction.
    """
    print("="*60)
    print("🗜️  SYSTEM COMPACTION STARTED")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    db = load_db()
    original_count = len(db["jobs"])
    
    # Separate jobs to keep vs archive
    jobs_to_keep = []
    jobs_to_archive = []
    
    for job in db["jobs"]:
        should_archive = False
        
        # Archive if completed and old
        if job["status"] == "DONE":
            age_days = get_job_age_days(job)
            if age_days > ARCHIVE_DAYS:
                should_archive = True
        
        if should_archive:
            jobs_to_archive.append(job)
        else:
            jobs_to_keep.append(job)
    
    # If we still have too many jobs, archive oldest completed ones
    if len(jobs_to_keep) > MAX_JOBS_KEEP:
        # Sort by completion date (oldest first)
        completed_jobs = [j for j in jobs_to_keep if j["status"] == "DONE"]
        completed_jobs.sort(key=lambda x: x.get("completed_at", "") or "")
        
        # Move oldest to archive until under limit
        excess = len(jobs_to_keep) - MAX_JOBS_KEEP
        jobs_to_archive.extend(completed_jobs[:excess])
        jobs_to_keep = [j for j in jobs_to_keep if j not in completed_jobs[:excess]]
    
    # Save archive
    if jobs_to_archive:
        archive_dir = Path("/Users/wxia/.openclaw/workspace/jobs/archive")
        archive_dir.mkdir(exist_ok=True)
        
        archive_file = archive_dir / f"jobs-archive-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        archive_data = {
            "archived_at": datetime.now().isoformat(),
            "job_count": len(jobs_to_archive),
            "jobs": jobs_to_archive
        }
        
        with open(archive_file, 'w') as f:
            json.dump(archive_data, f, indent=2)
        
        print(f"📦 Archived {len(jobs_to_archive)} jobs to:")
        print(f"   {archive_file}")
    
    # Update database with kept jobs
    db["jobs"] = jobs_to_keep
    
    # Recalculate lastJobId to max ID in kept jobs
    if jobs_to_keep:
        db["lastJobId"] = max(j["id"] for j in jobs_to_keep)
    
    save_db(db)
    
    # Print summary
    archived_count = len(jobs_to_archive)
    kept_count = len(jobs_to_keep)
    
    print()
    print("📊 COMPACTION SUMMARY")
    print("-"*60)
    print(f"Original jobs:     {original_count}")
    print(f"Archived jobs:     {archived_count}")
    print(f"Jobs kept:         {kept_count}")
    print(f"Reduction:         {round(archived_count/original_count*100, 1)}%" if original_count > 0 else "N/A")
    print()
    print(f"✅ Compaction complete - Database optimized")
    print("="*60)
    
    return {
        "original": original_count,
        "archived": archived_count,
        "kept": kept_count,
        "archive_file": str(archive_file) if jobs_to_archive else None
    }

def list_archives():
    """List all archived job files."""
    archive_dir = Path("/Users/wxia/.openclaw/workspace/jobs/archive")
    
    if not archive_dir.exists():
        print("📂 No archives found")
        return
    
    archives = sorted(archive_dir.glob("jobs-archive-*.json"))
    
    print("="*60)
    print("📂 JOB ARCHIVES")
    print("="*60)
    
    if not archives:
        print("No archives found")
        return
    
    total_archived = 0
    for archive in archives:
        with open(archive) as f:
            data = json.load(f)
            count = data.get("job_count", 0)
            archived_at = data.get("archived_at", "Unknown")
            size = archive.stat().st_size / 1024  # KB
            total_archived += count
            
            print(f"\n  📄 {archive.name}")
            print(f"     Jobs: {count} | Size: {round(size, 1)} KB")
            print(f"     Archived: {archived_at[:19]}")
    
    print(f"\n📊 Total archived jobs: {total_archived}")
    print("="*60)

def run_periodic_compact_daemon():
    """Run compaction periodically in the background."""
    print("="*60)
    print("🗜️  PERIODIC COMPACTION DAEMON")
    print("="*60)
    print(f"Compaction interval: {COMPACT_INTERVAL_HOURS} hours")
    print(f"Archive jobs older than: {ARCHIVE_DAYS} days")
    print(f"Max jobs to keep: {MAX_JOBS_KEEP}")
    print("\nPress Ctrl+C to stop\n")
    
    while True:
        try:
            # Run compaction
            compact_database()
            
            # Sleep until next compaction
            print(f"\n⏰ Next compaction in {COMPACT_INTERVAL_HOURS} hours...")
            time.sleep(COMPACT_INTERVAL_HOURS * 3600)
            
        except KeyboardInterrupt:
            print("\n\n👋 Compaction daemon stopped")
            break
        except Exception as e:
            print(f"\n⚠️  Error during compaction: {e}")
            time.sleep(3600)  # Retry in 1 hour on error

def main():
    if len(sys.argv) < 2:
        print("Compaction Service Commands:")
        print("\n  jobs compact                  - Run compaction now")
        print("  jobs compact --daemon         - Run periodic compaction")
        print("  jobs compact --list           - List all archives")
        print("\nConfiguration:")
        print(f"  Archive jobs older than: {ARCHIVE_DAYS} days")
        print(f"  Max jobs to keep: {MAX_JOBS_KEEP}")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "--daemon":
        run_periodic_compact_daemon()
    elif cmd == "--list":
        list_archives()
    else:
        compact_database()

if __name__ == "__main__":
    main()
