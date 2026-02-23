# Multi-Agent Job Dispatch System

A fully autonomous multi-agent workflow system where **Mac** (coordinator) routes jobs to specialist agents (**Sage** 🔍, **Atlas** 📋, **Glitch** ⚡), which automatically claim work from queues when idle.

## 🎯 Features

- **Autonomous Operation**: Agents poll for work every 5 seconds when idle
- **Hierarchical Jobs**: Main jobs [N] with sub-jobs [N/M] format
- **Parallel Processing**: Threading with double locking (fcntl + threading.Lock)
- **Time Estimation**: Intelligent estimates based on task complexity
- **Escalation**: Auto-escalation at 2x estimated duration
- **Retry Logic**: Auto-retry failed jobs (max 3 attempts)
- **GitHub Integration**: Glitch auto-commits and pushes code
- **Web Dashboard**: Real-time view at `http://localhost:8765`
- **Dead Letter Queue**: Failed jobs moved after max retries

## 🏗️ Architecture

```
User Request
    ↓
Mac 🖥️ (Coordinator)
    ↓
Sage 🔍 → Atlas 📋 → Glitch ⚡
    ↓
Auto-complete → Mac review → DONE
```

**Agent Roles:**
- **Sage** 🔍: Research, web search, analysis
- **Atlas** 📋: Planning, architecture, design docs
- **Glitch** ⚡: Coding, implementation, GitHub commits
- **Mac** 🖥️: Coordination, routing, reviews

## 🚀 Quick Start

```bash
# Create a new job
jobctl create "Build authentication system"

# View dashboard
open http://localhost:8765

# Start autonomous mode
jobctl master --daemon

# Check status
jobctl status
```

## 📊 Dashboard

Auto-refreshing web interface showing:
- Agent status and queues
- Job progress with expandable sub-jobs
- Escalation queue (high priority)
- Real-time statistics

## 🛠️ CLI Commands

```bash
# Job Management
jobctl create "description" [--agent Sage|Atlas|Glitch|Mac]
jobctl list [status] [agent]
jobctl show <id>
jobctl assign <id> <agent>
jobctl complete <id> [notes]

# Automation
jobctl master --daemon      # Run everything
jobctl poll --daemon        # Agents auto-poll
jobctl coordinator --daemon # Mac pushes to completion

# Maintenance
jobctl health [agent]       # Check agent health
jobctl retry <id>           # Retry failed job
jobctl compact              # Archive old jobs
```

## 📁 Project Structure

```
workspace/
├── jobs/                   # Core system
│   ├── jobs.py            # Job CRUD, database
│   ├── workflow.py        # Agent routing logic
│   ├── agent_worker.py    # Agent work simulation
│   ├── agent_poller.py    # Auto-polling daemon
│   ├── coordinator.py     # Mac coordination
│   ├── master_daemon.py   # Master controller
│   ├── compact_service.py # Archive old jobs
│   ├── dashboard/         # Web UI
│   └── jobs-db.json       # Job database
├── results/               # Agent outputs
│   ├── research/          # Sage research docs
│   ├── planning/          # Atlas design docs
│   └── escalations/       # Timeout reports
└── memory/                # Daily logs
```

## ⚙️ Configuration

Edit `jobs/jobs-db.json` directly or use CLI:
- `POLL_INTERVAL = 5` - Seconds between queue checks
- `MAX_CONCURRENT_PER_AGENT = 1` - One task at a time
- Default time estimates by agent type

## 🔧 Requirements

- Python 3.8+
- macOS (for fcntl locking)
- Git (for Glitch commits)
- Chrome/Edge/Safari (for dashboard)

## 📝 License

MIT
