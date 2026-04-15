# Idiograph — Doc Consolidation Migration Spec
**Status:** LIVING — anti-drift spec for Claude Code execution
**Re-read this file at the top of every prompt.**
**Do not deviate from the sequence. Flag blockers; do not invent solutions.**

---

## Objective

Bring the repository's documentation directory structure into conformance with the
taxonomy defined in `docs/naming-convention.md`. Every file ends up in the correct
directory with the correct name. Cross-references are updated. No content is changed
except what is required by format conversion (`.docx` → `.md`).

---

## Source of Truth

`docs/naming-convention.md` is the authority. When this spec and that document
conflict, that document wins. Read it before starting.

---

## Pre-Flight — Read Only, No Changes

Complete all of these before touching a single file.

**P1 — Read the April 9 duplicates**
Read both files in full:
- `docs/session-2026-04-09.md`
- `docs/session-2026-04-09 (1).md`

Determine: are these two distinct sessions on the same day, or is one a download
artifact (duplicate content)? Report your finding before proceeding. If they are
distinct sessions, they become `session-2026-04-09.md` and `session-2026-04-09-2.md`.
If one is a duplicate, the duplicate is deleted.

**P2 — Extract the .docx files**
```bash
pandoc docs/session_summary_amd012.docx -o /tmp/amd012_extracted.md
pandoc docs/session_summary_amd014_amd010.docx -o /tmp/amd014_extracted.md
```
Read both extracted files. Identify the session date from the document content.
If no specific date is present, run:
```bash
git log --follow --format="%ad" --date=short -- docs/session_summary_amd012.docx | head -1
git log --follow --format="%ad" --date=short -- docs/session_summary_amd014_amd010.docx | head -1
```
Record the dates. You will need them for naming.

**P3 — Read loose docs to determine topics for phase naming**
Read the first 10 lines of each file below to extract the phase topic for naming:
- `docs/phase_1_summary.md`
- `docs/phase_2_summary.md`
- `docs/phase_3_summary-1.md`
- `docs/phase_4_5_summary.md`
- `docs/phase_5_summary.md`
- `docs/phase_6_summary.md`
- `docs/phase_7_summary.md`
- `docs/state_management_migration.md`
- `docs/rename_summary.md`

For `state_management_migration.md` and `rename_summary.md`: identify the session
date from content or git history.

**P4 — Check `docs/decisions/amendments.md`**
Read the file. Record the last AMD number present. Confirm whether AMD-016 and
AMD-017 content is already there or only in the standalone files.

**P5 — Inspect `docs/Claude_files/`**
Run `ls docs/Claude_files/` and read the first few lines of the index file if
present. Confirm it is web-export assets (JS/CSS/HTML) with no unique content.

**P6 — Read `docs/nodeforge_architecture.md`**
Read the full file. Determine: does it contain content not present elsewhere,
or is it superseded/stale? It is likely a candidate for deletion given the rename.

**Report all pre-flight findings before proceeding to Phase 1.**

---

## Phase 1 — Create Missing Directories

```bash
mkdir -p docs/phases
mkdir -p docs/vision
mkdir -p docs/generated
```

`docs/sessions/`, `docs/specs/`, and `docs/decisions/` already exist.

---

## Phase 2 — Session Summaries → `docs/sessions/`

Use `git mv` for all moves and renames. This preserves git history.

**Already correctly located — no action:**
- `docs/sessions/session-2026-04-13.md`
- `docs/sessions/session-2026-04-13-2.md`
- `docs/sessions/session-2026-04-13-3.md`
- `docs/sessions/session-2026-04-14.md`

**Moves and renames:**

```bash
git mv "docs/session_summary_2026_04_03.md" "docs/sessions/session-2026-04-03.md"
git mv "docs/session-2026-04-08.md" "docs/sessions/session-2026-04-08.md"
git mv "docs/session-2026-04-10.md" "docs/sessions/session-2026-04-10.md"
```

**April 9 duplicates — execute based on P1 finding:**
- If distinct: `git mv "docs/session-2026-04-09.md" "docs/sessions/session-2026-04-09.md"` and `git mv "docs/session-2026-04-09 (1).md" "docs/sessions/session-2026-04-09-2.md"`
- If duplicate: `git mv "docs/session-2026-04-09.md" "docs/sessions/session-2026-04-09.md"` and `git rm "docs/session-2026-04-09 (1).md"`

**Additional session artifacts — move and rename:**

`state_management_migration.md` and `rename_summary.md` are session artifacts per
the naming convention. Move them using the date identified in P3:

```bash
git mv "docs/state_management_migration.md" "docs/sessions/session-[DATE-FROM-P3].md"
git mv "docs/rename_summary.md" "docs/sessions/session-[DATE-FROM-P3].md"
```

**`.docx` conversions — new files, then delete originals:**

For each .docx, write a new `.md` file at `docs/sessions/session-[DATE-FROM-P2].md`.

The converted file must use the standard session summary format:
```
# Idiograph — Session Summary
**Date:** YYYY-MM-DD
**Status:** FROZEN — historical record, do not revise
**Session type:** [brief description]

---

## Context
[content]

## What Was Built
[content]

## Key Decisions
[content as table where applicable]

## What's Next
[content]

---

*Companion documents: [list]*
```

Map the extracted .docx content into this structure. Do not add content that is
not in the source. Do not discard content that is in the source.

After the `.md` files are committed, delete the originals:
```bash
git rm "docs/session_summary_amd012.docx"
git rm "docs/session_summary_amd014_amd010.docx"
```

---

## Phase 3 — Phase Summaries → `docs/phases/`

Use `git mv` for all. Topic names are kebab-case, 2–4 words, derived from document
content (identified in P3).

| Current file | Target name |
|---|---|
| `docs/phase_0_summary.md` | `docs/phases/phase-00-foundation.md` |
| `docs/phase_1_summary.md` | `docs/phases/phase-01-[topic].md` |
| `docs/phase_2_summary.md` | `docs/phases/phase-02-[topic].md` |
| `docs/phase_3_summary-1.md` | `docs/phases/phase-03-[topic].md` |
| `docs/phase_4_5_summary.md` | `docs/phases/phase-04-05-[topic].md` |
| `docs/phase_5_summary.md` | `docs/phases/phase-05-[topic].md` |
| `docs/phase_6_summary.md` | `docs/phases/phase-06-[topic].md` |
| `docs/phase_7_summary.md` | `docs/phases/phase-07-[topic].md` |
| `docs/phase_8_summary.md` | `docs/phases/phase-08-mcp-integration.md` |

Fill in `[topic]` from P3 findings. Do not guess — read the file.

---

## Phase 4 — Vision Docs → `docs/vision/`

These files are stable per the naming convention. Move and rename:

| Current file | Target name |
|---|---|
| `docs/essay_blueprint.md` | `docs/vision/vision-essay-blueprint.md` |
| `docs/graph_theory_curriculum.md` | `docs/vision/vision-graph-theory-curriculum.md` |
| `docs/vision_and_thesis.md` | `docs/vision/vision-thesis-and-principles.md` |
| Root `Blueprint_` | `docs/vision/vision-blueprint-original.md` |
| Root `This_is_me` | `docs/vision/vision-author-context.md` |

Note: `Blueprint_` and `This_is_me` are in the repo root, not `docs/`. Use
`git mv` from root.

---

## Phase 5 — Decisions Cleanup

**AMD-016 and AMD-017 standalone files:**

Check P4 finding. If AMD-016 and AMD-017 are NOT yet in `docs/decisions/amendments.md`,
append them in sequence. Use the content from the standalone files verbatim.
Then delete the standalone files:

```bash
git rm "docs/amd-016-llm-node-placement-2.md"
# AMD-017 standalone if present in docs/
```

If they ARE already in amendments.md, just delete the standalone files.

**Blueprint amendments consolidation:**

Per naming convention, `blueprint_amendments-1.md` and `blueprint_amendments_2.md`
are archived — their content was consolidated into `docs/decisions/amendments.md`.
Verify this is true by checking the last AMD number in amendments.md vs. the last
AMD in amendments_2.md. If consolidated, delete both:

```bash
git rm "docs/blueprint_amendments-1.md"
git rm "docs/blueprint_amendments_2.md"
```

If NOT consolidated, do not delete — flag this for human review.

---

## Phase 6 — Specs Cleanup

Move the loose spec-adjacent files from `docs/` root to `docs/specs/`:

```bash
git mv "docs/spec-arxiv-pipeline-final.md" "docs/specs/spec-arxiv-pipeline-final.md"
git mv "docs/color_designer_spec-1.md" "docs/specs/spec-color-designer.md"
git mv "docs/phase_8_9_task_inventory.md" "docs/specs/spec-phase-08-09-task-inventory.md"
git mv "docs/demo_design_spec-1.md" "docs/specs/spec-demo-design.md"   # if present in docs/
```

Also move `phase_10_proposal` (no extension — check if it's a markdown file):
```bash
git mv "docs/phase_10_proposal" "docs/specs/spec-phase-10-usd-inversion.md"
```

---

## Phase 7 — Deletions

Execute based on pre-flight findings.

**`docs/Claude_files/`** — if confirmed as web-export dump with no unique content:
```bash
git rm -r "docs/Claude_files/"
```

**`docs/nodeforge_architecture.md`** — if confirmed as superseded by current docs:
```bash
git rm "docs/nodeforge_architecture.md"
```

If either file contains unique content not present elsewhere, do not delete —
flag for human review.

---

## Phase 8 — Cross-Reference Update

Search all `.md` files for broken companion document references and internal links
created by the moves above.

```bash
grep -r "phase_[0-9]_summary" docs/
grep -r "session_summary_" docs/
grep -r "blueprint_amendments" docs/
grep -r "essay_blueprint" docs/
grep -r "vision_and_thesis" docs/
grep -r "graph_theory_curriculum" docs/
grep -r "rename_summary" docs/
grep -r "state_management_migration" docs/
grep -r "demo_design_spec" docs/
grep -r "amd-016-llm-node-placement" docs/
```

For each hit: update the reference to the new filename and path. Do not change
any other content in the file. Flag if a reference is in a FROZEN document —
frozen documents should not be edited, so flag these for human decision.

---

## Commit Strategy

**One commit per phase.** Do not batch phases into a single commit.

```
chore: create docs/phases/, docs/vision/, docs/generated/ directories
chore: move session summaries to docs/sessions/
chore: convert .docx session summaries to markdown
chore: move phase summaries to docs/phases/ with canonical names
chore: move vision docs to docs/vision/
chore: consolidate AMD-016/017 into amendments.md, remove standalone files
chore: move loose specs to docs/specs/
chore: delete deprecated files (Claude_files, nodeforge_architecture)
chore: update cross-references after doc consolidation
```

All commits on a branch: `chore/doc-consolidation`
Merge via PR when complete, merge commit (not squash).

---

## Anti-Drift Rules

- Re-read this spec at the top of every prompt.
- Pre-flight findings must be reported before Phase 1 begins.
- Do not invent topic names for phase summaries — read the file.
- Do not change frozen document content. If a cross-reference update would
  require changing a frozen document, flag it instead.
- Do not delete any file without the pre-flight confirmation step.
- If any step is ambiguous, stop and ask. Do not resolve ambiguity silently.
- `git mv` for all moves. Never `cp` then `rm`.

---

## Done When

- `docs/` root contains only: `decisions/`, `phases/`, `sessions/`, `specs/`,
  `vision/`, `generated/`, `naming-convention.md`, `workflow.md`
- All session summaries are in `docs/sessions/` with `session-YYYY-MM-DD.md` naming
- All phase summaries are in `docs/phases/` with `phase-NN-topic.md` naming
- All vision docs are in `docs/vision/`
- No `.docx` files remain in the repo
- `docs/decisions/amendments.md` contains AMD-016 and AMD-017
- All cross-references updated
- CI green, 44 tests passing
