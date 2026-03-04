---
description: Strategic product planning - analyze current app state, research the bioinformatics tool market, and propose new high-value features not yet in the roadmap
user-invocable: true
argument-hint: "[focus-area]"
---

# Strategic Development Planning

Proactively analyze the app's state, research market trends, and propose the next wave of features.

## Parse Arguments

`$ARGUMENTS` can optionally specify a focus area (e.g., `aging`, `export`, `collaboration`, `pharma`). If empty, do a broad market scan.

## Workflow

### Step 1: Assess Current State

Read `.claude/commands/roadmap.md` — understand which features are done (checked) vs pending.

Read these files to understand what's actually implemented:
- `frontend/src/components/chat/AnalysisResultsDisplay.tsx` (results UI)
- `backend/app/services/geo_survival_workflow_orchestrator.py` (pipeline)
- `backend/app/api/routes.py` (endpoints)

Summarize: "The app currently has X, Y, Z. It does NOT yet have A, B, C."

### Step 2: Research Market Landscape

Use WebSearch to investigate (use 2026 in queries):
1. "KMPlot bioinformatics survival analysis new features 2026"
2. "cBioPortal recent updates cancer genomics 2025 2026"
3. "bioinformatics survival analysis tools researchers needs 2026"
4. "gene expression survival biomarker discovery tools comparison"
5. "GEO NCBI analysis tools researchers workflow"

If `$ARGUMENTS` contains a focus area, also search:
- `aging` → "longevity caloric restriction bioinformatics tools 2026"
- `pharma` → "drug target validation transcriptomics survival tools"
- `education` → "bioinformatics teaching tools gene expression"
- `collaboration` → "collaborative bioinformatics analysis sharing tools"

### Step 3: Identify Unmet Needs

After research, think about these under-served segments:

**Aging/Longevity researchers**: Caloric restriction, lifespan studies, animal model cross-species analysis — this app was originally built for this. What do they specifically need that KMPlot/cBioPortal won't provide? (Those tools focus on human cancer only.)

**Drug target discovery (pharma/biotech)**: Validation workflows, target prioritization, multi-indication analysis. What automation would save them days of work?

**Rare disease researchers**: Small cohorts, need to aggregate across many small studies. Meta-analysis across studies is our core strength.

**Bioinformatics educators**: Teaching survival analysis with real data. What would make this a good classroom tool?

**Collaborative labs**: PI + trainees working on same analysis. What multi-user features would they need?

### Step 4: Gap Analysis

For each finding, ask:
1. Does our tool already do this? (check roadmap — both done and planned features)
2. Could our chat/AI interface make this uniquely powerful?
3. Does our GEO-breadth (all datasets, not just TCGA) give us a unique angle?
4. Is this something competitors cannot easily copy?

### Step 5: Generate Feature Proposals

Propose 3-7 new features NOT already in the roadmap (F01-F15). For each:

```
## Proposal: [Feature Name]

**Target User Segment**: [who benefits specifically]
**Problem**: [what they currently do manually or cannot do at all]
**Solution**: [what this feature provides in one sentence]
**Competitive Moat**: [why KMPlot/cBioPortal cannot easily replicate this]
**Complexity**: S / M / L
**Market Impact**: Low / Medium / High — with rationale
**Key Files Affected**: [backend/frontend files likely involved]
**Prerequisite Features**: [from F01-F15 roadmap, if any]
```

### Step 6: Prioritize

Rank proposals by: `(impact × uniqueness) / complexity`

Present:
1. Top 3 ranked proposals with rationale
2. Which existing roadmap features should be deprioritized to make room (if any)

### Step 7: Offer to Extend Roadmap

Ask: "Should I add any of these proposals to the roadmap and create implementation specs?"

If user confirms, for each approved proposal:
1. Add a new entry to `.claude/commands/roadmap.md` (e.g., `- [ ] **F16** [Name] [Size]`)
2. Create `.claude/skills/implement-feature/references/F16.md` using the same format as F01-F15 (problem, files to read, implementation, verification, commit message)

## Example Invocations

- `/strategize` — broad market scan
- `/strategize aging` — focus on longevity/caloric restriction use cases
- `/strategize pharma` — focus on drug target validation workflows
- `/strategize collaboration` — focus on multi-user/team features
- `/strategize export` — focus on output and integration improvements
