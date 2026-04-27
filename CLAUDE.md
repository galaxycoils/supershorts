# Project Instructions

### PROTOCOL 0: Universal State Handoff (MANDATORY)
Claude/Gemini internal memory is the SINGLE source of truth for cross-agent context.
1. **On Session Start**: Recall all relevant project entities and relations from memory.
2. **During Execution**: Proactively save important facts, patterns, and decisions to memory via `remember_fact` or `create_entity`.
3. **On Session End**: Summarize the current state in a final `remember_fact` call to ensure the next agent has a clean pickup.
4. **Obsidian Fallback**: Use Obsidian paths ONLY if explicitly requested or if memory is unavailable.

### PROTOCOL 1: Universal Skill Library (MANDATORY)
Expert personas and workflows are managed via Claude/Gemini skills and memory.
1. **Search**: Use `mcp_memory_recall` to find relevant skills or patterns for the current task.
2. **Follow**: Adhere to the "Core Rules" and "Workflows" stored in the knowledge graph.
3. **Evolve**: Update memory entities with new findings and improved patterns after each task.

### Starting work

```text
/start-task
```

This is the default entry point. It primes the agent with relevant knowledge, guides you through scoping, and picks the right level of process for the task.

### For complex features (multi-file, spec-driven)

Describe what you want built, include a Definition of Done, and ask for the full workflow:

```text
I want you to build [description]. [Tech stack, DoD items, file scope.]
Use the full metaswarm orchestration workflow.
```

This triggers the full pipeline: Research → Plan → Design Review Gate → Work Unit Decomposition → Orchestrated Execution (4-phase loop per unit) → Final Review → PR.

### Available Commands

| Command | Purpose |
|---|---|
| `/start-task` | Begin tracked work on a task |
| `/prime` | Load relevant knowledge before starting |
| `/review-design` | Trigger parallel design review gate (5 agents) |
| `/pr-shepherd <pr>` | Monitor a PR through to merge |
| `/self-reflect` | Extract learnings after a PR merge |
| `/handle-pr-comments` | Handle PR review comments |
| `/brainstorm` | Refine an idea before implementation |
| `/create-issue` | Create a well-structured GitHub Issue |
| `/external-tools-health` | Check status of external AI tools (Codex, Gemini) |
| `/setup` | Interactive guided setup — detects project, configures metaswarm |
| `/update` | Update metaswarm to latest version |
| `/status` | Run diagnostic checks on your installation |
| `/start` | Alias for `/start-task` |

### Visual Review

Use the `visual-review` skill to take screenshots of web pages, presentations, or UIs for visual inspection. Requires Playwright (`npx playwright install chromium`). See `skills/visual-review/SKILL.md`.

## Testing

- **TDD is mandatory** — Write tests first, watch them fail, then implement
- **100% test coverage required** — Lines, branches, functions, and statements. Enforced via `.coverage-thresholds.json` as a blocking gate before PR creation and task completion
- Test command: `pytest`
- Coverage command: `pytest --cov=src`

## Coverage

Coverage thresholds are defined in `.coverage-thresholds.json` — this is the **source of truth** for coverage requirements.
The current floor is 71%. Ratchet incrementally (71% → 80% → 90%).

## Quality Gates

- **Design Review Gate**: Parallel 5-agent review after design is drafted (`/review-design`)
- **Plan Review Gate**: Automatic adversarial review after any implementation plan is drafted. ALL must PASS before the plan is presented to the user.
- **Coverage Gate**: Reads `.coverage-thresholds.json` and runs the enforcement command — BLOCKING gate before PR creation.

## Workflow Enforcement (MANDATORY)

These rules ensure the full metaswarm pipeline is followed regardless of which skill initiated the work.

### After Brainstorming

When brainstorming completes:
1. **STOP** — do NOT proceed directly to implementation.
2. **RUN the Design Review Gate**.
3. **WAIT** for all 5 review agents (PM, Architect, Designer, Security, CTO) to approve.
4. **ONLY THEN** proceed.

### After Any Plan Is Created

When a plan is produced:
1. **STOP**.
2. **RUN the Plan Review Gate**.
3. **WAIT** for PASS.
4. **ONLY THEN** present to user.

### Execution Method Choice

Always ask the user which approach they want: Metaswarm (thorough), Subagent-driven (fast), or Parallel session.

### Before Finishing a Development Branch

1. **STOP** before merge/PR.
2. **RUN `/self-reflect`** to capture learnings in memory.
3. **THEN** proceed.

### Use `/start-task` Instead of EnterPlanMode

Use `/start-task` for tasks touching 3+ files to ensure quality gates are not bypassed.

### Subagent Discipline

- **NEVER** use `--no-verify`.
- **NEVER** use `git push --force` without approval.
- **ALWAYS** follow TDD.
- **NEVER** self-certify.
- **STAY** within assigned file scope.

### Pre-PR Knowledge Capture

Run `/self-reflect` to extract learnings into memory before creating PRs.

### Context Recovery (Surviving Compaction)

Approved plans and state are persisted to memory and `.beads/` locally to survive session compaction.

## Key Decisions

Stored in knowledge graph memory. Use `recall` to find architectural precedents.

## Notes

- **LLM Factory**: ALWAYS use `get_llm_service()` from `src/infrastructure/llm.py`.
- **Path Attributes**: `pathlib.Path` attributes like `exists` are read-only; use `patch.object` for testing.
