---
name: skill-creator
description: Create new skills, edit or improve existing skills. Use when the user wants to add a new slash command or skill, update a skill's instructions, optimize a skill description for better triggering, convert a repeated workflow into a reusable skill, or ask "how do I make a skill for X". Trigger even when the user says things like "I want a skill that..." or "can you make a command for..." or "let's package this as a skill".
argument-hint: "<skill-name or 'new'>"
---

# Skill Creator

A skill for creating new skills and iteratively improving them in this project.

The core loop: **capture intent → research → draft → test → user review → iterate → finalize**.

Jump in wherever the user already is. If they hand you a draft, go straight to testing. If they just have a vague idea, start from intent capture.

---

## Step 1: Capture Intent

Before writing anything, understand what the skill should do. If the current conversation already shows a workflow the user wants to capture, extract the answers from context first — then confirm with the user.

Ask (only what isn't already clear):

1. What should this skill enable Claude to do?
2. When should it trigger? (user phrases, contexts, task types)
3. What does a good output look like?
4. Should we write test cases to verify it works? Skills with verifiable outputs (code generation, fixed workflows, data transforms) benefit from tests. Skills with subjective outputs (writing style, analysis strategy) usually don't need them.

---

## Step 2: Research Existing Skills

Before drafting, scan what already exists to avoid duplication and find reusable patterns:

```
.claude/skills/          ← 14 skills (may overlap with what user wants)
.claude/agents/          ← 9 agents (autonomous task runners; different from skills)
.claude/commands/        ← 10 commands (user-invocable slash commands)
.claude/rules/           ← 8 rules (always-loaded constraints)
```

Ask: Is this better as a skill (triggered on-demand), an agent (autonomous executor), a command (user-invoked workflow), or a rule (always-active constraint)? Skills are right when the content should load on-demand based on context.

Read `references/skill-format.md` for the full format spec.

---

## Step 3: Draft the SKILL.md

### Directory layout

```
.claude/skills/<name>/
├── SKILL.md              ← required; under 500 lines
└── references/           ← optional; for overflow content
    ├── backend.md
    └── frontend.md
```

### Frontmatter

```yaml
---
name: <kebab-case>
description: <trigger description — see below>
argument-hint: "<hint>"   # only if parameterized (e.g. /skill-name F01)
tools: Read, Grep, ...    # only if this is an agent-skill
model: sonnet             # only if this is an agent-skill
skills:                   # only if this skill depends on others
  - another-skill
memory: project           # only if this is an agent-skill that should remember
maxTurns: 30              # only if this is an agent-skill (cost control)
---
```

### Writing the description (critical)

The `description` field is the **primary trigger mechanism** — Claude decides whether to use this skill based on it. Two rules:

1. Include both *what it does* and *when to use it* (specific contexts, phrasings, situations).
2. Make it slightly "pushy" — Claude tends to undertrigger skills. Include edge cases explicitly. For example, don't just say "Use when creating skills" — say "Use when the user says things like 'I want a skill that...' or 'can you make a command for...' even if they don't explicitly ask for a skill."

### Writing the body

- Keep SKILL.md under 500 lines. If approaching that, add a `references/` subdir and link clearly from the body.
- Explain the *why* behind instructions, not just the what. "Don't use asyncio.run() inside an async function because it creates a nested event loop" beats "NEVER use asyncio.run()." When the model understands the reason, it can apply the rule intelligently to cases you didn't anticipate.
- Use imperative form: "Read the spec file first" not "You should read the spec file."
- Include realistic examples — concrete inputs/outputs are more useful than abstract descriptions.
- Reference files from `references/` with clear guidance on when to read them (e.g., "For detailed backend patterns, read `references/backend.md`").

See `references/examples.md` for three real skills from this project as models.

---

## Step 4: Test

After the draft, create 2–3 realistic test prompts — the kind of thing a real user would actually type. Run them as subagent tasks: one with the skill, one without (baseline). Save outputs to `<name>-workspace/iteration-1/`.

Example test structure:
```
skill-name-workspace/
└── iteration-1/
    ├── eval-0/
    │   ├── with_skill/    ← subagent had skill loaded
    │   └── without_skill/ ← baseline (no skill)
    └── eval-1/
        ...
```

Present results in the conversation — show what the skill produced vs. the baseline. Ask targeted questions: "Did the output match what you expected? What's missing or wrong?"

---

## Step 5: Iterate

Apply feedback from the user. When revising:

- **Generalize** from specific feedback — the skill will be used across many different prompts, not just these test cases. Avoid overfitting to the test examples.
- **Cut what isn't pulling its weight** — if a section didn't change the output, it's probably noise.
- **Explain the why** behind any new instructions you add.
- **Look for repeated work** — if all test runs independently wrote the same helper script or took the same multi-step approach, bundle that pattern into the skill.

Rerun the same test prompts into `iteration-2/`. Repeat until the user is satisfied or feedback is empty.

---

## Step 6: Finalize

Once the user is happy:

1. Write the final skill to `.claude/skills/<name>/SKILL.md` (and `references/` if needed).
2. Update `MEMORY.md` under "Key Patterns" or the skill index section to note the new skill exists.

---

## Optional: Description Optimization

If the user wants to tune when the skill triggers:

1. Generate 10 should-trigger queries and 10 should-not-trigger queries. Make the should-not-trigger ones genuinely tricky (adjacent domain, ambiguous phrasing) — not obviously irrelevant.
2. Review with user: are these realistic? Adjust as needed.
3. Iterate on the `description` field based on which queries fail, explaining your reasoning.
4. Show before/after descriptions.

Note: This project doesn't have the `run_loop.py` / `run_eval.py` scripts from the Anthropic skills repo. Do this iteration manually via discussion.

---

## Reference files

- `references/skill-format.md` — complete frontmatter field reference and structural patterns
- `references/examples.md` — three real skills from this project as annotated templates
