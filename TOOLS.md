# Tools Configuration

## Agent Visibility
All agents are configured with cross-visibility enabled.

## Cross-Agent Communication
- `tools.sessions.visibility: all` — All agents can see each other's sessions
- `tools.agentToAgent.enabled: true` — Agents can send messages to each other

## Available Agents
- **Mac** (main) — General assistant, orchestration, job dispatch
- **Glitch** ⚡ (coding) — Code review, development, technical tasks
- **Research** 🔍 (research) — Information gathering, analysis, web search
- **Planning** 📋 (planning) — Project planning, roadmaps, prioritization

## Communication Pattern
Mac acts as the coordinator:
1. User asks Mac for work
2. Mac analyzes and breaks down tasks
3. Mac dispatches to appropriate agent (Glitch for coding, Research for research, Planning for strategy)
4. Agents report back to Mac
5. Mac coordinates and reports to user
