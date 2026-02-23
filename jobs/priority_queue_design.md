# Priority Queue Implementation Plan

## Overview
Add priority levels to jobs so urgent tasks are processed first.

## Design

### 1. Job Schema Addition
```python
"priority": "high" | "medium" | "low"  # default: "medium"
```

### 2. Priority Order
- high = 3
- medium = 2  
- low = 1

### 3. Agent Queue Sorting
When agent gets pending jobs, sort by:
1. Priority (descending)
2. Created time (ascending)

### 4. CLI Commands
```bash
jobs create "Urgent task" --priority high
jobs list --priority high
```

### 5. Implementation Files
- jobs.py: Add priority field, sort in get_agent_pending_jobs()
- agent_worker.py: Update to respect priority order

## Testing
1. Create jobs with mixed priorities
2. Verify high priority processed first
3. Verify dashboard shows priority
