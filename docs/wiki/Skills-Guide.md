# Skills Guide

ETU uses **Zed Agent Skills** — reusable, on-demand instruction sets that AI agents load automatically when relevant. This guide explains what skills exist in this repo, how they work, and how to add new ones.

---

## 1. What Is a Skill?

A skill is a directory containing a `SKILL.md` file with YAML frontmatter (`name`, `description`) followed by instructions. When an agent works in this repo and encounters a matching situation (e.g., a failing test), it can load the skill's instructions automatically.

Skills can live in two places:

| Scope | Location | Notes |
|-------|----------|-------|
| Project-local | `<module>/.agents/skills/<name>/SKILL.md` | Committed to git, shared with all contributors |
| Global | `~/.agents/skills/<name>/SKILL.md` | Personal, machine-local, not committed |

---

## 2. Skills in This Repository

| Skill | Location | Purpose |
|-------|----------|---------|
| `debug` (demo) | [`demo/.agents/skills/debug/SKILL.md`](../../demo/.agents/skills/debug/SKILL.md) | Python debugging: pytest, pdb, profiling, GPU/torch issues, data validation |
| `debug` (files) | [`files/.agents/skills/debug/SKILL.md`](../../files/.agents/skills/debug/SKILL.md) | Files database debugging: index validation, integrity checks, cache cleanup, schema repair |

Both are project-local and scoped to their respective module, since debugging a Python numpy shape mismatch is a very different task from repairing a corrupted `index.json`.

### `demo` debug skill — Section Overview

1. Pytest debugging (flags, `--pdb`, flaky test isolation)
2. Traceback & pdb (breakpoints, post-mortem, logging)
3. Profiling (cProfile, snakeviz, memory profiling, leak checklist)
4. GPU/Torch debugging (CUDA/MPS checks, OOM handling, forcing CPU)
5. Data validation (input/output sanity checks, output diffing)
6. General triage ("it doesn't work" checklist, minimal repro script)

### `files` debug skill — Section Overview

1. Index validation (missing/orphaned/duplicate entries)
2. File integrity checks (format headers, size mismatch, checksums)
3. Schema repair (JSON validation, auto-repair script, type validation)
4. Cache debugging (freshness analysis, safe cleanup, nuclear reset)
5. Export debugging (vertex/face count verification, source tracing)
6. Full health check (one-command comprehensive report)

---

## 3. When Skills Get Used

An agent should reach for a skill when:
- A description closely matches the current task (e.g., "a pytest test is failing" → `demo` debug skill)
- The user explicitly asks for help debugging something in `demo/` or `files/`
- Deeper diagnostics are needed than a quick one-off command

You can also invoke a skill manually via the `/` slash command menu in Zed if you want to consult it without describing the problem first.

---

## 4. Creating a New Skill

Use Zed's built-in `create-skill` skill as the authoritative guide (ask the agent to load it), but the short version:

1. **Choose scope**: project-local (`<module>/.agents/skills/<name>/`) for repo-specific workflows, global (`~/.agents/skills/<name>/`) for personal ones.
2. **Name it**: lowercase, hyphen-separated, matching the directory name exactly (regex: `^[a-z0-9]+(-[a-z0-9]+)*$`).
3. **Write `SKILL.md`**:

```markdown
---
name: my-skill-name
description: Specific, actionable description of what this does and when to use it.
---

# Skill Title

Direct instructions for the agent...
```

4. **Add supporting files** if useful (templates, scripts, examples) and reference them with relative paths in the skill body.
5. **Test it** by asking an agent a question that should trigger the skill and confirming it uses the right instructions.

### Good vs. Bad Descriptions

| ✅ Good | ❌ Bad |
|--------|--------|
| "Python debugging toolkit for the ETU demo pipeline. Covers pdb breakpoints, pytest debugging, profiling..." | "Helps with debugging" |
| "File database debugging toolkit... Use when files go missing, index is corrupt..." | "For files stuff" |

---

## 5. Suggested Future Skills

Consider adding these as the project grows:

| Skill Name | Module | Purpose |
|------------|--------|---------|
| `release` | root | Automate version bump + changelog + tag workflow |
| `renderer-debug` | `src/` | GPU/graphics API debugging (DirectX/Metal/Vulkan/OpenGL specific) |
| `benchmark` | `demo/` or `src/` | Standardized performance benchmarking harness |
| `asset-import` | `files/` | Guided workflow for importing and tagging new assets |

When adding one of these, follow the same structure as the existing `debug` skills: a quick diagnostic flow at the top, then detailed sections with copy-pasteable commands/scripts.

---

## 6. Maintaining Skills

- Keep skill instructions **in sync with actual code** — if `pipeline.py`'s API changes, update code snippets in the `demo` debug skill.
- Skills should be **self-contained**: don't assume the agent has read other files unless explicitly referenced.
- Prefer **copy-pasteable commands** over prose descriptions — agents (and humans) act faster on concrete commands.
- Review skills periodically alongside [Development-Guide](Development-Guide.md) updates.
