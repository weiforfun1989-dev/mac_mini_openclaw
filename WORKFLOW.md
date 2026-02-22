# Job Dispatch Workflow

## Overview
A multi-agent job dispatch system where Mac acts as the central coordinator.

## Status: ✅ IMPLEMENTED

The workflow system is now active in `/Users/wxia/.openclaw/workspace/jobs/`

---

## Quick Start

```bash
# Create a new job (goes to Mac by default)
jobs create "Build a website"

# View dashboard
jobs workflow dashboard

# Dispatch to an agent
jobs workflow dispatch 1 research

# Agent completes work (auto-creates sub-job to Mac)
jobs workflow complete research 1 "Found 10 relevant sources"

# Mac evaluates and routes to next agent
jobs workflow evaluate 2
jobs workflow route 1 planning
```

---

## Workflow Rules

### 1. Job Creation
- **User creates jobs ONLY to Mac** (agent:main:main)
- All initial requests go through Mac
- Mac analyzes and decides on next steps

### 2. Sub-Job Hierarchy
- **Format:** Main job #5 → Sub-job #6, #7, etc.
- Main job stays **IN_PROGRESS** until ALL sub-jobs are **DONE**
- Mac manually marks main job as DONE when complete

### 3. Agent Handoff (AUTOMATIC)
When an agent finishes, the system auto-creates a completion sub-job to Mac:

```
Research completes job #3
    ↓
Auto-creates sub-job #4: "✅ Research complete for #1: [summary]"
    ↓
Assigned to Mac
    ↓
Mac evaluates → routes to next agent or completes
```

### 4. Mac's Role
- Receives all completion/clarification sub-jobs via `jobs workflow evaluate <id>`
- Analyzes and routes to next agent:
  - `jobs workflow route <main_id> planning`
  - `jobs workflow route <main_id> coding`
- **Manually marks main job DONE** when all sub-jobs complete: `jobs complete <id>`

---

## CLI Commands

### Basic Job Management
```bash
jobs list                              # Show all jobs
jobs list IN_PROGRESS                  # Filter by status
jobs list TODO Mac                     # Filter by status + agent
jobs create "description"              # Create job (assigned to Mac)
jobs sub <parent_id> "description"     # Create sub-job
jobs assign <id> <agent>               # Assign to agent
jobs complete <id> [notes]             # Mark job done
jobs show <id>                         # View job + sub-jobs
jobs pending <agent>                   # Show pending for agent
```

### Workflow Automation
```bash
# View dashboard
jobs workflow dashboard

# Dispatch job to agent
jobs workflow dispatch <job_id> <agent>

# Agent reports completion (auto-creates sub-job to Mac)
jobs workflow complete <agent> <job_id> "summary"

# Agent needs clarification
jobs workflow clarify <agent> <job_id> "question"

# Mac evaluates completion sub-job
jobs workflow evaluate <sub_job_id>

# Route main job to next agent
jobs workflow route <main_job_id> <agent>
```

---

## Agents

| Agent | Role | Handoff Command |
|-------|------|-----------------|
| **Mac** | Coordinator | Receives all completion sub-jobs |
| **Glitch** ⚡ | Coding | `jobs workflow complete glitch <id> "done"` |
| **Research** 🔍 | Research | `jobs workflow complete research <id> "found X"` |
| **Planning** 📋 | Planning | `jobs workflow complete planning <id> "plan ready"` |

---

## Status Flow

```
TODO (user creates job → Mac)
  ↓
IN_PROGRESS (Mac dispatches to agent)
  ↓
Agent works → completes
  ↓
Auto-creates completion sub-job → Mac
  ↓
Mac evaluates → creates next sub-job OR
                marks main job DONE
```

---

## Dashboard Features

The dashboard shows:
- ✅ Job hierarchy (main → sub-jobs)
- ✅ Workflow state on each job
- ✅ Completion percentage
- ✅ Which agent has which job
- ✅ Status of all sub-jobs

```bash
jobs workflow dashboard
```

---

## Example Workflow

```bash
# 1. User creates job
jobs create "Build e-commerce site"
# Created job #1

# 2. Mac dispatches to Research
jobs workflow dispatch 1 research

# 3. Research completes (auto-creates sub-job #2 to Mac)
jobs workflow complete research 1 "Analyzed 5 competitors"

# 4. Mac evaluates
jobs workflow evaluate 2
# → Suggests: route to planning

# 5. Mac routes to Planning
jobs workflow route 1 planning
# Created sub-job #3

# 6. Planning completes
jobs workflow complete planning 3 "Architecture plan ready"

# 7. Mac evaluates, routes to Glitch
jobs workflow evaluate 4
jobs workflow route 1 glitch

# 8. Glitch completes
jobs workflow complete glitch 5 "Code implemented"

# 9. All done! Mac marks complete
jobs complete 1
```

---

## Implementation Details

- **Database:** `/Users/wxia/.openclaw/workspace/jobs/jobs-db.json`
- **Scripts:** `/Users/wxia/.openclaw/workspace/jobs/`
  - `jobs.py` — Core job management
  - `workflow.py` — Workflow automation
- **Status values:** TODO, IN_PROGRESS, DONE

---

## Date

- Workflow defined: 2026-02-21
- **Implemented: 2026-02-22** ✅
