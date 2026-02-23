# Design: Job Dispatch System Improvements

**Project:** Job Dispatch Enhancement  
**Designer:** Atlas  
**Date:** 2026-02-23  
**Based on:** Sage Research - Job #49

---

## Architecture Overview

```
Current System                    Enhanced System
───────────────                   ───────────────
User → Mac → Sage                 User → Mac → Load Balancer
         ↓                                    ↓
       Atlas                              Priority Queue
         ↓                              /      |      \
       Glitch                       Sage    Atlas    Glitch
         ↓                            \       |       /
       DONE                      Event Bus ← Metrics → Cache
```

---

## Component Designs

### 1. Priority Queue Enhancement

```python
class PriorityQueue:
    def calculate_score(self, job):
        base_priority = {'high': 100, 'medium': 50, 'low': 10}
        
        # Weighted factors
        age_factor = (now - job.created_at).hours * 2
        deadline_factor = self.deadline_urgency(job)
        user_factor = self.user_importance(job.creator)
        
        return base_priority[job.priority] + age_factor + deadline_factor + user_factor
```

**Features:**
- Dynamic priority recalculation
- Aging boost (older jobs get higher priority)
- Deadline-aware scheduling
- User tier support

---

### 2. Event-Driven Notification System

```python
class EventBus:
    events = {
        'job.created': [notify_user, log_metrics],
        'job.started': [notify_agent, update_dashboard],
        'job.completed': [notify_mac, trigger_next],
        'job.failed': [notify_user, schedule_retry]
    }
```

**Benefits:**
- Decoupled components
- Real-time updates
- Extensible event handlers
- Better audit trail

---

### 3. Retry Logic with Exponential Backoff

```python
class RetryManager:
    def schedule_retry(self, job):
        if job.retry_count >= job.max_retries:
            self.move_to_dead_letter(job)
            return
        
        # Exponential backoff: 2^retry_count minutes
        delay = min(2 ** job.retry_count, 60)  # Max 60 min
        job.next_attempt = now + timedelta(minutes=delay)
        job.retry_count += 1
```

**Features:**
- Prevents thundering herd
- Respects system load
- Automatic escalation
- Dead letter analysis

---

### 4. Metrics & Observability

```python
class MetricsCollector:
    def record(self, event_type, job, duration=None):
        self.metrics[event_type].append({
            'timestamp': now(),
            'job_id': job.id,
            'agent': job.assigned_to,
            'duration': duration,
            'success': job.status == 'DONE'
        })
    
    def get_stats(self, agent=None, time_window='1h'):
        # Success rate, avg duration, throughput
```

**Dashboard Metrics:**
- Jobs per minute
- Agent utilization
- Error rates
- Queue depth
- Average completion time

---

### 5. Enhanced State Machine

```
                    ┌─────────┐
         ┌─────────→│  DONE   │
         │          └─────────┘
         │
┌─────┐  │    ┌──────────┐    ┌─────────┐
│TODO │──────→│IN_PROGRESS│───→│ BLOCKED │
└─────┘       └──────────┘    └─────────┘
   │                              │
   │    ┌─────────┐               │
   └───→│ CANCELLED│←──────────────┘
        └─────────┘
```

**New States:**
- **BLOCKED** - Waiting for dependencies
- **PAUSED** - Temporarily suspended
- **CANCELLED** - Explicitly cancelled

---

## Implementation Phases

### Phase 1: Core Improvements (Week 1-2)
1. Retry logic with exponential backoff
2. Enhanced state machine
3. Basic metrics collection

### Phase 2: Performance (Week 3-4)
4. Priority queue optimization
5. Caching layer (Redis)
6. Event-driven notifications

### Phase 3: Advanced Features (Week 5-6)
7. Dynamic resource allocation
8. Dependency management
9. Auto-scaling

---

## Technology Stack

| Component | Current | Proposed |
|-----------|---------|----------|
| Queue | Python list | Redis sorted set |
| Storage | JSON file | SQLite + Redis |
| Events | Polling | WebSocket + Redis pub/sub |
| Metrics | None | Prometheus + Grafana |
| Cache | None | Redis |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data migration | High | Backup first, gradual rollout |
| Learning curve | Medium | Documentation, training |
| Complexity | Medium | Phased implementation |

---

## Success Metrics

- 50% faster job completion
- 99.9% uptime
- < 1 second dashboard load time
- 80% reduction in manual interventions
