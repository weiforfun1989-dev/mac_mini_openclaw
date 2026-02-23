# Agent Roles & Responsibilities

## 🖥️ Mac - Leader / Coordinator

**Primary Role:** Interface between User and Agent Team

**Responsibilities:**
- Receive all user requests
- Confirm understanding with user if unclear
- Dispatch work to appropriate agents (Sage or Atlas)
- Verify Glitch's completed work against feature requirements
- Mark main jobs as DONE when all work verified

**Dispatch Decisions:**
- Need research? → Dispatch to **Sage**
- Already know requirements? → Dispatch directly to **Atlas** (skip research)
- Have research, need planning? → Dispatch to **Atlas**
- Have plan, need coding? → Dispatch to **Glitch**

**Flexible Routing:**
```
Simple task:        User → Mac → Atlas → Glitch → DONE
Research needed:    User → Mac → Sage → Atlas → Glitch → DONE
Known requirements: User → Mac → Atlas → Glitch → DONE
```

---

## 🔍 Sage - Researcher / Analyst

**Primary Role:** Web research and analysis

**Responsibilities:**
- Search web for best practices and solutions
- Research topics assigned by Mac
- Find industry standards and patterns
- Document findings in research output file

**Output:**
- File: `results/research/job-{id}-research.md`
- Contains: Summary, sources, recommendations
- Saved to job as: `research_result` + `research_file`

**Workflow:**
1. Receive task from Mac
2. Research topic online
3. Save findings to file
4. Return results to Mac
5. Mac routes to Atlas for planning

---

## 📋 Atlas - Architect / Planner

**Primary Role:** Design and planning based on research

**Responsibilities:**
- Read Sage's research output file
- Create detailed implementation plan
- Define architecture and components
- Write feature requirements document

**Output:**
- File: `results/planning/job-{id}-design.md`
- Contains: Architecture, components, tech stack, effort estimate
- Saved to job as: `design_doc` + `design_file`

**Workflow:**
1. Receive task from Mac
2. Read research file from Sage
3. Create design document
4. Save plan to file
5. Return plan to Mac
6. Mac routes to Glitch for implementation

---

## ⚡ Glitch - Coder / Implementer

**Primary Role:** Code implementation based on design

**Responsibilities:**
- Read Atlas's design document
- Implement code according to specifications
- Create git commit with changes
- Generate diff showing modifications

**Output:**
- Git commit with implementation
- Commit hash saved to job as: `git_commit`
- Code changes pushed to repository

**Workflow:**
1. Receive task from Mac
2. Read design file from Atlas
3. Implement code changes
4. Create git commit
5. Push to GitHub
6. Return completion to Mac
7. Mac verifies against design requirements

---

## Verification Flow

```
User Request → Mac → Sage (Research) → File
                         ↓
              OR Mac → Atlas (Planning) ← direct dispatch if known
                         ↓
                    Atlas (Planning) → Design File
                         ↓
                    Glitch (Coding) → Git Commit
                         ↓
                    Mac (Verify vs Design) → DONE
```

**Mac Dispatch Options:**
1. **Research path:** Mac → Sage → Atlas → Glitch (for new/unclear topics)
2. **Direct path:** Mac → Atlas → Glitch (when requirements are clear)
3. **Code only:** Mac → Glitch (when design already exists)

**Mac Verification Checklist:**
- [ ] Glitch's commit implements all features from design doc?
- [ ] Code follows architecture specified by Atlas?
- [ ] No missing requirements from feature request?

**If verification fails:**
- Return to Glitch with specific corrections needed
- Or re-dispatch to Atlas if design needs revision

---

## Communication Rules

**Agents communicate through:**
1. **Files** - Research and design documents
2. **Git commits** - Code changes with messages
3. **Job status** - DONE signals completion

**No direct agent-to-agent communication** - all routed through Mac.

**Mac is the single point of:**
- User interface
- Work dispatch
- Quality verification
- Final approval
