# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run all tests (76 test cases)
python -X utf8 tests.py

# One-time setup: generate training data, train models, self-check
python setup.py

# Run the interactive CLI demo
python -X utf8 demo.py
```

> `-X utf8` is required on Windows because tests.py uses Unicode box-drawing characters that cp1252 cannot encode.

## Git workflow

After completing any meaningful unit of work — adding a feature, fixing a bug, updating employees, updating tests — commit and push to GitHub immediately. Do not batch up multiple unrelated changes into one commit.

```bash
git add <specific files>
git commit -m "Short imperative summary

- Bullet detail if needed
- Another detail

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git push origin master
```

Always run `python -X utf8 tests.py` and confirm all tests pass before committing. Stage specific files by name rather than `git add .` to avoid accidentally committing generated artifacts or `.env` files.

## Architecture

This is **SHRMS IWR** (Intelligent Workflow Routing), a thesis project implementing a two-layer hybrid AI system for routing HR documents in a Philippine civil service (LGU) context. It routes two document types: IPCR performance evaluation forms and leave applications.

### Three-layer pipeline

```
Caller → WorkflowRouter → Layer 1: RuleEngine → Layer 2: DecisionTree
```

**`workflow_router.py`** — the only public entry point. Instantiate `WorkflowRouter` and call:
- `route_ipcr(form: dict) → dict`
- `route_leave(application: dict) → dict`

**`rule_engine.py`** (Layer 1) — uses the `durable-rules` library (Rete algorithm, forward chaining). Validates compliance against CSC rules. If any rule fails, the document is rejected immediately and Layer 2 never runs. Each call creates a uniquely-named ruleset (auto-incrementing counter) because durable-rules requires globally unique ruleset names per session.

**`decision_tree.py`** (Layer 2) — two sklearn `DecisionTreeClassifier` models loaded from pre-trained `.pkl` files. IPCR: 3-class classifier. Leave: 4-class classifier. Models are loaded once at `WorkflowRouter.__init__` and reused.

### Knowledge base

**`org_and_rules.py`** — single source of truth for everything. All other files import from here. Contains:
- `EMPLOYEES` dict — org chart with `name`, `role`, `supervisor_id` per employee ID
- `LEAVE_RULES` — CSC Omnibus Rules on Leave (max days, notice periods, attachment requirements)
- `IPCR_PASSING_SCORE = 2.5` — CSC minimum passing threshold
- `IPCR_EVALUATOR_ID` — set to `None` (each employee evaluated by their supervisor) or `"EMP-001"` to override all evaluations to the Department Head
- `ROLE_ENCODING`, `LEAVE_TYPE_ENCODING` — integer encodings for ML features; **must match** what was used during training

**`org_and_rules_no_pmt.py`** — backup of `org_and_rules.py` for use when the Department Head's IPCR is handled outside the system. Identical to `org_and_rules.py` except `PMT-001` is absent and `EMP-001.supervisor_id = None`. To activate: rename current `org_and_rules.py` → `org_and_rules_pmt.py`, then rename this file → `org_and_rules.py`. No retraining needed.

### Encodings contract

The integer encodings in `org_and_rules.py` must be consistent across three files: `org_and_rules.py`, `training_data.py`, and `workflow_router.py`. If you add a new role or leave type, update all three and retrain. Current leave type encoding goes 0–8 (9 types).

### Adding employees

Adding employees to `EMPLOYEES` with an existing role title requires no retraining. If a new role title is introduced, add it to `ROLE_ENCODING` and rerun `setup.py` to regenerate data and retrain both models.

### Current org structure

All 20 employees (EMP-002 to EMP-021) report directly to John Reyes (EMP-001, Department Head). EMP-001 has no supervisor in this configuration — IPCR for the Department Head is handled outside the system. For leave applications, the Department Head skips the DH-approval stage and goes directly to HR.

### Training data and models

Generated/trained by `setup.py` via `training_data.py` and `decision_tree.py`. Running `setup.py` overwrites existing files — no manual deletion needed. The Decision Tree features contain no employee IDs; adding employees does not require retraining unless a new role is introduced.

### Leave rules summary (current)

| Leave Type | Max | Notice | Attachments |
|---|---|---|---|
| Vacation | 15 days/year | 5 days | — |
| Sick | 15 days/year | — | Medical cert if > 6 days |
| Maternity | 105 days | 30 days | — |
| Paternity | 7 days | 30 days | Marriage Certificate |
| Solo Parent | 7 days | — | Solo Parent ID |
| Force | 5 days/year | 5 days | — |
| Special Privilege | 3 days/year | 5 days | — |
| Wellness | 5 days/year | 5 days | — |
| Special Sick Leave for Women | 90 days | 5 days | Medical cert (always) |

Leave credit tracking is out of scope on this branch — enforced by Smart-HRMS.

### Key constants (IPCR)
- Rating scale: 1.0–5.0
- Passing threshold: ≥ 2.5 (Satisfactory)
- IPCR DT classes: `0=route_to_evaluator`, `1=return_for_remarks`, `2=save_data`
- Leave DT classes: `0=route_to_department_head`, `1=route_to_hr`, `2=require_rejection_reason`, `3=completed`
