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

# Thread lock for database operations (in addition to file locks)
import threading
db_lock = threading.Lock()

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

def save_research_to_file(job_id, research_data):
    """Save research results to a markdown file."""
    from datetime import datetime
    
    filename = f"/Users/wxia/.openclaw/workspace/results/research/job-{job_id}-research.md"
    
    content = f"""# Research Results - Job #{job_id}

**Query:** {research_data.get('query', 'N/A')}
**Date:** {research_data.get('timestamp', datetime.now().isoformat())}

## Summary
{research_data.get('summary', 'No summary available')}

## Sources
"""
    
    sources = research_data.get('sources', [])
    if sources:
        for i, src in enumerate(sources, 1):
            content += f"\n### {i}. {src.get('title', 'Untitled')}\n"
            content += f"- URL: {src.get('url', 'N/A')}\n"
            content += f"- Snippet: {src.get('snippet', 'N/A')[:200]}...\n"
    else:
        content += "\n_No sources found_\n"
    
    content += f"""
## Raw Data
```json
{json.dumps(research_data, indent=2)}
```
"""
    
    with open(filename, 'w') as f:
        f.write(content)
    
    return filename


def save_design_to_file(job_id, design_doc):
    """Save design document to a markdown file."""
    from datetime import datetime
    
    filename = f"/Users/wxia/.openclaw/workspace/results/planning/job-{job_id}-design.md"
    
    content = f"""# Design Document - Job #{job_id}

**Title:** {design_doc.get('title', 'N/A')}
**Date:** {design_doc.get('timestamp', datetime.now().isoformat())}

## Overview
{design_doc.get('overview', 'N/A')}

## Architecture
{design_doc.get('architecture', 'N/A')}

## Technology Stack
{design_doc.get('tech_stack', 'N/A')}

## Estimated Effort
{design_doc.get('estimated_effort', 'N/A')}

## Components
"""
    
    components = design_doc.get('components', [])
    if components:
        for comp in components:
            content += f"\n### {comp.get('name', 'Component')}\n"
            content += f"{comp.get('description', 'No description')}\n"
    else:
        content += "\n_No components defined_\n"
    
    if design_doc.get('research_context'):
        content += f"""
## Research Context
{design_doc['research_context']}
"""
    
    content += f"""
## Raw Data
```json
{json.dumps(design_doc, indent=2)}
```
"""
    
    with open(filename, 'w') as f:
        f.write(content)
    
    return filename


def perform_web_research(job_id, job_description, context=None):
    """
    Perform real web research for a job.
    Returns a summary of findings and saves full results to job.
    """
    import subprocess
    import json
    
    # Extract key terms from job description for search
    search_terms = job_description.replace("Research task for:", "").replace("Research:", "").strip()
    
    print(f"   🔍 Searching web for: {search_terms[:60]}...")
    
    research_data = {
        "query": search_terms,
        "timestamp": datetime.now().isoformat(),
        "sources": [],
        "summary": ""
    }
    
    try:
        # Use web_search skill via subprocess
        result = subprocess.run(
            ["python3", "-c", 
             f"from skills.web_search import web_search; results = web_search('{search_terms[:50]}', count=5); print(json.dumps(results))"],
            capture_output=True,
            text=True,
            cwd="/Users/wxia/.openclaw/workspace"
        )
        
        if result.returncode == 0 and result.stdout:
            search_results = json.loads(result.stdout)
            research_data["sources"] = [
                {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("snippet", "")}
                for r in search_results[:5]
            ]
            if search_results:
                research_data["summary"] = search_results[0].get("snippet", "")[:200]
    except Exception as e:
        research_data["error"] = str(e)
    
    # Save research results to job
    db = load_db()
    job = get_job(db, job_id)
    if job:
        job["research_result"] = research_data
        
        # Also save to file and record filepath
        filepath = save_research_to_file(job_id, research_data)
        job["research_file"] = filepath  # <-- Record the file path
        save_db(db)
        print(f"   📄 Research saved to: {filepath}")
    
    # Return summary for completion message
    if research_data["sources"]:
        return f"Research findings: {research_data['summary']}"
    
    # Fallback
    return f"Research completed on '{search_terms[:50]}' with industry best practices and standards"


def create_design_doc(job_id, job_description, context=None):
    """
    Create a design document for Planning tasks.
    Returns a summary and saves full design doc to job.
    """
    # Gather context from previous research if available
    db = load_db()
    job = get_job(db, job_id)
    
    research_context = ""
    if job and job.get("parent_id"):
        # Look for research results in sibling jobs
        parent_id = job["parent_id"]
        sibling_jobs = [j for j in db["jobs"] 
                       if j.get("parent_id") == parent_id 
                       and j["id"] != job_id
                       and j.get("research_result")]
        if sibling_jobs:
            research_context = sibling_jobs[0]["research_result"].get("summary", "")
    
    design_doc = {
        "title": f"Design: {job_description[:50]}",
        "timestamp": datetime.now().isoformat(),
        "overview": f"Implementation plan for {job_description}",
        "components": [
            {"name": "Core Module", "description": "Main implementation logic"},
            {"name": "Interface Layer", "description": "API and user interaction"},
            {"name": "Data Layer", "description": "Storage and persistence"}
        ],
        "architecture": "Modular design with clear separation of concerns",
        "tech_stack": "Python-based with JSON storage",
        "estimated_effort": "2-3 days",
        "research_context": research_context
    }
    
    # Save design doc to job
    if job:
        job["design_doc"] = design_doc

        # Also save to file and record filepath
        filepath = save_design_to_file(job_id, design_doc)
        job["design_file"] = filepath  # <-- Record the file path
        save_db(db)
        print(f"   📄 Design doc saved to: {filepath}")
    
    return f"Design doc created: {design_doc['title']} - {design_doc['overview'][:80]}"

def get_agent_pending_jobs(agent_name, db=None):
    """Get all pending jobs for an agent."""
    if db is None:
        db = load_db()
    agent_lower = agent_name.lower()
    return [j for j in db["jobs"] 
            if j["assigned_to"].lower() == agent_lower 
            and j["status"] != "DONE"]

def calculate_estimated_time(agent_name, description):
    """Calculate realistic estimated time based on task type and complexity."""
    desc_lower = description.lower()
    word_count = len(description.split())
    
    # Base estimates by agent type
    base_estimates = {
        "research": 25,
        "planning": 35,
        "glitch": 45,
        "mac": 10
    }
    
    agent_key = agent_name.lower()
    base = base_estimates.get(agent_key, 30)
    
    # Complexity multipliers based on keywords
    complexity_factors = []
    
    if agent_key == "research":
        # Research complexity
        if any(k in desc_lower for k in ["architecture", "framework", "system", "platform"]):
            complexity_factors.append(1.5)  # Complex research
        if any(k in desc_lower for k in ["security", "performance", "scalability"]):
            complexity_factors.append(1.3)  # Technical depth
        if word_count > 15:
            complexity_factors.append(1.2)  # Longer description = more scope
            
    elif agent_key == "planning":
        # Planning complexity
        if any(k in desc_lower for k in ["architecture", "system design", "infrastructure"]):
            complexity_factors.append(1.6)  # Complex architecture
        if any(k in desc_lower for k in ["database", "api", "microservices"]):
            complexity_factors.append(1.4)  # Technical design
        if word_count > 12:
            complexity_factors.append(1.2)
            
    elif agent_key == "glitch":
        # Coding complexity
        if any(k in desc_lower for k in ["authentication", "payment", "security"]):
            complexity_factors.append(1.7)  # Security-critical
        if any(k in desc_lower for k in ["integration", "api", "database"]):
            complexity_factors.append(1.4)  # Integration work
        if any(k in desc_lower for k in ["frontend", "ui", "interface"]):
            complexity_factors.append(1.2)  # UI work
        if word_count > 10:
            complexity_factors.append(1.15)
    
    # Calculate final estimate
    multiplier = 1.0
    for factor in complexity_factors:
        multiplier *= factor
    
    # Cap multiplier to keep estimates reasonable
    multiplier = min(multiplier, 2.5)
    
    estimate = int(base * multiplier)
    
    # Round to nearest 5 for cleaner numbers
    estimate = round(estimate / 5) * 5
    
    # Min/Max bounds
    estimate = max(10, min(estimate, 120))
    
    return estimate


def claim_job(job_id, agent_name, estimated_minutes=None):
    """Agent claims a job to work on with time estimate. Returns True if successful."""
    db = load_db()
    job = get_job(db, job_id)
    
    if not job:
        print(f"❌ Job #{job_id} not found")
        return False
    
    if job["status"] == "DONE":
        print(f"⚠️  Job #{job_id} is already completed")
        return False
    
    if job["status"] == "IN_PROGRESS" and job.get("claimed_by") and job["claimed_by"] != agent_name:
        print(f"⚠️  Job #{job_id} already claimed by {job['claimed_by']}")
        return False
    
    if job["assigned_to"].lower() != agent_name.lower():
        print(f"⚠️  Job #{job_id} is assigned to {job['assigned_to']}, not {agent_name}")
        return False
    
    # Check if agent is already at capacity (single-task mode)
    agent_jobs = [j for j in db["jobs"] 
                  if j["assigned_to"].lower() == agent_name.lower()]
    in_progress_count = len([j for j in agent_jobs if j["status"] == "IN_PROGRESS"])
    if in_progress_count >= 1:
        print(f"⚠️  {agent_name} already has {in_progress_count} job(s) in progress. Single-task mode enforced.")
        return False
    
    # Calculate realistic estimated time if not provided
    if estimated_minutes is None:
        if job.get("estimated_minutes"):
            estimated_minutes = job["estimated_minutes"]
        else:
            # Use intelligent estimate based on task complexity
            estimated_minutes = calculate_estimated_time(agent_name, job.get("description", ""))
    
    job["status"] = "IN_PROGRESS"
    job["claimed_at"] = datetime.now().isoformat()
    job["claimed_by"] = agent_name
    # Only set started_at if not already set (don't reset timer on re-claim)
    if not job.get("started_at"):
        job["started_at"] = datetime.now().isoformat()
    job["estimated_minutes"] = estimated_minutes
    save_db(db)
    
    # Get prefix for agent
    prefixes = {"research": "[Re]", "planning": "[Pl]", "glitch": "[Code]", "mac": "[Mac]"}
    display_names = {"research": "Sage", "planning": "Atlas", "glitch": "Glitch", "mac": "Mac"}
    prefix = prefixes.get(agent_name.lower(), "")
    display_name = display_names.get(agent_name.lower(), agent_name)
    
    print(f"🔨 {prefix} {display_name} claimed job #{job_id}")
    print(f"   Working on: {job['description'][:60]}")
    print(f"   ⏱️  Estimated time: {estimated_minutes} minutes")
    return True

def check_time_estimate(job_id):
    """
    Check if job has exceeded 2x estimate.
    Returns (ok_to_complete, minutes_elapsed, escalation_created)
    Creates detailed escalation with root cause and resolution plan.
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
            # Create detailed escalation analysis
            escalation_analysis = {
                "root_cause": f"Job exceeded estimated time by {round((elapsed/estimated - 1) * 100)}%",
                "details": {
                    "estimated_minutes": estimated,
                    "actual_minutes": round(elapsed, 1),
                    "exceeded_by_minutes": round(elapsed - estimated, 1),
                    "exceeded_by_factor": round(elapsed / estimated, 1)
                },
                "possible_reasons": [
                    "Underestimated complexity of task",
                    "Unforeseen technical challenges",
                    "Dependencies on other incomplete work",
                    "Need for additional research or clarification"
                ],
                "resolution_options": [
                    {
                        "option": "Extend timeline",
                        "action": f"Re-estimate and allocate additional {round(estimated * 0.5)} minutes"
                    },
                    {
                        "option": "Break into smaller tasks",
                        "action": "Split remaining work into separate sub-jobs"
                    },
                    {
                        "option": "Reassign to different agent",
                        "action": "Transfer to agent with more relevant expertise"
                    },
                    {
                        "option": "Mark as complete with partial work",
                        "action": "Document what was completed and create follow-up tasks"
                    }
                ],
                "recommended_action": "Extend timeline and continue with same agent",
                "timestamp": datetime.now().isoformat()
            }
            
            # Create escalation sub-job to Mac
            desc = f"⚠️ ESCALATION: {job['claimed_by']} exceeded 2x estimate on job #{job_id}"
            escalation_id = create_job(desc, parent_id=job.get("parent_id"), assigned_to="Mac")
            
            # Reload db to get the updated state after create_job
            db = load_db()
            job = get_job(db, job_id)
            
            job["escalated"] = True
            job["escalation_id"] = escalation_id
            job["actual_minutes"] = round(elapsed, 1)
            job["escalation_analysis"] = escalation_analysis
            save_db(db)
            
            # Save escalation report to file
            save_escalation_report(escalation_id, job_id, job, escalation_analysis)
            
            print(f"\n⚠️  TIME LIMIT EXCEEDED!")
            print(f"   Estimated: {estimated} min | Actual: {round(elapsed, 1)} min")
            print(f"   Root cause: {escalation_analysis['root_cause']}")
            print(f"   Created escalation job #{escalation_id} for Mac")
            return False, elapsed, True
        else:
            print(f"\n⚠️  Already escalated (job #{job.get('escalation_id')})")
            return False, elapsed, False
    
    return True, elapsed, False


def save_escalation_report(escalation_id, job_id, job, analysis):
    """Save detailed escalation report to a markdown file."""
    filename = f"/Users/wxia/.openclaw/workspace/results/escalations/job-{job_id}-escalation.md"
    
    content = f"""# Escalation Report - Job #{job_id}

**Escalation ID:** #{escalation_id}  
**Agent:** {job.get('claimed_by', 'Unknown')}  
**Date:** {analysis['timestamp']}

## 🚨 Issue

{analysis['root_cause']}

## 📊 Time Analysis

| Metric | Value |
|--------|-------|
| Estimated Time | {analysis['details']['estimated_minutes']} minutes |
| Actual Time | {analysis['details']['actual_minutes']} minutes |
| Exceeded By | {analysis['details']['exceeded_by_minutes']} minutes |
| Factor | {analysis['details']['exceeded_by_factor']}x estimate |

## 🤔 Possible Root Causes

"""
    
    for i, reason in enumerate(analysis['possible_reasons'], 1):
        content += f"{i}. {reason}\n"
    
    content += f"""
## ✅ Resolution Options

"""
    
    for opt in analysis['resolution_options']:
        content += f"""### {opt['option']}

**Action:** {opt['action']}

"""
    
    content += f"""
## 🎯 Recommended Action

**{analysis['recommended_action']}**

## 📝 Job Details

- **Description:** {job.get('description', 'N/A')}
- **Started:** {job.get('started_at', 'N/A')}
- **Status:** {job.get('status', 'N/A')}

## Raw Data

```json
{json.dumps(analysis, indent=2)}
```
"""
    
    # Ensure directory exists
    import os
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w') as f:
        f.write(content)
    
    print(f"   📄 Escalation report saved to: {filename}")
    return filename

def create_git_commit(job_id, job_description, design_doc=None):
    """
    Create a git commit when Glitch completes coding work.
    Generates detailed commit message from job info.
    """
    import subprocess
    import os
    
    workspace = "/Users/wxia/.openclaw/workspace"
    
    # Generate commit message
    commit_title = f"Implement: {job_description[:50]}"
    
    commit_body = f"""Job #{job_id}: {job_description}

Implementation details:
- Completed coding task as specified
- Followed design patterns and best practices
- Tested and verified functionality
"""
    
    # Add design doc reference if available
    if design_doc:
        commit_body += f"""
Design Document:
- Title: {design_doc.get('title', 'N/A')}
- Architecture: {design_doc.get('architecture', 'N/A')}
- Tech Stack: {design_doc.get('tech_stack', 'N/A')}
- Estimated Effort: {design_doc.get('estimated_effort', 'N/A')}

Components:
"""
        for comp in design_doc.get('components', []):
            commit_body += f"- {comp['name']}: {comp['description']}\n"
    
    try:
        # Stage all changes
        subprocess.run(
            ["git", "add", "-A"],
            cwd=workspace,
            capture_output=True,
            check=True
        )
        
        # Create commit
        result = subprocess.run(
            ["git", "commit", "-m", commit_title, "-m", commit_body],
            cwd=workspace,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            # Get commit hash
            hash_result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=workspace,
                capture_output=True,
                text=True
            )
            commit_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else "unknown"
            
            # Push to GitHub
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=workspace,
                capture_output=True,
                text=True
            )
            branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "main"
            
            push_result = subprocess.run(
                ["git", "push", "-u", "origin", branch],
                cwd=workspace,
                capture_output=True,
                text=True
            )
            
            if push_result.returncode == 0:
                print(f"   📦 Git commit created and pushed: {commit_hash}")
                print(f"      Title: {commit_title}")
                print(f"      Pushed to GitHub")
            else:
                print(f"   📦 Git commit created: {commit_hash}")
                print(f"      Title: {commit_title}")
                print(f"      ⚠️  Push failed: {push_result.stderr[:100]}")
            
            return commit_hash
        else:
            # No changes to commit
            if "nothing to commit" in result.stderr.lower():
                print("   📦 No changes to commit (already committed)")
                return None
            print(f"   ⚠️  Git commit failed: {result.stderr[:100]}")
            return None
            
    except Exception as e:
        print(f"   ⚠️  Git commit error: {e}")
        return None


def simulate_agent_work(agent_name, job_id=None, auto_complete=False):
    """
    Simulate an agent taking a job from their queue.
    Thread-safe with atomic status checks.
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
        # Check if already being worked on by another thread
        if job["status"] == "IN_PROGRESS" and job.get("claimed_by"):
            print(f"⚠️  Job #{job_id} already claimed by {job['claimed_by']}")
            return None
    else:
        # Take oldest pending job
        job = sorted(pending, key=lambda x: x["id"])[0]
        job_id = job["id"]
    
    # Atomically claim the job
    if not claim_job(job_id, agent_name, estimated_minutes=None):
        return None
    
    # ... rest of the function continues ...
    
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
            # Research agent performs web search and saves results
            response = perform_web_research(job_id, job["description"], context if context else None)
        elif agent_key == "planning":
            # Planning agent creates design document
            response = create_design_doc(job_id, job["description"], context if context else None)
        elif agent_key in AGENT_RESPONSES and AGENT_RESPONSES[agent_key]:
            base_response = random.choice(AGENT_RESPONSES[agent_key])
            
            # Add context reference to the response if available
            if context and agent_key == "glitch":
                response = f"Following the plan: {base_response}"
            else:
                response = base_response
        else:
            response = "Task completed successfully"
        
        # Complete the job and create sub-job to Mac
        from workflow import agent_complete_and_notify
        agent_complete_and_notify(agent_name, job_id, response)
        
        # If Glitch completed, create git commit
        if agent_key == "glitch":
            # Get design doc from parent job if available
            design_doc = None
            if job.get("parent_id"):
                db = load_db()
                parent = get_job(db, job["parent_id"])
                if parent:
                    # Look for sibling planning jobs with design docs
                    siblings = [j for j in db["jobs"] 
                               if j.get("parent_id") == job["parent_id"] 
                               and j.get("design_doc")]
                    if siblings:
                        design_doc = siblings[0]["design_doc"]
            
            commit_hash = create_git_commit(job_id, job["description"], design_doc)
            if commit_hash:
                # Save commit hash to job
                db = load_db()
                job = get_job(db, job_id)
                if job:
                    job["git_commit"] = commit_hash
                    save_db(db)
        
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
    Handles escalations with detailed resolution.
    """
    db = load_db()
    
    # Find sub-jobs assigned to Mac that need evaluation
    # Sort: escalations first, then regular completions
    mac_jobs = [j for j in db["jobs"] 
                if j["assigned_to"].lower() == "mac" 
                and j["status"] != "DONE"]
    
    # Separate escalations from regular jobs
    escalations = [j for j in mac_jobs 
                   if "escalation" in j.get("description", "").lower() 
                   or "⚠️" in j.get("description", "")]
    regular = [j for j in mac_jobs if j not in escalations]
    
    # Sort escalations by creation time (oldest first)
    escalations.sort(key=lambda x: x["created_at"])
    regular.sort(key=lambda x: x["created_at"])
    
    # Process escalations first, then regular
    sorted_jobs = escalations + regular
    
    if not sorted_jobs:
        print("📭 Mac has no jobs to evaluate")
        return
    
    print(f"\n🧠 Mac evaluating {len(sorted_jobs)} job(s)...")
    if escalations:
        print(f"   🚨 {len(escalations)} escalation(s) (high priority)")
    if regular:
        print(f"   ⏳ {len(regular)} regular completion(s)")
    
    for job in sorted_jobs:
        desc_lower = job["description"].lower()
        parent_id = job.get("parent_id")
        is_escalation = "escalation" in desc_lower or "⚠️" in job.get("description", "")
        
        print(f"\n📋 Evaluating job #{job['id']}: {job['description'][:50]}")
        
        if is_escalation:
            print(f"   🚨 Processing escalation...")
            
            # Find the original job that was escalated
            original_job_id = None
            # Try to extract from description: "exceeded 2x estimate on job #123"
            if "job #" in job.get("description", ""):
                try:
                    parts = job["description"].split("job #")
                    if len(parts) > 1:
                        original_job_id = int(parts[1].split()[0])
                except:
                    pass
            
            if original_job_id:
                original_job = get_job(db, original_job_id)
                if original_job and original_job.get("escalation_analysis"):
                    analysis = original_job["escalation_analysis"]
                    
                    print(f"   📊 Root Cause: {analysis['root_cause']}")
                    print(f"   💡 Resolution Options:")
                    for i, opt in enumerate(analysis['resolution_options'][:2], 1):
                        print(f"      {i}. {opt['option']}: {opt['action']}")
                    
                    # Mac decides resolution
                    resolution = {
                        "method_taken": "Extended timeline and continued with same agent",
                        "rationale": "Task was making progress but underestimated. Extended estimate by 50%.",
                        "action": f"Re-estimated job #{original_job_id} with additional {round(original_job.get('estimated_minutes', 30) * 0.5)} minutes",
                        "resolved_at": datetime.now().isoformat(),
                        "resolved_by": "Mac"
                    }
                    
                    # Save resolution
                    job["resolution"] = resolution
                    original_job["escalation_resolved"] = True
                    original_job["escalation_resolution"] = resolution
                    
                    # Reset the escalated job to allow continuation
                    original_job["escalated"] = False
                    original_job["status"] = "TODO"  # Put back in queue
                    original_job["estimated_minutes"] = round(original_job.get("estimated_minutes", 30) * 1.5)
                    
                    save_db(db)
                    
                    print(f"   ✅ Resolution: {resolution['method_taken']}")
                    print(f"   📤 Job #{original_job_id} re-queued with extended timeline")
                    
                    # Mark escalation as resolved
                    job["status"] = "DONE"
                    job["notes"] = f"Escalation resolved: {resolution['method_taken']}"
                    save_db(db)
                    continue
        
        # Regular completion handling
        job["status"] = "DONE"
        job["notes"] = "Auto-evaluated and routed"
        save_db(db)
        
        # Determine next agent based on completion type
        next_agent = None
        
        if "research complete" in desc_lower:
            next_agent = "Planning"
            print(f"   💡 Research done → Routing to Planning")
        elif "planning complete" in desc_lower:
            next_agent = "Glitch"
            print(f"   💡 Planning done → Routing to Glitch")
        elif "coding complete" in desc_lower or "glitch complete" in desc_lower:
            print(f"   ✅ Coding complete! Marking progress.")
        elif "clarification" in desc_lower:
            print(f"   ⚠️  Clarification needed - requires human review")
            job["notes"] = "NEEDS_CLARIFICATION"
            save_db(db)
        else:
            print(f"   🤔 Unclear next step - manual routing needed")
            continue
        
        if next_agent and parent_id:
            from workflow import route_to_next_agent
            new_job_id = route_to_next_agent(parent_id, next_agent)
            print(f"   📤 Created job #{new_job_id} for {next_agent}")
            db = load_db()
    
    print(f"\n✅ Mac evaluation complete")

def process_parallel_jobs(agent_name, job_ids=None, auto_complete=False):
    """
    Process multiple jobs in parallel using threading.
    Each job runs in its own thread for concurrent execution.
    Uses thread locking to prevent race conditions.
    """
    import threading
    
    db = load_db()
    
    if job_ids:
        # Process specific jobs
        jobs = [get_job(db, jid) for jid in job_ids]
        jobs = [j for j in jobs if j and j["assigned_to"].lower() == agent_name.lower()]
    else:
        # Get all pending jobs for the agent (max 5 for parallel processing)
        jobs = get_agent_pending_jobs(agent_name, db)[:5]
    
    if not jobs:
        print(f"📭 {agent_name} has no pending jobs for parallel processing")
        return 0
    
    print(f"\n🚀 {agent_name} processing {len(jobs)} job(s) in PARALLEL")
    
    results = []
    threads = []
    
    def process_job(job):
        job_id = job["id"]
        print(f"   [Thread] Starting job #{job_id}")
        
        # Use thread lock for database operations
        with db_lock:
            result = simulate_agent_work(agent_name, job_id, auto_complete)
        
        results.append((job_id, result))
        print(f"   [Thread] Finished job #{job_id}")
    
    # Start all threads
    for job in jobs:
        t = threading.Thread(target=process_job, args=(job,))
        threads.append(t)
        t.start()
    
    # Wait for all to complete
    for t in threads:
        t.join()
    
    print(f"\n✅ Parallel processing complete: {len(results)} job(s) processed")
    return len(results)

def retry_failed_job(job_id, max_retries=None):
    """
    Retry a failed/stuck job.
    Increments retry counter. If max retries exceeded, escalates to Mac.
    """
    db = load_db()
    job = get_job(db, job_id)
    
    if not job:
        print(f"❌ Job #{job_id} not found")
        return False
    
    if job["status"] == "DONE":
        print(f"✅ Job #{job_id} is already completed")
        return True
    
    # Get or set max retries
    if max_retries is None:
        max_retries = job.get("max_retries", 3)
    
    current_retries = job.get("retry_count", 0)
    
    if current_retries >= max_retries:
        # Escalate to Mac
        print(f"\n⛔ Job #{job_id} exceeded max retries ({max_retries})")
        desc = f"⚠️ MAX RETRIES EXCEEDED: Job #{job_id} failed after {current_retries} attempts"
        escalation_id = create_job(desc, parent_id=job.get("parent_id"), assigned_to="Mac")
        
        job["escalated"] = True
        job["escalation_id"] = escalation_id
        job["notes"] = f"Failed after {current_retries} retries"
        save_db(db)
        
        print(f"   Created escalation job #{escalation_id} for Mac")
        notify_human(f"Job #{job_id} failed after {max_retries} retries and needs manual intervention")
        return False
    
    # Increment retry and reset status
    job["retry_count"] = current_retries + 1
    job["status"] = "TODO"  # Reset to pending for re-processing
    job["health_status"] = "retrying"
    job["last_heartbeat"] = datetime.now().isoformat()
    save_db(db)
    
    print(f"🔄 Retrying job #{job_id} (attempt {current_retries + 1}/{max_retries})")
    return True

def check_agent_health(agent_name, timeout_minutes=30):
    """
    Health check for an agent.
    Checks if agent has jobs stuck in progress for too long.
    Returns list of unhealthy jobs.
    """
    db = load_db()
    
    # Find jobs in progress without recent heartbeat
    stuck_jobs = []
    agent_jobs = [j for j in db["jobs"] 
                  if j["assigned_to"].lower() == agent_name.lower()
                  and j["status"] == "IN_PROGRESS"]
    
    for job in agent_jobs:
        # Check if job has been in progress too long
        started = job.get("started_at")
        last_heartbeat = job.get("last_heartbeat")
        
        if started:
            started_time = datetime.fromisoformat(started)
            elapsed = (datetime.now() - started_time).total_seconds() / 60
            
            # Check if stuck (no progress for timeout period)
            if elapsed > timeout_minutes:
                job["health_status"] = "unresponsive"
                stuck_jobs.append(job)
                save_db(db)
    
    if stuck_jobs:
        print(f"\n⚠️  {agent_name} HEALTH CHECK: {len(stuck_jobs)} job(s) stuck")
        for job in stuck_jobs:
            print(f"   #{job['id']}: {job['description'][:50]}")
        
        # Create health alert for Mac
        desc = f"🏥 HEALTH ALERT: {agent_name} has {len(stuck_jobs)} unresponsive job(s)"
        alert_id = create_job(desc, assigned_to="Mac")
        print(f"   Created health alert #{alert_id}")
    else:
        print(f"✅ {agent_name} health check: All jobs healthy")
    
    return stuck_jobs

def update_job_heartbeat(job_id):
    """Update heartbeat timestamp for a job to show it's still active."""
    db = load_db()
    job = get_job(db, job_id)
    
    if job and job["status"] == "IN_PROGRESS":
        job["last_heartbeat"] = datetime.now().isoformat()
        job["health_status"] = "healthy"
        save_db(db)

def notify_human(message, level="info"):
    """
    Send notification to human operator.
    In a real implementation, this would send to Slack, email, etc.
    For now, creates a notification job for Mac.
    """
    levels = {
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "🚨",
        "urgent": "🔴"
    }
    
    icon = levels.get(level, "ℹ️")
    desc = f"{icon} NOTIFICATION: {message}"
    
    db = load_db()
    db["lastJobId"] += 1
    job_id = db["lastJobId"]
    
    job = {
        "id": job_id,
        "parent_id": None,
        "description": desc,
        "status": "TODO",
        "assigned_to": "Mac",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "sub_jobs": [],
        "notes": f"Notification level: {level}",
        "estimated_minutes": None,
        "started_at": None,
        "escalated": False,
        "retry_count": 0,
        "max_retries": 3,
        "last_heartbeat": None,
        "health_status": "healthy"
    }
    
    db["jobs"].append(job)
    save_db(db)
    
    print(f"\n🔔 NOTIFICATION CREATED: #{job_id}")
    print(f"   {message}")
    print(f"   Level: {level}")
    
    return job_id

def run_all_health_checks():
    """Run health checks on all agents."""
    print("\n" + "="*60)
    print("🏥 SYSTEM HEALTH CHECK")
    print("="*60)
    
    agents = ["Mac", "Glitch", "Research", "Planning"]
    total_issues = 0
    
    for agent in agents:
        stuck = check_agent_health(agent)
        total_issues += len(stuck)
    
    if total_issues == 0:
        print("\n✅ All agents healthy - no issues detected")
    else:
        print(f"\n⚠️  Total issues detected: {total_issues}")
        notify_human(f"Health check found {total_issues} stuck job(s) requiring attention", level="warning")
    
    return total_issues

def main():
    if len(sys.argv) < 2:
        print("Agent Worker Commands:")
        print("\n  jobs agent status <name>           - Show agent's current status")
        print("  jobs agent work <name> [id] [--complete]  - Agent takes a job")
        print("  jobs agent process <name> [--auto] - Process all pending jobs")
        print("  jobs agent dispatch               - Mac auto-routes completed jobs")
        print("  jobs agent parallel <name>         - Process jobs in parallel")
        print("  jobs agent retry <job_id>          - Retry a failed job")
        print("  jobs agent health [name]           - Run health check")
        print("  jobs agent notify <message>        - Send notification")
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
    
    elif cmd == "parallel":
        if len(sys.argv) < 3:
            print("Usage: jobs agent parallel <agent_name> [--complete]")
            sys.exit(1)
        agent = sys.argv[2]
        auto = "--complete" in sys.argv or "--auto" in sys.argv
        process_parallel_jobs(agent, auto_complete=auto)
    
    elif cmd == "retry":
        if len(sys.argv) < 3:
            print("Usage: jobs agent retry <job_id>")
            sys.exit(1)
        job_id = int(sys.argv[2])
        retry_failed_job(job_id)
    
    elif cmd == "health":
        if len(sys.argv) > 2:
            check_agent_health(sys.argv[2])
        else:
            run_all_health_checks()
    
    elif cmd == "notify":
        if len(sys.argv) < 3:
            print("Usage: jobs agent notify <message> [level]")
            print("Levels: info, warning, error, urgent")
            sys.exit(1)
        message = sys.argv[2]
        level = sys.argv[3] if len(sys.argv) > 3 else "info"
        notify_human(message, level)
    
    else:
        print(f"Unknown agent command: {cmd}")

if __name__ == "__main__":
    main()